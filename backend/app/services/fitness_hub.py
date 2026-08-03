"""Fitness Hub aggregation helpers (99-phase plan, Phases 5-7, 35-38).

Composable helpers shared by the ``fitness`` router (weight-goal, membership)
and the ``fitness_hub`` summary router.
"""
import json
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    DietPlan,
    Expense,
    Exercise,
    Habit,
    HabitLog,
    MuscleGroup,
    PersonalRecord,
    User,
    WorkoutSplit,
)

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def weight_progress(user: Optional[User]) -> Optional[dict]:
    """Phase 5: initial → current → target progress (percent clamped 0-100)."""
    if not user or user.initial_weight is None or user.current_weight is None or user.target_weight is None:
        return None
    initial = user.initial_weight or 0
    current = user.current_weight or 0
    target = user.target_weight or 0
    if target == initial:
        percent = 100.0 if current >= target else 0.0
    else:
        percent = (current - initial) / (target - initial) * 100
    return {
        "initial": initial,
        "current": current,
        "target": target,
        "percent": max(0.0, min(100.0, round(percent, 1))),
    }


def pr_summary(db: Session, user: Optional[User]) -> list[dict]:
    """Phase 6: per-lift current/target/percent from PersonalRecord rows."""
    q = db.query(PersonalRecord)
    if user:
        q = q.filter(PersonalRecord.user_id == user.id)
    rows = q.all()
    return [
        {
            "id": r.id,
            "exercise_name": r.exercise_name,
            "current_weight": r.current_weight,
            "target_weight": r.target_weight,
            "unit": r.unit,
            "percent": (
                max(0.0, min(100.0, round(r.current_weight / r.target_weight * 100, 1)))
                if r.target_weight
                else 0.0
            ),
        }
        for r in rows
    ]


def membership_info(user: Optional[User]) -> dict:
    """Phase 33: membership status + next payment countdown."""
    if not user:
        return {"membership_status": "Active", "next_payment_date": None, "days_to_payment": None}
    days = None
    if user.next_payment_date:
        days = (user.next_payment_date - date.today()).days
    return {
        "membership_status": user.membership_status or "Active",
        "next_payment_date": str(user.next_payment_date) if user.next_payment_date else None,
        "days_to_payment": days,
    }


def habit_heatmap_json(db: Session, habit: Habit, days: int = 49) -> list[dict]:
    """Phase 7: 7x7 grid (last ``days`` days) serialized from HabitLogs.

    Each cell: ``{date, completed, count}``. Prefers the cached
    ``heatmap_data`` JSON when present and fresh (same window), else derives
    from live HabitLog rows and refreshes the cache.
    """
    today = date.today()
    start = today - timedelta(days=days - 1)
    try:
        cached = json.loads(habit.heatmap_data) if habit.heatmap_data else None
        if cached and len(cached) == days and cached[0].get("date") == str(start) and cached[-1].get("date") == str(today):
            return cached
    except (ValueError, TypeError, AttributeError):
        cached = None

    logs = (
        db.query(HabitLog)
        .filter(HabitLog.habit_id == habit.id, HabitLog.date >= start, HabitLog.date <= today)
        .all()
    )
    by_date = {str(l.date): l for l in logs}
    grid = []
    day = start
    for _ in range(days):
        log = by_date.get(str(day))
        grid.append(
            {
                "date": str(day),
                "completed": bool(log and log.completed),
                "count": log.count if log else 0,
            }
        )
        day = day + timedelta(days=1)
    habit.heatmap_data = json.dumps(grid)
    return grid


def spec_habits_heatmap(db: Session, habit_rows: list[Habit]) -> list[dict]:
    """Phase 37: the 4 spec habits with goal / days-completed / percent / 7x7 grid."""
    out = []
    for h in habit_rows:
        grid = habit_heatmap_json(db, h, 49)
        completed_days = sum(1 for cell in grid if cell["completed"])
        percent = round(completed_days / len(grid) * 100, 1) if grid else 0.0
        out.append(
            {
                "id": h.id,
                "name": h.name,
                "goal": h.goal,
                "days_completed": completed_days,
                "percent": percent,
                "heatmap_7x7": grid,
            }
        )
    return out


def weekly_split(db: Session, user: Optional[User], week_number: int = 1) -> list[dict]:
    """Phase 36: ordered Mon-Sat {day, split_name, exercises:[...]} for a week."""
    q = db.query(WorkoutSplit).filter(WorkoutSplit.week_number == week_number)
    if user:
        q = q.filter(WorkoutSplit.user_id == user.id)
    rows = q.order_by(WorkoutSplit.day_of_week, WorkoutSplit.id).all()
    by_day: dict[int, dict] = {}
    for r in rows:
        try:
            exercises = json.loads(r.exercise_list) if r.exercise_list else []
        except (ValueError, TypeError):
            exercises = []
        by_day.setdefault(
            r.day_of_week,
            {"id": r.id, "split_name": r.split_name, "exercises": exercises},
        )
    out = []
    for dow in range(6):  # Mon-Sat
        entry = by_day.get(dow)
        split_name = entry["split_name"] if entry else "REST"
        exercises = entry["exercises"] if entry else []
        out.append(
            {
                "day": WEEKDAY_LABELS[dow],
                "day_of_week": dow,
                "split_name": split_name,
                "exercises": exercises,
            }
        )
    return out


def muscle_group_overview(db: Session, user: Optional[User]) -> list[dict]:
    """Phase 38: muscle groups with exercise counts."""
    q = db.query(MuscleGroup).order_by(MuscleGroup.sort_order, MuscleGroup.id)
    if user:
        q = q.filter(MuscleGroup.user_id == user.id)
    groups = q.all()
    counts = {
        gid: n
        for gid, n in (
            db.query(Exercise.muscle_group_id, Exercise.id)
            .group_by(Exercise.muscle_group_id)
            .all()
        )
    }
    return [
        {
            "id": g.id,
            "name": g.name,
            "body_part": g.body_part,
            "image_3d_url": g.image_3d_url,
            "exercise_count": counts.get(g.id, 0),
        }
        for g in groups
    ]


def expenses_summary(db: Session, user: Optional[User]) -> dict:
    """Phase 29: expense totals by category."""
    q = db.query(Expense)
    if user:
        q = q.filter(Expense.user_id == user.id)
    rows = q.all()
    by_category: dict[str, float] = {"Supplement": 0.0, "Equipment": 0.0, "Gym": 0.0}
    total = 0.0
    for r in rows:
        cat = r.category or "Supplement"
        by_category[cat] = by_category.get(cat, 0.0) + (r.cost or 0.0)
        total += r.cost or 0.0
    return {"total": round(total, 2), "by_category": by_category}


def diet_plans(db: Session, user: Optional[User]) -> list[dict]:
    """Active + inactive diet plans ordered by sort_order."""
    q = db.query(DietPlan).order_by(DietPlan.sort_order, DietPlan.id)
    if user:
        q = q.filter(DietPlan.user_id == user.id)
    return [
        {"id": p.id, "title": p.title, "is_active": p.is_active, "sort_order": p.sort_order}
        for p in q.all()
    ]


def fitness_hub_summary(db: Session, user: Optional[User]) -> dict:
    """Phase 35: single aggregated payload for the fitness-hub sidebar + rows."""
    return {
        "weight_goal": weight_progress(user),
        "pr_tracker": pr_summary(db, user),
        "membership": membership_info(user),
        "diet_plans": diet_plans(db, user),
        "expenses_summary": expenses_summary(db, user),
        "weekly_split": {1: weekly_split(db, user, 1), 2: weekly_split(db, user, 2)},
        "muscle_groups": muscle_group_overview(db, user),
        "spec_habits": spec_habits_heatmap(db, _spec_habits(db, user)),
    }


def _spec_habits(db: Session, user: Optional[User]) -> list[Habit]:
    """The 4 spec fitness habits (Workout, 3000 Kcal, 4L water, Supplements)."""
    names = ["Workout", "3000 Kcal Diet", "Drink 4L water", "Take all supplements"]
    by_name = {h.name: h for h in db.query(Habit).all()}
    return [by_name[n] for n in names if n in by_name]
