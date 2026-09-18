"""Daily-note endpoints (Phase 4, Idea 35)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb.daily_notes import append_daily_entry, get_daily_notes, get_today
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-daily-notes"])


@router.get("/daily-notes")
def daily_notes(
    date: date,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return get_daily_notes(db, current_user.id, date)


@router.get("/daily-notes/today")
def daily_notes_today(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    return get_today(db, current_user.id)


class CompleteTaskRequest(BaseModel):
    """Audit defect #66: a completed task is echoed into today's daily note."""

    title: str
    # Optional identifiers so the caller can trace the line back to its source.
    task_id: int | None = None
    source: str | None = None


@router.post("/daily-notes/complete-task")
def complete_task_in_daily_note(
    body: CompleteTaskRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Append ``- [x] <title>`` to today's ``daily-life/YYYY-MM-DD.md``.

    Completing a task anywhere in the app (Eisenhower quick-complete, task list)
    also writes the completion into the vault's daily note, which is the user's
    own record of the day. Returns ``{ok, date, path, created}`` with ``ok:
    False`` + ``reason`` when the vault has no reachable daily-life folder.
    """
    title = (body.title or "").strip()
    if not title:
        raise HTTPException(400, "title is required")
    result = append_daily_entry(db, current_user.id, f"[x] {title}", section="Tasks")
    return result
