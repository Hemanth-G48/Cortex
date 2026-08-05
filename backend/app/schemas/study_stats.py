from pydantic import BaseModel


class CourseAnalytics(BaseModel):
    course_id: int
    course_title: str
    total: int
    done: int
    done_ratio: float


class OverallAnalytics(BaseModel):
    total: int
    done: int
    completion_pct: float


class AssignmentAnalyticsResponse(BaseModel):
    per_course: list[CourseAnalytics]
    overall: OverallAnalytics
