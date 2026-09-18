from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Habit, HabitLog, User
from app.schemas.habit import (
    HabitArchiveRequest, HabitCreate, HabitResponse,
    HabitLogCreate, HabitLogResponse, HabitLogReorder, HabitLogUpdate,
)
from app.services.habit_xp import GOOD, BAD, record_log

router = APIRouter(prefix="/api", tags=["habits"])


@router.get("/habits", response_model=List[HabitResponse])
def list_habits(
    include_archived: bool = False,
    type: Optional[str] = Query(None, description="Filter by habit_type: good / bad"),
    db: Session = Depends(get_db),
):
    q = db.query(Habit)
    if not include_archived:
        q = q.filter(Habit.is_archived == False)  # noqa: E712
    if type in (GOOD, BAD):
        q = q.filter(Habit.habit_type == type)
    return q.all()


@router.get("/habits/good", response_model=List[HabitResponse])
def list_good_habits(db: Session = Depends(get_db)):
    """Alias: only good habits (spec URL surface)."""
    return (
        db.query(Habit)
        .filter(Habit.habit_type == GOOD, Habit.is_archived == False)  # noqa: E712
        .all()
    )


@router.get("/habits/bad", response_model=List[HabitResponse])
def list_bad_habits(db: Session = Depends(get_db)):
    """Alias: only bad habits (spec URL surface)."""
    return (
        db.query(Habit)
        .filter(Habit.habit_type == BAD, Habit.is_archived == False)  # noqa: E712
        .all()
    )


@router.get("/habits/today")
def habits_today(db: Session = Depends(get_db)):
    """Did-Today aggregation: every habit with ``log_today`` + ``xp_today``."""
    today = date.today()
    habits = db.query(Habit).filter(Habit.is_archived == False).all()  # noqa: E712
    result = []
    for h in habits:
        log = (
            db.query(HabitLog)
            .filter(HabitLog.habit_id == h.id, HabitLog.date == today)
            .order_by(HabitLog.id.desc())
            .first()
        )
        result.append(
            {
                "id": h.id,
                "name": h.name,
                "habit_type": h.habit_type,
                "xp_reward": h.xp_reward,
                "xp_penalty": h.xp_penalty,
                "image_url": h.image_url,
                "current_streak": h.current_streak,
                "days_caught": h.days_caught,
                "log_today": bool(log),
                "xp_today": log.xp_change if log else 0,
                "status": log.status if log else None,
            }
        )
    return result


@router.get("/habits/heatmaps")
def habit_heatmaps_batch(db: Session = Depends(get_db)):
    """All habit heatmaps in one call (audit defect #51 — kills the N+1 loop)."""
    habits = db.query(Habit).filter(Habit.is_archived == False).all()  # noqa: E712
    return _heatmap_payload(db, habits)


@router.get("/habits/{habit_id}", response_model=HabitResponse)
def get_habit(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    return habit


@router.post("/habits", response_model=HabitResponse)
def create_habit(data: HabitCreate, db: Session = Depends(get_db)):
    habit = Habit(**data.model_dump())
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


@router.put("/habits/{habit_id}", response_model=HabitResponse)
def update_habit(habit_id: int, data: HabitCreate, db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    for key, val in data.model_dump().items():
        setattr(habit, key, val)
    db.commit()
    db.refresh(habit)
    return habit


@router.put("/habits/{habit_id}/goal", response_model=HabitResponse)
def update_habit_goal(habit_id: int, data: dict, db: Session = Depends(get_db)):
    """Fitness Hub (Phase 84): edit only the habit's goal text."""
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    habit.goal = data.get("goal")
    db.commit()
    db.refresh(habit)
    return habit


@router.delete("/habits/{habit_id}")
def delete_habit(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    db.delete(habit)
    db.commit()
    return {"ok": True}


@router.post("/habits/{habit_id}/archive", response_model=HabitResponse)
def archive_habit(
    habit_id: int,
    data: Optional[HabitArchiveRequest] = None,
    db: Session = Depends(get_db),
):
    """Archive a habit, recording why (audit defect #49).

    ``reason`` defaults to a plain manual archive; when a vault document drove
    the archive, its id is stored too so the Archive page can link back to it.
    """
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    habit.is_archived = True
    habit.archived_reason = (data.reason if data and data.reason else "Archived manually")
    if data and data.document_id is not None:
        habit.archived_document_id = data.document_id
    db.commit()
    db.refresh(habit)
    return habit


@router.post("/habits/{habit_id}/unarchive", response_model=HabitResponse)
def unarchive_habit(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    habit.is_archived = False
    # The provenance describes the archive, not the active habit — clear it.
    habit.archived_reason = None
    habit.archived_document_id = None
    db.commit()
    db.refresh(habit)
    return habit


# Habit Logs
@router.get("/habits/{habit_id}/logs", response_model=List[HabitLogResponse])
def list_habit_logs(habit_id: int, db: Session = Depends(get_db)):
    return db.query(HabitLog).filter(HabitLog.habit_id == habit_id).all()


@router.post("/habit-logs", response_model=HabitLogResponse)
def create_habit_log(data: HabitLogCreate, db: Session = Depends(get_db)):
    """Log a completion; award/penalize XP via the habit_xp engine."""
    habit = db.query(Habit).filter(Habit.id == data.habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")

    if data.completed:
        user = db.query(User).filter(User.id == habit.user_id).first()
        if user:
            # record_log infers type/status/xp_change from habit.habit_type
            # (Phase 16): good → +xp_reward, bad → -xp_penalty.
            return record_log(db, habit, user, data.date)

    log = HabitLog(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.put("/habit-logs/{log_id}", response_model=HabitLogResponse)
def update_habit_log(log_id: int, data: HabitLogUpdate, db: Session = Depends(get_db)):
    log = db.query(HabitLog).filter(HabitLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "Habit log not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(log, key, val)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/habit-logs/{log_id}")
def delete_habit_log(log_id: int, db: Session = Depends(get_db)):
    log = db.query(HabitLog).filter(HabitLog.id == log_id).first()
    if not log:
        raise HTTPException(404, "Habit log not found")
    db.delete(log)
    db.commit()
    return {"ok": True}


@router.get("/habit-logs/calendar")
def habit_logs_calendar(
    type: Optional[str] = Query(None, description="good / bad"),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Completed-habit calendar rows: HabitLogs grouped by date."""
    from collections import OrderedDict

    today = date.today()
    start = start or today - timedelta(days=6)
    end = end or today
    q = db.query(HabitLog).filter(HabitLog.date >= start, HabitLog.date <= end)
    if type in (GOOD, BAD):
        q = q.filter(HabitLog.type == type)
    logs = q.order_by(HabitLog.date, HabitLog.sort_order, HabitLog.id).all()

    habits = {h.id: h for h in db.query(Habit).all()}
    grouped: "OrderedDict[str, list[dict]]" = OrderedDict()
    for l in logs:
        day = str(l.date)
        grouped.setdefault(day, []).append(
            {
                "id": l.id,
                "habit_id": l.habit_id,
                "habit_name": habits[l.habit_id].name if l.habit_id in habits else "Unknown",
                "habit_type": l.type,
                "status": l.status,
                "xp_change": l.xp_change,
                "count": l.count,
                "completed": l.completed,
                "sort_order": l.sort_order,
            }
        )
    return [{"date": day, "logs": items} for day, items in grouped.items()]


@router.post("/habit-logs/reorder")
def reorder_habit_logs(data: HabitLogReorder, db: Session = Depends(get_db)):
    """Persist a day column's visual order (Phase 91 drag-and-drop).

    ``log_ids`` lists the ids in their new top-to-bottom order; each log's
    ``sort_order`` is set to its index. Logs not listed are left untouched.
    """
    for index, log_id in enumerate(data.log_ids):
        log = db.query(HabitLog).filter(HabitLog.id == log_id).first()
        if not log:
            raise HTTPException(404, f"Habit log {log_id} not found")
        log.sort_order = index
    db.commit()
    return {"ok": True, "reordered": len(data.log_ids)}


@router.get("/habits/{habit_id}/stats")
def habit_stats(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")

    today = date.today()
    first_of_month = today.replace(day=1)
    logs = db.query(HabitLog).filter(
        HabitLog.habit_id == habit_id,
        HabitLog.date >= first_of_month,
        HabitLog.date <= today,
    ).all()

    completed = {str(l.date): l for l in logs if l.completed}
    records_this_month = len(completed)
    days_elapsed = (today - first_of_month).days + 1
    days_missed = days_elapsed - records_this_month

    is_new_record = habit.current_streak > 0 and habit.current_streak >= habit.longest_streak

    # Streak graph: walk the past 30 days oldest -> newest; each point carries the
    # consecutive-streak count ending at that date, so the last point = current streak.
    streak_graph = []
    run = 0
    day = today - timedelta(days=29)
    for _ in range(30):
        if str(day) in completed:
            run += 1
        else:
            run = 0
        streak_graph.append({"date": str(day), "streak_length": run})
        day = day + timedelta(days=1)

    return {
        "records_this_month": records_this_month,
        "days_missed": days_missed,
        "days_in_month": days_elapsed,
        "is_new_record": is_new_record,
        "streak_graph": streak_graph,
    }


@router.get("/habits/{habit_id}/heatmap")
def habit_heatmap(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id).first()
    if not habit:
        raise HTTPException(404, "Habit not found")
    return _heatmap_payload(db, [habit])[str(habit_id)]


def _heatmap_payload(db: Session, habits: List[Habit]) -> dict:
    """Build the 30-day heatmap payload for every habit in one query."""
    today = date.today()
    start = today - timedelta(days=29)
    logs = db.query(HabitLog).filter(
        HabitLog.date >= start,
        HabitLog.date <= today,
    ).all()
    by_habit_date: dict = {}
    for log in logs:
        by_habit_date[(log.habit_id, str(log.date))] = log

    out = {}
    for habit in habits:
        days = []
        day = start
        for _ in range(30):
            log = by_habit_date.get((habit.id, str(day)))
            days.append({
                "date": str(day),
                "completed": bool(log and log.completed),
                "count": log.count if log else 0,
            })
            day = day + timedelta(days=1)
        out[str(habit.id)] = {"month": today.strftime("%B %Y"), "days": days}
    return out
