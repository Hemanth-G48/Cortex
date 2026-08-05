"""Quiz model for AI-generated unit quizzes."""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func
from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("curriculum_units.id"), nullable=False)
    questions = Column(JSON, nullable=False, default=list)
    difficulty = Column(String(20), nullable=False, default="medium")
    created_at = Column(DateTime, server_default=func.now())
