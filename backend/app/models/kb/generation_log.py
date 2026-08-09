"""KbGenerationLog model — the shared Phase 4 generation budget meter.

Every *real* LLM generation (summary, explanation, note quiz, flashcard
candidates, quality suggestions, brain-dump split) appends one row so the
``KB_DAILY_GEN_LIMIT`` cap can be enforced uniformly across features. The
deterministic fallback paths never log a row — offline/disabled-AI use is
budget-exempt (mirrors the ``SUMMARY_DAILY_LIMIT`` demo exemption).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func

from app.database import Base


class KbGenerationLog(Base):
    __tablename__ = "kb_generation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # summary | explain | quiz | flashcards | quality | split
    kind = Column(String(30), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_kb_generation_logs_user_day", "user_id", "created_at"),
    )
