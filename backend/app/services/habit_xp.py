"""Gamification engine for the Gamified Habit Tracker (\"Gold & Punishment\").

Each helper is deliberately small and unit-testable. The single wallet model:
good-habit completions add ``xp_reward`` and bad-habit admissions subtract
``xp_penalty`` from BOTH the owning ``User.total_xp`` and the linked
``Character.xp`` (mirrors ``quest_centre`` + reward claims so every feature
draws from the same pool).
"""
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models import Character, Habit, HabitLog, LifeArea, User

GOOD = "good"
BAD = "bad"

LEVEL_XP = 1000  # XP required per character level (mirrors quest_centre)

DONE_STATUS = "Completed"
BAD_STATUS = "Shit I did it"


def _character_for(db: Session, user: User) -> Character | None:
    return db.query(Character).filter(Character.user_id == user.id).first()


# ---------------------------------------------------------------------------
# Phase 10 — Good-habit completion XP award
# ---------------------------------------------------------------------------
def award_good_habit(db: Session, habit: Habit, user: User) -> int:
    """Add ``habit.xp_reward`` to the user + character wallet; return xp_change."""
    xp_change = habit.xp_reward or 0
    user.total_xp = (user.total_xp or 0) + xp_change
    char = _character_for(db, user)
    if char:
        char.xp = (char.xp or 0) + xp_change
        # Level only ever rises (mirrors the characters router): a level stored
        # above the xp-derived value must never be downgraded by a habit log.
        new_level = char.xp // LEVEL_XP + 1
        if new_level > (char.level or 1):
            char.level = new_level
    return xp_change


# ---------------------------------------------------------------------------
# Phase 11 — Bad-habit penalty
# ---------------------------------------------------------------------------
def penalize_bad_habit(db: Session, habit: Habit, user: User) -> int:
    """Subtract ``habit.xp_penalty`` from both wallets, floored at 0."""
    xp_change = -(habit.xp_penalty or 0)
    user.total_xp = max((user.total_xp or 0) + xp_change, 0)
    char = _character_for(db, user)
    if char:
        char.xp = max((char.xp or 0) + xp_change, 0)
    return xp_change


# ---------------------------------------------------------------------------
# Phase 12 — Streak / days_caught increment
# ---------------------------------------------------------------------------
def bump_streak(habit: Habit) -> None:
    """Good → ``current_streak += 1`` (+ longest); Bad → ``days_caught += 1``."""
    if habit.habit_type == BAD:
        habit.days_caught = (habit.days_caught or 0) + 1
    else:
        habit.current_streak = (habit.current_streak or 0) + 1
        if habit.current_streak > (habit.longest_streak or 0):
            habit.longest_streak = habit.current_streak


# ---------------------------------------------------------------------------
# Phase 13 — HabitLog xp_change writer
# ---------------------------------------------------------------------------
def record_log(
    db: Session,
    habit: Habit,
    user: User,
    log_date: date | None = None,
) -> HabitLog:
    """Persist a spec-consistent ``HabitLog`` and apply XP + streak side effects.

    Good habit → ``status="Completed"`` + ``+xp_reward``.
    Bad habit  → ``status="Shit I did it"`` + ``-xp_penalty``.
    """
    is_good = habit.habit_type == GOOD
    xp_change = award_good_habit(db, habit, user) if is_good else penalize_bad_habit(db, habit, user)
    bump_streak(habit)
    log = HabitLog(
        habit_id=habit.id,
        date=log_date or date.today(),
        completed=True,
        count=1,
        type=habit.habit_type,
        status=DONE_STATUS if is_good else BAD_STATUS,
        xp_change=xp_change,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# Phase 14 — Life-area XP attribution
# ---------------------------------------------------------------------------
def credit_life_area(db: Session, area: LifeArea, xp_change: int) -> None:
    """Attribute a positive XP change to a life area's all-time total."""
    if xp_change > 0:
        area.total_xp_earned = (area.total_xp_earned or 0) + xp_change
    db.commit()


# ---------------------------------------------------------------------------
# Phase 15 — Gamification summary helper
# ---------------------------------------------------------------------------
def habit_gamification_summary(db: Session) -> dict[str, Any]:
    """Aggregate ``{total_xp, level, current_streak, good_today, bad_today, xp_to_next}``."""
    today = date.today()
    user = db.query(User).order_by(User.id).first()
    char = _character_for(db, user) if user else None

    xp = char.xp if char else (user.total_xp if user else 0)
    level = char.level if char else (user.current_level if user else 1)

    good_today = 0
    bad_today = 0
    habits = db.query(Habit).filter(Habit.is_archived == False).all()  # noqa: E712
    for h in habits:
        logged = (
            db.query(HabitLog)
            .filter(HabitLog.habit_id == h.id, HabitLog.date == today)
            .first()
        )
        if not logged:
            continue
        if h.habit_type == BAD:
            bad_today += 1
        else:
            good_today += 1

    return {
        "total_xp": xp,
        "level": level,
        "current_streak": user.current_streak if user else 0,
        "good_today": good_today,
        "bad_today": bad_today,
        "xp_to_next": LEVEL_XP - (xp % LEVEL_XP),
    }
