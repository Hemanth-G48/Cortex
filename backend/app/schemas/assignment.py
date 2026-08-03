from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class AssignmentBase(BaseModel):
    title: str
    description: Optional[str] = None
    course_id: int
    due_date: date
    status: str = "Not started"


class AssignmentCreate(AssignmentBase):
    pass


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
