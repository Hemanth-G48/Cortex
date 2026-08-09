"""InterviewSession model — interview prep mode (Idea 65)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Skill id from the skill taxonomy (Idea 70) or a free-form label.
    skill = Column(String(200), nullable=False)
    # beginner | intermediate | advanced
    level = Column(String(20), default="intermediate")
    # JSON: [{question, topic_id, expected, model_solution}]
    questions = Column(Text, nullable=True)
    # JSON: {index: {answer, score, feedback}}
    answers = Column(Text, nullable=True)
    # Aggregate 0–100 across answered questions (phrase 47).
    total_score = Column(Integer, default=0)
    # in_progress | completed
    status = Column(String(20), default="in_progress", index=True)
    created_at = Column(DateTime, server_default=func.now())
