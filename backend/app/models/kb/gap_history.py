"""GapAnalysisHistory model — snapshot log of gap analyses over time.

One row per re-analysis of a scope (a course/subject OR a career goal). The
``course_gap_analysis`` / ``goal_gap_analysis`` tables hold only the *latest*
snapshot; this table keeps the compact history of every analysis so the UI can
show how a subject's gaps changed across re-analyses (new gaps, resolved gaps,
level changes). Rows are appended on every compute/re-analyze and pruned to the
most recent ``HISTORY_CAP`` (25) per scope. Unlike the cache rows, history is
never invalidated by resync/reindex — it is the permanent record of change.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)

from app.database import Base


class GapAnalysisHistory(Base):
    __tablename__ = "gap_analysis_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # course | goal
    scope_type = Column(String(10), nullable=False)
    # Exactly one of these is set, depending on scope_type.
    course_id = Column(Integer, nullable=True, index=True)
    goal_key = Column(String(60), nullable=True, index=True)
    # Compact snapshot (see gap_history service): analyzed_at, counts,
    # coverage, and per-gap / per-strength summaries — enough to diff two
    # snapshots without storing the full (large) analysis payload.
    snapshot_json = Column(Text, nullable=False)
    analyzed_at = Column(DateTime, nullable=False, index=True)

    __table_args__ = (
        Index(
            "ix_gap_history_course",
            "user_id",
            "scope_type",
            "course_id",
            "analyzed_at",
        ),
        Index(
            "ix_gap_history_goal",
            "user_id",
            "scope_type",
            "goal_key",
            "analyzed_at",
        ),
    )
