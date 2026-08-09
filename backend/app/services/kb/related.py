"""Related-document inference (Second Brain Phase 2, Idea 17, phrases 61-70).

Everything here is per-user scoped.  Inference is *incremental*: a single
document is compared against the rest of the index (never N²), so the
``GET /documents/{id}/related`` endpoint stays cheap as the vault grows.

Functions:
- ``doc_avg_embedding`` — mean of a document's stored chunk embeddings.
- ``infer_related_for_doc`` — compare one doc against the user's other docs;
  pairs above ``KB_SIM_THRESHOLD`` become ``RELATED`` edges (provenance
  ``auto``, weight = cosine score).  Uses ``graph.add_edge`` for the
  dedupe + overwrite policy (phrase 67).
- ``infer_shared_concepts`` — SHARES_CONCEPT edges for docs sharing concepts
  (reuses ``graph.cooccurrence_edges`` which is idempotent).
- ``related_documents`` — query helper returning a document's related docs
  with relation labels (wraps ``graph.related_docs`` + ``neighbors``).
"""

from __future__ import annotations

import logging

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbEmbedding
from app.services.kb import KbService
from app.services.kb import graph
from app.services.kb import utcnow

logger = logging.getLogger(__name__)


def _decoded(vector) -> list[float] | None:
    """Decode a JSON-encoded embedding row (safe against garbage)."""
    if isinstance(vector, str):
        parsed = KbService.json_loads(vector)
        if isinstance(parsed, list):
            return parsed
        return None
    if isinstance(vector, (list, tuple)):
        return list(vector)
    return None


def doc_avg_embedding(db: Session, user_id: int, doc_id: int) -> list[float] | None:
    """Mean of the document's stored chunk embeddings (phrase 62).

    Returns ``None`` when the document has no embeddings.  Dimension is
    normalized to ``settings.EMBEDDINGS_DIM`` (pad/truncate) so pairs always
    compare cleanly regardless of provider drift.
    """
    rows = (
        db.query(KbEmbedding)
        .join(KbChunk, KbEmbedding.chunk_id == KbChunk.id)
        .filter(
            KbEmbedding.user_id == user_id,
            KbChunk.document_id == doc_id,
        )
        .all()
    )
    vecs: list[list[float]] = []
    dim = settings.EMBEDDINGS_DIM
    for row in rows:
        vec = _decoded(row.vector)
        if not vec:
            continue
        vec = list(vec)
        if len(vec) > dim:
            vec = vec[:dim]
        elif len(vec) < dim:
            vec = vec + [0.0] * (dim - len(vec))
        vecs.append(vec)
    if not vecs:
        return None
    return np.mean(np.asarray(vecs, dtype=np.float32), axis=0).tolist()


def _cosine(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=np.float64)
    vb = np.asarray(b, dtype=np.float64)
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def infer_related_for_doc(db: Session, user_id: int, doc_id: int) -> int:
    """Compare one document against the user's other documents (phrase 64).

    The target document's average embedding is computed once; every other
    document with embeddings is compared to it.  Pairs with cosine >=
    ``KB_SIM_THRESHOLD`` become ``RELATED`` edges (provenance ``auto``,
    weight = cosine).  ``graph.add_edge`` dedupes/overwrites by
    ``(user, source, target, relation)`` so re-runs replace stale edges
    (phrase 67).  Returns the number of edges written.
    """
    target = (
        db.query(KbDocument)
        .filter(KbDocument.id == doc_id, KbDocument.user_id == user_id)
        .first()
    )
    if target is None:
        return 0

    target_vec = doc_avg_embedding(db, user_id, doc_id)
    if target_vec is None:
        return 0

    # All other documents belonging to the user that have embeddings.
    others = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.id != doc_id,
            KbDocument.status != "deleted",
        )
        .all()
    )

    threshold = settings.KB_SIM_THRESHOLD
    written = 0
    for other in others:
        other_vec = doc_avg_embedding(db, user_id, other.id)
        if other_vec is None:
            continue
        score = _cosine(target_vec, other_vec)
        if score < threshold:
            continue
        edge = graph.add_edge(
            db,
            user_id,
            target.id,
            target_document_id=other.id,
            relation="RELATED",
            weight=round(score, 4),
            provenance="auto",
            target_type="document",
            overwrite=True,
        )
        if edge is not None:
            written += 1
    db.commit()
    return written


def infer_shared_concepts(db: Session, user_id: int) -> int:
    """SHARES_CONCEPT edges for documents sharing concepts (phrase 63).

    Delegates to ``graph.cooccurrence_edges`` which is idempotent and
    weight-thresholded by ``KB_EDGE_MIN_WEIGHT``.
    """
    edges = graph.cooccurrence_edges(db, user_id)
    db.commit()
    return len(edges)


def related_documents(
    db: Session,
    user_id: int,
    doc_id: int,
    relation: str | None = None,
    infer: bool = True,
) -> dict:
    """Return a document's related documents (phrase 70).

    When ``infer=True`` (default) the incremental embedding-similarity pass
    runs first, so fresh documents surface related links without a manual
    reindex.  Results combine outbound ``RELATED``/``WIKILINK``/``CITES``
    edges with inbound ``BACKLINK`` neighbors via ``graph.neighbors``,
    deduped by ``(target id, relation)`` so a pair linked by several
    relation types keeps each of them (e.g. inbound WIKILINK + outbound
    BACKLINK between the same two documents).

    Returns ``{"document_id", "related": [...], "method"}`` where each item
    is ``{id, title, relation, weight, provenance, direction}`` sorted by
    weight descending.
    """
    if infer:
        infer_related_for_doc(db, user_id, doc_id)

    neighbors = graph.neighbors(db, user_id, doc_id, relation=relation)
    seen: set[tuple[int, str]] = set()
    items: list[dict] = []
    for n in neighbors:
        target_id = n.get("document_id")
        relation_n = n.get("relation")
        key = (target_id, relation_n)
        if target_id is None or key in seen:
            continue
        seen.add(key)
        title = n.get("label")
        items.append(
            {
                "id": target_id,
                "title": title or "",
                "relation": relation_n,
                "weight": n.get("weight"),
                "provenance": n.get("provenance"),
                "direction": n.get("direction"),
            }
        )

    # Sort by weight desc, then id for determinism.
    items.sort(key=lambda i: (-(i["weight"] or 0.0), i["id"]))
    return {
        "document_id": doc_id,
        "related": items,
        "method": "embedding" if infer else "rule",
    }
