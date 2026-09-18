from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None
    course_id: int
    created_date: date
    pinned: bool = False
    updated_at: Optional[datetime] = None


class NoteCreate(NoteBase):
    pass


class NoteResponse(NoteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class NotePinResponse(BaseModel):
    id: int
    pinned: bool


class GoalBase(BaseModel):
    title: str
    quarter: str
    progress_percentage: float = 0.0
    year: int
    habit_id: Optional[int] = None
    target_date: Optional[date] = None
    is_completed: bool = False
    # Phase 10 (Idea 98) linkage. Surfaced so the Life Planner can show vault
    # mastery for the goal's subject (audit defect #40).
    subject_id: Optional[int] = None
    roadmap_id: Optional[int] = None


class GoalCreate(GoalBase):
    pass


class GoalResponse(GoalBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
