from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    DailyLog, Event, Goal, Habit, HabitLog, LifeArea, Reminder, Task,
)

router = APIRouter(prefix="/api", tags=["life-planner"])


@router.get("/life-planner/summary")
def life_planner_summary(db: Session = Depends(get_db)):
    today = date.today()

    # Streaks: longest continuous run of days with at least one completed log.
    logs = db.query(HabitLog).filter(
        HabitLog.completed == True  # noqa: E712
    ).order_by(HabitLog.date.asc()).all()
    active_dates = sorted({l.date for l in logs})
    current_streak = 0
    longest_streak = 0
    run = 0
    prev = None
    for d in active_dates:
        if prev is not None and (d - prev).days == 1:
            run += 1
        else:
            run = 1
        longest_streak = max(longest_streak, run)
        prev = d
    if active_dates and active_dates[-1] in (today, today - timedelta(days=1)):
        current_streak = run

    daily_log_today = db.query(DailyLog).filter(DailyLog.date == today).first()

    tasks_due_today = db.query(Task).filter(
        Task.due_date == today,
        Task.status != "Completed",
    ).count()

    goals_active = db.query(Goal).filter(Goal.is_completed == False).count()  # noqa: E712
    habits_active = db.query(Habit).filter(Habit.is_archived == False).count()  # noqa: E712

    areas = db.query(LifeArea).order_by(LifeArea.sort_order.asc()).all()
    life_area_progress = [
        {
            "id": a.id,
            "name": a.name,
            "progress_percent": a.progress_percent or 0.0,
        }
        for a in areas
    ]

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "daily_log_today": {
            "date": today.isoformat(),
            "time_focused": daily_log_today.time_focused if daily_log_today else 0,
            "status": daily_log_today.status if daily_log_today else "active",
        },
        "tasks_due_today": tasks_due_today,
        "habits_active": habits_active,
        "goals_active": goals_active,
        "life_area_progress": life_area_progress,
    }


@router.get("/quick-tasks")
def quick_tasks(db: Session = Depends(get_db)):
    """Unified quick task list: incomplete reminders, not-completed tasks, and
    today's events, each tagged with a type and time for sorting."""
    today = date.today()

    reminders = db.query(Reminder).filter(Reminder.is_completed == False).all()  # noqa: E712
    tasks = db.query(Task).filter(Task.status != "Completed").all()
    events = db.query(Event).filter(Event.date == today).all()

    items = []
    for r in reminders:
        items.append({
            "id": r.id,
            "type": "reminder",
            "title": r.title,
            "time": r.time.isoformat() if r.time else None,
            "date": r.date.isoformat(),
            "completed": r.is_completed,
        })
    for t in tasks:
        items.append({
            "id": t.id,
            "type": "task",
            "title": t.title,
            "time": None,
            "date": t.due_date.isoformat() if t.due_date else None,
            "completed": t.status == "Completed",
        })
    for e in events:
        items.append({
            "id": e.id,
            "type": "event",
            "title": e.title,
            "time": e.time.isoformat() if e.time else None,
            "date": e.date.isoformat(),
            "completed": e.is_completed,
        })

    def sort_key(item):
        return (item["time"] or "23:59:59", item["type"])
    items.sort(key=sort_key)
    return items
