"""Study plans CRUD."""
from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import StudyPlan
from app.schemas.study_plan import StudyPlanCreate, StudyPlanResponse

router = APIRouter(prefix="/api/study-plans", tags=["study-plans"])


def _to_response(plan: StudyPlan) -> StudyPlanResponse:
    try:
        weeks = json.loads(plan.weeks_json or "[]")
    except json.JSONDecodeError:
        weeks = []
    return StudyPlanResponse(
        id=plan.id,
        subject=plan.subject,
        exam_date=plan.exam_date,
        weeks=weeks,
        created_at=plan.created_at,
    )


@router.get("", response_model=List[StudyPlanResponse])
def list_study_plans(db: Session = Depends(get_db)):
    plans = db.query(StudyPlan).order_by(StudyPlan.id.desc()).all()
    return [_to_response(p) for p in plans]


@router.get("/{plan_id}", response_model=StudyPlanResponse)
def get_study_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Study plan not found")
    return _to_response(plan)


@router.post("", response_model=StudyPlanResponse)
def create_study_plan(data: StudyPlanCreate, db: Session = Depends(get_db)):
    plan = StudyPlan(
        subject=data.subject,
        exam_date=data.exam_date,
        weeks_json=json.dumps([w.model_dump() for w in data.weeks], ensure_ascii=False),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.delete("/{plan_id}")
def delete_study_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(StudyPlan).filter(StudyPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(404, "Study plan not found")
    db.delete(plan)
    db.commit()
    return {"ok": True}
