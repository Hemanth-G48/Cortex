"""MissingNoteSuggestion model (Phase 8, Idea 77).

A suggestion that the user studies concept X (or topic T) but has no note on
it. ``reason`` summarizes the gap evidence; ``outline_template`` is a JSON
heading list used to pre-fill a draft note; ``linked_material_ids`` is a JSON
list of kb_document ids the user can capture from. ``status`` lifecycle:
suggested → accepted (creates a draft note) | dismissed (never re-suggested).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class MissingNoteSuggestion(Base):
    __tablename__ = "missing_note_suggestions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("kb_concepts.id"), nullable=True, index=True)
    # Nullable — suggestions can be topic-level rather than concept-level.
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    # JSON list of suggested markdown headings for the missing note.
    outline_template = Column(Text, nullable=True)
    # JSON list of kb_document ids to capture from.
    linked_material_ids = Column(Text, nullable=True)
    # suggested | accepted | dismissed
    status = Column(String(20), default="suggested", index=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_missing_notes_user_status", "user_id", "status"),
    )
