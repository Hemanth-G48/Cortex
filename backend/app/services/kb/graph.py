"""Knowledge-graph helpers (Idea 16, phrases 51-58).

**Responsibility (audit M8):** this module owns *graph construction and
edge vocabulary* — creating/querying ``KbEdge`` rows (wikilinks, MENTIONS,
RELATED), the canonical relation vocabulary (``RELATION_VOCAB``), and
concept/document link aggregation. Sibling module ``connect.py`` owns
*suggestion ranking* — deciding which links are worth proposing for a newly
ingested note. Keep ranking heuristics out of here; keep edge mechanics out
of there.

Every function is user-scoped — ``user_id`` filters all queries.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbConcept, KbDocument, KbDocumentTag, KbEdge, KbTag
from app.schemas.kb import KbGraphEdge, KbGraphNode, KbGraphResponse
from app.services.kb import KbService, utcnow

logger = logging.getLogger(__name__)

# Relation vocabulary (phrase 51).
RELATION_VOCAB = {
    "WIKILINK", "BACKLINK", "CITES", "MENTIONS", "RELATED",
    "SHARES_CONCEPT", "SYNONYM_OF", "DEPENDS_ON", "DUPLICATE_OF",
}

# Regex for [[target]] wikilinks — captures the target, optional section
# anchor (#...), and optional display alias (|...).
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(#[^\]|]*)?(\|[^\]]*)?\]\]")


def parse_wikilinks(text: str) -> list[str]:
    """Extract wikilink targets from ``text``.

    Strips section anchors (``#...``) and display aliases (``|...``),
    trims whitespace, and drops empty results.

    Examples matched:
        [[Note name]]           → "Note name"
        [[Folder/Note]]         → "Folder/Note"
        [[Note#Section]]        → "Note"
        [[Note|Alias]]          → "Note"
        [[Note#Sec|Alias]]      → "Note"
    """
    targets: list[str] = []
    for raw in WIKILINK_RE.findall(text):
        # raw[0] is the target path before any # or |
        target = raw[0].strip()
        if target:
            targets.append(target)
    return targets


def add_edge(
    db: Session,
    user_id: int,
    source_document_id: int,
    *,
    target_document_id: int | None = None,
    relation: str = "RELATED",
    weight: float = 1.0,
    provenance: str = "auto",
    target_type: str = "document",
    target_concept_id: int | None = None,
    overwrite: bool = True,
) -> KbEdge | None:
    """Upsert a ``KbEdge`` for ``user_id``.

    Dedupe key: ``(user_id, source_document_id, target_document_id,
    target_concept_id, relation)``.  When ``overwrite=True`` an existing
    row is updated in place (weight/provenance refreshed) instead of
    inserting a duplicate.  Returns the edge, or ``None`` when the weight
    is below ``KB_EDGE_MIN_WEIGHT`` or the target cannot be resolved.
    """
    if weight < settings.KB_EDGE_MIN_WEIGHT:
        return None

    if target_document_id is None and target_concept_id is None:
        return None

    # Normalise relation to uppercase.
    relation = relation.upper()
    if relation not in RELATION_VOCAB:
        relation = "RELATED"

    existing = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == source_document_id,
            KbEdge.target_document_id == target_document_id,
            KbEdge.target_concept_id == target_concept_id,
            KbEdge.relation == relation,
        )
        .first()
    )

    if existing:
        if overwrite:
            existing.weight = weight
            existing.provenance = provenance
            existing.target_type = target_type
            db.add(existing)
            db.flush()
        return existing

    edge = KbEdge(
        user_id=user_id,
        source_document_id=source_document_id,
        target_document_id=target_document_id,
        relation=relation,
        weight=weight,
        provenance=provenance,
        target_type=target_type,
        target_concept_id=target_concept_id,
    )
    db.add(edge)
    db.flush()
    return edge


def _normalise_path(path_rel: str) -> str:
    """Strip leading ``./`` and trailing ``.md`` for wikilink resolution."""
    normalised = path_rel.lstrip("./")
    if normalised.endswith(".md"):
        normalised = normalised[:-3]
    return normalised


def _resolve_document_by_path(
    db: Session, user_id: int, target_path: str
) -> KbDocument | None:
    """Try to match a wikilink target to a ``KbDocument``.

    First compares normalised ``path_rel`` (strip ``./`` / ``.md``),
    then falls back to an exact title match.  Both comparisons are
    case-insensitive.
    """
    target_normalised = _normalise_path(target_path)

    # Match on normalised path_rel (strip .md from stored path too).
    doc = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.path_rel.is_not(None),
        )
        .all()
    )
    for d in doc:
        if _normalise_path(d.path_rel or "").lower() == target_normalised.lower():
            return d

    # Fall back to case-insensitive title match.
    doc = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.title.ilike(target_normalised),
        )
        .first()
    )
    return doc


def build_wikilink_edges(
    db: Session, user_id: int, doc: KbDocument, backlinks: bool = True
) -> list[KbEdge]:
    """Scan ``doc.extracted_text`` and frontmatter tags for wikilinks.

    For each link target, resolves a ``KbDocument`` by normalised
    ``path_rel`` (strip ``./`` / ``.md``) then exact title match.
    Creates a ``WIKILINK`` edge (provenance ``rule``).  When
    ``backlinks=True`` (default) also creates the symmetric ``BACKLINK``
    edge target→source.
    """
    if not doc.extracted_text:
        return []

    links = parse_wikilinks(doc.extracted_text)

    # Also scan frontmatter tags for wikilinks (tags can contain [[...]]).
    frontmatter = KbService.json_loads(doc.frontmatter_json) or {}
    for tag_val in frontmatter.get("tags", []):
        if isinstance(tag_val, str):
            links.extend(parse_wikilinks(tag_val))

    edges: list[KbEdge] = []
    seen: set[tuple[int, int, str]] = set()

    for target_path in links:
        target = _resolve_document_by_path(db, user_id, target_path)
        if target is None or target.id == doc.id:
            continue

        key = (doc.id, target.id, "WIKILINK")
        if key in seen:
            continue
        seen.add(key)

        edge = add_edge(
            db,
            user_id,
            doc.id,
            target_document_id=target.id,
            relation="WIKILINK",
            weight=1.0,
            provenance="rule",
            target_type="document",
            overwrite=True,
        )
        if edge is not None:
            edges.append(edge)

        if backlinks:
            bkey = (target.id, doc.id, "BACKLINK")
            if bkey not in seen:
                seen.add(bkey)
                bedge = add_edge(
                    db,
                    user_id,
                    target.id,
                    target_document_id=doc.id,
                    relation="BACKLINK",
                    weight=1.0,
                    provenance="rule",
                    target_type="document",
                    overwrite=True,
                )
                if bedge is not None:
                    edges.append(bedge)

    return edges


def link_mentions_edges(db: Session, user_id: int, doc: KbDocument) -> list[KbEdge]:
    """Create ``MENTIONS`` edges from ``doc`` to ``KbConcept`` rows.

    Scans ``doc.extracted_text`` for concept canonical names and aliases;
    the edge weight is the relative mention frequency (count / total
    concepts found).  Independent and idempotent — re-runnable.
    """
    if not doc.extracted_text:
        return []

    concepts = (
        db.query(KbConcept)
        .filter(KbConcept.user_id == user_id)
        .all()
    )
    if not concepts:
        return []

    # Build a lookup of all names/aliases → concept.
    name_to_concept: list[tuple[str, KbConcept]] = []
    for concept in concepts:
        name_to_concept.append((concept.canonical_name.lower(), concept))
        aliases = KbService.json_loads(concept.aliases) or []
        for alias in aliases:
            name_to_concept.append((alias.lower(), concept))

    text_lower = doc.extracted_text.lower()
    mention_counts: dict[int, int] = defaultdict(int)
    total_mentions = 0

    for name_lower, concept in name_to_concept:
        count = text_lower.count(name_lower)
        if count > 0:
            mention_counts[concept.id] += count
            total_mentions += count

    if total_mentions == 0:
        return []

    edges: list[KbEdge] = []
    for concept_id, count in mention_counts.items():
        weight = count / total_mentions
        edge = add_edge(
            db,
            user_id,
            doc.id,
            target_concept_id=concept_id,
            relation="MENTIONS",
            weight=round(weight, 4),
            provenance="rule",
            target_type="concept",
            overwrite=True,
        )
        if edge is not None:
            edges.append(edge)

    return edges


def cooccurrence_edges(db: Session, user_id: int) -> list[KbEdge]:
    """Add ``SHARES_CONCEPT`` edges between documents that co-occur in chunks.

    Finds documents that both have ``MENTIONS`` edges to the same concept
    within the same chunk, then computes a Jaccard-like co-occurrence
    weight (shared concepts / union of concepts).  Only documents with
    MENTIONS edges are considered; work is capped per-user.
    """
    # Get all MENTIONS edges for this user, grouped by document.
    mentions = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
        )
        .all()
    )

    if not mentions:
        return []

    # doc_id → set of concept_ids
    doc_concepts: dict[int, set[int]] = defaultdict(set)
    for m in mentions:
        if m.target_concept_id is not None:
            doc_concepts[m.source_document_id].add(m.target_concept_id)

    doc_ids = list(doc_concepts.keys())

    # Existing SHARES_CONCEPT pairs, loaded ONCE.  The old implementation
    # called ``add_edge`` per pair — a SELECT + flush per pair — which made
    # this whole-user pass O(docs²) DB round-trips (6.8M pairs at ~3.7k
    # concept-bearing docs) and effectively hung the reindex / graph sync.
    existing = {
        (r.source_document_id, r.target_document_id)
        for r in db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "SHARES_CONCEPT",
            KbEdge.target_document_id.is_not(None),
            KbEdge.source_document_id.is_not(None),
        )
        .all()
    }

    edges: list[KbEdge] = []
    seen: set[tuple[int, int]] = set()

    for i, a_id in enumerate(doc_ids):
        a_set = doc_concepts[a_id]
        for b_id in doc_ids[i + 1 :]:
            b_set = doc_concepts[b_id]
            shared = a_set & b_set
            if not shared:
                continue
            union = a_set | b_set
            weight = len(shared) / len(union) if union else 0.0
            if weight < settings.KB_EDGE_MIN_WEIGHT:
                continue

            # Ensure source < target for deterministic ordering.
            src, tgt = (a_id, b_id) if a_id < b_id else (b_id, a_id)
            key = (src, tgt)
            if key in seen or key in existing:
                continue
            seen.add(key)
            edges.append(
                KbEdge(
                    user_id=user_id,
                    source_document_id=src,
                    target_document_id=tgt,
                    relation="SHARES_CONCEPT",
                    weight=round(weight, 4),
                    provenance="rule",
                    target_type="document",
                )
            )

    if edges:
        db.add_all(edges)
        db.flush()
    return edges


def neighbors(
    db: Session, user_id: int, doc_id: int, relation: str | None = None
) -> list[dict]:
    """Return both inbound and outbound edges for ``doc_id`` as dicts.

    Each dict has ``id``, ``document_id``/``concept_id``, ``label``,
    ``relation``, ``weight``, ``provenance``, and ``direction``
    (``outbound`` or ``inbound``).  Ordered by ``weight`` descending.
    """
    q = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            (KbEdge.source_document_id == doc_id)
            | (KbEdge.target_document_id == doc_id),
        )
    )
    if relation:
        q = q.filter(KbEdge.relation == relation.upper())

    rows = q.order_by(KbEdge.weight.desc()).all()

    results: list[dict] = []
    for row in rows:
        if row.source_document_id == doc_id:
            direction = "outbound"
            target_id = row.target_document_id
            kind = "document"
            label = None
            if target_id is not None:
                target_doc = (
                    db.query(KbDocument)
                    .filter(KbDocument.id == target_id, KbDocument.user_id == user_id)
                    .first()
                )
                label = target_doc.title if target_doc else None
        else:
            direction = "inbound"
            target_id = row.source_document_id
            kind = "document"
            label = None
            if target_id is not None:
                target_doc = (
                    db.query(KbDocument)
                    .filter(KbDocument.id == target_id, KbDocument.user_id == user_id)
                    .first()
                )
                label = target_doc.title if target_doc else None

        results.append(
            {
                "id": row.id,
                "document_id": target_id if kind == "document" else None,
                "concept_id": row.target_concept_id if row.target_type == "concept" else None,
                "label": label,
                "relation": row.relation,
                "weight": row.weight,
                "provenance": row.provenance,
                "direction": direction,
            }
        )

    return results


def related_docs(db: Session, user_id: int, doc_id: int) -> list[dict]:
    """Return document targets of edges for ``doc_id``.

    Each entry has ``id``, ``title``, ``relation``, ``weight``, and
    ``edge_id`` (the ``KbEdge`` row id, so the UI can delete it).
    Only edges with ``weight >= KB_EDGE_MIN_WEIGHT`` are included.
    """
    q = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == doc_id,
            KbEdge.target_document_id.is_not(None),
            KbEdge.weight >= settings.KB_EDGE_MIN_WEIGHT,
        )
    )

    results: list[dict] = []
    for row in q.order_by(KbEdge.weight.desc()).all():
        target = (
            db.query(KbDocument)
            .filter(KbDocument.id == row.target_document_id, KbDocument.user_id == user_id)
            .first()
        )
        if target is None:
            continue
        results.append(
            {
                "id": target.id,
                "edge_id": row.id,
                "title": target.title or target.path_rel or "",
                "relation": row.relation,
                "weight": row.weight,
            }
        )
    return results


def concepts_of(db: Session, user_id: int, doc_id: int) -> list[dict]:
    """Return MENTIONS concept targets for ``doc_id``.

    Each entry has ``concept_id``, ``name`` (canonical_name), ``weight``,
    and ``edge_id`` (the ``KbEdge`` row id, so the UI can delete it).
    """
    q = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == doc_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
            KbEdge.weight >= settings.KB_EDGE_MIN_WEIGHT,
        )
    )

    results: list[dict] = []
    for row in q.order_by(KbEdge.weight.desc()).all():
        concept = (
            db.query(KbConcept)
            .filter(KbConcept.id == row.target_concept_id, KbConcept.user_id == user_id)
            .first()
        )
        if concept is None:
            continue
        results.append(
            {
                "concept_id": concept.id,
                "edge_id": row.id,
                "name": concept.canonical_name,
                "weight": row.weight,
            }
        )
    return results


def build_graph(
    db: Session,
    user_id: int,
    *,
    source: str | None = None,
    tag: str | None = None,
    concept: str | None = None,
    relation: str | None = None,
    doc_ids: set[int] | None = None,
    limit: int = 200,
) -> KbGraphResponse:
    """Build a graph response with nodes and edges for ``user_id``.

    Filters:
        ``source`` — document source_id (matches KbDocument.source_id).
        ``tag`` — document has a ``document_tags`` join to that tag name.
        ``concept`` — document has a MENTIONS edge to that concept name.
        ``relation`` — edge relation type.
        ``doc_ids`` — restrict to these documents and their incident edges;
            concepts are likewise scoped to those mentioned by the documents
            (used for subject-scoped graphs on course pages).
        ``limit`` — cap nodes returned.

    Nodes with ``id`` formatted as ``"doc:<id>"`` or ``"concept:<id>"``.
    Edges use the same node ``id`` strings for ``source``/``target``.
    Edges below ``KB_EDGE_MIN_WEIGHT`` are dropped.  When ``limit`` is
    exceeded ``truncated=True`` and full counts are reported.
    """
    # ── Collect document candidates ──
    doc_q = db.query(KbDocument).filter(KbDocument.user_id == user_id)

    if source is not None:
        try:
            doc_q = doc_q.filter(KbDocument.source_id == int(source))
        except (ValueError, TypeError):
            pass

    if tag is not None:
        doc_q = doc_q.join(
            KbDocumentTag, KbDocument.id == KbDocumentTag.document_id
        ).join(
            KbTag, KbDocumentTag.tag_id == KbTag.id
        ).filter(KbTag.name == tag)

    if concept is not None:
        doc_q = doc_q.join(
            KbEdge, KbDocument.id == KbEdge.source_document_id
        ).join(
            KbConcept, KbEdge.target_concept_id == KbConcept.id
        ).filter(
            KbEdge.relation == "MENTIONS",
            KbConcept.user_id == user_id,
            KbConcept.canonical_name.ilike(f"%{concept}%"),
        )

    # Apply relation filter to documents that have matching edges.
    if relation is not None:
        rel_upper = relation.upper()
        doc_q = doc_q.join(
            KbEdge,
            (KbDocument.id == KbEdge.source_document_id) | (KbDocument.id == KbEdge.target_document_id),
        ).filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == rel_upper,
        ).distinct()

    all_docs = doc_q.all()

    # ── Collect concept candidates ──
    concept_q = db.query(KbConcept).filter(KbConcept.user_id == user_id)
    if concept is not None:
        concept_q = concept_q.filter(KbConcept.canonical_name.ilike(f"%{concept}%"))

    # When scoping to specific documents, restrict concepts to those they
    # actually mention so unrelated vault concepts never pollute the graph.
    if doc_ids is not None:
        all_docs = [d for d in all_docs if d.id in doc_ids]
        mentioned = {
            r[0]
            for r in db.query(KbEdge.target_concept_id)
            .filter(
                KbEdge.user_id == user_id,
                KbEdge.source_document_id.in_(doc_ids),
                KbEdge.relation == "MENTIONS",
                KbEdge.target_type == "concept",
                KbEdge.target_concept_id.isnot(None),
            )
            .all()
        }
        if mentioned:
            concept_q = concept_q.filter(KbConcept.id.in_(mentioned))
        else:
            concept_q = concept_q.filter(KbConcept.id < 0)  # nothing

    all_concepts = concept_q.all()

    # ── Build node lookup ──
    doc_degree: dict[int, int] = defaultdict(int)
    concept_degree: dict[int, int] = defaultdict(int)

    # Collect all relevant edges
    filtered_doc_ids = {d.id for d in all_docs}
    concept_ids = {c.id for c in all_concepts}

    edge_q = db.query(KbEdge).filter(KbEdge.user_id == user_id)
    if relation is not None:
        edge_q = edge_q.filter(KbEdge.relation == relation.upper())
    if filtered_doc_ids:
        edge_q = edge_q.filter(
            (KbEdge.source_document_id.in_(filtered_doc_ids))
            | (KbEdge.target_document_id.in_(filtered_doc_ids))
        )
    all_edges = edge_q.all()

    for e in all_edges:
        if e.source_document_id in filtered_doc_ids:
            doc_degree[e.source_document_id] += 1
        if e.target_document_id in filtered_doc_ids:
            doc_degree[e.target_document_id] += 1
        if e.target_concept_id in concept_ids:
            concept_degree[e.target_concept_id] += 1

    # Build nodes
    nodes: list[dict] = []
    truncated = len(all_docs) + len(all_concepts) > limit
    total_nodes = len(all_docs) + len(all_concepts)
    total_edges = len(all_edges)

    for doc in all_docs:
        if len(nodes) >= limit:
            break
        nodes.append(
            KbGraphNode(
                id=f"doc:{doc.id}",
                kind="document",
                label=doc.title or doc.path_rel or "",
                doc_type=doc.doc_type,
                status=doc.status,
                degree=doc_degree.get(doc.id, 0),
            ).model_dump()
        )

    for conc in all_concepts:
        if len(nodes) >= limit:
            break
        nodes.append(
            KbGraphNode(
                id=f"concept:{conc.id}",
                kind="concept",
                label=conc.canonical_name,
                degree=concept_degree.get(conc.id, 0),
            ).model_dump()
        )

    # Build edges. When the node list is truncated by ``limit``, only return
    # edges whose BOTH endpoints made it into the returned node set — dangling
    # edges (hundreds/thousands on large subjects) wasted payload and never
    # rendered anyway. ``total_edges`` still reports the full graph count so
    # the “Load more (X nodes, Y edges)” affordance stays truthful.
    returned_node_ids = {n["id"] for n in nodes}
    edges: list[dict] = []
    for e in all_edges:
        if e.weight < settings.KB_EDGE_MIN_WEIGHT:
            continue
        source_id = f"doc:{e.source_document_id}" if e.source_document_id else None
        target_id: str | None = None
        if e.target_document_id is not None:
            target_id = f"doc:{e.target_document_id}"
        elif e.target_concept_id is not None:
            target_id = f"concept:{e.target_concept_id}"

        if source_id is None or target_id is None:
            continue
        if source_id not in returned_node_ids or target_id not in returned_node_ids:
            continue

        edges.append(
            KbGraphEdge(
                source=source_id,
                target=target_id,
                relation=e.relation,
                weight=e.weight,
                provenance=e.provenance,
            ).model_dump()
        )

    # Return a plain dict so service callers can subscript the result;
    # the router's response_model=KbGraphResponse coerces it for the API.
    return KbGraphResponse(
        nodes=nodes,
        edges=edges,
        truncated=truncated,
        total_nodes=total_nodes,
        total_edges=total_edges,
    ).model_dump()
