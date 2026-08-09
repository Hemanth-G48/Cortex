"""KbDocumentTag model — document↔tag association (Phase 2, Idea 14).

``provenance`` tracks where the association came from:
- ``rule`` — inline ``#tags`` parsed from content (never suggested for deletion)
- ``ai``   — LLM proposal (kept as suggestions until the user confirms)
- ``manual`` — user-confirmed via the apply endpoint

A unique ``(document_id, tag_id)`` makes the association idempotent.
"""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class KbDocumentTag(Base):
    __tablename__ = "document_tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    tag_id = Column(Integer, ForeignKey("kb_tags.id"), nullable=False, index=True)
    # rule | ai | manual
    provenance = Column(String(10), default="rule")

    document = relationship("KbDocument", back_populates="document_tags")

    __table_args__ = (
        UniqueConstraint("document_id", "tag_id", name="uq_document_tags_doc_tag"),
        Index("ix_document_tags_user", "user_id", "document_id"),
    )
