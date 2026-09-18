"""Vault mastery read model (audit defects #40, #71, #76, #82, #96).

Exposes the mastery spine (``LearningEvent`` → per-topic score) as an API so
non-study surfaces can show vault-derived competency: the Life Planner goal
sparkline, the Grades GPA panel, the Leaderboard breakdown, the RPG stat radar
and the Reading insights merge.

``GET /api/kb/mastery``                 → whole-vault aggregate
``GET /api/kb/mastery?subject=<id>``    → one curriculum subject
``GET /api/kb/mastery?subject_name=...``→ resolve a subject by title
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import mastery as mastery_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-mastery"])


@router.get("/mastery")
def get_mastery(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    subject: int | None = Query(
        default=None,
        description="Curriculum subject id to scope the aggregate to.",
    ),
    subject_name: str | None = Query(
        default=None,
        description="Resolve a subject by name when the id is not known (case-insensitive).",
    ),
    days: int = Query(
        mastery_service.TREND_DAYS,
        ge=1,
        le=730,
        description="Window for the mastery sparkline, in days.",
    ),
) -> dict:
    """Vault-derived competency scores + daily trend (read-only)."""
    return mastery_service.mastery_payload(
        db,
        current_user.id,
        subject=subject,
        subject_name=subject_name,
        days=days,
    )
