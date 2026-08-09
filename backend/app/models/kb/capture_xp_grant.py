"""CaptureXpGrant model — once-per-trigger XP guard (Idea 69).

Mirrors the once-per-quiz rule in ``quiz_stats.grant_quiz_xp``: each event
type may grant XP at most once per unique trigger (revision id / document
id). The unique constraint is the double-count guard (phrase 86).
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.database import Base


class CaptureXpGrant(Base):
    __tablename__ = "capture_xp_grants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # revision | daily_note | dump_filed (phrase 81–83).
    kind = Column(String(20), nullable=False, index=True)
    # The unique trigger key: e.g. "revision:{schedule_id}" / "doc:{document_id}".
    trigger_key = Column(String(200), nullable=False)
    amount = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "trigger_key", name="uq_capture_xp_trigger"),
    )
