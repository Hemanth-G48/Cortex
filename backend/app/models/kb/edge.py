"""KbEdge model — the knowledge-graph spine (Phase 2, Ideas 16–19).

Relation vocabulary (Idea 16, phrase 51):
    WIKILINK, BACKLINK, CITES, MENTIONS, RELATED, SHARES_CONCEPT,
    SYNONYM_OF, DEPENDS_ON, DUPLICATE_OF

Polymorphic target: edges are always *about* a source document, but the
target may be another document (``target_document_id``) or a concept
(``target_type='concept'`` + ``target_concept_id``). ``provenance`` records
how the edge was created: ``rule`` (parser) | ``auto`` (inferred) |
``ai`` (LLM) | ``manual`` (user override).
"""

from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Index, Integer, String

from app.database import Base


class KbEdge(Base):
    __tablename__ = "kb_edges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    target_document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=True, index=True
    )
    # WIKILINK | BACKLINK | CITES | MENTIONS | RELATED | SHARES_CONCEPT |
    # SYNONYM_OF | DEPENDS_ON | DUPLICATE_OF
    relation = Column(String(30), default="RELATED", index=True)
    weight = Column(Float, default=1.0)
    # rule | auto | ai | manual
    provenance = Column(String(10), default="auto")
    # Phase 9 (Idea 83) pending-edge review: "active" edges are live in the
    # graph; "pending" pairs wait in the auto-link review queue; "rejected"
    # pairs are kept for idempotency (never re-proposed).
    status = Column(String(20), default="active")
    # Polymorphic target: "document" (target_document_id) or "concept".
    target_type = Column(String(20), default="document")
    target_concept_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_kb_edges_user_docs", "user_id", "source_document_id", "target_document_id"),
    )
