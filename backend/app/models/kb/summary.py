"""KbSummary model — cached structured summaries of vault documents (Idea 31).

One row per ``(user_id, document_id)``; the cache key is the document's
``content_hash`` so a content change invalidates the summary (phrase 4).
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class KbSummary(Base):
    __tablename__ = "kb_summaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    # The generated summary paragraph (TL;DR).
    content = Column(Text, nullable=False, default="")
    # JSON lists — key_points, definitions (term → explanation), open_questions.
    key_points = Column(Text, nullable=True)
    definitions = Column(Text, nullable=True)
    open_questions = Column(Text, nullable=True)
    # AI model that produced this summary (fallbacks store "demo").
    model = Column(String(120), nullable=True)
    # SHA-256 of the source content this summary was generated from.
    content_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "document_id", name="uq_kb_summaries_user_doc"),
        Index("ix_kb_summaries_user_doc", "user_id", "document_id"),
    )
