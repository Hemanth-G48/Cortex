"""KbCitation model — the per-user citation registry (Idea 36).

Citations are parsed from PDF reference lists and inline ``@cite``/``[[cite:…]]``
markdown syntax, deduped on ``(user_id, cite_key)``, and exportable as BibTeX
(phrase 51, 56, 58).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class KbCitation(Base):
    __tablename__ = "kb_citations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # Document the citation was parsed from (None for manually entered rows).
    document_id = Column(Integer, ForeignKey("kb_documents.id"), nullable=True, index=True)
    cite_key = Column(String(200), nullable=False)
    title = Column(Text, nullable=True)
    # JSON list of author strings.
    authors = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    venue = Column(String(300), nullable=True)
    doi = Column(String(300), nullable=True)
    arxiv_id = Column(String(100), nullable=True)
    # The raw reference line this citation was parsed from.
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "cite_key", name="uq_kb_citations_user_key"),
    )
