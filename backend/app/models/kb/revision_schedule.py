"""RevisionSchedule model — FSRS spaced repetition per topic (Phase 6, Idea 52).

One row per topic (unique per user+topic). ``apply_review`` in
``app/services/kb/revision.py`` runs the FSRS scheduler (vendored py-fsrs, see
``app/services/srs.py``) and persists the FSRS state fields — ``stability``,
``difficulty``, ``state``, ``step`` — alongside the legacy display columns
``interval_days`` / ``ease`` / ``repetitions`` / ``due_date`` that the API
still returns.

Schema note: ``state`` (FSRS IntEnum: 1 Learning, 2 Review, 3 Relearning) and
``step`` mirror the py-fsrs ``Card`` dataclass so a schedule can be rehydrated
into a ``Card`` and handed back to the scheduler on the next review.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint, func

from app.database import Base


class RevisionSchedule(Base):
    __tablename__ = "revision_schedule"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    interval_days = Column(Integer, default=0)
    # Legacy SM-2 ease factor, kept for display (floored at 1.3). FSRS
    # scheduling uses stability/difficulty instead.
    ease = Column(Float, default=2.5)
    # Consecutive successful reviews (legacy repetitions counter).
    repetitions = Column(Integer, default=0)
    due_date = Column(DateTime, nullable=False, index=True)
    last_reviewed_at = Column(DateTime, nullable=True)

    # ── FSRS state (py-fsrs Card fields, persisted for rehydration) ──
    stability = Column(Float, nullable=True)
    difficulty = Column(Float, nullable=True)
    # py-fsrs State IntEnum: 1 Learning, 2 Review, 3 Relearning.
    state = Column(Integer, nullable=True)
    # Current learning/relearning step index (None once in Review state).
    step = Column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_revision_user_topic"),
    )
