"""KbDocument model — one indexed document in the Knowledge Core (Idea 1)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class KbDocument(Base):
    __tablename__ = "kb_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("kb_sources.id"), nullable=True, index=True)
    path_rel = Column(String(1000), nullable=True)
    # Absolute path of the underlying file (scanned docs under the source root;
    # uploads under settings.UPLOAD_DIR) — lets ingest re-extract on reindex.
    file_path = Column(String(1000), nullable=True)
    title = Column(String(500), nullable=True)
    # pdf | md | txt | docx
    doc_type = Column(String(20), default="md")
    # SHA-256 of the raw file bytes (Idea 8, phrase 80) — NULL until ingested.
    content_hash = Column(String(64), nullable=True)
    char_count = Column(Integer, default=0)
    frontmatter_json = Column(Text, nullable=True)
    outline_json = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    ocr_used = Column(Boolean, default=False)
    needs_ocr = Column(Boolean, default=False)
    # new | changed | unchanged | deleted | failed
    status = Column(String(20), default="new", index=True)
    # Daily-note date detected from the filename (Idea 4, phrase 38).
    doc_date = Column(Date, nullable=True)

    # ── Phase 2 metadata fields (Idea 13) ──
    author = Column(String(300), nullable=True)
    source_url = Column(String(1000), nullable=True)
    language = Column(String(20), nullable=True)
    reading_time_seconds = Column(Integer, nullable=True)

    # ── Phase 2 incremental-reindex dirty flags (Idea 20) ──
    # True when that stage's output is stale and must be recomputed. Each
    # stage clears its own flag only after succeeding (phrase 93).
    embedding_dirty = Column(Boolean, default=True)
    graph_dirty = Column(Boolean, default=True)
    tags_dirty = Column(Boolean, default=True)

    # ── Phase 4 note-quality scoring (Idea 39, phrase 84) ──
    # Cached 0–100 composite score + JSON detail {components, weights}.
    # Recomputed lazily on read and on content change (ingest).
    quality_score = Column(Integer, nullable=True)
    quality_detail = Column(Text, nullable=True)

    # ── Phase 9 summary staleness (Idea 86) ──
    # True when the document's content hash changed since its summary was
    # generated — the nightly summary job selects on this flag.
    summary_dirty = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)
    indexed_at = Column(DateTime, nullable=True)

    # Dedupe safety net (Idea 8, phrase 71): one canonical row per (user,
    # content_hash). SQLite treats NULLs as distinct, so pending documents
    # without a hash are unaffected.
    __table_args__ = (
        Index("ix_kb_documents_user_hash", "user_id", "content_hash", unique=True),
    )

    source = relationship("KbSource", back_populates="documents")
    chunks = relationship(
        "KbChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KbChunk.seq",
    )
    versions = relationship(
        "KbVersion",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="KbVersion.version_seq.desc()",
    )
    # Document↔tag association rows (Idea 14). Exposed so the tag endpoints
    # can read applied tags (``provenance`` rule|ai|manual) off the document.
    document_tags = relationship(
        "KbDocumentTag",
        back_populates="document",
        cascade="all, delete-orphan",
    )
