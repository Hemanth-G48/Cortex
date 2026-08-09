"""Lab model — lab tracking (Phase 6, Idea 55).

``pre_requisite_topic_ids`` is a JSON list of the Phase 5 topic ids that should
be reviewed before the lab (used by the "read before lab" prep feature).
"""

from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class Lab(Base):
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    lab_date = Column(Date, nullable=True, index=True)
    # scheduled | done | missed
    status = Column(String(20), default="scheduled", index=True)
    # JSON list of topic ids to review before the lab.
    pre_requisite_topic_ids = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    submission_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
