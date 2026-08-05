"""Study analytics router."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import analytics

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)) -> dict:
    return analytics.analytics_summary(db)


@router.get("/weekly-focus")
def weekly_focus(weeks: int = 8, db: Session = Depends(get_db)) -> list[dict]:
    return analytics.weekly_focus(db, weeks=weeks)


@router.get("/heatmap")
def heatmap(weeks: int = 52, db: Session = Depends(get_db)) -> list[dict]:
    return analytics.focus_heatmap(db, weeks=weeks)
