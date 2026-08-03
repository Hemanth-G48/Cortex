from pydantic import BaseModel, ConfigDict
from typing import Optional


class CourseBase(BaseModel):
    title: str
    image_url: Optional[str] = None
    current_assignment: int = 0
    total_assignments: int = 0
    next_exam: Optional[int] = None
    total_exams: int = 0
    status: str = "Not started"


class CourseCreate(CourseBase):
    user_id: int


class CourseResponse(CourseBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)
