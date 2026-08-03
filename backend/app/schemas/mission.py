from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MissionBase(BaseModel):
    title: str
    description: Optional[str] = None
    mission_type: Optional[str] = None
    priority: str = "Medium"
    status: str = "Not started"
    due_date: Optional[date] = None
    xp_reward: int = 100
    linked_quests: Optional[str] = None


class MissionCreate(MissionBase):
    user_id: int


class MissionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    mission_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    xp_reward: Optional[int] = None
    linked_quests: Optional[str] = None


class MissionResponse(MissionBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class MissionTaskBase(BaseModel):
    mission_id: int
    title: str
    completed: bool = False
    sort_order: int = 0


class MissionTaskCreate(MissionTaskBase):
    pass


class MissionTaskUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None
    sort_order: Optional[int] = None


class MissionTaskResponse(MissionTaskBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
