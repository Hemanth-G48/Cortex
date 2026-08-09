"""KbJob model — ingestion job queue state (Idea 10)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class KbJob(Base):
    __tablename__ = "kb_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # scan | ingest | reindex
    job_type = Column(String(20), default="scan")
    # queued | running | done | failed | interrupted
    status = Column(String(20), default="queued", index=True)
    # Job target (scan → source; ingest/reindex → documents):
    ref_type = Column(String(20), nullable=True)  # "source" | "documents"
    ref_id = Column(Integer, nullable=True)
    ref_ids_json = Column(Text, nullable=True)
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    # Last scan/ingest summary (files_seen, added, …, duplicates_found) so the
    # API can echo it back after a synchronous run.
    summary_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
