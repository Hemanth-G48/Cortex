from sqlalchemy import Column, Integer, String, Text, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    mission_type = Column(String(50), nullable=True)
    priority = Column(String(20), default="Medium")
    status = Column(String(50), default="Not started")
    due_date = Column(Date, nullable=True)
    xp_reward = Column(Integer, default=100)
    linked_quests = Column(String(500), nullable=True)  # comma-separated quest ids
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MissionTask(Base):
    __tablename__ = "mission_tasks"

    id = Column(Integer, primary_key=True, index=True)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    title = Column(String(200), nullable=False)
    completed = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
