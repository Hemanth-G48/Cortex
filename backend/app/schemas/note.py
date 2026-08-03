from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None
    course_id: int
    created_date: date


class NoteCreate(NoteBase):
    pass


class NoteResponse(NoteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GoalBase(BaseModel):
    title: str
    quarter: str
    progress_percentage: float = 0.0
    year: int
    habit_id: Optional[int] = None
    target_date: Optional[date] = None
    is_completed: bool = False


class GoalCreate(GoalBase):
    pass


class GoalResponse(GoalBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
