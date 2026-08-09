from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CurriculumUnit(Base):
    __tablename__ = "curriculum_units"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False)
    unit_number = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    # Phase 5 (Idea 43): string term ("Fall 2026") mirrored from the profile.
    semester = Column(String(20), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("subject_id", "unit_number", name="uq_curriculum_unit_subject_number"),
    )

    subject = relationship("CurriculumSubject", back_populates="units")
