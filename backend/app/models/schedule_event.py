from sqlalchemy import Column, Integer, String, Time, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class ScheduleEvent(Base):
    __tablename__ = "schedule_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    event_type = Column(String(50), nullable=True)  # "class", "social", "health", "work", ...
    location = Column(String(200), nullable=True)
    reference_type = Column(String(50), nullable=True)  # "quest", "mission", "task"
    reference_id = Column(Integer, nullable=True)
    color = Column(String(20), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
