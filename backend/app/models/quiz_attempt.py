"""Quiz attempt model for tracking student quiz submissions."""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, func
from app.database import Base


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    answers = Column(JSON, nullable=False, default=list)
    score = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
