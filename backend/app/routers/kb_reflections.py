"""Idea 98 — goal planning & reflection router.

- ``GET /api/kb/reflections`` — weekly reflections (phrase 79).
- ``POST /api/kb/reflections/generate`` — generate the current week's
  reflection + push insight notification (phrases 75–76).
- ``GET/POST /api/kb/goals/derived`` — auto-proposed subject goals + confirm
  (phrase 72).
- ``GET /api/kb/goals`` + ``GET /api/kb/goals/{id}/progress`` — goal list +
  roadmap-completion progress (phrase 71).
- ``POST /api/kb/reflections/adjust`` — apply reflection-driven plan
  adjustments (phrase 77).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import reflections as reflection_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-reflections"])


@router.get("/reflections")
def list_reflections(
    limit: int = Query(default=12, ge=1, le=50),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return {"items": reflection_service.list_reflections(db, current_user.id, limit=limit)}


class GenerateReflectionRequest(BaseModel):
    week_start: date | None = None


@router.post("/reflections/generate")
def generate_reflection(
    body: GenerateReflectionRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = reflection_service.get_or_generate(
        db, current_user.id, body.week_start
    )
    db.commit()
    return result


@router.post("/reflections/adjust")
def adjust_plans(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    applied = reflection_service.apply_plan_adjustments(db, current_user.id)
    db.commit()
    return {"applied": applied, "count": len(applied)}


# --------------------------------------------------------------------------- #
# Goals ↔ roadmaps (phrases 71–72)
# --------------------------------------------------------------------------- #


@router.get("/goals/derived")
def derived_goals(
    quarter: str | None = Query(default=None),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return {
        "items": reflection_service.derive_goals(
            db, current_user.id, quarter=quarter
        )
    }


class ConfirmDerivedGoalRequest(BaseModel):
    title: str
    subject_id: int
    quarter: str = "Q1"
    year: int | None = None
    target_date: date | None = None
    roadmap_id: int | None = None


@router.post("/goals/derived/confirm")
def confirm_derived_goal(
    body: ConfirmDerivedGoalRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        goal = reflection_service.confirm_derived_goal(
            db, current_user.id, body.model_dump(exclude_none=True)
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True, "goal_id": goal.id}


@router.get("/goals")
def list_goals(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return {"items": reflection_service.list_goals(db, current_user.id)}


@router.get("/goals/{goal_id}/progress")
def goal_progress(
    goal_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = reflection_service.goal_progress(db, current_user.id, goal_id)
    if result is None:
        raise HTTPException(404, "Goal not found")
    db.commit()
    return result
