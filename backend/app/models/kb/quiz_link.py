"""KbQuizLink model — traceability between a generated quiz and the vault
document it was built from (Idea 33, phrases 25–26).

The ``Quiz`` model itself is user-agnostic (curriculum legacy); this join row
restores per-user provenance so a note-generated quiz is traceable from both
sides (note → quiz and quiz → note).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UniqueConstraint, func

from app.database import Base


class KbQuizLink(Base):
    __tablename__ = "kb_quiz_links"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "quiz_id", name="uq_kb_quiz_links_user_quiz"),
        Index("ix_kb_quiz_links_user_doc", "user_id", "document_id"),
    )
