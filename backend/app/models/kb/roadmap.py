"""Roadmap model — versioned week-by-week study plans (Phase 5, Idea 47).

Each generation inserts a new row; the newest ``active`` row is the current
plan. ``plan_json`` holds ``{"weeks": [{week, topic_ids, topics, est_mins}]}``.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("curriculum_subjects.id"), nullable=False, index=True)
    version = Column(Integer, default=1)
    # draft | active | archived
    status = Column(String(20), default="active", index=True)
    plan_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
