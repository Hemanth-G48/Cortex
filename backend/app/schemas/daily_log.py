import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DailyLogBase(BaseModel):
    date: datetime.date
    time_focused: int = 0  # minutes
    status: str = "active"


class DailyLogCreate(DailyLogBase):
    user_id: int


class DailyLogUpdate(BaseModel):
    date: Optional[datetime.date] = None
    time_focused: Optional[int] = None
    status: Optional[str] = None
    user_id: Optional[int] = None


class DailyLogResponse(DailyLogBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
