"""Idea 100 — observability router.

- ``GET /api/kb/observability`` — admin/teacher-guarded dashboard payload
  (cost, latency, feedback, eval) (phrase 97).
- ``GET /api/kb/observability/report`` — the weekly report for the user
  (phrase 95).
- ``POST /api/kb/observability/{log_id}/feedback`` — thumbs on any interaction
  (phrase 94).
- ``GET/POST /api/kb/prompts`` — A/B-able prompt versions (phrase 96).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PromptVersion, User
from app.services.kb import ai_log as ai_log_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-observability"])


@router.get("/observability")
def observability(
    since_days: int = Query(default=7, ge=1, le=90),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Single-owner dashboard payload (no role gate)."""
    payload = ai_log_service.aggregate(db)
    payload["recent"] = ai_log_service.recent_logs(db, current_user.id, limit=20)
    return payload


@router.get("/observability/report")
def weekly_report(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    return ai_log_service.weekly_report(db, current_user.id)


class FeedbackRequest(BaseModel):
    feedback: int = Field(ge=-1, le=1)


@router.post("/observability/{log_id}/feedback")
def log_feedback(
    log_id: int,
    body: FeedbackRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = ai_log_service.set_feedback(db, current_user.id, log_id, body.feedback)
    if row is None:
        raise HTTPException(404, "Log entry not found")
    db.commit()
    return {"ok": True, "log_id": row.id, "feedback": row.feedback}


# --------------------------------------------------------------------------- #
# Prompt versioning (phrase 96)
# --------------------------------------------------------------------------- #


@router.get("/prompts")
def list_prompts(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(PromptVersion).order_by(PromptVersion.feature, PromptVersion.version).all()
    return {
        "items": [
            {
                "id": p.id,
                "feature": p.feature,
                "version": p.version,
                "is_active": bool(p.is_active),
                "template": p.template,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in rows
        ]
    }


class PinPromptRequest(BaseModel):
    feature: str = Field(min_length=1, max_length=30)
    template: str = Field(min_length=1, max_length=8000)
    version: int | None = None


@router.post("/prompts")
def pin_prompt(
    body: PinPromptRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = ai_log_service.pin_prompt(db, body.feature, body.template, body.version)
    db.commit()
    return {
        "ok": True,
        "feature": row.feature,
        "version": row.version,
        "is_active": bool(row.is_active),
    }
