"""SubjectProfile model — syllabus proposals (Phase 5, Idea 41).

A proposed subject is a *draft* parsed from a syllabus; nothing is written to
the existing curriculum tables until the user confirms it (review-before-write).
``status``: proposed | confirmed | rejected. ``parsed_json`` holds the strict
parse schema from ``syllabus.py`` (units → topics → outcomes → deadlines).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class SubjectProfile(Base):
    __tablename__ = "subject_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    curriculum_subject_id = Column(
        Integer, ForeignKey("curriculum_subjects.id"), nullable=True
    )
    raw_syllabus_text = Column(Text, nullable=True)
    parsed_json = Column(Text, nullable=True)
    # e.g. "Fall 2026" (Idea 43)
    semester = Column(String(30), nullable=True)
    # proposed | confirmed | rejected
    status = Column(String(20), default="proposed", index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def parsed_title(self) -> str | None:
        """Convenience: the parsed syllabus title (Phase 6 plan/exam prep)."""
        import json

        try:
            data = json.loads(self.parsed_json or "{}")
        except (ValueError, TypeError):
            return None
        title = data.get("title") if isinstance(data, dict) else None
        return str(title) if title else None
