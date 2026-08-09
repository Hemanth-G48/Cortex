"""Topic model — per-subject study topics (Phase 5, Ideas 44/48/49/50).

Topics are extracted from parsed syllabi and human-reviewable (confirm/merge/
reject). ``normalized_name`` is the synonym-folded canonical name (Idea 44,
phrase 34) — Phase 3's gap detection (Idea 28) keys off it, so it must stay
stable. Difficulty/time estimates and outcomes all live on the row.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # The confirmed curriculum subject this topic belongs to (Idea 41 confirm).
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False, index=True)
    unit_id = Column(Integer, ForeignKey("curriculum_units.id"), nullable=True, index=True)

    name = Column(String(200), nullable=False)
    normalized_name = Column(String(200), nullable=False, index=True)
    # Remember | Understand | Apply | Analyze | Evaluate | Create (Idea 44, phrase 37)
    bloom_level = Column(String(30), nullable=True)
    # E | M | H (Idea 48)
    difficulty = Column(String(1), nullable=True)
    difficulty_confidence = Column(Float, default=0.0)
    # Idea 49: first-pass / review / mastery minutes
    first_pass_mins = Column(Integer, default=0)
    review_mins = Column(Integer, default=0)
    mastery_mins = Column(Integer, default=0)
    # Idea 50: JSON list of {text, status (pending|done), completed_at}
    outcomes = Column(Text, nullable=True)
    # pending | confirmed | merged | rejected (Idea 44, phrase 31)
    status = Column(String(20), default="pending", index=True)
    # Phase 6 (Idea 58): mastery 0–1 + weak|medium|strong|unknown,
    # recomputed on learning-event writes (phrase 79).
    mastery_score = Column(Float, default=0.0)
    mastery_classification = Column(String(10), default="unknown", index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id", "subject_id", "normalized_name",
            name="uq_topic_user_subject_name",
        ),
    )
