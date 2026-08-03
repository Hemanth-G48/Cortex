from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    name: str
    avatar: Optional[str] = None
    avatar_class: str = "Wizard"
    current_level: int = 1
    current_streak: int = 0
    total_xp: int = 0
    # Fitness Hub (Phases 1-2)
    current_weight: Optional[float] = None
    initial_weight: Optional[float] = None
    target_weight: Optional[float] = None
    membership_status: str = "Active"
    next_payment_date: Optional[date] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    avatar_class: Optional[str] = None
    current_level: Optional[int] = None
    current_streak: Optional[int] = None
    total_xp: Optional[int] = None
    current_weight: Optional[float] = None
    initial_weight: Optional[float] = None
    target_weight: Optional[float] = None
    membership_status: Optional[str] = None
    next_payment_date: Optional[date] = None


class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
