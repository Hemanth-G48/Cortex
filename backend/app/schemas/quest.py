from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class QuestBase(BaseModel):
    title: str
    description: Optional[str] = None
    xp_reward: int = 50
    status: str = "Not started"
    due_date: Optional[date] = None
    category: Optional[str] = None
    priority: str = "Medium"
    time_estimate: Optional[int] = None


class QuestCreate(QuestBase):
    user_id: int


class QuestResponse(QuestBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class QuestTaskBase(BaseModel):
    quest_id: int
    title: str
    completed: bool = False


class QuestTaskCreate(QuestTaskBase):
    pass


class QuestTaskResponse(QuestTaskBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
