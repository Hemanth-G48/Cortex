"""Phase 6 revision scheduling — FSRS (Idea 52).

``apply_review`` runs the Free Spaced Repetition Scheduler (py-fsrs, vendored
under ``app/services/fsrs`` — MIT) instead of the classic SM-2 update. FSRS
models per-item memory with stability + difficulty and schedules intervals
toward a target retention, which is measurably more accurate than SM-2 (the
algorithm Anki adopted in 2023).

Grade mapping: 0–1 → ``Again``, 2 → ``Hard``, 3 → ``Good``, 4–5 → ``Easy``
(see ``app/services/srs.py``). Each review also logs a ``revision``
LearningEvent so mastery and progress still move exactly as before. Due
reviews materialize into the daily schedule (phrase 16).

API compatibility: the endpoints and the response fields (``interval_days``,
``ease``, ``repetitions``, ``due_date``) are unchanged — ``interval_days`` is
now derived from the FSRS due date, ``ease`` is a legacy display indicator,
and ``repetitions`` is the successful-review counter.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import DailyScheduleItem, RevisionSchedule, Topic
from app.services.kb import utcnow
from app.services.kb.mastery import log_event
from app.services.srs import (
    card_from_state,
    grade_to_rating,
    interval_days,
    make_scheduler,
    update_legacy_ease,
)


def _scheduler() -> object:
    """FSRS scheduler bounded by the configured max interval (deterministic)."""
    return make_scheduler(settings.revision_max_interval)


def apply_review(
    db: Session,
    user_id: int,
    topic: Topic,
    grade: int,
    *,
    reviewed_at=None,
) -> RevisionSchedule:
    """FSRS update for a topic review (phrases 13–14). Grade is 0–5."""
    grade = max(0, min(5, int(grade)))
    reviewed_at = reviewed_at or utcnow()
    # The app stores naive UTC, but FSRS demands timezone-aware UTC.
    reviewed_at_utc = (
        reviewed_at.replace(tzinfo=timezone.utc)
        if reviewed_at.tzinfo is None
        else reviewed_at.astimezone(timezone.utc)
    )

    schedule = (
        db.query(RevisionSchedule)
        .filter(
            RevisionSchedule.user_id == user_id,
            RevisionSchedule.topic_id == topic.id,
        )
        .first()
    )
    if schedule is None:
        schedule = RevisionSchedule(
            user_id=user_id,
            topic_id=topic.id,
            interval_days=0,
            ease=2.5,
            repetitions=0,
            due_date=reviewed_at,
        )
        db.add(schedule)

    card = card_from_state(
        card_id=topic.id,
        state=schedule.state,
        step=schedule.step,
        stability=schedule.stability,
        difficulty=schedule.difficulty,
        due=schedule.due_date,
        last_review=schedule.last_reviewed_at,
    )
    rating = grade_to_rating(grade)
    card, _ = _scheduler().review_card(card, rating, review_datetime=reviewed_at_utc)

    # Persist FSRS state (naive UTC to match the app's storage convention).
    schedule.stability = card.stability
    schedule.difficulty = card.difficulty
    schedule.state = card.state.value
    schedule.step = card.step
    # Legacy/display columns (API compatibility).
    schedule.interval_days = interval_days(card, reviewed_at_utc)
    schedule.ease = update_legacy_ease(schedule.ease, grade, settings.revision_min_ease)
    schedule.repetitions = schedule.repetitions + 1 if grade >= 3 else 0
    schedule.due_date = card.due.replace(tzinfo=None)
    schedule.last_reviewed_at = reviewed_at

    # Mastery event: value = grade/5 so it feeds the score (phrase 72).
    log_event(db, user_id, event_type="revision", topic_id=topic.id, value=grade / 5.0)
    db.flush()
    return schedule


def first_review(db: Session, user_id: int, topic: Topic) -> RevisionSchedule:
    """Enter a topic into the schedule when first studied (phrase 17)."""
    existing = (
        db.query(RevisionSchedule)
        .filter(
            RevisionSchedule.user_id == user_id,
            RevisionSchedule.topic_id == topic.id,
        )
        .first()
    )
    if existing is not None:
        return existing
    now = utcnow()
    schedule = RevisionSchedule(
        user_id=user_id,
        topic_id=topic.id,
        interval_days=0,
        ease=2.5,
        repetitions=0,
        due_date=now,
    )
    db.add(schedule)
    db.flush()
    return schedule


def due_reviews(db: Session, user_id: int, on: date | None = None) -> list[dict]:
    """The user's revision queue (phrase 15): due today or earlier.

    When ``on`` is a ``date`` the bound is the *end* of that day, so a topic
    scheduled later today (e.g. ``utcnow()``) still counts as due today.
    """
    now = on or date.today()
    bound = (
        now
        if isinstance(now, datetime)
        else datetime.combine(now, time.max)
    )
    rows = (
        db.query(RevisionSchedule, Topic)
        .join(Topic, Topic.id == RevisionSchedule.topic_id)
        .filter(
            RevisionSchedule.user_id == user_id,
            RevisionSchedule.due_date <= bound,
        )
        .order_by(RevisionSchedule.due_date.asc())
        .all()
    )
    return [
        {
            "schedule_id": rs.id,
            "topic_id": t.id,
            "topic_name": t.name,
            "subject_id": t.subject_id,
            "interval_days": rs.interval_days,
            "ease": rs.ease,
            "repetitions": rs.repetitions,
            "due_date": rs.due_date.date().isoformat() if rs.due_date else None,
        }
        for rs, t in rows
    ]


def materialize_due(db: Session, user_id: int, on: date | None = None) -> int:
    """Materialize today's due reviews into the daily schedule (phrase 16).

    Idempotent: a schedule block for the same day + topic is skipped.
    """
    on = on or date.today()
    due = due_reviews(db, user_id, on=on)
    created = 0
    for item in due:
        existing = (
            db.query(DailyScheduleItem)
            .filter(
                DailyScheduleItem.user_id == user_id,
                DailyScheduleItem.date == on,
                DailyScheduleItem.activity == f"Review: {item['topic_name']}",
            )
            .first()
        )
        if existing is not None:
            continue
        db.add(
            DailyScheduleItem(
                user_id=user_id,
                date=on,
                time_range="17:00-17:30",
                activity=f"Review: {item['topic_name']}",
                category="Study Time",
                energy="Medium",
            )
        )
        created += 1
    db.flush()
    return created


def revision_state(db: Session, user_id: int, topic_id: int) -> dict | None:
    rs = (
        db.query(RevisionSchedule)
        .filter(
            RevisionSchedule.user_id == user_id,
            RevisionSchedule.topic_id == topic_id,
        )
        .first()
    )
    if rs is None:
        return None
    return {
        "topic_id": topic_id,
        "interval_days": rs.interval_days,
        "ease": rs.ease,
        "repetitions": rs.repetitions,
        "due_date": rs.due_date.date().isoformat() if rs.due_date else None,
        "last_reviewed_at": rs.last_reviewed_at.isoformat() if rs.last_reviewed_at else None,
        # FSRS state (new, additive — old clients ignore it).
        "stability": round(rs.stability, 4) if rs.stability is not None else None,
        "difficulty": round(rs.difficulty, 4) if rs.difficulty is not None else None,
        "state": rs.state,
    }
