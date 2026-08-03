from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DailyLog
from app.schemas.daily_log import DailyLogCreate, DailyLogUpdate, DailyLogResponse

router = APIRouter(prefix="/api", tags=["daily-logs"])


@router.get("/daily-logs", response_model=List[DailyLogResponse])
def list_daily_logs(db: Session = Depends(get_db)):
    return db.query(DailyLog).order_by(DailyLog.date.desc()).all()


@router.post("/daily-logs", response_model=DailyLogResponse)
def create_daily_log(data: DailyLogCreate, db: Session = Depends(get_db)):
    # One log per user per day: upsert so "Log In Today" is idempotent.
    existing = db.query(DailyLog).filter(
        DailyLog.user_id == data.user_id,
        DailyLog.date == data.date,
    ).first()
    if existing:
        existing.time_focused = data.time_focused
        existing.status = data.status
        db.commit()
        db.refresh(existing)
        return existing
    log = DailyLog(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.put("/daily-logs/{log_id}", response_model=DailyLogResponse)
def update_daily_log(log_id: int, data: DailyLogUpdate, db: Session = Depends(get_db)):
    log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "Daily log not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(log, key, val)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/daily-logs/{log_id}")
def delete_daily_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(DailyLog).filter(DailyLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "Daily log not found")
    db.delete(log)
    db.commit()
    return {"ok": True}


@router.get("/daily-logs/stats")
def daily_log_stats(db: Session = Depends(get_db)):
    today = date.today()
    first_of_month = today.replace(day=1)
    month_logs = db.query(DailyLog).filter(
        DailyLog.date >= first_of_month,
        DailyLog.date <= today,
    ).all()
    return {
        "total_focused_minutes": sum(l.time_focused for l in month_logs),
        "days_active_this_month": sum(1 for l in month_logs if l.status == "active"),
        "days_in_month": (today - first_of_month).days + 1,
        "today": {
            "date": today.isoformat(),
            "time_focused": next(
                (l.time_focused for l in month_logs if l.date == today), 0
            ),
        },
    }
