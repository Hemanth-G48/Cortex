"""KbConcept model — canonical concepts (Phase 2, Idea 15).

One canonical row per ``(user_id, canonical_name)``; variant spellings are
folded into ``aliases`` (JSON list). ``MENTIONS`` edges in ``kb_edges`` point
at a concept via ``target_concept_id`` (polymorphic edge target).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class KbConcept(Base):
    __tablename__ = "kb_concepts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    canonical_name = Column(String(300), nullable=False)
    definition = Column(Text, nullable=True)
    # JSON list of alias spellings resolved to the canonical name.
    aliases = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "canonical_name", name="uq_kb_concepts_user_name"),
    )
