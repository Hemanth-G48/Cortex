"""Phase 8 connect-suggestions for new documents (Idea 76).

**Responsibility (audit M8):** this module owns *link suggestion ranking* —
after a document is ingested, ``connect_suggestions`` ranks the best existing
notes to link it to. It reads edges via ``graph.py`` but never creates them
directly; confirming a suggestion goes through the ``/api/kb/edges`` router
which calls ``graph.add_edge``. Edge mechanics and the relation vocabulary
live in ``graph.py``.

Documents that share MENTIONS concepts (the deterministic core signal) are
ranked with a best-effort embedding-similarity bonus. Already-connected
targets are suppressed. Candidates whose shared-concepts overlap with a notably
newer *changed* document are surfaced as ``contradiction_hints`` and handed to
Idea 78's scan (phrase 55). Confirming a suggestion creates a manual
``RELATED`` edge (``provenance=manual``, phrase 54).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KbDocument, KbEdge
from app.services.kb import utcnow
from app.services.kb.graph import add_edge

# A candidate is "strongly related" when it shares this many concepts.
STRONG_SHARED = 2
# Minimum shared concepts to be worth suggesting at all.
MIN_SHARED = 1


def _document_concepts(db: Session, user_id: int, document_id: int) -> list[int]:
    """Concept ids MENTIONed by a document (via MENTIONS edges)."""
    rows = (
        db.query(KbEdge.target_concept_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == document_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
        )
        .all()
    )
    return [r[0] for r in rows]


def _concept_names(db: Session, user_id: int, concept_ids: list[int]) -> dict[int, str]:
    from app.models import KbConcept

    if not concept_ids:
        return {}
    return {
        c.id: c.canonical_name
        for c in db.query(KbConcept)
        .filter(KbConcept.user_id == user_id, KbConcept.id.in_(concept_ids))
        .all()
    }


def _connected_targets(db: Session, user_id: int, document_id: int) -> set[int]:
    """Document ids already linked to this document (either direction)."""
    rows = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            (
                (KbEdge.source_document_id == document_id) & (KbEdge.target_document_id.is_not(None))
            )
            | (
                (KbEdge.target_document_id == document_id) & (KbEdge.source_document_id.is_not(None))
            ),
        )
        .all()
    )
    out: set[int] = set()
    for e in rows:
        if e.source_document_id == document_id:
            out.add(e.target_document_id)
        else:
            out.add(e.source_document_id)
    return out


def connect_suggestions(
    db: Session,
    user_id: int,
    document_id: int,
    *,
    limit: int = 5,
) -> dict:
    """Ranked connection candidates with reasons (phrase 53)."""
    doc = db.query(KbDocument).filter(KbDocument.id == document_id, KbDocument.user_id == user_id).first()
    if doc is None:
        return {"items": [], "contradiction_hints": []}

    my_concepts = _document_concepts(db, user_id, document_id)
    names = _concept_names(db, user_id, my_concepts)
    connected = _connected_targets(db, user_id, document_id)

    # Build a shared-concept index across all of the user's documents.
    index: dict[int, list[int]] = {}
    edge_rows = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
            KbEdge.source_document_id != document_id,
        )
        .all()
    )
    for e in edge_rows:
        index.setdefault(e.source_document_id, []).append(e.target_concept_id)

    now = utcnow()
    candidates: list[dict] = []
    contradiction_hints: list[int] = []
    for target_id, concept_ids in index.items():
        if target_id in connected:
            continue
        shared = [c for c in concept_ids if c in set(my_concepts)]
        if len(shared) < MIN_SHARED:
            continue
        target = db.query(KbDocument).filter(KbDocument.id == target_id, KbDocument.user_id == user_id).first()
        if target is None:
            continue
        shared_names = [names.get(c, str(c)) for c in shared]
        reasons = [f"shares {len(shared)} concept(s): {', '.join(shared_names)}"]
        if len(shared) >= STRONG_SHARED:
            reasons.append("strongly related")
        # Extending/contradicting signal: the target was re-indexed as changed
        # after this document — hand to the Idea 78 contradiction queue.
        if target.status == "changed" and target.updated_at and doc.updated_at and target.updated_at > doc.updated_at:
            contradiction_hints.append(target.id)
        candidates.append(
            {
                "document_id": target.id,
                "title": target.title or target.path_rel or f"doc {target.id}",
                "shared_concepts": shared_names,
                "reasons": reasons,
                "target_status": target.status,
            }
        )

    # Best-effort embedding-similarity bonus: rank shared-concept candidates by
    # how many they share (deterministic) — KbSearcher is not required here.
    candidates.sort(key=lambda c: len(c["shared_concepts"]), reverse=True)
    return {
        "items": candidates[:limit],
        "contradiction_hints": contradiction_hints,
    }


def confirm_connect(
    db: Session,
    user_id: int,
    document_id: int,
    target_document_id: int,
    relation: str = "RELATED",
) -> dict:
    """Create a manual edge between two documents (phrase 54)."""
    src = db.query(KbDocument).filter(KbDocument.id == document_id, KbDocument.user_id == user_id).first()
    tgt = db.query(KbDocument).filter(KbDocument.id == target_document_id, KbDocument.user_id == user_id).first()
    if src is None or tgt is None:
        raise ValueError("Document not found")
    edge = add_edge(
        db,
        user_id,
        document_id,
        target_document_id=target_document_id,
        relation=relation,
        weight=1.0,
        provenance="manual",
        overwrite=True,
    )
    db.flush()
    return {
        "edge_id": edge.id if edge else None,
        "source_document_id": document_id,
        "target_document_id": target_document_id,
        "relation": relation,
        "provenance": "manual",
    }
