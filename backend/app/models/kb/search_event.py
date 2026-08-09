"""KbSearchEvent model — search feedback & learning log (Phase 3, Idea 29).

One row per search interaction: the raw query, mode, the top result chunk ids
(result_ids JSON), an optional clicked chunk id (implicit click, Idea 25
phrase 48), and an explicit rating (-1 | 0 | 1) from the result card
feedback control. Per-user; the (user_id, created_at) index feeds the batch
weight analysis job (phrase 86).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class KbSearchEvent(Base):
    __tablename__ = "kb_search_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query = Column(String(500), nullable=False)
    mode = Column(String(20), default="hybrid")
    # JSON list of top result chunk ids returned for this query.
    result_ids = Column(Text, nullable=True)
    # Chunk the user clicked through to (implicit signal, may be null).
    clicked_id = Column(Integer, nullable=True)
    # -1 | 0 | 1 — explicit user rating (null until rated).
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_kb_search_events_user_time", "user_id", "created_at"),
    )
