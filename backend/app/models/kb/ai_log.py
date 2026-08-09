"""AiLog model — the Phase 10 observability meter (Idea 100, Rule A).

Every AI surface (tutor, agents, grading, explanations, summaries,
recommendations) writes one row per interaction so the platform can report
cost, latency, and quality trends — and the feedback column feeds the
self-improvement loop. ``retrieval`` keeps the chunk-id map for faithfulness
audits; ``faithfulness_score`` is the Phase 10 RAG groundedness gate (Idea 93).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class AiLog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # tutor | agent | grading | explain | summary | recommend | forecast | research
    feature = Column(String(30), nullable=False, index=True)
    request = Column(Text, nullable=True)
    # JSON chunk-id map + retrieval mode (faithfulness audit, Idea 93).
    retrieval = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    latency_ms = Column(Integer, default=0)
    tokens = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)
    # -1 | 0 | 1 — explicit user feedback (thumbs), defaults to 0.
    feedback = Column(Integer, default=0)
    faithfulness_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_ai_logs_user_created", "user_id", "created_at"),
        Index("ix_ai_logs_user_feature", "user_id", "feature"),
    )
