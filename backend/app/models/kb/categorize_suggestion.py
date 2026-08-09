"""CategorizeSuggestion model — auto-categorization review queue (Idea 81).

One row per proposed folder move for a document. ``status`` is ``pending`` →
``accepted`` (move applied + version-history logged) or ``rejected``. ``rule``
records whether the proposal came from deterministic folder rules or the LLM.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func

from app.database import Base


class CategorizeSuggestion(Base):
    __tablename__ = "categorize_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    # The vault folder/category this document should move into.
    proposed_path = Column(String(1000), nullable=False)
    # rule | ai
    rule = Column(String(10), default="rule")
    # pending | accepted | rejected
    status = Column(String(20), default="pending", index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_categorize_user_status", "user_id", "status"),
    )
