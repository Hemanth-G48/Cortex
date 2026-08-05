from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class StudyPlanWeek(BaseModel):
    week: int
    topic: str
    tasks: list[str] = []


class StudyPlanBase(BaseModel):
    subject: str
    exam_date: Optional[str] = None


class StudyPlanCreate(StudyPlanBase):
    weeks: list[StudyPlanWeek] = []


class StudyPlanResponse(StudyPlanBase):
    id: int
    weeks: list[StudyPlanWeek] = []
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
