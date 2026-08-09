"""KbQualitySuggestion model — actionable note-improvement proposals (Idea 39,
phrase 85).

LLM (or heuristic) suggestions like "split this note", "add a definition of X",
"link to Y" are stored per document with ``status`` pending | dismissed so the
frontend can show a work-list without re-generating.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class KbQualitySuggestion(Base):
    __tablename__ = "kb_quality_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    # e.g. "split", "define", "link", "expand", "tag"
    action = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    # pending | dismissed
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_kb_quality_suggestions_user_status", "user_id", "status"),
    )
