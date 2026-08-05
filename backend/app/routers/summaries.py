"""Summary generation and retrieval router."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User, Summary
from app.schemas.summary import SummaryGenerateRequest, SummaryListItem, SummaryResponse
from app.services.security import get_current_user
from app.services.summaries import (
    find_cached,
    generate_summary,
    list_summaries,
    delete_summary,
)

router = APIRouter(prefix="/api/summaries", tags=["summaries"])


def _daily_generation_count(db: Session) -> int:
    """Count summaries generated in the current UTC day.

    Global (not per-user): the local app is effectively single-user, and the
    cached hit path below never counts against the cap.
    """
    # created_at is stored naive (func.now on SQLite) → drop tzinfo for the comparison.
    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    return db.query(Summary).filter(Summary.created_at >= start).count()


@router.post("")
def create_summary(
    data: SummaryGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # G13 (Phase 87): per-day LLM cost guard for *new* generations. A cache hit
    # is never a generation, so it skips the cap; the deterministic demo
    # fallback (AI disabled) is exempt so offline use never hits the cap.
    if settings.AI_ENABLED and find_cached(db, data.unit_ids) is None:
        if _daily_generation_count(db) >= settings.SUMMARY_DAILY_LIMIT:
            raise HTTPException(
                429,
                f"Daily summary limit reached ({settings.SUMMARY_DAILY_LIMIT}/day). Try again tomorrow.",
            )
    result = generate_summary(db, data.unit_ids)
    return result


@router.get("", response_model=list[SummaryListItem])
def get_summaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = list_summaries(db)
    return [
        SummaryListItem(
            id=r.id,
            unit_ids=r.unit_ids,
            content=r.content,
            key_points=r.key_points or [],
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/{summary_id}")
def remove_summary(
    summary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    found = delete_summary(db, summary_id)
    if not found:
        raise HTTPException(404, "Summary not found")
    return {"ok": True}
