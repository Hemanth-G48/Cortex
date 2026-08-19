"""Study-Session Loop workflow — learning plan × micro-sessions.

Bridges the Learning Path Planner (``LearningPlan`` / ``LearningTask`` rows
with persistent progress) and the Phase-6 micro-session machinery
(``MicroSession`` + ``mastery.log_event``):

- ``plan_session_state`` — READ-ONLY: the plan's current session (started or
  most recent), the next incomplete task, live progress. Never creates rows
  and never calls the LLM — page loads stay instant.
- ``start_plan_session`` — explicit user action: open a micro-session on the
  plan's next incomplete task (lowest phase, then sort order). Reuses
  ``sessions.build_session`` so a Pomodoro can launch from it.
- ``complete_plan_session`` — explicit user action: mark the session done,
  mark its learning task done, log the mastery event, recompute progress and
  recommend the next task.

Every session row is user-scoped; a plan session is linked via
``learning_plan_id`` / ``learning_task_id`` (no curriculum topic required).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import LearningTask, MicroSession
from app.services.kb import utcnow

DEFAULT_DURATION_MINS = 25


# ---------------------------------------------------------------------------
# Read side — never mutates, never calls the LLM
# ---------------------------------------------------------------------------


def _next_task(db: Session, plan_id: int) -> LearningTask | None:
    return (
        db.query(LearningTask)
        .filter(LearningTask.plan_id == plan_id, LearningTask.done.is_(False))
        .order_by(LearningTask.phase.asc(), LearningTask.sort_order.asc(), LearningTask.id.asc())
        .first()
    )


def _live_session(db: Session, user_id: int, plan_id: int) -> MicroSession | None:
    return (
        db.query(MicroSession)
        .filter(
            MicroSession.user_id == user_id,
            MicroSession.learning_plan_id == plan_id,
            MicroSession.status == "started",
        )
        .order_by(MicroSession.id.desc())
        .first()
    )


def _last_session(db: Session, user_id: int, plan_id: int) -> MicroSession | None:
    return (
        db.query(MicroSession)
        .filter(
            MicroSession.user_id == user_id,
            MicroSession.learning_plan_id == plan_id,
        )
        .order_by(MicroSession.id.desc())
        .first()
    )


def _task_dict(task: LearningTask) -> dict | None:
    if task is None:
        return None
    return {
        "id": task.id,
        "phase": task.phase,
        "phase_title": task.phase_title,
        "title": task.title,
        "description": task.description,
        "resource_title": task.resource_title,
        "resource_url": task.resource_url,
        "resource_type": task.resource_type,
        "difficulty": task.difficulty,
        "est_time": task.est_time,
        "path_id": task.path_id,
        "done": task.done,
    }


def _session_dict(session: MicroSession) -> dict | None:
    if session is None:
        return None
    return {
        "id": session.id,
        "learning_plan_id": session.learning_plan_id,
        "learning_task_id": session.learning_task_id,
        "practice_task": session.practice_task,
        "duration_mins": session.duration_mins,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


def _progress(db: Session, plan_id: int) -> dict:
    tasks = db.query(LearningTask).filter(LearningTask.plan_id == plan_id).all()
    total = len(tasks)
    done = sum(1 for t in tasks if t.done)
    return {
        "total_tasks": total,
        "done_tasks": done,
        "progress_percent": round((done / total) * 100) if total else 0,
    }


def plan_session_state(db: Session, user_id: int, plan_id: int) -> dict:
    """Read-only snapshot: live session, last session, next task, progress.

    Never creates rows and never calls the LLM — safe on every page load.
    """
    live = _live_session(db, user_id, plan_id)
    last = live or _last_session(db, user_id, plan_id)
    next_task = _next_task(db, plan_id)
    progress = _progress(db, plan_id)
    return {
        "plan_id": plan_id,
        "live_session": _session_dict(live),
        "last_session": _session_dict(last),
        "next_task": _task_dict(next_task),
        "progress": progress,
        # True when every tracked task is complete (nothing left to start).
        "completed": progress["total_tasks"] > 0 and progress["done_tasks"] == progress["total_tasks"],
    }


# ---------------------------------------------------------------------------
# Write side — explicit user actions only
# ---------------------------------------------------------------------------


def start_plan_session(
    db: Session,
    user_id: int,
    plan_id: int,
    *,
    duration_mins: int | None = None,
    task_id: int | None = None,
) -> MicroSession:
    """Start a micro-session on a roadmap task.

    ``task_id`` starts the session on that SPECIFIC task (e.g. the first
    incomplete task of a scheduled study day); when omitted, the plan's next
    incomplete task is used. Raises ``ValueError`` when every task is done,
    the task is already complete, or a session is already live for this plan.
    """
    live = _live_session(db, user_id, plan_id)
    if live is not None:
        raise ValueError("A study session for this plan is already in progress")
    if task_id is not None:
        task = (
            db.query(LearningTask)
            .filter(
                LearningTask.id == task_id,
                LearningTask.plan_id == plan_id,
                LearningTask.done.is_(False),
            )
            .first()
        )
        if task is None:
            raise ValueError(
                "That task is already complete or does not belong to this plan"
            )
    else:
        task = _next_task(db, plan_id)
        if task is None:
            raise ValueError("Every task in this plan is already complete")
    minutes = duration_mins or DEFAULT_DURATION_MINS
    session = MicroSession(
        user_id=user_id,
        learning_plan_id=plan_id,
        learning_task_id=task.id,
        practice_task=task.title,
        duration_mins=max(15, min(45, int(minutes))),
        status="started",
    )
    db.add(session)
    db.flush()
    return session


def complete_plan_session(db: Session, user_id: int, plan_id: int, session_id: int) -> dict:
    """Complete a started plan session: mark the session done AND its task
    done, log the mastery event, then return the fresh state + next task."""
    session = (
        db.query(MicroSession)
        .filter(
            MicroSession.id == session_id,
            MicroSession.user_id == user_id,
            MicroSession.learning_plan_id == plan_id,
        )
        .first()
    )
    if session is None:
        raise ValueError("Study session not found")
    if session.status == "done":
        raise ValueError("Study session already completed")

    session.status = "done"
    session.completed_at = utcnow()

    task_completed = False
    if session.learning_task_id:
        task = (
            db.query(LearningTask)
            .filter(LearningTask.id == session.learning_task_id, LearningTask.plan_id == plan_id)
            .first()
        )
        if task is not None and not task.done:
            task.done = True
            task_completed = True

    # Log the mastery event (same shape as curriculum micro-sessions) so the
    # session feeds forecast/mastery — topic-less plan sessions still count.
    if session.learning_task_id:
        try:
            from app.services.kb.mastery import log_event

            log_event(
                db,
                user_id,
                event_type="session",
                topic_id=None,
                value=float(session.duration_mins or 0),
            )
        except Exception:  # noqa: BLE001 — mastery logging is best-effort
            pass

    db.flush()
    state = plan_session_state(db, user_id, plan_id)
    return {
        "session": _session_dict(session),
        "task_completed": task_completed,
        **state,
    }
