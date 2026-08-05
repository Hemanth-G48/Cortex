from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CurriculumCourse(Base):
    __tablename__ = "curriculum_courses"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    duration = Column(Integer, default=8)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_curriculum_course_institution_code"),
    )

    institution = relationship("Institution", back_populates="programs")
    subjects = relationship("CurriculumSubject", back_populates="program")
