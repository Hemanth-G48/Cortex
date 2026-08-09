"""LearningEvent model — the Phase 6 event spine (Idea 57, phrase 61).

Every study surface logs into this table: reviews (``revision``), exam-prep
task completion (``study``), labs (``lab``), micro-sessions (``session``),
outcome completion (``outcome``), and Phase 7 quiz accuracy (``quiz``). The
``value`` column is numeric (accuracy 0–1, minutes, grade/5, …) so mastery and
progress aggregation stay pure math over rows.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, func

from app.database import Base

EVENT_TYPES = ("study", "quiz", "revision", "lab", "session", "outcome")


class LearningEvent(Base):
    __tablename__ = "learning_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Nullable — global events (weekly summaries, non-topic study) live here too.
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    event_type = Column(String(20), nullable=False, index=True)
    # Accuracy (0–1) | minutes | review grade/5 | 1 for completion markers.
    value = Column(Float, default=1.0)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_learning_user_topic_created", "user_id", "topic_id", "created_at"),
    )
