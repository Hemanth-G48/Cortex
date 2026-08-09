"""Leaderboard (adapted from Shiori-v1 ``loadLeaderboard`` / QuestLog).

Ranks users by their XP wallet (``User.total_xp``, the same pool every feature
draws from — quests, habit XP, rewards, character). The response marks the
calling user with ``me: true`` so the frontend can highlight their row, and
includes their percentile so the board stays meaningful at any cohort size.

Endpoint: ``GET /api/leaderboard?limit=20`` (auth required).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, User
from app.services.security import get_current_user

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("")
def leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User, Character)
        .outerjoin(Character, Character.user_id == User.id)
        .filter(User.total_xp.is_not(None), User.total_xp > 0)
        .order_by(User.total_xp.desc(), User.id.asc())
        .limit(limit)
        .all()
    )

    entries = []
    for rank, (user, char) in enumerate(rows, start=1):
        entries.append(
            {
                "rank": rank,
                "user_id": user.id,
                "name": user.name or user.username or f"User {user.id}",
                "username": user.username,
                "avatar_class": char.class_name if char else user.avatar_class,
                "level": (char.level if char else None) or user.current_level or 1,
                "current_streak": user.current_streak or 0,
                "total_xp": user.total_xp or 0,
                "me": user.id == current_user.id,
            }
        )

    # Where does the caller sit? Compute from the full population (cheap count
    # + their own xp), not just the returned slice.
    # Cohort size and rank are computed over the same population the board
    # shows (XP > 0), so percentile/rank always match the displayed rows.
    # A caller with 0 XP doesn't appear on the board — rank them last.
    my_row = db.query(User).filter(User.id == current_user.id).first()
    total = db.query(User).filter(User.total_xp.is_not(None), User.total_xp > 0).count()
    above = 0
    if my_row and my_row.total_xp:
        above = (
            db.query(User)
            .filter(User.total_xp > (my_row.total_xp or 0))
            .count()
        )
        my_rank = above + 1
    else:
        my_rank = total + 1  # No XP yet → last place, not first.
    percentile = round(100.0 * (1 - above / total), 1) if total else 100.0

    return {
        "items": entries,
        "me": {
            "user_id": current_user.id,
            "total_xp": my_row.total_xp if my_row else 0,
            "rank": my_rank,
            "percentile": percentile,
            "total_users": total,
        },
    }
