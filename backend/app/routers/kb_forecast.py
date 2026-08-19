"""Idea 99 — trajectory forecasting router.

- ``GET /api/kb/forecast/{subject_id}`` — trajectory points, readiness score,
  at-risk flag (phrase 85).
- ``POST /api/kb/forecast/scan`` — sweep all subjects; fire coalesced
  early-warning alerts (phrase 86).

Pure math, per-user scoped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import forecast as forecast_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-forecast"])


@router.get("/forecast/{subject_id}")
def get_forecast(
    subject_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return forecast_service.trajectory(db, current_user.id, subject_id)


@router.post("/forecast/scan")
def scan_forecast(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = forecast_service.run(db, current_user.id)
    db.commit()
    return result
