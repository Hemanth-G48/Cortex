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
    # SyllabusAI G12 (Phase 78): optional link to a catalog subject.
    curriculum_subject_id: Optional[int] = None


class CourseCreate(CourseBase):
    user_id: int


class CourseResponse(CourseBase):
    id: int
    user_id: int
    # STUDENT-PLANAR G11 (Phase 76): computed from assignment completion.
    progress_percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)
