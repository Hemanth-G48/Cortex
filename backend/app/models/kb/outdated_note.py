"""OutdatedNote model — outdated-note detection queue (Phase 8, Idea 78).

One row per flagged document. ``reason`` is one of contradiction (an LLM
verdict over a similar-document pair), stale (untouched/unread for
``KB_STALE_DAYS``), or material_changed (a referenced material's content hash
changed). ``evidence_json`` holds detector-specific detail (the paired doc id,
the stale date, the changed hash). ``status`` lifecycle: open → updated |
archived | dismissed.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class OutdatedNote(Base):
    __tablename__ = "outdated_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=False, index=True)
    # contradiction | stale | material_changed
    reason = Column(String(30), nullable=False, index=True)
    evidence_json = Column(Text, nullable=True)
    # open | updated | archived | dismissed
    status = Column(String(20), default="open", index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_outdated_notes_user_status", "user_id", "status"),
    )
