"""Aggregation helpers for the Gamified Quest Centre dashboard."""
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models import Character, Quest, Task, User

DONE_STATUSES = {"Done", "Completed"}

LEVEL_XP = 1000  # XP required per character level


def group_by_priority(db: Session) -> dict[str, list[dict[str, Any]]]:
    """Bucket open Quests + Tasks into High / Medium / Low folders.

    Each item carries ``title``, ``time_estimate`` (minutes), ``id``, and a
    ``kind`` marker (``quest`` | ``task``). Tasks have no ``time_estimate``
    column, so they report ``None``.
    """
    buckets: dict[str, list[dict[str, Any]]] = {"High": [], "Medium": [], "Low": []}

    quests = db.query(Quest).filter(~Quest.status.in_(DONE_STATUSES)).all()
    for q in quests:
        prio = (q.priority or "Medium").strip().capitalize()
        if prio in buckets:
            buckets[prio].append(
                {"title": q.title, "time_estimate": q.time_estimate, "id": q.id, "kind": "quest"}
            )

    tasks = db.query(Task).filter(~Task.status.in_(DONE_STATUSES)).all()
    for t in tasks:
        prio = (t.priority_tag or "Medium").strip().capitalize()
        if prio in buckets:
            buckets[prio].append(
                {"title": t.title, "time_estimate": None, "id": t.id, "kind": "task"}
            )

    return buckets


def status_window_data(db: Session) -> dict[str, Any]:
    """Assemble the sidebar Status-Window payload.

    Returns ``{character, xp_to_next, today_tasks}`` where ``character`` merges
    the character row with the owning user's gamification fields
    (``avatar_class``, ``current_streak``), ``xp_to_next`` is the XP remaining
    to the next level (``LEVEL_XP - (xp % LEVEL_XP)``), and ``today_tasks`` are
    quests due today or completed today.
    """
    char = db.query(Character).order_by(Character.id).first()
    today = date.today()

    character = None
    xp_to_next = None
    if char:
        user = db.query(User).filter(User.id == char.user_id).first()
        character = {
            "id": char.id,
            "name": char.name,
            "class_name": char.class_name,
            "level": char.level,
            "xp": char.xp,
            "avatar_class": user.avatar_class if user else None,
            "current_streak": user.current_streak if user else 0,
        }
        xp_to_next = LEVEL_XP - (char.xp % LEVEL_XP)

    today_quests = (
        db.query(Quest)
        .filter(Quest.due_date == today)
        .order_by(Quest.id)
        .all()
    )
    completed_today = (
        db.query(Quest)
        .filter(Quest.status == "Completed")
        .order_by(Quest.id)
        .all()
    )
    # Due today OR completed today (completion date approximated by updated_at)
    seen: set[int] = set()
    today_tasks: list[dict[str, Any]] = []
    for q in list(today_quests) + list(completed_today):
        if q.id in seen:
            continue
        completed = q.status in DONE_STATUSES and (q.updated_at and q.updated_at.date() == today)
        if q.status in DONE_STATUSES and not completed:
            continue  # completed on an earlier day is not a today task
        seen.add(q.id)
        today_tasks.append(
            {
                "id": q.id,
                "title": q.title,
                "status": q.status,
                "due_date": str(q.due_date) if q.due_date else None,
                "xp_reward": q.xp_reward,
            }
        )

    return {
        "character": character,
        "xp_to_next": xp_to_next,
        "today_tasks": today_tasks,
    }


def progress_report(db: Session) -> dict[str, int]:
    """Compute Year / Month / Week / Day progress percentages.

    Mirrors the calendar math in the frontend ``ProgressBars`` widget
    (elapsed / period elapsed), extended with a Day bar for the quest-centre.
    ``db`` is accepted for signature consistency with the other helpers.
    """
    import calendar as _cal
    import datetime as _dt

    today = _dt.date.today()
    current = _dt.datetime.now()

    # Year: elapsed days / total days in current year
    year_start = _dt.date(today.year, 1, 1)
    year_end = _dt.date(today.year + 1, 1, 1)
    year_pct = round(((today - year_start).days / (year_end - year_start).days) * 100)

    # Month: (day - 1) / days in month
    days_in_month = _cal.monthrange(today.year, today.month)[1]
    month_pct = round(((today.day - 1) / days_in_month) * 100)

    # Week: day of week (Mon=0) / 7
    week_pct = round((today.weekday() / 7) * 100)

    # Day: elapsed hours (incl. minutes) / 24
    day_pct = round(((current.hour + current.minute / 60) / 24) * 100)

    return {
        "year": year_pct,
        "month": month_pct,
        "week": week_pct,
        "day": day_pct,
    }


def quests_by_date(db: Session) -> list[dict[str, Any]]:
    """Group quests by due date for the calendar.

    Returns a list of ``{"date": "YYYY-MM-DD", "quests": [{id, title, status,
    priority, category, xp_reward}]}`` ordered chronologically. Quests with a
    null ``due_date`` are excluded.
    """
    from collections import OrderedDict

    grouped: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()
    quests = (
        db.query(Quest)
        .filter(Quest.due_date.isnot(None))
        .order_by(Quest.due_date, Quest.id)
        .all()
    )
    for q in quests:
        day = str(q.due_date)
        grouped.setdefault(day, []).append(
            {
                "id": q.id,
                "title": q.title,
                "status": q.status,
                "priority": q.priority,
                "category": q.category,
                "xp_reward": q.xp_reward,
            }
        )
    return [{"date": day, "quests": items} for day, items in grouped.items()]
