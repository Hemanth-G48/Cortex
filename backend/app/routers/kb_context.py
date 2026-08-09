"""Idea 95 — context-aware responses router.

- ``GET /api/kb/context`` — the derived per-user context bundle (phrase 44).
- ``PUT /api/kb/context`` — user override (active subject).

The bundle is per-user; overrides persist per user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import context as context_service
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-context"])


class ContextOverrideRequest(BaseModel):
    active_subject_id: int | None = None
    active_subject_name: str | None = None


@router.get("/context")
def get_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return context_service.build_bundle(db, current_user.id)


@router.put("/context")
def put_context(
    body: ContextOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = context_service.save_override(
        db, current_user.id, body.model_dump(exclude_none=True)
    )
    db.commit()
    return {"saved": saved, "bundle": context_service.build_bundle(db, current_user.id)}
