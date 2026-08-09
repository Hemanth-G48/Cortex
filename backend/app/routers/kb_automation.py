"""Phase 9 automation endpoints (Ideas 81–90).

A single router (per the Phase 9 plan) that exposes the automation runner:
run one job or all enabled jobs, and inspect which jobs are registered with
their gate/cap state. Every job persists a ``kb_jobs`` row; proposals land in
per-feature review queues, never silent writes.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import automation
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb/automation", tags=["kb-automation"])


class RunRequest(BaseModel):
    # "one" → run the named job; "all" → run every enabled job.
    mode: Literal["one", "all"] = "one"
    name: str | None = None
    # Bypass the KB_AUTO_* toggle for a manual / debugging run.
    force: bool = False


@router.get("/jobs", response_model=dict)
def list_automation_jobs(
    current_user: User = Depends(get_current_user),
):
    """Registered Phase 9 jobs + enabled/cap state (for a control UI)."""
    return {"jobs": automation.registered_jobs()}


@router.post("/run", response_model=dict)
def run_automation(
    payload: RunRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run one named job (``mode="one"``) or all enabled jobs (``mode="all"``)."""
    if payload.mode == "one":
        if not payload.name:
            raise HTTPException(422, "name is required when mode='one'")
        try:
            return automation.run_one(
                db, current_user.id, payload.name, force=payload.force
            )
        except ValueError as exc:
            raise HTTPException(404, str(exc))
    return automation.run_all(db, current_user.id, force=payload.force)
