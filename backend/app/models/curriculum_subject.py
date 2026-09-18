from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CurriculumSubject(Base):
    __tablename__ = "curriculum_subjects"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("curriculum_courses.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False)
    semester = Column(Integer, nullable=True)
    # Display label for the semester (e.g. "Fall 2026"), editable in the DB.
    # When unset the API falls back to formatting ``semester`` (defect #9).
    semester_label = Column(String(50), nullable=True)
    credits = Column(Integer, default=3)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("program_id", "code", name="uq_curriculum_subject_program_code"),
    )

    program = relationship("CurriculumCourse", back_populates="subjects")
    units = relationship("CurriculumUnit", back_populates="subject")
