from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base

# Mood states the session-design mapping understands.
MOODS = ("stressed", "focused", "relaxed")


class MoodLog(Base):
    __tablename__ = "mood_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, default=1, index=True)
    mood = Column(String(20), nullable=False)  # stressed | focused | relaxed
    energy = Column(Integer, nullable=False, default=3)  # 1..5
    note = Column(Text, nullable=True)
    logged_at = Column(DateTime, server_default=func.now(), index=True)
