"""PracticeQuestion model — reviewable AI-generated question bank (Idea 63).

Candidates are generated (``status=pending``), hash-deduped per user, then
human-approved into the reusable bank (``status=approved``) used by mock tests
and adaptive practice (Ideas 64/67).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class PracticeQuestion(Base):
    __tablename__ = "practice_questions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    # JSON list of 4 options (strings).
    options = Column(Text, nullable=True)
    # The correct option's display text (mirrors the quiz model convention).
    answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    # Remember | Understand | Apply | Analyze | Evaluate | Create (Idea 63, phrase 23).
    bloom_level = Column(String(30), nullable=True)
    # E | M | H (Idea 67 tier).
    difficulty = Column(String(1), nullable=True)
    # JSON list of chunk ids the question was derived from.
    source_chunk_ids = Column(Text, nullable=True)
    # pending | approved | rejected (phrase 26).
    status = Column(String(10), default="pending", index=True)
    # Normalized question text hash — dedupe key (phrase 25).
    question_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "question_hash", name="uq_practice_user_hash"),
    )
