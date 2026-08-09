"""UserSkill model — mastery-derived skill profile (Idea 70)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Skill id from the seeded taxonomy (backend/app/data/skills.json).
    skill_id = Column(String(120), nullable=False, index=True)
    # 1–5 (phrase 95: derived from contributing-topic mastery).
    level = Column(Integer, default=1)
    # 0–1 aggregated mastery across contributing topics.
    mastery = Column(Float, default=0.0)
    # JSON: [{topic_id, topic_name, score}]
    contributing_topics = Column(Text, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )
