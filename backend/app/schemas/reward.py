from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RewardBase(BaseModel):
    title: str
    description: Optional[str] = None
    xp_cost: int
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_available: bool = True


class RewardCreate(RewardBase):
    user_id: int


class RewardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    xp_cost: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_available: Optional[bool] = None


class RewardResponse(RewardBase):
    id: int
    user_id: int
    claimed_date: Optional[datetime] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class ClaimRewardResponse(BaseModel):
    reward_id: int
    title: str
    xp_cost: int
    xp_remaining: int
    claimed_at: datetime
