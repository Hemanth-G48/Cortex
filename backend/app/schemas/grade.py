from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class GradeBase(BaseModel):
    course_id: int
    assignment_id: Optional[int] = None
    title: str = "Assignment"
    points_earned: float = 0.0
    points_possible: float = 0.0
    category_id: Optional[int] = None
    date: Optional[date] = None


class GradeCreate(GradeBase):
    pass


class GradeResponse(GradeBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CourseWeightBase(BaseModel):
    course_id: int
    name: str
    weight: float = 0.0


class CourseWeightCreate(CourseWeightBase):
    pass


class CourseWeightUpdate(BaseModel):
    name: Optional[str] = None
    weight: Optional[float] = None


class CourseWeightResponse(CourseWeightBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class GradeCalculateRequest(BaseModel):
    course_id: int


class GradeCalculateResponse(BaseModel):
    course_id: int
    percentage: Optional[float] = None
    letter_grade: Optional[str] = None
    is_weighted: bool = False
    total_earned: Optional[float] = None
    total_possible: Optional[float] = None
    grade_count: int = 0


class NeededOnFinalRequest(BaseModel):
    current_pct: float
    final_weight_pct: float = 30.0
    desired_pct: float = 90.0


class NeededOnFinalResponse(BaseModel):
    needed_pct: float


class GPACourse(BaseModel):
    course_id: int
    title: str
    credits: int
    percentage: Optional[float] = None
    letter_grade: Optional[str] = None
    gpa: Optional[float] = None


class GPAResponse(BaseModel):
    gpa: Optional[float] = None
    courses: list[GPACourse]
