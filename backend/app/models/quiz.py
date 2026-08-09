"""Quiz model for AI-generated unit quizzes."""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func
from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable since Phase 4 (Idea 33): note-generated quizzes have no
    # curriculum unit. The column was NOT NULL in legacy tables; a one-off
    # SQLite rebuild in ``database.migrate_schema`` relaxes it.
    unit_id = Column(Integer, ForeignKey("curriculum_units.id"), nullable=True)
    questions = Column(JSON, nullable=False, default=list)
    difficulty = Column(String(20), nullable=False, default="medium")
    created_at = Column(DateTime, server_default=func.now())
