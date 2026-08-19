"""Weekly review ritual endpoints (workflow glue)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import weekly_review as weekly_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-weekly-review"])


@router.get("/weekly-review")
def get_weekly_review(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """The full weekly-review ritual payload (read-only)."""
    return weekly_service.weekly_review(db, current_user.id)


class GenerateReflectionRequest(BaseModel):
    regenerate: bool = False


@router.post("/weekly-review/generate-reflection")
def generate_weekly_reflection(
    body: GenerateReflectionRequest | None = None,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Generate (or regenerate) this week's reflection from learning events."""
    result = weekly_service.generate_reflection(
        db, current_user.id, regenerate=bool(body and body.regenerate)
    )
    db.commit()
    return result


class ConfirmGoalRequest(BaseModel):
    title: str
    subject_id: int
    quarter: str = "Q1"
    year: int | None = None
    target_date: str | None = None
    roadmap_id: int | None = None


@router.post("/weekly-review/goals/confirm")
def confirm_goal(
    body: ConfirmGoalRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Confirm an auto-proposed term goal so it appears in the Goals page."""
    try:
        result = weekly_service.confirm_derived_goal(
            db, current_user.id, body.model_dump(exclude_none=True)
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return result
