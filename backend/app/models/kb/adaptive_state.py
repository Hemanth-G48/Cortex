"""AdaptiveState model — per-(user, topic) practice difficulty state (Idea 67)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class AdaptiveState(Base):
    __tablename__ = "practice_adaptive_state"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    # Current difficulty tier: E | M | H (phrase 61).
    tier = Column(String(1), default="M", nullable=False)
    # JSON: {tier: {correct, total}} — attempts + accuracy by tier (phrase 62).
    attempts_json = Column(Text, nullable=True)
    # Consecutive correct answers at the current tier (frontend streak).
    streak = Column(Integer, default=0)
    # JSON: {last_correct: bool, last_tier: "E|M|H", updated_at}
    last_result = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_adaptive_user_topic"),
    )
