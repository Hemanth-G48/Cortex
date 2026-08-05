"""Sleep tracker router (Zenith-Study-Planner G3, Phases 15–21)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import SleepLog
from app.schemas.sleep import (
    SleepAnalytics,
    SleepCreate,
    SleepDayPoint,
    SleepRecommendation,
    SleepResponse,
    SleepSummary,
    SleepUpdate,
)
from app.services import sleep as sleep_service
from app.services.users import current_user_id

router = APIRouter(prefix="/api/sleep", tags=["sleep"])


# ── CRUD (Phase 16) ─────────────────────────────────────────────────────── #

@router.post("", response_model=SleepResponse)
def create_sleep(data: SleepCreate, db: Session = Depends(get_db)):
    existing = db.query(SleepLog).filter(
        SleepLog.user_id == current_user_id(db), SleepLog.date == data.date
    ).first()
    if existing:
        raise HTTPException(409, "A sleep log already exists for this date")
    log = SleepLog(user_id=current_user_id(db), **data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[SleepResponse])
def list_sleep(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(SleepLog).filter(SleepLog.user_id == current_user_id(db))
    if start:
        query = query.filter(SleepLog.date >= start)
    if end:
        query = query.filter(SleepLog.date <= end)
    return query.order_by(SleepLog.date.desc()).all()


@router.put("/{sleep_id}", response_model=SleepResponse)
def update_sleep(sleep_id: int, data: SleepUpdate, db: Session = Depends(get_db)):
    log = db.query(SleepLog).filter(
        SleepLog.id == sleep_id, SleepLog.user_id == current_user_id(db)
    ).first()
    if not log:
        raise HTTPException(404, "Sleep log not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(log, key, val)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{sleep_id}")
def delete_sleep(sleep_id: int, db: Session = Depends(get_db)):
    log = db.query(SleepLog).filter(
        SleepLog.id == sleep_id, SleepLog.user_id == current_user_id(db)
    ).first()
    if not log:
        raise HTTPException(404, "Sleep log not found")
    db.delete(log)
    db.commit()
    return {"ok": True}


# ── Analytics / recommendations / summary (Phases 17–20) ────────────────── #

@router.get("/analytics", response_model=SleepAnalytics)
def get_analytics(
    days: int = Query(default=14, ge=1, le=365),
    db: Session = Depends(get_db),
):
    logs = _recent_logs(db, days)
    return sleep_service.analytics(logs)


@router.get("/recommendations", response_model=SleepRecommendation)
def get_recommendations(
    wake_time: str = Query(default="07:00"),
    days: int = Query(default=14, ge=1, le=365),
    db: Session = Depends(get_db),
):
    logs = _recent_logs(db, days)
    result = sleep_service.recommend_bedtime(
        wake_time, target_hours=settings.sleep_target_hours, history=logs
    )
    result["schedule_hints"].extend(
        sleep_service.schedule_hints(logs, target_hours=settings.sleep_target_hours)
    )
    # Dedupe while preserving order.
    seen: set[str] = set()
    hints = []
    for hint in result["schedule_hints"]:
        if hint not in seen:
            seen.add(hint)
            hints.append(hint)
    result["schedule_hints"] = hints
    return result


@router.get("/summary", response_model=SleepSummary)
def get_summary(db: Session = Depends(get_db)):
    """Last-7-days series + today status for the dashboard widget."""
    today = date.today()
    start = today - timedelta(days=6)
    logs = (
        db.query(SleepLog)
        .filter(
            SleepLog.user_id == current_user_id(db),
            SleepLog.date >= start,
            SleepLog.date <= today,
        )
        .order_by(SleepLog.date)
        .all()
    )

    by_date = {log.date: log for log in logs}
    week = []
    last_night = None
    for offset in range(7):
        day = start + timedelta(days=offset)
        log = by_date.get(day)
        point = SleepDayPoint(
            date=day,
            hours=sleep_service.hours_between(log.bedtime, log.wake_time) if log else None,
            quality=log.quality if log else None,
        )
        week.append(point)
    last_night = week[-1]

    all_logs = db.query(SleepLog).filter(SleepLog.user_id == current_user_id(db)).all()
    analytics = sleep_service.analytics(all_logs)

    return SleepSummary(
        target_hours=round(settings.sleep_target_hours, 2),
        last_night=last_night if last_night and last_night.hours is not None else None,
        week=week,
        avg_hours=analytics["avg_hours"],
        nights_under_target=analytics["nights_under_target"],
    )


def _recent_logs(db: Session, days: int):
    start = date.today() - timedelta(days=days)
    return (
        db.query(SleepLog)
        .filter(SleepLog.user_id == current_user_id(db), SleepLog.date >= start)
        .order_by(SleepLog.date)
        .all()
    )
