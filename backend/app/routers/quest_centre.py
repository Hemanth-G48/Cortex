"""Gamified Quest Centre dashboard endpoints.

Each route composes the aggregation helpers from ``app.services.quest_centre``
into the shapes consumed by the quest-centre frontend widgets.
"""
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LifeArea, ScheduleEvent, User
from app.services.quest_centre import (
    group_by_priority,
    progress_report,
    quests_by_date,
    status_window_data,
)

router = APIRouter(prefix="/api", tags=["quest-centre"])


@router.get("/quest-centre/status-window")
def get_status_window(db: Session = Depends(get_db)):
    """Sidebar Status-Window: character card, XP-to-next, today's task checklist."""
    return status_window_data(db)


@router.get("/quest-centre/progress")
def get_progress(db: Session = Depends(get_db)):
    """Year / Month / Week / Day progress percentages (macroscopic bars)."""
    return progress_report(db)


@router.get("/quest-centre/priority-window")
def get_priority_window(db: Session = Depends(get_db)):
    """High / Medium / Low folder buckets from open Quests + Tasks."""
    return group_by_priority(db)


@router.get("/quest-centre/quick-actions")
def get_quick_actions():
    """Available create targets for the Quick-Action list.

    The frontend opens its existing create modals for these targets; the
    endpoint is kept spec-consistent so the list stays data-driven.
    """
    return {
        "actions": [
            {"label": "Add New Quest", "kind": "quest", "route": "/quests"},
            {"label": "Add New Mission", "kind": "mission", "route": "/missions"},
            {"label": "Add New Life Area", "kind": "life_area", "route": "/life-areas"},
            {"label": "Add New Reward", "kind": "reward", "route": "/rewards"},
        ]
    }


@router.get("/quest-centre/life-areas")
def get_quest_centre_life_areas(db: Session = Depends(get_db)):
    """Life areas incl. ``target_days``, ``status`` and computed
    ``complete_in_days`` (``target_days - days since creation``)."""
    areas = db.query(LifeArea).order_by(LifeArea.sort_order, LifeArea.id).all()
    today = date.today()
    result: list[dict[str, Any]] = []
    for area in areas:
        days_since = (today - area.created_at.date()).days if area.created_at else 0
        complete_in_days = None
        if area.status == "Completed":
            complete_in_days = 0
        elif area.target_days is not None:
            complete_in_days = max(area.target_days - days_since, 0)
        result.append(
            {
                "id": area.id,
                "name": area.name,
                "goal": area.goal,
                "description": area.description,
                "image_url": area.image_url,
                "progress_percent": area.progress_percent,
                "target_days": area.target_days,
                "status": area.status,
                "sort_order": area.sort_order,
                "complete_in_days": complete_in_days,
            }
        )
    return result


@router.get("/quest-centre/calendar")
def get_quest_centre_calendar(db: Session = Depends(get_db)):
    """Quests grouped by due date, merged with the weekly ``ScheduleEvent`` rows
    so the calendar can plot quests and events on the same timeline."""
    events = db.query(ScheduleEvent).order_by(ScheduleEvent.day_of_week, ScheduleEvent.start_time).all()
    return {
        "quests_by_date": quests_by_date(db),
        "schedule_events": [
            {
                "id": e.id,
                "title": e.title,
                "day_of_week": e.day_of_week,
                "start_time": str(e.start_time) if e.start_time else None,
                "end_time": str(e.end_time) if e.end_time else None,
                "event_type": e.event_type,
                "reference_type": e.reference_type,
                "reference_id": e.reference_id,
                "color": e.color,
            }
            for e in events
        ],
    }


@router.get("/quest-centre/gamification")
def get_gamification_profile(
    user_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """User gamification profile: ``avatar_class``, ``current_streak``,
    ``total_xp``, ``current_level``. Defaults to the first user (local app)."""
    user = db.query(User).filter(User.id == user_id).first() if user_id else db.query(User).order_by(User.id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return {
        "id": user.id,
        "name": user.name,
        "avatar_class": user.avatar_class,
        "current_streak": user.current_streak,
        "total_xp": user.total_xp,
        "current_level": user.current_level,
    }
