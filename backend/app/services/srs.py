"""Shared FSRS scheduling helpers (Idea 52 — spaced repetition).

Replaces the classic SM-2 update in ``app/services/kb/revision.py`` with the
FSRS engine vendored from ``open-spaced-repetition/py-fsrs`` (MIT), and gives
flashcards the same scheduler.

Design notes
------------
- **Day-granularity for both topics and cards.** The upstream default learning
  steps (1 min / 10 min) are sub-day, which is wrong for topic reviews and for
  cards we don't want to re-show within a session. We configure the scheduler
  with *empty* learning/relearning steps so every card graduates straight to
  the ``Review`` state on its first review (Anki-style "learn steps = none").
  ``Again`` then schedules a shortened review-state interval instead of a
  minute-later re-show.
- **Determinism.** ``enable_fuzzing=False`` makes FSRS fully deterministic so
  unit tests can assert exact intervals.
- **Rating mapping (grade 0–5 → FSRS rating).** The existing review endpoints
  accept a 0–5 grade. 0–1 → ``Again``, 2 → ``Hard``, 3 → ``Good``, 4–5 →
  ``Easy``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.fsrs import Card, Rating, Scheduler, State

# Ease adjustment per the old SM-2 formula, kept ONLY as a display-friendly
# "how fast is this item advancing" indicator. FSRS drives the actual
# scheduling via stability/difficulty; this value is not used in any schedule
# computation anymore.
def _ease_delta(grade: int) -> float:
    x = 5 - grade
    return 0.1 - x * (0.08 + x * 0.02)


def grade_to_rating(grade: int) -> Rating:
    """Map a 0–5 review grade to an FSRS 1–4 rating."""
    grade = max(0, min(5, int(grade)))
    if grade <= 1:
        return Rating.Again
    if grade == 2:
        return Rating.Hard
    if grade == 3:
        return Rating.Good
    return Rating.Easy


def make_scheduler(max_interval_days: int) -> Scheduler:
    """Day-granularity, deterministic FSRS scheduler (empty learn/relearn steps)."""
    return Scheduler(
        learning_steps=(),
        relearning_steps=(),
        maximum_interval=max(1, int(max_interval_days)),
        enable_fuzzing=False,
    )


def card_from_state(
    *,
    card_id: int,
    state: int | None,
    step: int | None,
    stability: float | None,
    difficulty: float | None,
    due: datetime | None,
    last_review: datetime | None,
) -> Card:
    """Rehydrate an FSRS Card from persisted columns (UTC naive → aware)."""
    return Card(
        card_id=card_id,
        state=State(state) if state is not None else State.Learning,
        step=step,
        stability=stability,
        difficulty=difficulty,
        due=_as_utc(due) if due is not None else None,
        last_review=_as_utc(last_review) if last_review is not None else None,
    )


def _as_utc(dt: datetime) -> datetime:
    """Treat naive stored datetimes as UTC (the app stores UTC).

    Accepts plain ``date`` objects too (some code backdates ``due_date`` with
    ``date.today()``) — a date is interpreted as midnight UTC.
    """
    if not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def interval_days(card: Card, review_datetime: datetime) -> int:
    """Days until the next due date, for API/display compatibility."""
    return max(0, (card.due - review_datetime).days)


def update_legacy_ease(current: float, grade: int, min_ease: float = 1.3) -> float:
    """Display ease updated with the SM-2 formula (see module docstring)."""
    return max(min_ease, round((current or 2.5) + _ease_delta(grade), 4))


__all__ = [
    "grade_to_rating",
    "make_scheduler",
    "card_from_state",
    "interval_days",
    "update_legacy_ease",
]
