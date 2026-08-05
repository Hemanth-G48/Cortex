"""Notification model (STUDENT-PLANAR G10): in-app messages for teacher broadcasts."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(30), default="broadcast")
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=True)
    ref_type = Column(String(30), nullable=True)  # assignment | course | todo | book | schedule
    ref_id = Column(Integer, nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
