from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LifeAreaBase(BaseModel):
    name: str
    satisfaction_score: int = 5
    goal: Optional[str] = None
    target_days: Optional[int] = None
    status: str = "In progress"
    description: Optional[str] = None
    image_url: Optional[str] = None
    progress_percent: float = 0.0
    sort_order: int = 0
    # Gamified Habit Tracker (Phase 7)
    total_xp_earned: int = 0


class LifeAreaCreate(LifeAreaBase):
    user_id: int


class LifeAreaUpdate(BaseModel):
    name: Optional[str] = None
    satisfaction_score: Optional[int] = None
    goal: Optional[str] = None
    target_days: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    progress_percent: Optional[float] = None
    sort_order: Optional[int] = None
    total_xp_earned: Optional[int] = None


class LifeAreaResponse(LifeAreaBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
