from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(200), nullable=False)
    exam_date = Column(String(20), nullable=True)
    # JSON array: [{"week": 1, "topic": "...", "tasks": [...]}, ...]
    weeks_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, server_default=func.now())
