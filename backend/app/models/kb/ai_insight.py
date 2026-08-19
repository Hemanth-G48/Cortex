"""AiInsight model — persisted productivity-insights snapshot (Idea 95).

One row per user: the last AI productivity insight (text + the stats bundle
it was generated from) is stored here so opening the dashboard reads the
saved result instead of re-calling the LLM. It is only regenerated when the
user explicitly clicks Refresh (``force=True``).

Mirrors the save-and-reuse pattern of ``GoalGapAnalysis`` / ``KbSummary``:
compute once on the first request, persist, reuse on every later view.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # The generated insight text (LLM or deterministic fallback).
    text = Column(Text, nullable=False)
    # The stats bundle the insight was generated from (JSON-encoded) — lets the
    # UI show the numbers that produced the insight.
    stats_json = Column(Text, nullable=False, default="{}")
    # True when the text came from the LLM provider (False = fallback).
    ai_used = Column(Boolean, nullable=False, default=False)
    # When the snapshot was computed.
    analyzed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        # One snapshot per user — the service upserts on this key (and the
        # unique constraint guards against concurrent first-load races).
        UniqueConstraint("user_id", name="uq_ai_insights_user"),
    )
