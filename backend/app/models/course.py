from sqlalchemy import Column, Integer, String, ForeignKey
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
