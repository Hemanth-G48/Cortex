"""UserMemory model — long-term learning memory store (Phase 8, Idea 79).

One row per ``(user_id, concept_id)``: the durable record of what a user has
actually studied. ``strength`` is 0–1 and decays with an exponential half-life
(``KB_MEMORY_HALF_LIFE_DAYS``); ``exposure_count`` and ``last_seen`` track
recency. ``source`` records which surface last touched it (quiz | tutor |
revision | note | practice).

Rule A (Phase 8): the tutor and explanations may only reference concepts whose
row exists here with ``strength > 0`` — this table is the single source of truth
for "the user knows X". It is also the documented substrate for Idea 99
(learning-trajectory forecasting), so the schema must stay stable.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint, func

from app.database import Base

MEMORY_SOURCES = ("quiz", "tutor", "revision", "note", "practice")


class UserMemory(Base):
    __tablename__ = "user_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    concept_id = Column(Integer, ForeignKey("kb_concepts.id"), nullable=False, index=True)
    strength = Column(Float, default=0.0)
    exposure_count = Column(Integer, default=0)
    last_seen = Column(DateTime, nullable=True)
    # quiz | tutor | revision | note | practice
    source = Column(String(20), default="practice")
    updated_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "concept_id", name="uq_user_memory_user_concept"),
        Index("ix_user_memory_user_strength", "user_id", "strength"),
    )
