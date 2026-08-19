"""KbSource model — a registered knowledge source (Second Brain, Idea 1/2)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class KbSource(Base):
    __tablename__ = "kb_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    # vault_folder | local_dir | upload | cloud
    source_type = Column(String(30), default="local_dir")
    root_path = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True)
    last_scanned_at = Column(DateTime, nullable=True)

    # Per-scan stats (Idea 3, phrase 26).
    files_seen = Column(Integer, default=0)
    files_added = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    files_removed = Column(Integer, default=0)

    # JSON map ``{path_rel: canonical_document_id}`` of files already deduped
    # against a canonical document (Idea 8, phrase 73). Persistent so re-scans
    # treat a known duplicate as stable instead of re-counting it as new.
    duplicate_map_json = Column(Text, nullable=True)

    # ── Phase 9 external sync (Idea 89) ──
    # none | git | drive | clip | local — which adapter syncs this source.
    sync_type = Column(String(20), default="none")
    # Per-source sync cursor (commit hash / Drive cursor / clip id) so only
    # deltas import on each run.
    sync_cursor_json = Column(Text, nullable=True)
    # External vault/notes directory for the ``local`` adapter ("Copy Recent
    # Notes"): the source-of-truth folder whose knowledge Markdown files are
    # mirrored into this source's root (``second_brain/notes``). Unchanged
    # files are never re-copied or re-embedded (content-hash identity).
    sync_source_path = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    documents = relationship(
        "KbDocument",
        back_populates="source",
        cascade="all, delete-orphan",
    )
