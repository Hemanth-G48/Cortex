"""KbEmbedding model — persisted chunk embeddings (Phase 2, Idea 12).

The persistent source of truth for the vector index. ``vector`` holds a
JSON-encoded list of floats (portable across the numpy/file backends); a
pgvector column is the prod migration path (import-guarded in the store
backend, not here). Identical chunk text never re-embeds (Idea 11, phrase 7):
``content_hash`` + the ``(user_id, chunk_id)`` uniqueness make the cache.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class KbEmbedding(Base):
    __tablename__ = "kb_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    chunk_id = Column(
        Integer, ForeignKey("kb_chunks.id"), nullable=False, unique=True, index=True
    )
    model = Column(String(100), default="text-embedding-3-small")
    dim = Column(Integer, default=1536)
    # SHA-256 of the chunk content — the embedding cache key (Idea 11, phrase 7).
    content_hash = Column(String(64), nullable=True, index=True)
    # JSON-encoded list[float] (numpy/file backends); pgvector swaps the type.
    vector = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    chunk = relationship("KbChunk")

    __table_args__ = (
        Index("ix_kb_embeddings_user_chunk", "user_id", "chunk_id"),
    )
