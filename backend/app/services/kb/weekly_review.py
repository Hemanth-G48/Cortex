"""Workflow glue — weekly review ritual.

A guided end-of-week review that assembles everything the reflection needs in
one payload:

- **What you did** — captures this week (vault docs), learning events
  (sessions, reviews, quizzes), focus minutes.
- **How it went** — the weekly reflection (existing or generated on demand,
  reusing Idea 98), goal progress, weak topics.
- **What's next** — auto-proposed term goals, weekly quests, next week start.

Deterministic: reflection generation falls back to the Idea 98 aggregate
fallback when AI is off.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Goal,
    KbDocument,
    LearningEvent,
    MicroSession,
    PomodoroSession,
    Quest,
    Reflection,
)
from app.services.kb.mastery import mastery_by_topic
from app.services.kb.reflections import (
    derive_goals,
    get_or_generate,
    list_goals,
    week_start,
)

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _week_bounds(ws: date) -> tuple[datetime, datetime]:
    start = datetime.combine(ws, time.min)
    return start, start + timedelta(days=7)


def _learning_events(db: Session, user_id: int, start: datetime, end: datetime) -> list[LearningEvent]:
    return (
        db.query(LearningEvent)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.created_at >= start,
            LearningEvent.created_at < end,
        )
        .order_by(LearningEvent.created_at.asc())
        .all()
    )


def _weak_topics(db: Session, user_id: int, limit: int = 8) -> list[dict]:
    from app.models import Topic

    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.status.in_(("pending", "confirmed")))
        .all()
    )
    if not topics:
        return []
    mastery = mastery_by_topic(db, user_id, [t.id for t in topics])
    weak = [
        {
            "topic_id": t.id,
            "topic_name": t.name,
            "subject_id": t.subject_id,
            "score": mastery[t.id]["score"],
            "classification": mastery[t.id]["classification"],
        }
        for t in topics
        if mastery[t.id]["classification"] in ("weak", "unknown")
    ]
    weak.sort(key=lambda x: x["score"])
    return weak[:limit]


def _weekly_quests(db: Session, user_id: int) -> list[dict]:
    monday = week_start()
    rows = (
        db.query(Quest)
        .filter(
            Quest.user_id == user_id,
            Quest.category == "Weekly",
            Quest.due_date >= monday,
        )
        .order_by(Quest.id.asc())
        .all()
    )
    return [
        {
            "id": q.id,
            "title": q.title,
            "description": q.description,
            "xp_reward": q.xp_reward,
            "status": q.status,
            "due_date": q.due_date.isoformat() if q.due_date else None,
        }
        for q in rows
    ]


def weekly_review(db: Session, user_id: int) -> dict:
    """Assemble the full weekly-review ritual payload (no writes)."""
    ws = week_start()
    start, end = _week_bounds(ws)
    we = (ws + timedelta(days=6)).isoformat()

    # ── What you did this week ──
    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.created_at >= start,
            KbDocument.created_at < end,
            KbDocument.status != "deleted",
        )
        .order_by(KbDocument.created_at.desc())
        .all()
    )
    events = _learning_events(db, user_id, start, end)
    sessions = (
        db.query(MicroSession)
        .filter(
            MicroSession.user_id == user_id,
            MicroSession.status == "done",
            MicroSession.completed_at.isnot(None),
            MicroSession.completed_at >= start,
            MicroSession.completed_at < end,
        )
        .all()
    )
    pomodoros = (
        db.query(PomodoroSession)
        .filter(
            PomodoroSession.user_id == user_id,
            PomodoroSession.start_time >= start,
            PomodoroSession.start_time < end,
        )
        .all()
    )
    # Sessions completed within the week (completed_at is set on completion).
    sessions_done = sessions
    minutes = sum(p.duration_minutes or 0 for p in pomodoros)

    # ── How it went ──
    reflection_row = (
        db.query(Reflection)
        .filter(Reflection.user_id == user_id, Reflection.week_start == ws)
        .first()
    )
    reflection = None
    if reflection_row is not None:
        from app.services.kb import KbService

        reflection = {
            "id": reflection_row.id,
            "week_start": reflection_row.week_start.isoformat(),
            "content": reflection_row.content,
            "insights": KbService.json_loads(reflection_row.insights) or {},
            "created_at": reflection_row.created_at.isoformat() if reflection_row.created_at else None,
        }

    goals = list_goals(db, user_id)
    derived = derive_goals(db, user_id)
    weak = _weak_topics(db, user_id)

    # Weekly quests created by the weekly-reset endpoint (if any).
    quests = _weekly_quests(db, user_id)

    return {
        "week_start": ws.isoformat(),
        "week_end": we,
        "week_label": f"{_DAYS[ws.weekday()]}, {ws.isoformat()} — {we}",
        "activity": {
            "captures": [
                {
                    "id": d.id,
                    "title": d.title or d.path_rel or f"doc {d.id}",
                    "doc_type": d.doc_type,
                    "quality_score": d.quality_score,
                }
                for d in docs[:50]
            ],
            "captures_count": len(docs),
            "sessions_done": len(sessions_done),
            "learning_events": len(events),
            "focus_minutes": minutes,
            "pomodoro_count": len(pomodoros),
        },
        "reflection": reflection,
        "goals": goals,
        "derived_goals": derived,
        "weak_topics": weak,
        "weekly_quests": quests,
        "week_start_monday": ws.isoformat(),
    }


def generate_reflection(db: Session, user_id: int, *, regenerate: bool = False) -> dict:
    """Generate (or regenerate) this week's reflection + return the ritual payload."""
    ws = week_start()
    result = get_or_generate(db, user_id, ws, regenerate=regenerate)
    db.flush()
    return {
        "reflection": result,
        "week_start": ws.isoformat(),
    }


def confirm_derived_goal(db: Session, user_id: int, proposal: dict) -> dict:
    """Persist one auto-proposed term goal (Idea 98, phrase 72)."""
    from app.services.kb.reflections import confirm_derived_goal as _confirm

    goal = _confirm(db, user_id, proposal)
    db.flush()
    return {"ok": True, "goal_id": goal.id}
