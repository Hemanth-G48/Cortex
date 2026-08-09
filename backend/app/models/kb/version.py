"""KbVersion model — content snapshots for version history & diff (Idea 9)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.database import Base


class KbVersion(Base):
    __tablename__ = "kb_versions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    version_seq = Column(Integer, default=1)
    content_hash = Column(String(64), nullable=True)
    # Small-document snapshots live inline; large documents store a file path
    # in snapshot_text instead (Idea 9, phrase 86).
    snapshot_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("document_id", "version_seq", name="uq_kb_versions_doc_seq"),
        Index("ix_kb_versions_doc_created", "document_id", "created_at"),
    )

    document = relationship("KbDocument", back_populates="versions")
