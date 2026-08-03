from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class LifeArea(Base):
    __tablename__ = "life_areas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    satisfaction_score = Column(Integer, default=5)
    goal = Column(Text, nullable=True)
    target_days = Column(Integer, nullable=True)
    status = Column(String(50), default="In progress")
    # Gamified Habit Tracker (Phase 7): "All Time XP" per area
    total_xp_earned = Column(Integer, default=0)

    # RPG Weekly Planner fields
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    progress_percent = Column(Float, default=0.0)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
