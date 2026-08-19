"""GoalGapAnalysis model — saved Goal-level Gap Analysis (Phase 8, Idea 72).

One row per ``(user_id, goal_key)``: the goal view of the gap engine is
computed once, stored here, and reused on later visits — the same save-and-
reuse pattern as ``CourseGapAnalysis`` for subjects. It is only recomputed
when the user explicitly re-runs it (``POST /api/kb/gaps/goal/analyze``) or
after a KB reindex (the underlying evidence may have changed, so the cached
copy is invalidated).
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class GoalGapAnalysis(Base):
    __tablename__ = "goal_gap_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Static career-goal key from the gap-engine catalog (e.g. "ctf").
    goal_key = Column(String(60), nullable=False, index=True)
    # Full goal analysis payload (JSON-encoded).
    payload_json = Column(Text, nullable=False)
    analyzed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "goal_key", name="uq_goal_gap_analysis_user_goal"),
    )
