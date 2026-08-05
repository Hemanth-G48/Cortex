"""Enrollment progress router for SyllabusAI (G12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.enrollment_stats import enrollment_summary
from app.services.security import get_current_user

router = APIRouter(prefix="/api/enrollment", tags=["enrollment"])


@router.get("/summary")
def summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return enrollment_summary(db, current_user)
