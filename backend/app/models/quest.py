from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Quest(Base):
    __tablename__ = "quests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    xp_reward = Column(Integer, default=50)
    status = Column(String(50), default="Not started")
    due_date = Column(Date, nullable=True)

    # RPG Weekly Planner fields
    category = Column(String(100), nullable=True)
    priority = Column(String(20), default="Medium")
    time_estimate = Column(Integer, nullable=True)  # minutes
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class QuestTask(Base):
    __tablename__ = "quest_tasks"

    id = Column(Integer, primary_key=True, index=True)
    quest_id = Column(Integer, ForeignKey("quests.id"))
    title = Column(String(200), nullable=False)
    completed = Column(Boolean, default=False)
