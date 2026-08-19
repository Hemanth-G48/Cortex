"""Knowledge Core stats endpoint (Phase 2, Idea 12, phrase 20)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.kb import KbStatsResponse
from app.services.kb.embedder import stats
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-stats"])


@router.get("/stats", response_model=KbStatsResponse)
def kb_stats(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> KbStatsResponse:
    data = stats(db, current_user.id)
    return KbStatsResponse(**data)
