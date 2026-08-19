"""Phase 6 attendance router (Idea 56).

Mark present/absent per subject+date (unique, upsert), fetch history, and
compute per-subject percent + streaks. Falling-pattern alerts (N consecutive
misses) write a Notification row via the notifications table directly.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Attendance, Notification, User
from app.services.users import current_user

router = APIRouter(prefix="/api", tags=["kb-attendance"])


class AttendanceMark(BaseModel):
    subject_id: int
    class_date: date
    present: bool = True
    note: str | None = None


def _history(db: Session, user_id: int, subject_id: int) -> list[Attendance]:
    return (
        db.query(Attendance)
        .filter(Attendance.user_id == user_id, Attendance.subject_id == subject_id)
        .order_by(Attendance.class_date.asc())
        .all()
    )


@router.post("/attendance")
def mark_attendance(
    body: AttendanceMark,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Mark a class day present/absent (upsert per user+subject+date)."""
    row = (
        db.query(Attendance)
        .filter(
            Attendance.user_id == current_user.id,
            Attendance.subject_id == body.subject_id,
            Attendance.class_date == body.class_date,
        )
        .first()
    )
    if row is None:
        row = Attendance(
            user_id=current_user.id,
            subject_id=body.subject_id,
            class_date=body.class_date,
            present=body.present,
            note=body.note,
        )
        db.add(row)
    else:
        row.present = body.present
        row.note = body.note
    db.commit()
    db.refresh(row)

    alert = _check_falling_pattern(db, current_user.id, body.subject_id)
    return {
        "ok": True,
        "attendance": {
            "id": row.id,
            "subject_id": row.subject_id,
            "class_date": row.class_date.isoformat(),
            "present": row.present,
            "note": row.note,
        },
        "alert": alert,
    }


@router.get("/subjects/{subject_id}/attendance")
def attendance_history(
    subject_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = _history(db, current_user.id, subject_id)
    stats = _stats(rows)
    return {
        "subject_id": subject_id,
        "items": [
            {
                "id": r.id,
                "class_date": r.class_date.isoformat(),
                "present": r.present,
                "note": r.note,
            }
            for r in rows
        ],
        "stats": stats,
    }


@router.get("/attendance/analytics")
def attendance_analytics(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Per-subject attendance % + streak summary (phrase 55)."""
    rows = (
        db.query(Attendance)
        .filter(Attendance.user_id == current_user.id)
        .order_by(Attendance.class_date.asc())
        .all()
    )
    by_subject: dict[int, list[Attendance]] = {}
    for r in rows:
        by_subject.setdefault(r.subject_id, []).append(r)
    return {
        "subjects": {
            str(sid): _stats(list_)
            for sid, list_ in sorted(by_subject.items())
        },
        "total_classes": len(rows),
        "present": sum(1 for r in rows if r.present),
    }


def _stats(rows: list[Attendance]) -> dict:
    total = len(rows)
    present = sum(1 for r in rows if r.present)
    percent = round(present / total * 100, 1) if total else 0.0
    # Current streak: consecutive classes ending today/yesterday.
    streak = 0
    cursor = date.today()
    for r in reversed(rows):
        if r.class_date > cursor:
            continue
        if r.class_date != cursor:
            break
        if not r.present:
            break
        streak += 1
        cursor -= timedelta(days=1)
    return {
        "total": total,
        "present": present,
        "absent": total - present,
        "percent": percent,
        "current_streak": streak,
        "is_falling": _recent_misses(rows) >= settings.KB_ATTENDANCE_ALERT_STREAK,
    }


def _recent_misses(rows: list[Attendance]) -> int:
    """Consecutive most-recent classes that were missed."""
    misses = 0
    for r in reversed(rows):
        if r.present:
            break
        misses += 1
    return misses


def _check_falling_pattern(db: Session, user_id: int, subject_id: int) -> dict | None:
    """N consecutive misses → Notification (phrase 56)."""
    rows = _history(db, user_id, subject_id)
    if _recent_misses(rows) < settings.KB_ATTENDANCE_ALERT_STREAK:
        return None
    existing = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.kind == "attendance_alert",
            Notification.ref_id == subject_id,
            Notification.read.is_(False),
        )
        .first()
    )
    if existing is not None:
        return {"kind": "attendance_alert", "subject_id": subject_id}
    db.add(
        Notification(
            user_id=user_id,
            kind="attendance_alert",
            title="Attendance slipping",
            body=(
                f"You have missed {_recent_misses(rows)} classes in a row for this "
                "subject. Consider checking in — small steps keep the streak alive."
            ),
            ref_type="subject",
            ref_id=subject_id,
        )
    )
    db.flush()
    return {"kind": "attendance_alert", "subject_id": subject_id}
