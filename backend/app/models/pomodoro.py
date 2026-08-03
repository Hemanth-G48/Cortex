from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey

from app.database import Base


class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    completed = Column(Boolean, default=False)
    task_description = Column(String(500), nullable=True)
    # Gamified Habit Tracker (Phase 6)
    mode = Column(String(10), default="Focus")  # Focus / Break
