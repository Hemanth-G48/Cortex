"""Gamified Habit Tracker dashboard endpoints.

Composes the ``habit_xp`` service helpers + the spec data model into the
payload shapes consumed by the GamifiedHabitTracker page widgets:
sidebar Status-Window, Row-1 progress/life-areas, and the aggregate summary.
"""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Character, Habit, HabitLog, LifeArea, Reward, User
from app.services.habit_xp import BAD, LEVEL_XP, habit_gamification_summary

router = APIRouter(prefix="/api", tags=["habit-tracker"])


@router.get("/habit-tracker/status-window")
def habit_tracker_status_window(db: Session = Depends(get_db)):
    """Sidebar Status-Window: wizard card + habit \"Today's Stats\" list."""
    user = db.query(User).order_by(User.id).first()
    char = db.query(Character).order_by(Character.id).first()
    today = date.today()

    character = None
    xp_to_next = None
    if char:
        owner = db.query(User).filter(User.id == char.user_id).first()
        character = {
            "id": char.id,
            "name": char.name,
            "class_name": char.class_name,
            "level": char.level,
            "xp": char.xp,
            "avatar_class": owner.avatar_class if owner else (user.avatar_class if user else None),
            "current_streak": owner.current_streak if owner else (user.current_streak if user else 0),
        }
        xp_to_next = LEVEL_XP - (char.xp % LEVEL_XP)

    logs = db.query(HabitLog).filter(HabitLog.date == today).order_by(HabitLog.id).all()
    habits = {h.id: h for h in db.query(Habit).all()}
    today_stats = []
    for log in logs:
        h = habits.get(log.habit_id)
        today_stats.append(
            {
                "id": log.id,
                "habit_id": log.habit_id,
                "habit_name": h.name if h else "Unknown",
                "habit_type": log.type or (h.habit_type if h else "good"),
                "status": log.status,
                "xp_change": log.xp_change,
            }
        )

    return {
        "character": character,
        "xp_to_next": xp_to_next,
        "today_habits": today_stats,
    }


@router.get("/habit-tracker/summary")
def habit_tracker_summary(db: Session = Depends(get_db)):
    """Aggregate: counts, wallet, life-area totals and available rewards."""
    today = date.today()
    habits = db.query(Habit).filter(Habit.is_archived == False).all()  # noqa: E712
    good = [h for h in habits if h.habit_type != BAD]
    bad = [h for h in habits if h.habit_type == BAD]

    good_today = 0
    bad_today = 0
    for h in habits:
        logged = (
            db.query(HabitLog)
            .filter(HabitLog.habit_id == h.id, HabitLog.date == today)
            .first()
        )
        if logged:
            if h.habit_type == BAD:
                bad_today += 1
            else:
                good_today += 1

    areas = db.query(LifeArea).order_by(LifeArea.sort_order, LifeArea.id).all()
    rewards = (
        db.query(Reward)
        .filter(Reward.is_available == True)  # noqa: E712
        .order_by(Reward.xp_cost)
        .all()
    )
    summary = habit_gamification_summary(db)

    return {
        **summary,
        "good_count": len(good),
        "bad_count": len(bad),
        "good_today": good_today,
        "bad_today": bad_today,
        "life_areas": [
            {
                "id": area.id,
                "name": area.name,
                "goal": area.goal,
                "image_url": area.image_url,
                "status": area.status,
                "progress_percent": area.progress_percent,
                "sort_order": area.sort_order,
                "total_xp_earned": area.total_xp_earned,
            }
            for area in areas
        ],
        "rewards_available": [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "xp_cost": r.xp_cost,
                "image_url": r.image_url,
                "category": r.category,
                "is_available": r.is_available,
                "claimed_date": str(r.claimed_date) if r.claimed_date else None,
            }
            for r in rewards
        ],
    }
