"""Today command center endpoints (workflow glue)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb.today import today_overview
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-today"])


@router.get("/today")
def get_today_overview(
    day: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Morning-plan + evening-close payload for the Today page.

    ``?date=YYYY-MM-DD`` renders a different day (default: today).
    """
    return today_overview(db, current_user.id, day)
