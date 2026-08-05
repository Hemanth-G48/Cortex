from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailyScheduleItemBase(BaseModel):
    date: date
    time_range: str
    activity: str
    category: str = "Study Time"  # School | Study Time | Break
    cat_class: Optional[str] = None
    location: Optional[str] = None
    energy: str = "Medium"  # High | Medium | Low
    e_class: Optional[str] = None
    notes: Optional[str] = None
    done: bool = False


class DailyScheduleItemCreate(DailyScheduleItemBase):
    pass


class DailyScheduleItemUpdate(BaseModel):
    time_range: Optional[str] = None
    activity: Optional[str] = None
    category: Optional[str] = None
    cat_class: Optional[str] = None
    location: Optional[str] = None
    energy: Optional[str] = None
    e_class: Optional[str] = None
    notes: Optional[str] = None
    done: Optional[bool] = None


class DailyScheduleItemResponse(DailyScheduleItemBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DailyScheduleStats(BaseModel):
    date: date
    total: int = 0
    done: int = 0
    ratio: float = 0.0
