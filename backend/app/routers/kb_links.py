"""Auto-link review queue (Idea 83, phrase 25).

Batch review endpoints for pending-edge proposals (low-confidence pairs):
    GET  /api/kb/links/queue        — pending edge proposals
    POST /api/kb/links/accept       — accept (bulk) → edges go live
    POST /api/kb/links/reject       — reject (bulk) → never re-proposed
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import auto_link
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/links", tags=["kb-links"])


class LinkAction(BaseModel):
    edge_ids: list[int] = Field(default_factory=list)


@router.get("/queue")
def get_queue(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Pending auto-link proposals for review (strongest first)."""
    return {"items": auto_link.queue(db, current_user.id)}


@router.post("/accept")
def accept(
    body: LinkAction,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Promote approved pending edges to the live graph (bulk)."""
    accepted = auto_link.accept(db, current_user.id, body.edge_ids)
    return {"ok": True, "accepted": accepted}


@router.post("/reject")
def reject(
    body: LinkAction,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Reject proposals (bulk); rejected pairs are never re-proposed."""
    rejected = auto_link.reject(db, current_user.id, body.edge_ids)
    return {"ok": True, "rejected": rejected}
