"""Phase 7 knowledge-capture & revision XP (Idea 69, phrases 81–90).

Reuses the existing gamification wallet — ``User.total_xp`` + ``Character.xp``
(mirrors ``quiz_stats.grant_quiz_xp`` and ``habit_xp``) — with NO new
gamification system (phrase 84). Amounts come from ``KB_XP_REWARDS``
(zero-defaults → disabled, phrase 85) and the ``capture_xp_grants`` unique
constraint prevents double-counting per trigger (phrase 86).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CaptureXpGrant, Character, User


def _grant(db: Session, user: User, kind: str, trigger_key: str, amount: int) -> bool:
    """Best-effort once-per-trigger grant. Returns True when XP was credited."""
    if amount <= 0:
        return False
    existing = (
        db.query(CaptureXpGrant)
        .filter(
            CaptureXpGrant.user_id == user.id,
            CaptureXpGrant.kind == kind,
            CaptureXpGrant.trigger_key == trigger_key,
        )
        .first()
    )
    if existing is not None:
        return False
    db.add(CaptureXpGrant(user_id=user.id, kind=kind, trigger_key=trigger_key, amount=amount))
    return True


def award_capture_xp(db: Session, user: User, kind: str, trigger_key: str) -> int:
    """Award XP for a capture/revision trigger (phrases 81–83).

    Returns the amount granted (0 when disabled, unknown kind, or already
    granted). Callers commit; the grant row + wallet update happen here.
    """
    amount = settings.kb_xp_rewards.get(kind, 0)
    if amount <= 0:
        return 0
    if not _grant(db, user, kind, trigger_key, amount):
        return 0

    user.total_xp = (user.total_xp or 0) + amount
    char = db.query(Character).filter(Character.user_id == user.id).first()
    if char is not None:
        char.xp = (char.xp or 0) + amount
    db.flush()
    return amount


__all__ = ["award_capture_xp"]
