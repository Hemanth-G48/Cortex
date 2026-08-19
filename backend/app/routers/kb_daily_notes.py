"""Daily-note endpoints (Phase 4, Idea 35)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb.daily_notes import get_daily_notes, get_today
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
