"""KbFlashcardCandidate model — review queue for note-derived cards (Idea 34).

Candidates are generated from a document but never enter a ``FlashcardDeck``
until the user approves them (phrase 33). ``status``: ``pending`` →
``approved`` (creates a ``Flashcard`` row, records ``deck_id``) or
``rejected``.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class KbFlashcardCandidate(Base):
    __tablename__ = "kb_flashcard_candidates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    document_id = Column(
        Integer, ForeignKey("kb_documents.id"), nullable=False, index=True
    )
    source_chunk_id = Column(Integer, nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    # pending | approved | rejected
    status = Column(String(20), default="pending", index=True)
    # Set when approved — the deck the card was committed to.
    deck_id = Column(Integer, nullable=True)
    # Phase 9 (Idea 85, phrase 44): manual | auto — who queued this candidate
    # so the review UI can mark auto-generated rows.
    source = Column(String(10), default="manual", index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_kb_flashcard_candidates_user_status", "user_id", "status"),
    )
