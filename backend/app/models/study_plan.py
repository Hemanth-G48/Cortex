from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func
from app.database import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    # Phase 6 (Idea 51, phrase 1): the original model had no owner — added so
    # topic-grounded plans are per-user. Nullable: legacy seeded rows survive.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    subject = Column(String(200), nullable=False)
    exam_date = Column(String(20), nullable=True)
    # JSON array: [{"week": 1, "topic": "...", "tasks": [...]}, ...]
    # Phase 6 (Idea 51, phrase 2): typed weeks may carry topic_ids[],
    # chunk_refs[], hours_estimate alongside the display fields.
    weeks_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, server_default=func.now())
