from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    xp_cost = Column(Integer, nullable=False)
    image_url = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)
    is_available = Column(Boolean, default=True)
    claimed_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
