"""Phase 7 — Skill mapping router (Idea 70, phrases 97–98).

- ``POST /api/kb/skills/map`` — map a subject's topics → skills (phrase 94).
- ``GET /api/kb/skills`` — the mastery-derived profile (phrase 97).
- ``GET /api/kb/skills/export`` — JSON/markdown summary (phrase 98).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SubjectProfile, User
from app.services.kb import skills as skills_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-skills"])


class MapRequest(BaseModel):
    subject_id: int


@router.post("/skills/map")
def map_subject_skills(
    body: MapRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    profile = (
        db.query(SubjectProfile)
        .filter(
            SubjectProfile.user_id == current_user.id,
            SubjectProfile.curriculum_subject_id == body.subject_id,
        )
        .first()
    )
    if profile is None:
        raise HTTPException(400, "Confirmed subject not found")
    rows = skills_service.map_subject(db, current_user.id, body.subject_id)
    db.commit()
    return {"mapped": len(rows), "skills": skills_service.profile(db, current_user.id)}


@router.get("/skills")
def get_skills(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return {"skills": skills_service.profile(db, current_user.id)}


@router.get("/skills/export")
def export_skills(
    fmt: str = Query(default="markdown", pattern="^(markdown|json)$"),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return {"format": fmt, "content": skills_service.export(db, current_user.id, fmt)}
