"""Attendance model — per-class presence logging (Phase 6, Idea 56).

Unique on ``(user_id, subject_id, class_date)`` so a day can only be marked
once per subject; re-marking toggles/updates the row.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False, index=True)
    class_date = Column(Date, nullable=False, index=True)
    present = Column(Boolean, default=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id", "subject_id", "class_date",
            name="uq_attendance_user_subject_date",
        ),
    )
