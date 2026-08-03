import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventBase(BaseModel):
    title: str
    time: Optional[datetime.time] = None
    date: datetime.date
    location: Optional[str] = None
    is_completed: bool = False


class EventCreate(EventBase):
    user_id: int


class EventUpdate(BaseModel):
    title: Optional[str] = None
    time: Optional[datetime.time] = None
    date: Optional[datetime.date] = None
    location: Optional[str] = None
    is_completed: Optional[bool] = None
    user_id: Optional[int] = None


class EventResponse(EventBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
