"""KbChunk model — a semantic chunk of a document (Idea 1 / Idea 7)."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class KbChunk(Base):
    __tablename__ = "kb_chunks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    seq = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    # Absolute char offsets into extracted_text (source highlighting, Idea 7).
    char_start = Column(Integer, default=0)
    char_end = Column(Integer, default=0)
    # Heading context, e.g. "Introduction > Setup".
    heading_path = Column(String(500), nullable=True)
    # ≈ chars/4 — the batching seam for Phase 2 embeddings (Idea 12).
    token_estimate = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_kb_chunks_doc_seq", "document_id", "seq"),
    )

    document = relationship("KbDocument", back_populates="chunks")
