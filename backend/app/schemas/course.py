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
    # Folder-derived subjects: metadata read from the folder's index.md
    # frontmatter (description / status / color keys).
    description: Optional[str] = None
    color: Optional[str] = None
    # SyllabusAI G12 (Phase 78): optional link to a catalog subject.
    curriculum_subject_id: Optional[int] = None


class CourseCreate(CourseBase):
    # Single-user app: the owner id is assigned by the router. Accepted but
    # not required for backward-compatible request bodies.
    user_id: Optional[int] = None


class CourseResponse(CourseBase):
    id: int
    user_id: int
    # STUDENT-PLANAR G11 (Phase 76): computed from assignment completion.
    progress_percentage: float = 0.0
    # Origin of the course row: manual | classroom | kb_tag | kb_folder.
    source_type: str = "manual"
    # Set when derived from a Second Brain `course:*` tag.
    kb_tag_id: Optional[int] = None
    # Set when derived from a top-level vault folder (source + folder path).
    kb_source_id: Optional[int] = None
    kb_folder_path: Optional[str] = None
    # Google Classroom course id / course page link.
    google_id: Optional[str] = None
    classroom_url: Optional[str] = None
    # Second Brain docs linked to the `course:*` tag or vault folder (distinct
    # from total_assignments, which counts real Assignment rows).
    kb_document_count: int = 0

    model_config = ConfigDict(from_attributes=True)
