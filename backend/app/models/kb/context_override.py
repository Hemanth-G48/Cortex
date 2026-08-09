"""ContextOverride model — the Phase 10 per-user context bundle override (Idea 95).

The context bundle (active subject, deadlines, recent topics) is derived
automatically, but the user can pin values (e.g. "my active subject is DSA").
One row per user; ``data_json`` holds the pinned fields (``active_subject_id``,
``active_subject_name``). Per-user privacy is guaranteed by the user_id FK.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, func

from app.database import Base


class ContextOverride(Base):
    __tablename__ = "kb_context_overrides"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, unique=True)
    # JSON: {active_subject_id?, active_subject_name?}
    data_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)
