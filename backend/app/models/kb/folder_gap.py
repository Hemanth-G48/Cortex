"""FolderGapAnalysis model — saved per-domain/topic Gap Analysis (one row per user + folder).

Mirrors ``CourseGapAnalysis``: a domain's gap analysis is computed once,
persisted here, and reused on every later visit (``cached: True`` +
``analyzed_at``). Only the explicit Re-analyze action (or a KB reindex, since
the evidence changed) refreshes it — opening a domain page never re-runs the
analysis.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    func,
)

from app.database import Base


class FolderGapAnalysis(Base):
    __tablename__ = "folder_gap_analysis"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    folder_id = Column(Integer, ForeignKey("kb_folders.id"), nullable=False, index=True)
    # Full domain-gaps payload (JSON-encoded) — same actionable-engine shape
    # as course gaps (summary/strengths/gaps/path/next/coverage).
    payload_json = Column(Text, nullable=False)
    analyzed_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "folder_id", name="uq_folder_gap_analysis_user_folder"),
    )
