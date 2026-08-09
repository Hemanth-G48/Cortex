"""Idea 90 — auto-create revision tasks (Phase 9 Automation).

The daily job turns ``revision_schedule`` rows with ``due_date <= today`` into
concrete ``Task`` rows (phrase 91) — title from the topic, deep-link metadata
in ``priority_quadrant`` is not needed; we keep it simple: a ``subject_tag``
set to the topic's subject id string and a due date of today (phrase 92). The
Phase 6 materializer also fills the daily schedule (phrase 16 of Idea 52),
and a Reminder is attached for the due date (phrase 93).

Micro-sessions (phrase 94) are created when the topic has a recommended chunk
(suggested status) so the student can dive straight into practice.

Completions feed back through the existing review flow — finishing the task's
linked review grades the topic and runs the SM-2 update (phrase 95) via the
Phase 6 revision router; this job only materializes.

Deterministic and idempotent (phrase 97): re-running skips tasks/reminders
that already exist for the same day + topic. No LLM cost → no ``budget_kind``.
"""

from __future__ import annotations

import logging
from datetime import date, time

from sqlalchemy.orm import Session

from app.models import (
    KbChunk,
    MicroSession,
    Notification,
    Reminder,
    RevisionSchedule,
    Task,
    Topic,
)
from app.services.kb.automation import auto_job
from app.services.kb.revision import due_reviews, materialize_due

logger = logging.getLogger(__name__)


def _task_title(topic_name: str) -> str:
    return f"Review: {topic_name}"


def _topic_by_id(db: Session, user_id: int, topic_id: int) -> Topic | None:
    return (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.id == topic_id)
        .first()
    )


def _recommended_chunk(
    db: Session, user_id: int, topic_id: int
) -> KbChunk | None:
    """Best-effort: the topic's first chunk (via its documents) for a micro-session."""
    rows = (
        db.query(KbChunk)
        .filter(KbChunk.user_id == user_id)
        .order_by(KbChunk.document_id.asc(), KbChunk.seq.asc())
        .all()
    )
    for chunk in rows:
        # Cheap topic-name match on the chunk content.
        topic = _topic_by_id(db, user_id, topic_id)
        if topic and (topic.name or "").lower() in (chunk.content or "").lower():
            return chunk
    return None


@auto_job(
    "auto_revision",
    toggle="KB_AUTO_REVISION_TASKS_ENABLED",
    cap="",
    description=(
        "Materialize due revision rows as tasks, reminders, and micro-sessions."
    ),
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Create tasks for today's due revisions, idempotently (phrases 91–94)."""
    due = due_reviews(db, user_id, on=date.today())
    if limit is not None:
        due = due[:limit]

    # Phase 6 materializer: also surface due reviews in the daily schedule.
    schedule_items = materialize_due(db, user_id, on=date.today())

    tasks_created = 0
    reminders_created = 0
    sessions_created = 0
    skipped = 0
    for item in due:
        topic = _topic_by_id(db, user_id, item["topic_id"])
        title = _task_title(item["topic_name"])
        today = date.today()

        existing_task = (
            db.query(Task)
            .filter(
                Task.user_id == user_id,
                Task.title == title,
                Task.due_date == today,
            )
            .first()
        )
        if existing_task is None:
            db.add(
                Task(
                    user_id=user_id,
                    title=title,
                    subject_tag=str(topic.subject_id) if topic else None,
                    priority_tag="Medium",
                    due_date=today,
                    status="Not started",
                )
            )
            tasks_created += 1
        else:
            skipped += 1

        existing_reminder = (
            db.query(Reminder)
            .filter(Reminder.title == title, Reminder.date == today)
            .first()
        )
        if existing_reminder is None:
            db.add(Reminder(title=title, time=time(17, 0), date=today))
            reminders_created += 1

        # Phrase 94: wrap as a micro-session when the topic has material.
        if topic is not None and _recommended_chunk(db, user_id, topic.id) is not None:
            existing_session = (
                db.query(MicroSession)
                .filter(
                    MicroSession.user_id == user_id,
                    MicroSession.topic_id == topic.id,
                    MicroSession.status == "suggested",
                )
                .first()
            )
            if existing_session is None:
                db.add(
                    MicroSession(
                        user_id=user_id,
                        topic_id=topic.id,
                        practice_task=title,
                        duration_mins=25,
                        status="suggested",
                    )
                )
                sessions_created += 1

    if tasks_created or reminders_created:
        db.commit()
        db.add(
            Notification(
                user_id=user_id,
                kind="revision_tasks",
                title=f"{tasks_created} revision task(s) ready today",
                body="Your spaced-repetition reviews are due — start with the highest-priority topic.",
            )
        )
        db.commit()

    return {
        "due": len(due),
        "schedule_items": schedule_items,
        "tasks_created": tasks_created,
        "reminders_created": reminders_created,
        "sessions_created": sessions_created,
        "skipped": skipped,
    }
