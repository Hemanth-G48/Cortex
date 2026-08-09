"""Embedding pipeline for the Knowledge Core (Second Brain Phase 2, Idea 11–12).

Provides the source-of-truth write path for chunk embeddings,
index sync from the database, and per-user stats.

Functions:
- ``embed_document_chunks`` — embed a doc's chunks, writing KbEmbedding rows.
- ``sync_index`` — rebuild the active store from kb_embeddings rows.
- ``stats`` — per-user Knowledge Core statistics.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbEdge, KbEmbedding, KbTag, KbConcept
from app.services import embeddings
from app.services.kb import KbService, utcnow
from app.services.vector_store import get_store

logger = logging.getLogger(__name__)


def embed_document_chunks(db: Session, user_id: int, doc_id: int) -> dict:
    """Embed all un-embedded chunks of a document in a single transaction.

    Skips chunks whose ``content_hash`` already has an embedding row
    (cache hit).  Enforces the per-day embedding budget; falls back
    to the deterministic local embedder when the provider is
    unavailable.  Writes ``KbEmbedding`` rows and the chunk rows in
    the same transaction (phrase 17).  Sets ``doc.embedding_dirty = False``
    on success.

    Returns ``{"embedded": n, "skipped": n, "total": n}``.
    """
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == doc_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        return {"embedded": 0, "skipped": 0, "total": 0}

    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc_id, KbChunk.user_id == user_id)
        .order_by(KbChunk.seq)
        .all()
    )

    embedded = 0
    skipped = 0
    total = len(chunks)

    # Collect content hashes that already have embeddings for this user.
    existing_hashes: set[str] = set()
    if chunks:
        chunk_ids = [c.id for c in chunks]
        existing = (
            db.query(KbEmbedding.content_hash)
            .filter(
                KbEmbedding.user_id == user_id,
                KbEmbedding.chunk_id.in_(chunk_ids),
            )
            .all()
        )
        existing_hashes = {row.content_hash for row in existing if row.content_hash}

    texts_to_embed: list[str] = []
    chunk_indices: list[int] = []  # index into chunks list

    for idx, chunk in enumerate(chunks):
        h = embeddings.embedding_hash(chunk.content)
        if h in existing_hashes:
            skipped += 1
            continue
        texts_to_embed.append(chunk.content)
        chunk_indices.append(idx)

    if not texts_to_embed:
        doc.embedding_dirty = False
        db.add(doc)
        db.commit()
        return {"embedded": 0, "skipped": skipped, "total": total}

    # Route through the active backend chain (provider → fastembed → hash).
    # Budget is enforced inside backend_embed for the provider leg only;
    # fastembed/hash rows are marked budget-exempt.
    # force_local=True skips the provider (omniroute) and goes directly to local embedding.
    vectors, model = embeddings.backend_embed(
        texts_to_embed, db=db, user_id=user_id, budget_check=True, force_local=True
    )

    dim = settings.EMBEDDINGS_DIM
    now = utcnow()

    for i, vec in enumerate(vectors):
        chunk = chunks[chunk_indices[i]]
        h = embeddings.embedding_hash(chunk.content)
        row = KbEmbedding(
            user_id=user_id,
            chunk_id=chunk.id,
            model=model,
            dim=dim,
            content_hash=h,
            vector=KbService.json_dumps(vec),
            created_at=now,
        )
        db.add(row)
        embedded += 1

    doc.embedding_dirty = False
    db.add(doc)
    db.commit()

    return {"embedded": embedded, "skipped": skipped, "total": total}


def embed_dirty_batch(
    db: Session,
    user_id: int,
    doc_ids: list[int] | None = None,
    batch_size: int = 512,
) -> dict:
    """Embed every pending chunk of dirty documents in large GPU-friendly batches.

    The reindex job runs this **once** before the per-document stages so the
    local fastembed (onnxruntime-GPU) model sees big batches (hundreds of
    texts) instead of one call per document with 1-4 chunks — that is what
    actually keeps the GPU busy. Provider budget is still enforced for the
    provider leg (fastembed/local rows are budget-exempt, so offline/GPU
    embedding never hits the cap).

    Skips chunks whose ``content_hash`` already has an embedding row (cache
    hit), clears ``embedding_dirty`` on every processed document, and commits
    once at the end.

    Returns ``{"docs": n, "chunks": n, "embedded": n, "skipped": n, "batches": n}``.
    """
    query = db.query(KbDocument).filter(
        KbDocument.user_id == user_id,
        KbDocument.embedding_dirty == True,  # noqa: E712
    )
    if doc_ids is not None:
        query = query.filter(KbDocument.id.in_(doc_ids))
    docs = query.order_by(KbDocument.id.asc()).all()
    if not docs:
        return {"docs": 0, "chunks": 0, "embedded": 0, "skipped": 0, "batches": 0}

    doc_ids_set = {d.id for d in docs}
    chunks = (
        db.query(KbChunk)
        .filter(
            KbChunk.user_id == user_id,
            KbChunk.document_id.in_(doc_ids_set),
        )
        .order_by(KbChunk.document_id.asc(), KbChunk.seq.asc())
        .all()
    )

    # Content hashes that already have an embedding row for this user.
    existing_hashes: set[str] = set()
    if chunks:
        chunk_ids = [c.id for c in chunks]
        existing = (
            db.query(KbEmbedding.content_hash)
            .filter(
                KbEmbedding.user_id == user_id,
                KbEmbedding.chunk_id.in_(chunk_ids),
            )
            .all()
        )
        existing_hashes = {row.content_hash for row in existing if row.content_hash}

    # (chunk, text, hash) triples that still need a vector.
    pending: list[tuple[KbChunk, str, str]] = []
    for chunk in chunks:
        h = embeddings.embedding_hash(chunk.content)
        if h in existing_hashes:
            continue
        pending.append((chunk, chunk.content, h))

    embedded = 0
    batches = 0
    dim = settings.EMBEDDINGS_DIM
    now = utcnow()

    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        texts = [content for _, content, _ in batch]
        # force_local=True skips the provider (omniroute) and goes directly to local embedding.
        vectors, model = embeddings.backend_embed(
            texts, db=db, user_id=user_id, budget_check=True, force_local=True
        )
        batches += 1
        for (chunk, _, h), vec in zip(batch, vectors):
            row = KbEmbedding(
                user_id=user_id,
                chunk_id=chunk.id,
                model=model,
                dim=dim,
                content_hash=h,
                vector=KbService.json_dumps(vec),
                created_at=now,
            )
            db.add(row)
            embedded += 1
        # Commit less frequently for GPU workloads to reduce DB overhead.
        # Commit every 3 batches instead of every batch - this balances
        # performance with data safety for large GPU batches.
        if batches % 3 == 0 or start + batch_size >= len(pending):
            db.commit()

    for doc in docs:
        doc.embedding_dirty = False
        db.add(doc)
    db.commit()

    return {
        "docs": len(docs),
        "chunks": len(chunks),
        "embedded": embedded,
        "skipped": len(chunks) - len(pending),
        "batches": batches,
    }


def sync_index(db: Session, user_id: int) -> dict:
    """Rebuild the active vector store from kb_embeddings rows for a user.

    Idempotent — clears the store then re-adds every vector.
    The file store is saved to disk so a fresh instance (post-restart)
    picks up the same data (phrase 19).

    Returns ``{"vectors": n, "dim": d}``.
    """
    store = get_store()
    store.clear()

    rows = (
        db.query(KbEmbedding)
        .filter(KbEmbedding.user_id == user_id)
        .all()
    )

    dim = settings.EMBEDDINGS_DIM
    ids: list[str] = []
    vectors: list[list[float]] = []

    for row in rows:
        vec = KbService.json_loads(row.vector)
        if vec is None or not isinstance(vec, list):
            continue
        # Normalize dimension to match the configured dim.
        vec = list(vec)
        if len(vec) > dim:
            vec = vec[:dim]
        elif len(vec) < dim:
            vec = vec + [0.0] * (dim - len(vec))
        ids.append(f"chunk:{row.chunk_id}")
        vectors.append(vec)

    if ids:
        store.add(ids, vectors)

    # Persist if the store is file-backed (no-op for in-memory).
    if hasattr(store, "save"):
        store.save()

    return {"vectors": len(ids), "dim": dim}


def stats(db: Session, user_id: int) -> dict:
    """Per-user Knowledge Core statistics (phrase 20).

    Returns a dict matching ``KbStatsResponse`` fields.
    """
    document_count = db.query(KbDocument).filter(KbDocument.user_id == user_id).count()
    chunk_count = db.query(KbChunk).filter(KbChunk.user_id == user_id).count()
    embedding_count = db.query(KbEmbedding).filter(KbEmbedding.user_id == user_id).count()

    # Distinct documents that have at least one embedding.
    embedded_documents = (
        db.query(KbChunk.document_id)
        .join(KbEmbedding, KbChunk.id == KbEmbedding.chunk_id)
        .filter(KbEmbedding.user_id == user_id)
        .distinct()
        .count()
    )

    tag_count = db.query(KbTag).filter(KbTag.user_id == user_id).count()
    edge_count = db.query(KbEdge).filter(KbEdge.user_id == user_id).count()
    duplicate_count = (
        db.query(KbEdge)
        .filter(KbEdge.user_id == user_id, KbEdge.relation == "DUPLICATE_OF")
        .count()
    )

    total_tokens = (
        db.query(func.sum(KbChunk.token_estimate))
        .scalar()
    ) or 0

    budget = embeddings.embedding_budget(db, user_id)
    embeddings_today = budget["today"]
    embeddings_limit = budget["limit"]

    dirty_documents = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.embedding_dirty == True)
        .count()
    )

    concept_count = db.query(KbConcept).filter(KbConcept.user_id == user_id).count()

    return {
        "document_count": document_count,
        "chunk_count": chunk_count,
        "embedding_count": embedding_count,
        "embedded_documents": embedded_documents,
        "tag_count": tag_count,
        "concept_count": concept_count,
        "edge_count": edge_count,
        "duplicate_count": duplicate_count,
        "total_tokens": total_tokens,
        "embeddings_today": embeddings_today,
        "embeddings_limit": embeddings_limit,
        "inferences_today": 0,
        "inference_limit": settings.KB_INFER_DAILY_BUDGET,
        "dirty_documents": dirty_documents,
    }