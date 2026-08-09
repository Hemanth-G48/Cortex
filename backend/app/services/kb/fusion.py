"""Idea 94 — knowledge-graph + vector fusion.

Two-stage retrieval: vector/hybrid top-k (Phase 3) → graph expansion over
``kb_edges`` (Phase 2) for ``KB_GRAPH_EXPAND_HOPS`` hops. Expansion walks
relation types that carry learning value — ``DEPENDS_ON`` (prerequisites),
``RELATED``, ``SHARES_CONCEPT`` — plus concept ``MENTIONS`` (a hit's concepts
pull in documents that mention them). Expanded neighbors are re-scored as
``graph_proximity × vector_score``, deduped, and capped at
``KB_GRAPH_EXPAND_CAP`` added candidates (perf guard, phrase 40).

Every query is user-scoped; the module is deterministic (no LLM calls).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbEdge
from app.services.kb import KbService

# Relations that add *learning value* when expanded (phrase 32). DUPLICATE_OF
# and self-loops are never expanded.
EXPAND_RELATIONS = ("DEPENDS_ON", "RELATED", "SHARES_CONCEPT", "SYNONYM_OF")
# Concept-mention relations that pull in sibling documents.
MENTION_RELATION = "MENTIONS"


@dataclass
class ExpandedHit:
    """One graph-expanded candidate."""

    chunk_id: int | None  # None when the neighbor has no chunk resolved
    document_id: int
    title: str
    snippet: str
    score: float
    vector_score: float
    hops: int
    via: list[str]  # human-readable expansion labels (phrase 38)


def graph_expand(
    db: Session,
    user_id: int,
    hits: list[dict],
    *,
    hops: int | None = None,
    cap: int | None = None,
) -> list[dict]:
    """Expand a resolved hit list via graph neighbors.

    ``hits`` are unified search items (with ``document_id``). Returns enriched
    items — originals plus expanded neighbors — each with ``sources`` including
    ``"graph:<relation>"`` labels. Never exceeds the cap of *added* candidates.
    """
    hops = settings.KB_GRAPH_EXPAND_HOPS if hops is None else max(1, int(hops))
    cap = settings.KB_GRAPH_EXPAND_CAP if cap is None else max(0, int(cap))
    if not hits or cap == 0:
        return hits

    original_by_doc: dict[int, dict] = {}
    for h in hits:
        if h.get("document_id"):
            original_by_doc[h["document_id"]] = h

    expanded: dict[int, ExpandedHit] = {}
    frontier = set(original_by_doc.keys())
    seen_docs: set[int] = set(original_by_doc.keys())

    for hop in range(1, hops + 1):
        if not frontier or len(expanded) >= cap:
            break
        next_frontier: set[int] = set()
        for doc_id in frontier:
            for neighbor in _neighbor_docs(db, user_id, doc_id):
                ndoc = neighbor["document_id"]
                if ndoc in seen_docs:
                    continue
                seen_docs.add(ndoc)
                if len(expanded) >= cap:
                    break
                vector_score = original_by_doc.get(doc_id, {}).get("score", 0.0)
                prox = max(0.0, float(neighbor.get("weight") or 0.0)) * (0.5 ** (hop - 1))
                score = vector_score * (0.4 + 0.6 * prox)
                existing = expanded.get(ndoc)
                if existing is None or score > existing.score:
                    expanded[ndoc] = ExpandedHit(
                        chunk_id=None,
                        document_id=ndoc,
                        title=neighbor.get("title") or f"doc {ndoc}",
                        snippet="",
                        score=round(score, 6),
                        vector_score=round(vector_score, 6),
                        hops=hop,
                        via=[neighbor["label"] or neighbor["relation"]],
                    )
                else:
                    via = neighbor.get("label") or neighbor["relation"]
                    if via not in existing.via:
                        existing.via.append(via)
                next_frontier.add(ndoc)
        frontier = next_frontier

    # Resolve chunk_ids for expanded docs (best-effort, first chunk each).
    if expanded:
        doc_chunk = _first_chunk_map(db, user_id, list(expanded.keys()))
        for ndoc, hit in expanded.items():
            hit.chunk_id = doc_chunk.get(ndoc)

    ranked = sorted(expanded.values(), key=lambda e: (-e.score, e.document_id))[:cap]
    out = list(hits)
    for e in ranked:
        out.append(
            {
                "chunk_id": e.chunk_id,
                "document_id": e.document_id,
                "seq": 0,
                "title": e.title,
                "snippet": e.snippet,
                "score": e.score,
                "mode": "graph_fused",
                "source_path": None,
                "heading_path": None,
                "doc_type": "graph",
                "doc_date": None,
                "char_start": 0,
                "char_end": 0,
                "sources": [f"graph:{v}" for v in e.via],
            }
        )
    return out


def prerequisite_chains(db: Session, user_id: int, document_ids: list[int], limit: int = 4) -> list[str]:
    """Human-readable prerequisite chains for prompt injection (phrase 34).

    ``"B builds on A"`` lines from DEPENDS_ON edges whose postreq document is in
    the candidate set. Deterministic, user-scoped.
    """
    if not document_ids:
        return []
    chains: list[str] = []
    edges = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "DEPENDS_ON",
            KbEdge.target_document_id.in_(document_ids),
        )
        .all()
    )
    for e in edges:
        src = db.query(KbDocument).filter(KbDocument.id == e.source_document_id).first()
        tgt = db.query(KbDocument).filter(KbDocument.id == e.target_document_id).first()
        if src is None or tgt is None:
            continue
        chains.append(
            f"{src.title or 'note'} → {tgt.title or 'note'} (prerequisite)"
        )
        if len(chains) >= limit:
            break
    return chains


def _neighbor_docs(db: Session, user_id: int, doc_id: int) -> list[dict]:
    """Direct document/document neighbors (via doc edges + shared concepts)."""
    out: list[dict] = []
    seen: set[tuple[int, str]] = set()

    edges = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation.in_(EXPAND_RELATIONS),
        )
        .all()
    )
    for e in edges:
        if e.source_document_id == doc_id and e.target_document_id:
            key = (e.target_document_id, e.relation)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "document_id": e.target_document_id,
                    "relation": e.relation,
                    "weight": e.weight or 0.0,
                    "label": f"via: {e.relation.lower().replace('_', ' ')}",
                }
            )
        elif e.target_document_id == doc_id and e.source_document_id:
            key = (e.source_document_id, e.relation)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "document_id": e.source_document_id,
                    "relation": e.relation,
                    "weight": e.weight or 0.0,
                    "label": f"via: {e.relation.lower().replace('_', ' ')}",
                }
            )

    # Concept MENTIONS: documents that mention the same concepts as this doc.
    concept_ids = [
        e.target_concept_id
        for e in db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == MENTION_RELATION,
            KbEdge.source_document_id == doc_id,
            KbEdge.target_concept_id.is_not(None),
        )
        .all()
    ]
    if concept_ids:
        siblings = (
            db.query(KbEdge)
            .filter(
                KbEdge.user_id == user_id,
                KbEdge.relation == MENTION_RELATION,
                KbEdge.target_concept_id.in_(concept_ids),
                KbEdge.source_document_id != doc_id,
            )
            .all()
        )
        for e in siblings:
            key = (e.source_document_id, "MENTIONS")
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "document_id": e.source_document_id,
                    "relation": "MENTIONS",
                    "weight": (e.weight or 0.0) * 0.8,
                    "label": "via: shared concept",
                }
            )
    return out


def _first_chunk_map(db: Session, user_id: int, document_ids: list[int]) -> dict[int, int]:
    """First chunk id per document (cheap approximation for snippet display)."""
    if not document_ids:
        return {}
    from app.models import KbChunk

    rows = (
        db.query(KbChunk.document_id, KbChunk.id)
        .filter(
            KbChunk.user_id == user_id,
            KbChunk.document_id.in_(document_ids),
        )
        .order_by(KbChunk.document_id, KbChunk.seq.asc())
        .all()
    )
    out: dict[int, int] = {}
    for doc_id, chunk_id in rows:
        out.setdefault(doc_id, chunk_id)
    return out


__all__ = ["graph_expand", "prerequisite_chains"]
