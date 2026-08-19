"""Phase 6 micro-sessions (Idea 60).

``build_session`` turns a topic into a concrete focus session: a specific vault
chunk (or the topic itself) + a practice task + a 15–45 minute duration.
``complete_session`` logs a ``session`` LearningEvent (value = minutes) that
feeds mastery + progress. One-tap Pomodoro launch reuses the pomodoro router
shape by creating a ``PomodoroSession`` row directly.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KbChunk, MicroSession, PomodoroSession, Topic
from app.services.kb import utcnow
from app.services.kb.mastery import log_event

MIN_DURATION = 15
MAX_DURATION = 45
DEFAULT_DURATION = 25


def _practice_task(topic: Topic) -> str:
    """Deterministic practice task by Bloom level (phrase 91)."""
    bloom = (topic.bloom_level or "Understand").lower()
    tasks = {
        "remember": f"Recall and list the key facts of {topic.name} without notes.",
        "understand": f"Explain {topic.name} in your own words, then check against your notes.",
        "apply": f"Work through a practice problem that uses {topic.name}.",
        "analyze": f"Break {topic.name} into parts and compare each with a related concept.",
        "evaluate": f"Critique your own understanding of {topic.name} — what is still fuzzy?",
        "create": f"Build a short study sheet or diagram for {topic.name}.",
    }
    return tasks.get(bloom, f"Study {topic.name} and take focused notes.")


def _chunk_for(db: Session, user_id: int, topic: Topic) -> KbChunk | None:
    """Pick the most relevant vault chunk for the topic (phrase 92)."""
    from app.services.kb.search import KbSearcher

    try:
        result = KbSearcher(db, user_id).search(topic.name, mode="hybrid", limit=1)
        items = result.get("items") or []
        if items and items[0].get("chunk_id"):
            chunk = db.get(KbChunk, items[0]["chunk_id"])
            if chunk is not None:
                return chunk
    except Exception:  # noqa: BLE001 — sessions work without vault content
        pass
    return None


def build_session(
    db: Session,
    user_id: int,
    topic: Topic,
    *,
    duration_mins: int | None = None,
) -> MicroSession:
    """Factory: suggested micro-session from a topic (phrase 91–92)."""
    duration = max(MIN_DURATION, min(MAX_DURATION, int(duration_mins or DEFAULT_DURATION)))
    chunk = _chunk_for(db, user_id, topic)
    session = MicroSession(
        user_id=user_id,
        topic_id=topic.id,
        chunk_id=chunk.id if chunk else None,
        practice_task=_practice_task(topic),
        duration_mins=duration,
        status="suggested",
    )
    db.add(session)
    db.flush()
    return session


def start_session(db: Session, user_id: int, session: MicroSession) -> MicroSession:
    session.status = "started"
    db.flush()
    return session


def complete_session(db: Session, user_id: int, session: MicroSession) -> MicroSession:
    session.status = "done"
    session.completed_at = utcnow()
    log_event(
        db,
        user_id,
        event_type="session",
        topic_id=session.topic_id,
        value=float(session.duration_mins or 0),
    )
    db.flush()
    return session


def launch_pomodoro(db: Session, user_id: int, session: MicroSession) -> PomodoroSession:
    """One-tap Pomodoro launch (phrase 96): create a focused session row."""
    pomo = PomodoroSession(
        user_id=user_id,
        start_time=utcnow(),
        duration_minutes=session.duration_mins,
        completed=False,
        task_description=f"{session.practice_task} ({session.id})"[:200],
        mode="Focus",
    )
    db.add(pomo)
    db.flush()
    return pomo


def session_dict(s: MicroSession, topic: Topic | None = None) -> dict:
    return {
        "id": s.id,
        "topic_id": s.topic_id,
        "topic_name": topic.name if topic else None,
        "chunk_id": s.chunk_id,
        "practice_task": s.practice_task,
        "duration_mins": s.duration_mins,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
    }
