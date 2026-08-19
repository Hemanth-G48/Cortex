"""Auto-categorization review queue (Idea 81, phrase 7).

Batch review endpoints for CategorizeSuggestion proposals:
    GET  /api/kb/categorize/queue   — pending proposals
    POST /api/kb/categorize/accept  — accept (bulk ids) → move + version log
    POST /api/kb/categorize/reject  — reject (bulk ids)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import auto_categorize
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/categorize", tags=["kb-categorize"])


class CategorizeAction(BaseModel):
    suggestion_ids: list[int] = Field(default_factory=list)


@router.get("/queue")
def get_queue(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Pending folder-move proposals for review."""
    return {"items": auto_categorize.queue(db, current_user.id)}


@router.post("/accept")
def accept(
    body: CategorizeAction,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Apply approved folder moves (bulk) with version-history logging."""
    applied = auto_categorize.accept(db, current_user.id, body.suggestion_ids)
    return {"ok": True, "applied": applied}


@router.post("/reject")
def reject(
    body: CategorizeAction,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Reject proposals (bulk); rejected moves are never re-proposed."""
    rejected = auto_categorize.reject(db, current_user.id, body.suggestion_ids)
    return {"ok": True, "rejected": rejected}
