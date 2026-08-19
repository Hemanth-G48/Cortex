"""Focus/Readiness Loop workflow endpoints.

``GET /api/kb/focus`` — read-only \"what should I study right now\" board:
per-subject readiness (forecast) + top recommendations (next_action), ordered
by exam urgency. Never calls the LLM on navigation.

``POST /api/kb/focus/start`` — explicit action: start a micro-session on a
recommended topic (reuses the standard session machinery).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import focus as focus_svc
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/focus", tags=["kb-focus"])


@router.get("")
def focus_board(
    limit: int = Query(default=5, ge=1, le=10),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only readiness board (deterministic — no LLM, no mutation)."""
    return focus_svc.focus_board(db, current_user.id, limit=limit)


class StartFocusSessionRequest(BaseModel):
    topic_id: int
    duration_mins: int | None = Field(default=None, ge=15, le=45)


@router.post("/start")
def start_focus_session(
    body: StartFocusSessionRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: start a micro-session on a recommended topic."""
    try:
        session = focus_svc.start_focus_session(
            db, current_user.id, body.topic_id, duration_mins=body.duration_mins
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    db.commit()
    return {"ok": True, "session": session}
