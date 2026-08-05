from sqlalchemy import Column, Integer, String, Time, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    time = Column(Time, nullable=True)
    date = Column(Date, nullable=False)
    location = Column(String(200), nullable=True)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    google_id = Column(String(100), nullable=True)
