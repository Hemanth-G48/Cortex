from datetime import datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ScheduleEventBase(BaseModel):
    title: str
    day_of_week: int  # 0=Mon, 6=Sun
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    color: Optional[str] = None


class ScheduleEventCreate(ScheduleEventBase):
    user_id: int


class ScheduleEventUpdate(BaseModel):
    title: Optional[str] = None
    day_of_week: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    color: Optional[str] = None


class ScheduleEventResponse(ScheduleEventBase):
    id: int
    user_id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
