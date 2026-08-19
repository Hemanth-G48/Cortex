"""KbFolder model — canonical persisted folder/domain entity (Idea: folder = source of truth).

The Second Brain folder hierarchy is the canonical organization model: a
top-level vault folder is a Course, its child folders are Domains/Topics, and
the notes inside them are the Documents. This model persists that hierarchy
explicitly so every surface (course page, domain page, dashboard, gap
analysis) references the *same* folder entity instead of recomputing folder
paths on the fly.

``KbFolder`` rows are derived during course sync (``domain_service``):
one row per non-ignored folder below a course's root folder, keyed by
``(user_id, source_id, path)`` so a re-sync idempotently updates existing
rows and drops stale ones (renamed/deleted folders disappear automatically).
Documents belong to a folder by path prefix — no manual assignment.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class KbFolder(Base):
    __tablename__ = "kb_folders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=True, index=True)
    # The Course this folder belongs to (null until a matching course exists).
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True, index=True)
    # Parent folder (null for a top-level domain under the course root).
    parent_id = Column(Integer, ForeignKey("kb_folders.id"), nullable=True, index=True)
    # Folder path relative to the source root, e.g. ``Cybersecurity/Web Security``.
    path = Column(String(1000), nullable=False)
    # Folder basename, e.g. ``Web Security``.
    name = Column(String(300), nullable=False)
    # Depth below the course root: 1 = domain, 2 = nested subdomain, …
    depth = Column(Integer, default=1)
    # Number of documents directly inside this folder (not recursive).
    doc_count = Column(Integer, default=0)
    # Metadata read from the folder's ``index.md`` frontmatter (mirrors the
    # course-derivation ``_folder_metadata`` behaviour).
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # One canonical folder row per (user, source, path) — the sync upserts
        # on this key and deletes rows whose path no longer resolves.
        UniqueConstraint("user_id", "source_id", "path", name="uq_kb_folders_user_source_path"),
        Index("ix_kb_folders_user_course", "user_id", "course_id"),
    )
