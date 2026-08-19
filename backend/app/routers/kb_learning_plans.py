"""Learning Path Planner endpoints (workflow glue)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LearningPlan, User
from app.services.kb import learning_planner as planner
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/learning-plans", tags=["kb-learning-plans"])


class ResourceInput(BaseModel):
    label: str | None = Field(default=None, max_length=300)
    url: str | None = Field(default=None, max_length=600)


class CreatePlanRequest(BaseModel):
    goal: str = Field(min_length=2, max_length=300)
    description: str | None = Field(default=None, max_length=2000)
    resources: list[ResourceInput] = Field(min_length=1, max_length=20)
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    goal_key: str | None = Field(default=None, max_length=60)


@router.post("")
def create_plan(
    body: CreatePlanRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a learning plan in one shot: Layer-1 discovery + Layer-2 roadmap.

    The crawler visits the supplied URL(s), discovers the real learning paths
    and resources on the platform (each labeled with an honest crawl status),
    then the AI (or the deterministic fallback) builds a personalised roadmap
    whose every task references a real discovered resource. No resources are
    invented when the platform cannot be reached.
    """
    try:
        plan = planner.generate_plan(
            db,
            current_user.id,
            body.goal,
            [r.model_dump() for r in body.resources],
            body.known,
            body.unknown,
            description=body.description,
            goal_key=body.goal_key,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"plan": planner.plan_dict(db, plan)}


@router.post("/discover")
def discover_source(
    body: CreatePlanRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Layer 1 only: crawl the supplied URL(s) and persist the REAL platform
    structure (learning paths → resources) without generating a roadmap.

    The response includes the source hierarchy and the honest crawl report.
    Call ``POST /{plan_id}/generate`` afterwards to build the personalised
    roadmap on top of it.
    """
    try:
        plan = planner.discover_plan(
            db,
            current_user.id,
            body.goal,
            [r.model_dump() for r in body.resources],
            body.known,
            body.unknown,
            description=body.description,
            goal_key=body.goal_key,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"plan": planner.plan_dict(db, plan)}


class GenerateRequest(BaseModel):
    known: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# PortSwigger sign-in session (lets the crawler verify auth-gated URLs)
# ---------------------------------------------------------------------------


class SessionLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=512)
    # Store the credentials locally (obfuscated) so an expired session can be
    # refreshed without re-entering them. Defaults to True — the user asked
    # for local reuse.
    remember: bool = True


class SessionLogoutRequest(BaseModel):
    clear_credentials: bool = False


@router.get("/session")
def session_status(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """PortSwigger sign-in status (configured? live session? expiry?).

    Never includes the password or the raw cookies — only a public status
    snapshot for the UI.
    """
    from app.services.kb import portswigger_session as ps

    return {"session": ps.session_status(db, current_user.id)}


@router.post("/session/login")
def session_login(
    body: SessionLoginRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Log in to PortSwigger with the user's own account and store the
    session (credentials too when ``remember``) so the crawler can verify
    sign-in-gated resource URLs."""
    from app.services.kb import portswigger_session as ps

    try:
        result = ps.login(body.email, body.password)
    except ps.AuthError as e:
        raise HTTPException(400, str(e))
    ps.save_session(
        db,
        current_user.id,
        result["email"],
        body.password,
        result["cookies"],
        result["expires_at"],
        remember=body.remember,
    )
    db.commit()
    return {"session": ps.session_status(db, current_user.id)}


@router.post("/session/logout")
def session_logout(
    body: SessionLogoutRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Drop the stored session (and optionally the stored credentials)."""
    from app.services.kb import portswigger_session as ps

    ps.logout(db, current_user.id, clear_credentials=body.clear_credentials)
    db.commit()
    return {"session": ps.session_status(db, current_user.id)}


@router.post("/{plan_id}/generate")
def generate_roadmap(
    plan_id: int,
    body: GenerateRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Layer 2: build the personalised roadmap on top of the persisted Layer-1
    structure (explicit user action — never run automatically).
    """
    plan = _plan_or_404(db, current_user.id, plan_id)
    try:
        planner.generate_from_discovery(
            db, current_user.id, plan, known=body.known, unknown=body.unknown
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"plan": planner.plan_dict(db, plan)}


# ---------------------------------------------------------------------------
# Study Schedule — roadmap → day-by-day plan (explicit user action)
# ---------------------------------------------------------------------------


class ScheduleRequest(BaseModel):
    # daily_hours | modules_per_day | time_slots | hybrid | ai_instruction
    mode: str = "daily_hours"
    daily_hours: float | None = Field(default=None, ge=0.25, le=12)
    modules_per_day: int | None = Field(default=None, ge=1, le=30)
    time_slots: list[str] = Field(default_factory=list, max_length=6)
    # Free-text routine for ai_instruction mode ("1h daily at 7am, 2h weekends").
    instruction: str | None = Field(default=None, max_length=2000)


@router.get("/{plan_id}/schedule")
def get_schedule(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only: the stored day-by-day study schedule (or null).

    Never calls the LLM and never mutates rows — safe on every navigation.
    ``done``/``stale`` are recomputed from the live task rows.
    """
    plan = _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import roadmap_schedule as rs

    return {"schedule": rs.schedule_dict(db, plan)}


@router.post("/{plan_id}/schedule")
def create_schedule(
    plan_id: int,
    body: ScheduleRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: build the study schedule from the roadmap.

    The user chooses HOW they want to study (daily hours, modules per day,
    fixed time slots, hybrid, or a free-text routine for the AI). Only real
    roadmap tasks are scheduled; completed tasks are skipped and reported.
    """
    plan = _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import roadmap_schedule as rs

    try:
        schedule = rs.build_schedule(
            db,
            plan,
            mode=body.mode,
            daily_hours=body.daily_hours,
            modules_per_day=body.modules_per_day,
            time_slots=body.time_slots,
            instruction=body.instruction,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"schedule": schedule}


@router.delete("/{plan_id}/schedule")
def clear_schedule(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Drop the stored schedule (explicit user action)."""
    plan = _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import roadmap_schedule as rs

    rs.clear_schedule(plan)
    db.commit()
    return {"ok": True}


@router.get("")
def list_plans(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    plans = (
        db.query(LearningPlan)
        .filter(LearningPlan.user_id == current_user.id)
        .order_by(LearningPlan.created_at.desc())
        .all()
    )
    return {"items": [planner.plan_summary(p) for p in plans]}


def _plan_or_404(db: Session, user_id: int, plan_id: int) -> LearningPlan:
    plan = db.query(LearningPlan).filter(
        LearningPlan.id == plan_id, LearningPlan.user_id == user_id
    ).first()
    if plan is None:
        raise HTTPException(404, "Learning plan not found")
    return plan


@router.get("/{plan_id}")
def get_plan(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    plan = _plan_or_404(db, current_user.id, plan_id)
    return {"plan": planner.plan_dict(db, plan)}


class ToggleTaskRequest(BaseModel):
    done: bool


@router.post("/{plan_id}/reverify")
def reverify_resources(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: use the stored PortSwigger session to re-crawl
    the plan's paths (the signed-in view exposes a real URL for every
    resource) and re-verify the previously gated/failed resource URLs.
    Returns the updated plan plus an honest re-verify report.
    """
    plan = _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import portswigger_session as ps

    try:
        report = ps.reverify_plan(db, current_user.id, plan)
    except ps.AuthError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"plan": planner.plan_dict(db, plan), "reverify": report}


# ---------------------------------------------------------------------------
# Study-Session Loop (workflow) — learning plan × micro-sessions
# ---------------------------------------------------------------------------


class StartPlanSessionRequest(BaseModel):
    duration_mins: int | None = Field(default=None, ge=15, le=45)
    # Optional: start the session on a SPECIFIC roadmap task (e.g. the first
    # incomplete task of a scheduled day) instead of the global next task.
    task_id: int | None = Field(default=None, ge=1)


@router.get("/{plan_id}/session")
def plan_session_state(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only: current session + next task + progress for the plan.

    Never creates rows and never calls the LLM — safe on every navigation.
    """
    _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import study_loop

    return {"session": study_loop.plan_session_state(db, current_user.id, plan_id)}


@router.post("/{plan_id}/session/start")
def start_plan_session(
    plan_id: int,
    body: StartPlanSessionRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: open a micro-session on the next incomplete task.

    Reuses the standard micro-session machinery, so the started session can
    launch a Pomodoro or be completed (which marks the task done).
    """
    _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import study_loop

    try:
        session = study_loop.start_plan_session(
            db,
            current_user.id,
            plan_id,
            duration_mins=body.duration_mins,
            task_id=body.task_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    state = study_loop.plan_session_state(db, current_user.id, plan_id)
    return {"ok": True, "session": state["live_session"], "state": state}


@router.post("/{plan_id}/session/{session_id}/complete")
def complete_plan_session(
    plan_id: int,
    session_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: complete the session, mark its task done, and
    return the fresh progress + next task."""
    _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import study_loop

    try:
        result = study_loop.complete_plan_session(db, current_user.id, plan_id, session_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"ok": True, **result}


@router.post("/{plan_id}/resync")
def resync_plan(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: re-crawl the stored source URL(s) and refresh
    Layer 1 in place — new paths are added, missing ones flagged removed,
    and the personalised roadmap is left untouched."""
    plan = _plan_or_404(db, current_user.id, plan_id)
    from app.services.kb import portswigger_session as ps

    cookies = None
    try:
        row = ps.load_session(db, current_user.id)
        if row is not None and row.cookies_json and ps._session_authenticated(ps._cookies_of(row)):
            cookies = ps._cookies_of(row)
    except Exception:  # noqa: BLE001 — resync works without a session
        cookies = None
    try:
        report = planner.resync_plan(db, current_user.id, plan, cookies=cookies)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"plan": planner.plan_dict(db, plan), "resync": report}


@router.post("/{plan_id}/tasks/{task_id}/toggle")
def toggle_task(
    plan_id: int,
    task_id: int,
    body: ToggleTaskRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Check/uncheck a roadmap task (persistent progress)."""
    _plan_or_404(db, current_user.id, plan_id)
    task = planner.toggle_task(db, current_user.id, task_id, body.done)
    if task is None:
        raise HTTPException(404, "Task not found")
    db.commit()
    return {"ok": True, "task": planner.task_dict(task)}


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    plan = _plan_or_404(db, current_user.id, plan_id)
    from app.models import (
        LearningDependency,
        LearningPath,
        LearningPathResource,
        LearningResource,
        LearningTask,
    )

    path_ids = [p.id for p in db.query(LearningPath.id).filter(LearningPath.plan_id == plan.id).all()]
    if path_ids:
        db.query(LearningPathResource).filter(LearningPathResource.path_id.in_(path_ids)).delete(
            synchronize_session=False
        )
    db.query(LearningTask).filter(LearningTask.plan_id == plan.id).delete(synchronize_session=False)
    db.query(LearningDependency).filter(LearningDependency.plan_id == plan.id).delete(
        synchronize_session=False
    )
    db.query(LearningPath).filter(LearningPath.plan_id == plan.id).delete(synchronize_session=False)
    db.query(LearningResource).filter(LearningResource.plan_id == plan.id).delete(
        synchronize_session=False
    )
    db.delete(plan)
    db.commit()
    return {"ok": True}
