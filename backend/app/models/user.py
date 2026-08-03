from sqlalchemy import Column, Integer, String, DateTime, Float, Date
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    avatar = Column(String(255), nullable=True)
    avatar_class = Column(String(50), default="Wizard")
    current_level = Column(Integer, default=1)
    current_streak = Column(Integer, default=0)
    total_xp = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Fitness Hub (99-phase plan, Phases 1-2): weight-goal + membership
    current_weight = Column(Float, nullable=True)
    initial_weight = Column(Float, nullable=True)
    target_weight = Column(Float, nullable=True)
    membership_status = Column(String(50), default="Active")
    next_payment_date = Column(Date, nullable=True)
