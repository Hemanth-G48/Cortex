"""Google Classroom sync endpoints (thin wrappers over classroom_sync).

The response is labelled with ``source`` so the UI can distinguish live data
from the deterministic offline mock: ``{"courses": [...], "source": "live"}``
or ``{"courses": [...], "source": "mock"}``. Mocks are never persisted.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services import classroom_sync
from app.services.users import current_user

router = APIRouter(prefix="/api/classroom", tags=["classroom"])


@router.get("/courses")
def classroom_courses(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch Classroom courses; merge into the current user's Course rows."""
    return classroom_sync.sync_classroom_courses(db, current_user.id)


@router.get("/assignments")
def classroom_assignments(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Fetch course work across all courses; merge into Assignment by google_id."""
    return classroom_sync.sync_classroom_assignments(db, current_user.id)
