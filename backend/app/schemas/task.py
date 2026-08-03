import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TaskBase(BaseModel):
    title: str
    subject_tag: Optional[str] = None
    priority_tag: Optional[str] = None
    priority_quadrant: Optional[str] = None  # Urgent/Important | Important/Not Urgent | Urgent/Not Important | Not Important/Not Urgent
    due_date: Optional[datetime.date] = None
    status: str = "Not started"
    project_id: Optional[int] = None


class TaskCreate(TaskBase):
    user_id: int


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    subject_tag: Optional[str] = None
    priority_tag: Optional[str] = None
    priority_quadrant: Optional[str] = None
    due_date: Optional[datetime.date] = None
    status: Optional[str] = None
    project_id: Optional[int] = None
    user_id: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ReminderBase(BaseModel):
    title: str
    time: Optional[datetime.time] = None
    date: datetime.date
    is_completed: bool = False


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    time: Optional[datetime.time] = None
    date: Optional[datetime.date] = None
    is_completed: Optional[bool] = None


class ReminderResponse(ReminderBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ScheduleBase(BaseModel):
    day: str
    time_slot: str
    subject_name: str
    color: Optional[str] = None


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleResponse(ScheduleBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
