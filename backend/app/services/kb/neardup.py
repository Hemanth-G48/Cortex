"""Near-duplicate detection service (Phase 2, Idea 19, phrases 82-86).

Cosine-similarity over stored ``kb_embeddings`` rows; MinHash via
``datasketch`` is optional (import-guarded).  Every function is
per-user scoped.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    KbChunk,
    KbDocument,
    KbDocumentTag,
    KbEdge,
    KbEmbedding,
    KbVersion,
    User,
)
from app.services.kb import KbService
from app.services.embeddings import local_embed

logger = logging.getLogger(__name__)


def cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors (numpy)."""
    va = np.array(a, dtype=np.float64)
    vb = np.array(b, dtype=np.float64)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def _embeddings_by_document(
    db: Session, user_id: int
) -> dict[int, list[KbEmbedding]]:
    """All of *user_id*'s chunk embeddings, grouped by document id.

    Single batched query — the old implementation built the *full*
    cross-document pair list here, which is O(chunks²) (≈66M pairs at 11.5k
    embeddings) and effectively hung the near-dup scan / reindex / nightly
    auto-duplicates job on any non-trivial vault.
    """
    embeddings = (
        db.query(KbEmbedding)
        .join(KbChunk, KbEmbedding.chunk_id == KbChunk.id)
        .join(KbDocument, KbChunk.document_id == KbDocument.id)
        .filter(
            KbEmbedding.user_id == user_id,
            KbChunk.user_id == user_id,
            KbDocument.user_id == user_id,
        )
        .all()
    )
    by_doc: dict[int, list[KbEmbedding]] = {}
    for emb in embeddings:
        by_doc.setdefault(emb.chunk.document_id, []).append(emb)
    return by_doc


def _normalized_vec(vector, dim: int) -> np.ndarray | None:
    """Decode *vector* and pad/truncate it to *dim*; None when empty."""
    vec = _decoded_vector(vector)
    if not vec:
        return None
    arr = np.asarray(vec, dtype=np.float64)
    if arr.ndim != 1 or arr.size == 0:
        return None
    if arr.size > dim:
        arr = arr[:dim]
    elif arr.size < dim:
        arr = np.concatenate([arr, np.zeros(dim - arr.size)])
    return arr


def _pooled_vector(embs: list[KbEmbedding], dim: int) -> np.ndarray | None:
    """Mean of a document's chunk vectors (pad/truncate to *dim*)."""
    vecs = [
        v
        for v in (_normalized_vec(e.vector, dim) for e in embs)
        if v is not None
    ]
    if not vecs:
        return None
    return np.mean(np.asarray(vecs, dtype=np.float64), axis=0)


def _max_chunk_sim(
    embs_a: list[KbEmbedding],
    embs_b: list[KbEmbedding],
    dim: int,
) -> tuple[float, KbEmbedding | None, KbEmbedding | None]:
    """Exact max chunk-pair cosine between two documents (vectorized).

    Returns ``(max_sim, emb_a, emb_b)`` — the two chunk embeddings that
    achieve the maximum — preserving the original chunk-pair semantics with
    one tiny matmul instead of an O(chunks²) Python loop.
    """
    va_rows = [_normalized_vec(e.vector, dim) for e in embs_a]
    vb_rows = [_normalized_vec(e.vector, dim) for e in embs_b]
    va = np.asarray([v for v in va_rows if v is not None], dtype=np.float64)
    vb = np.asarray([v for v in vb_rows if v is not None], dtype=np.float64)
    if va.size == 0 or vb.size == 0:
        return 0.0, None, None
    na = np.linalg.norm(va, axis=1, keepdims=True)
    nb = np.linalg.norm(vb, axis=1, keepdims=True)
    na[na == 0] = 1.0
    nb[nb == 0] = 1.0
    scores = (va / na) @ (vb / nb).T
    flat = int(np.argmax(scores))
    i, j = divmod(flat, scores.shape[1])
    emb_a = [e for e, v in zip(embs_a, va_rows) if v is not None][i]
    emb_b = [e for e, v in zip(embs_b, vb_rows) if v is not None][j]
    return float(scores[i, j]), emb_a, emb_b


def _existing_dup_keys(db: Session, user_id: int) -> set[frozenset[int]]:
    """All ``DUPLICATE_OF`` doc pairs already recorded for *user_id*.

    One query instead of two per candidate pair (the old hot loop).
    """
    rows = (
        db.query(KbEdge.source_document_id, KbEdge.target_document_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "DUPLICATE_OF",
            KbEdge.source_document_id.is_not(None),
            KbEdge.target_document_id.is_not(None),
            KbEdge.source_document_id != KbEdge.target_document_id,
        )
        .all()
    )
    return {frozenset((s, t)) for s, t in rows}


def _decoded_vector(vector) -> list[float]:
    """Decode a JSON-encoded embedding vector stored in ``kb_embeddings``."""
    if isinstance(vector, str):
        try:
            return json.loads(vector)
        except (ValueError, TypeError):
            return []
    return vector or []


def _skip_existing_duplicate(
    db: Session,
    user_id: int,
    doc_a_id: int,
    doc_b_id: int,
) -> bool:
    """Return True if a DUPLICATE_OF edge already links these two docs."""
    existing = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "DUPLICATE_OF",
            KbEdge.source_document_id == doc_a_id,
            KbEdge.target_document_id == doc_b_id,
        )
        .first()
    )
    if existing is not None:
        return True
    existing = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "DUPLICATE_OF",
            KbEdge.source_document_id == doc_b_id,
            KbEdge.target_document_id == doc_a_id,
        )
        .first()
    )
    return existing is not None


def candidate_pairs(
    db: Session,
    user_id: int,
    method: Optional[str] = None,
) -> list[tuple[KbEmbedding, KbEmbedding, float]]:
    """Return candidate near-duplicate embedding pairs for *user_id*.

    *method* defaults to ``settings.KB_NEARDUP_METHOD``.  Only the
    ``"embedding"`` path is implemented here; MinHash is import-guarded
    and falls back to embedding with a log message.

    Constraints (phrases 82-83):
    - Only compare chunks from **different** documents.
    - Skip pairs already represented by a ``DUPLICATE_OF`` edge.
    - Return only pairs whose cosine similarity is >= the threshold.

    Two-tier scan: a mean-pooled doc×doc cosine matrix (one matmul) narrows
    candidates, then the exact chunk-pair similarity is recomputed for the
    few pairs near the threshold — the O(chunks²) all-pairs list is never
    materialized, so this stays fast as the vault grows.
    """
    method = method or settings.KB_NEARDUP_METHOD

    if method == "minhash":
        # Optional dependency — fall back gracefully.
        try:
            from datasketch import MinHash, MinHashLSH
        except ImportError:
            logger.warning(
                "datasketch not installed; falling back to embedding path for near-dup"
            )
            method = "embedding"

    if method == "embedding":
        threshold = settings.KB_NEARDUP_THRESHOLD
        dim = settings.EMBEDDINGS_DIM
        by_doc = _embeddings_by_document(db, user_id)
        if len(by_doc) < 2:
            return []

        # Two-tier scan (never materializes the O(chunks²) pair list):
        #   1. Mean-pool each doc's chunk vectors and compute the full
        #      doc×doc cosine matrix in one matmul (1569 docs ≈ 2.4M cells).
        #   2. Only pairs near the threshold get the exact chunk-pair recheck.
        doc_ids: list[int] = []
        pooled: list[np.ndarray] = []
        for did in sorted(by_doc):
            p = _pooled_vector(by_doc[did], dim)
            if p is not None:
                doc_ids.append(did)
                pooled.append(p)
        n = len(doc_ids)
        if n < 2:
            return []
        matrix = np.asarray(pooled, dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        sims = (matrix / norms) @ (matrix / norms).T

        existing = _existing_dup_keys(db, user_id)
        pre = threshold - 0.25  # generous pre-filter; exact recheck below
        rows_idx, cols_idx = np.triu_indices(n, k=1)
        order = np.argsort(-sims[rows_idx, cols_idx])

        results: list[tuple[KbEmbedding, KbEmbedding, float]] = []
        for k in order:
            s = float(sims[rows_idx[k], cols_idx[k]])
            if s < pre:
                break  # descending — every remaining pair is below the bar
            a_id = doc_ids[rows_idx[k]]
            b_id = doc_ids[cols_idx[k]]
            if frozenset((a_id, b_id)) in existing:
                continue
            max_sim, emb_a, emb_b = _max_chunk_sim(by_doc[a_id], by_doc[b_id], dim)
            if emb_a is not None and max_sim >= threshold:
                results.append((emb_a, emb_b, max_sim))
        return results

    # Fallback (should not be reached after the import-guard above).
    return []


def scan_duplicates(
    db: Session, user_id: int, commit: bool = True
) -> list[dict]:
    """Scan and record near-duplicate document pairs for *user_id*.

    For each qualifying pair a ``DUPLICATE_OF`` edge is created/upserted:

    - ``source_document_id`` = the later document (higher id) or the one
      with more chunks.
    - ``target_document_id`` = the other (canonical).
    - ``weight`` = cosine similarity.
    - ``provenance`` = ``"auto"``.
    - ``relation`` = ``"DUPLICATE_OF"``.

    Returns the list of created/updated pair dicts:
    ``[{document_id, duplicate_of_id, similarity, method}]``.
    """
    pairs = candidate_pairs(db, user_id)
    threshold = settings.KB_NEARDUP_THRESHOLD
    results: list[dict] = []

    for emb_a, emb_b, sim in pairs:
        doc_a_id = emb_a.chunk.document_id
        doc_b_id = emb_b.chunk.document_id

        # Determine canonical (target) and duplicate (source).
        # The "later" document (higher id) is the duplicate; the earlier
        # one is canonical.  If same id, skip (shouldn't happen).
        if doc_a_id == doc_b_id:
            continue

        if doc_a_id > doc_b_id:
            source_id = doc_a_id
            target_id = doc_b_id
        else:
            source_id = doc_b_id
            target_id = doc_a_id

        # Check again for dedupe (race between candidate_pairs and here).
        if _skip_existing_duplicate(db, user_id, source_id, target_id):
            continue

        # Record via KbService.record_duplicate for the canonical side.
        KbService.record_duplicate(db, user_id, target_id)

        # Create the DUPLICATE_OF edge source→target.
        edge = KbEdge(
            user_id=user_id,
            source_document_id=source_id,
            target_document_id=target_id,
            relation="DUPLICATE_OF",
            weight=sim,
            provenance="auto",
        )
        db.add(edge)

        results.append(
            {
                "document_id": source_id,
                "duplicate_of_id": target_id,
                "similarity": round(sim, 4),
                "method": "embedding",
            }
        )

    if commit:
        db.commit()

    return results


def list_duplicates(
    db: Session, user_id: int, method: Optional[str] = None
) -> list[dict]:
    """Return all ``DUPLICATE_OF`` edges for *user_id* as KbDuplicateItem dicts.

    ``document_id`` is the source (duplicate), ``duplicate_of_id`` is the
    target (canonical), ``similarity`` is the edge weight, ``method`` is
    always ``"embedding"`` for the current implementation.
    """
    _ = method  # reserved for future minhash filtering
    edges = (
        db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "DUPLICATE_OF",
            KbEdge.source_document_id != KbEdge.target_document_id,
        )
        .all()
    )
    return [
        {
            "document_id": e.source_document_id,
            "duplicate_of_id": e.target_document_id,
            "similarity": round(e.weight or 0.0, 4),
            "method": "embedding",
            # KbEdge has no timestamp column; schema field is nullable.
            "created_at": None,
        }
        for e in edges
    ]


def merge_documents(
    db: Session, user_id: int, keep_id: int, merge_ids: list[int]
) -> dict:
    """Merge duplicate documents into *keep_id*.

    Reassigns all per-user references (chunks, edges, document tags,
    versions) from the merged documents to *keep_id*, then deletes the
    merged document rows.  Conservative: only operates on rows owned by
    *user_id*.

    Returns ``{"kept": keep_id, "merged": len(merge_ids)}``.
    """
    # Verify ownership of keep_id.
    keep_doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == keep_id, KbDocument.user_id == user_id)
        .first()
    )
    if keep_doc is None:
        raise ValueError(f"Document {keep_id} not found or not owned by user {user_id}")

    merged_count = 0
    for mid in merge_ids:
        if mid == keep_id:
            continue
        doc = (
            db.query(KbDocument)
            .filter(KbDocument.id == mid, KbDocument.user_id == user_id)
            .first()
        )
        if doc is None:
            continue

        # Reassign chunks.
        db.query(KbChunk).filter(
            KbChunk.document_id == mid, KbChunk.user_id == user_id
        ).update({KbChunk.document_id: keep_id})

        # Reassign edges where the merged doc is source or target.
        db.query(KbEdge).filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == mid,
        ).update({KbEdge.source_document_id: keep_id})
        db.query(KbEdge).filter(
            KbEdge.user_id == user_id,
            KbEdge.target_document_id == mid,
        ).update({KbEdge.target_document_id: keep_id})

        # Reassign document tags.
        db.query(KbDocumentTag).filter(
            KbDocumentTag.document_id == mid, KbDocumentTag.user_id == user_id
        ).update({KbDocumentTag.document_id: keep_id})

        # Reassign versions.
        db.query(KbVersion).filter(
            KbVersion.document_id == mid, KbVersion.user_id == user_id
        ).update({KbVersion.document_id: keep_id})

        # Delete the merged document.
        db.delete(doc)
        merged_count += 1

    db.commit()
    return {"kept": keep_id, "merged": merged_count}


def archive_document(db: Session, user_id: int, doc_id: int) -> dict:
    """Archive a duplicate document by setting its status to ``"archived"``.

    Returns ``{"ok": True}``.
    """
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == doc_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        raise ValueError(f"Document {doc_id} not found or not owned by user {user_id}")
    doc.status = "archived"
    db.add(doc)
    db.commit()
    return {"ok": True}