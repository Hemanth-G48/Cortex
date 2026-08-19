"""Workflow glue — the daily "Today" command center.

Aggregates everything a single day needs into one payload, split into the
ritual phases the Today page renders:

- ``morning`` — plan the day: due reviews, next action, suggested sessions,
  today's schedule, upcoming deadlines.
- ``evening`` — close the day: what was captured, focus time logged, journal.

No AI is used and nothing is written — pure read-side aggregation over the
existing Phase 4/6 services (daily notes, revision, next-action, sessions).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Assignment,
    Course,
    DailyScheduleItem,
    Exam,
    JournalEntry,
    KbDocument,
    PomodoroSession,
    Task,
)
from app.services.kb import utcnow
from app.services.kb.daily_notes import get_today
from app.services.kb.next_action import recommend
from app.services.kb.revision import due_reviews

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min)
    return start, start + timedelta(days=1)


def _deadline_dict(row: Assignment | Exam | Task) -> dict:
    if isinstance(row, Assignment):
        return {
            "kind": "assignment",
            "id": row.id,
            "title": row.title,
            "course_id": row.course_id,
            "due_date": row.due_date.isoformat() if row.due_date else None,
            "status": row.status,
        }
    if isinstance(row, Exam):
        return {
            "kind": "exam",
            "id": row.id,
            "title": row.title,
            "course_id": row.course_id,
            "due_date": row.date.isoformat() if row.date else None,
            "status": row.status,
        }
    return {
        "kind": "task",
        "id": row.id,
        "title": row.title,
        "due_date": row.due_date.isoformat() if row.due_date else None,
        "status": row.status,
    }


def today_overview(db: Session, user_id: int, day: date | None = None) -> dict:
    """One payload for the Today page (morning plan + evening close)."""
    day = day or date.today()
    start, end = _day_bounds(day)

    # ── Evening: what happened today ──
    # Focus minutes count COMPLETED pomodoros only (a running timer is not yet
    # earned focus time); unfinished sessions are still listed below.
    
    captured_docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.created_at >= start,
            KbDocument.created_at < end,
            KbDocument.status != "deleted",
        )
        .order_by(KbDocument.created_at.desc())
        .all()
    )
    pomodoros = (
        db.query(PomodoroSession)
        .filter(
            PomodoroSession.user_id == user_id,
            PomodoroSession.start_time >= start,
            PomodoroSession.start_time < end,
        )
        .all()
    )
    journal = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user_id, JournalEntry.date == day)
        .order_by(JournalEntry.id.desc())
        .all()
    )
    schedule_items = (
        db.query(DailyScheduleItem)
        .filter(DailyScheduleItem.user_id == user_id, DailyScheduleItem.date == day)
        .order_by(DailyScheduleItem.time_range.asc())
        .all()
    )
    focus_minutes = sum(
        p.duration_minutes or 0 for p in pomodoros if p.completed
    )

    # ── Morning: what to do today ──
    reviews = due_reviews(db, user_id, on=day)
    next_actions = recommend(db, user_id, limit=3)

    deadline_rows: list[Assignment | Exam | Task] = []
    courses = {
        c.id
        for c in db.query(Course).filter(Course.user_id == user_id).all()
    }
    if courses:
        deadline_rows.extend(
            db.query(Assignment)
            .filter(Assignment.course_id.in_(courses), Assignment.status != "Completed")
            .order_by(Assignment.due_date.asc())
            .limit(5)
            .all()
        )
        deadline_rows.extend(
            db.query(Exam)
            .filter(Exam.course_id.in_(courses), Exam.date >= day)
            .order_by(Exam.date.asc())
            .limit(5)
            .all()
        )
    deadline_rows.extend(
        db.query(Task)
        .filter(Task.user_id == user_id, Task.status != "Completed")
        .order_by(Task.due_date.asc())
        .limit(5)
        .all()
    )
    deadline_rows.sort(key=lambda r: (r.due_date or date.max, r.id))
    deadlines = [_deadline_dict(r) for r in deadline_rows[:8]]

    daily = get_today(db, user_id)

    return {
        "date": day.isoformat(),
        "day_name": _DAYS[day.weekday()],
        "morning": {
            "reviews_due": reviews,
            "next_actions": next_actions,
            "schedule": [
                {
                    "id": s.id,
                    "time_range": s.time_range,
                    "activity": s.activity,
                    "category": s.category,
                    "done": s.done,
                }
                for s in schedule_items
            ],
            "deadlines": deadlines,
            # Reused from the daily-note aggregator so the UI shows the same
            # "vault captures today" list without a second query.
            "captured_documents": [
                {
                    "id": d.id,
                    "title": d.title or d.path_rel or f"doc {d.id}",
                    "doc_type": d.doc_type,
                    "char_count": d.char_count,
                    "quality_score": d.quality_score,
                }
                for d in captured_docs
            ],
        },
        "evening": {
            "focus_minutes": focus_minutes,
            "pomodoros": [
                {
                    "id": p.id,
                    "duration_minutes": p.duration_minutes,
                    "task_description": p.task_description,
                    "completed": p.completed,
                }
                for p in pomodoros
            ],
            "journal": [
                {
                    "id": j.id,
                    "mood": j.mood,
                    "content": (j.content or "")[:400],
                    "tags": j.tags,
                }
                for j in journal
            ],
            # Daily-note aggregator: documents + schedule + journal for the day.
            "daily": daily,
        },
        "captured_today_count": len(captured_docs),
    }
