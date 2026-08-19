"""Leaderboard — single-owner view.

Adapted from Shiori-v1 ``loadLeaderboard`` / QuestLog. The application is
single-user, so the board shows the owner's own stats (rank 1, percentile
100) in the same response shape the frontend already consumes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character
from app.services.users import current_user

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("")
def leaderboard(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    owner = current_user(db)
    char = db.query(Character).filter(Character.user_id == owner.id).first()

    entries = [
        {
            "rank": 1,
            "user_id": owner.id,
            "name": owner.name or owner.username or "Owner",
            "username": owner.username,
            "avatar_class": char.class_name if char else owner.avatar_class,
            "level": (char.level if char else None) or owner.current_level or 1,
            "current_streak": owner.current_streak or 0,
            "total_xp": owner.total_xp or 0,
            "me": True,
        }
    ]

    return {
        "items": entries[:limit],
        "me": {
            "user_id": owner.id,
            "total_xp": owner.total_xp or 0,
            "rank": 1,
            "percentile": 100.0,
            "total_users": 1 if owner.total_xp else 0,
        },
    }
