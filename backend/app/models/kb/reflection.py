"""Reflection model — the Phase 10 weekly reflection (Idea 98).

One row per ``(user_id, week_start)``: an AI-generated review of the week's
learning events (what worked / what didn't / what to change) with structured
``insights`` for the plan-adjustment trigger (phrase 77).
"""

from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class Reflection(Base):
    __tablename__ = "reflections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Monday of the week this reflection covers (local server week).
    week_start = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    # JSON: {worked[], struggled[], change[], insights[]}
    insights = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_reflections_user_week"),
        Index("ix_reflections_user_week", "user_id", "week_start"),
    )
