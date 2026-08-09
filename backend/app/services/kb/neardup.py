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


def _load_embedding_pairs(
    db: Session, user_id: int
) -> list[tuple[KbEmbedding, KbEmbedding]]:
    """Return all (emb_a, emb_b) pairs for different documents belonging to user."""
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
    # Group by document_id
    by_doc: dict[int, list[KbEmbedding]] = {}
    for emb in embeddings:
        doc_id = emb.chunk.document_id
        by_doc.setdefault(doc_id, []).append(emb)

    doc_ids = list(by_doc.keys())
    pairs: list[tuple[KbEmbedding, KbEmbedding]] = []
    for i in range(len(doc_ids)):
        for j in range(i + 1, len(doc_ids)):
            for emb_a in by_doc[doc_ids[i]]:
                for emb_b in by_doc[doc_ids[j]]:
                    pairs.append((emb_a, emb_b))
    return pairs


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
        pairs = _load_embedding_pairs(db, user_id)
        threshold = settings.KB_NEARDUP_THRESHOLD
        results: list[tuple[KbEmbedding, KbEmbedding, float]] = []
        for emb_a, emb_b in pairs:
            # Dedupe: skip if edge already exists.
            if _skip_existing_duplicate(
                db, user_id, emb_a.chunk.document_id, emb_b.chunk.document_id
            ):
                continue
            sim = cosine_sim(_decoded_vector(emb_a.vector), _decoded_vector(emb_b.vector))
            if sim >= threshold:
                results.append((emb_a, emb_b, sim))
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