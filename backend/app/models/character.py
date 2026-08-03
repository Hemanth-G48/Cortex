from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    class_name = Column(String(50), default="Wizard")
    level = Column(Integer, default=1)
    xp = Column(Integer, default=0)
    strength = Column(Integer, default=5)
    agility = Column(Integer, default=5)
    intelligence = Column(Integer, default=5)
    endurance = Column(Integer, default=5)
    current_quests = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
