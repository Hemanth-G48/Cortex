from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    course_id: Optional[int] = None
    due_date: date
    status: str = "Not started"
    # STUDENT-PLANAR G6 (Phase 37)
    type: str = "Homework"  # Homework | Quiz | Project | Test | Other
    type_color: Optional[str] = None
    time_estimate: Optional[int] = None  # minutes
    file_url: Optional[str] = None


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    course_id: Optional[int] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    type: Optional[str] = None
    type_color: Optional[str] = None
    time_estimate: Optional[int] = None
    file_url: Optional[str] = None


class AssignmentStatusUpdate(BaseModel):
    status: str  # "Not started" | "In progress" | "Completed"


class AssignmentResponse(AssignmentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class ExamBase(BaseModel):
    title: str
    course_id: int
    date: date
    status: str = "Not started"


class ExamCreate(ExamBase):
    pass


class ExamResponse(ExamBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
