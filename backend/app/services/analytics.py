"""Study analytics aggregation (99-phase plan, Group 11).

Aggregates focus hours (``pomodoro_sessions``), assignment completion rate,
GPA (via ``services.grade_calc``), XP/level and a 52-week focus heatmap.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Assignment, Course, CourseWeight, Grade, PomodoroSession, User
from app.services import grade_calc


def _completed_focus(pomos: list[PomodoroSession]) -> list[PomodoroSession]:
    return [p for p in pomos if p.completed]


def analytics_summary(db: Session) -> dict:
    """Headline stats for the Analytics page stat cards."""
    user = db.query(User).first()
    pomos = _completed_focus(db.query(PomodoroSession).all())
    assignments = db.query(Assignment).all()

    total_focus_minutes = sum((p.duration_minutes or 0) for p in pomos)
    week_ago = datetime.now() - timedelta(days=7)
    weekly_focus_minutes = sum(
        (p.duration_minutes or 0)
        for p in pomos
        if p.start_time is not None and p.start_time >= week_ago
    )

    completed_count = sum(1 for a in assignments if a.status == "Completed")
    completion_rate = round(completed_count / len(assignments) * 100, 1) if assignments else 0.0

    gpa = _cumulative_gpa(db)

    return {
        "total_focus_minutes": total_focus_minutes,
        "weekly_focus_minutes": weekly_focus_minutes,
        "completed_assignments": completed_count,
        "total_assignments": len(assignments),
        "completion_rate": completion_rate,
        "gpa": gpa,
        "total_xp": user.total_xp if user else 0,
        "level": user.current_level if user else 0,
        "current_streak": user.current_streak if user else 0,
    }


def weekly_focus(db: Session, weeks: int = 8) -> list[dict]:
    """Focus minutes per ISO week for the last ``weeks`` weeks (for the bars)."""
    pomos = _completed_focus(db.query(PomodoroSession).all())
    today = date.today()
    start_iso = today.isocalendar()

    buckets: list[dict] = []
    for offset in range(weeks - 1, -1, -1):
        # Anchor: this week's Monday minus offset*7 days.
        monday = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
        label = f"{monday.isoformat()}"
        buckets.append({"week": monday.isoformat(), "label": label, "minutes": 0})

    for p in pomos:
        if p.start_time is None:
            continue
        d = p.start_time.date()
        monday = d - timedelta(days=d.weekday())
        for bucket in buckets:
            if bucket["week"] == monday.isoformat():
                bucket["minutes"] += p.duration_minutes or 0
                break
    return buckets


def focus_heatmap(db: Session, weeks: int = 52) -> list[dict]:
    """Per-day focus minutes for the last ``weeks``*7 days (GitHub-style)."""
    pomos = _completed_focus(db.query(PomodoroSession).all())
    by_date: dict[str, int] = {}
    for p in pomos:
        if p.start_time is None:
            continue
        key = p.start_time.date().isoformat()
        by_date[key] = by_date.get(key, 0) + (p.duration_minutes or 0)

    today = date.today()
    days: list[dict] = []
    for i in range(weeks * 7 - 1, -1, -1):
        d = today - timedelta(days=i)
        minutes = by_date.get(d.isoformat(), 0)
        days.append({"date": d.isoformat(), "minutes": minutes})
    return days


def _cumulative_gpa(db: Session) -> float | None:
    pairs: list[tuple[float, int]] = []
    for course in db.query(Course).all():
        grades = db.query(Grade).filter(Grade.course_id == course.id).all()
        weights = db.query(CourseWeight).filter(CourseWeight.course_id == course.id).all()
        result = grade_calc.calculate_course_grade(
            [
                {"points_earned": g.points_earned, "points_possible": g.points_possible, "category_id": g.category_id}
                for g in grades
            ],
            [{"id": w.id, "weight": w.weight} for w in weights],
        )
        if result and result["percentage"] is not None:
            pairs.append((result["percentage"], course.credits or 3))
    return grade_calc.cumulative_gpa(pairs)
