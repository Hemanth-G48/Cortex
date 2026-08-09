"""EpisodicMemory model — the Phase 10 episodic journal (Idea 92).

Beyond the Phase 8 ``user_memory`` concept table (what the user knows), this
table records *episodes* — events that happened in the learner's history
(event_type, summary, refs). The weekly consolidation job (phrase 14) folds old
episodes into durable facts written back into ``user_memory``.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base

EPISODE_TYPES = ("study", "quiz", "revision", "doubt", "session", "outcome", "consolidated")


class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # study | quiz | revision | doubt | session | outcome | consolidated
    event_type = Column(String(30), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    # JSON refs: {topic_id?, subject_id?, learning_event_ids?[]}
    refs = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_episodic_memory_user_created", "user_id", "created_at"),
    )
