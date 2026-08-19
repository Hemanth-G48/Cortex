from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, UniqueConstraint, func
from app.database import Base


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    image_url = Column(String(500), nullable=True)
    current_assignment = Column(Integer, default=0)
    total_assignments = Column(Integer, default=0)
    next_exam = Column(Integer, nullable=True)
    total_exams = Column(Integer, default=0)
    status = Column(String(50), default="Not started")
    user_id = Column(Integer, ForeignKey("users.id"))
    credits = Column(Integer, default=3)
    google_id = Column(String(100), nullable=True)
    # SyllabusAI G12: optional link to a catalog subject (enrichment only).
    curriculum_subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=True)
    # Origin of the course row: manual | classroom | kb_tag | kb_folder.
    source_type = Column(String(20), default="manual")
    # Set when derived from a Second Brain `course:*` tag (Course ↔ KbTag).
    kb_tag_id = Column(Integer, ForeignKey("kb_tags.id"), nullable=True)
    # Set when derived from a top-level vault folder: which source the folder
    # lives in and the folder's relative path (e.g. "Operating Systems").
    kb_source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=True)
    kb_folder_path = Column(String(500), nullable=True)
    # Google Classroom course page (alternateLink) for classroom-sourced rows.
    classroom_url = Column(String(1000), nullable=True)
    # Number of Second Brain documents linked to the `course:*` tag or the
    # vault folder (distinct from total_assignments, which counts real
    # Assignment rows).
    kb_document_count = Column(Integer, default=0)
    # Folder-derived subjects: description / status / color read from the
    # folder's index.md frontmatter (description, status, color keys).
    description = Column(Text, nullable=True)
    color = Column(String(50), nullable=True)

    # Idempotency guarantees for KB-derived courses: one Course per tag (or
    # per source+folder) per owner. SQLite treats NULLs as distinct, so rows
    # of other origins never collide with these constraints.
    __table_args__ = (
        UniqueConstraint("user_id", "kb_tag_id", name="uq_courses_user_kb_tag"),
        UniqueConstraint("user_id", "kb_source_id", "kb_folder_path", name="uq_courses_user_kb_folder"),
    )


class CourseSyncLog(Base):
    """Latest per-user course-sync run (KB tag derivation diagnostics).

    One row per user, upserted on each run so the UI can explain the last
    sync (counts, sources/documents/tags seen, and any partial failures).
    """

    __tablename__ = "course_sync_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, unique=True)
    created = Column(Integer, default=0)
    updated = Column(Integer, default=0)
    removed = Column(Integer, default=0)
    courses = Column(Integer, default=0)
    sources = Column(Integer, default=0)
    documents = Column(Integer, default=0)
    course_tags = Column(Integer, default=0)
    course_folders = Column(Integer, default=0)
    errors_json = Column(Text, nullable=True)
    synced_at = Column(DateTime, server_default=func.now())


class CourseGapAnalysis(Base):
    """Saved Gap Analysis for one course (one row per user + course).

    Gap Analysis is expensive relative to the page load, and the results are
    meant to persist: a subject's analysis is computed once, stored here, and
    reused on subsequent visits. It is only recomputed when the user explicitly
    re-runs it (``POST /api/courses/{id}/gaps/analyze``) or after a resync
    (the underlying data may have changed, so the cached copy is invalidated).
    """

    __tablename__ = "course_gap_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    # Full ``course_gaps`` payload (JSON-encoded).
    payload_json = Column(Text, nullable=False)
    analyzed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_gap_analysis_user_course"),
    )
