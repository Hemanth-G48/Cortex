"""Ingestion job status endpoints (Idea 10, phrase 94)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbJob, User
from app.schemas.kb import KbJobResponse
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-jobs"])


@router.get("/jobs", response_model=dict)
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Recent jobs (newest first) so the UI can poll progress."""
    jobs = (
        db.query(KbJob)
        .filter(KbJob.user_id == current_user.id)
        .order_by(KbJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return {"items": [KbJobResponse.model_validate(j) for j in jobs], "total": len(jobs)}


@router.get("/jobs/{job_id}", response_model=KbJobResponse)
def get_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    job = (
        db.query(KbJob)
        .filter(KbJob.id == job_id, KbJob.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(404, "Job not found")
    return KbJobResponse.model_validate(job)
