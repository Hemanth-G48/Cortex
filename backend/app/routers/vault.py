from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Goal, Habit, HabitLog, Project, ScheduleEvent, Task, User,
)
from app.schemas.task import TaskResponse

router = APIRouter(prefix="/api/vault", tags=["vault"])


@router.get("/summary")
def vault_summary(db: Session = Depends(get_db)):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())

    overdue_tasks = db.query(Task).filter(
        Task.status != "Completed",
        Task.due_date.isnot(None),
        Task.due_date < today,
    ).count()

    # Tasks that fell due (and are still incomplete) during the previous
    # calendar week (Mon..Sun). Drives the PerformanceWidget "last week" line.
    last_week_start = start_of_week - timedelta(days=7)
    overdue_last_week = db.query(Task).filter(
        Task.status != "Completed",
        Task.due_date.isnot(None),
        Task.due_date >= last_week_start,
        Task.due_date < start_of_week,
    ).count()

    completed_today = db.query(HabitLog).filter(
        HabitLog.date == today,
        HabitLog.completed == True,  # noqa: E712
    ).count()

    total_habits = db.query(Habit).count()
    active_habits = db.query(Habit).filter(Habit.is_archived == False).count()  # noqa: E712

    # Current week streak per active habit (completion rate Sun..Sat).
    habits = db.query(Habit).filter(Habit.is_archived == False).all()  # noqa: E712
    current_week_streaks = []
    for h in habits:
        logs = db.query(HabitLog).filter(
            HabitLog.habit_id == h.id,
            HabitLog.date >= start_of_week,
            HabitLog.date <= today,
            HabitLog.completed == True,  # noqa: E712
        ).count()
        current_week_streaks.append({"habit": h.name, "streak": logs})

    return {
        "overdue_tasks": overdue_tasks,
        "overdue_last_week": overdue_last_week,
        "completed_today": completed_today,
        "total_habits": total_habits,
        "active_habits": active_habits,
        "current_week_streaks": current_week_streaks,
    }


@router.get("/tasks", response_model=List[TaskResponse])
def vault_tasks(tab: str = Query(default="today"), db: Session = Depends(get_db)):
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    q = db.query(Task)
    if tab == "completed":
        q = q.filter(Task.status == "Completed")
    elif tab == "inbox":
        q = q.filter(Task.due_date.is_(None), Task.status != "Completed")
    elif tab == "unrelated":
        q = q.filter(Task.project_id.is_(None), Task.status != "Completed")
    elif tab == "this_week":
        q = q.filter(
            Task.due_date.isnot(None),
            Task.due_date >= start_of_week,
            Task.due_date <= end_of_week,
            Task.status != "Completed",
        )
    else:  # today
        q = q.filter(Task.due_date == today, Task.status != "Completed")
    return q.all()


@router.get("/calendar")
def vault_calendar(db: Session = Depends(get_db)):
    """Per-day arrays for the current week (Mon..Sun).

    Combines Task.due_date, ScheduleEvent.day_of_week (recurring events),
    and Project.deadline into one day-keyed structure for the vault calendar.
    """
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    tasks = db.query(Task).filter(
        Task.due_date.isnot(None),
        Task.due_date >= start_of_week,
        Task.due_date <= end_of_week,
    ).all()
    tasks_by_date = {}
    for t in tasks:
        tasks_by_date.setdefault(t.due_date, []).append(t)

    events = db.query(ScheduleEvent).all()
    events_by_day = {}
    for e in events:
        events_by_day.setdefault(e.day_of_week, []).append(e)

    projects = db.query(Project).filter(
        Project.deadline.isnot(None),
        Project.deadline >= start_of_week,
        Project.deadline <= end_of_week,
    ).all()
    projects_by_date = {}
    for p in projects:
        projects_by_date.setdefault(p.deadline, []).append(p)

    days = []
    for i in range(7):
        d = start_of_week + timedelta(days=i)
        days.append({
            "date": d.isoformat(),
            "day_of_week": i,
            "label": days_of_week[i],
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "subject_tag": t.subject_tag,
                    "priority_tag": t.priority_tag,
                    "status": t.status,
                    "project_id": t.project_id,
                }
                for t in tasks_by_date.get(d, [])
            ],
            "schedule": [
                {
                    "id": e.id,
                    "title": e.title,
                    "start_time": e.start_time.isoformat() if e.start_time else None,
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                    "reference_type": e.reference_type,
                    "color": e.color,
                }
                for e in events_by_day.get(i, [])
            ],
            "deadlines": [
                {
                    "id": p.id,
                    "name": p.name,
                    "status": p.status,
                }
                for p in projects_by_date.get(d, [])
            ],
        })

    return {
        "start": start_of_week.isoformat(),
        "end": end_of_week.isoformat(),
        "days": days,
    }


@router.get("/database")
def vault_database_counts(db: Session = Depends(get_db)):
    """Row counts for the vault Quick Action 'Database' link."""
    return {
        "users": db.query(User).count(),
        "habits": db.query(Habit).count(),
        "tasks": db.query(Task).count(),
        "projects": db.query(Project).count(),
        "goals": db.query(Goal).count(),
        "logs": db.query(HabitLog).count(),
    }
