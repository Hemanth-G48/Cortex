"""Phase 7 — AI Tutor router (Ideas 61–62).

- ``POST /api/kb/tutor/chat`` — RAG-grounded, cited answers (Idea 61).
- ``POST /api/kb/tutor/doubt`` — gap-first doubt resolution (Idea 62).

Both are user-scoped and budget-capped; deterministic fallbacks work with
``AI_ENABLED=false``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TutorSession, User
from app.services.kb import tutor as tutor_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-tutor"])


class TutorChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None


@router.post("/tutor/chat")
def tutor_chat(
    body: TutorChatRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = tutor_service.tutor_chat(db, current_user.id, body.message, body.session_id)
    db.commit()
    return result


class TutorDoubtRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    step_where_stuck: str | None = Field(default=None, max_length=2000)


@router.post("/tutor/doubt")
def tutor_doubt(
    body: TutorDoubtRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = tutor_service.tutor_doubt(db, current_user.id, body.question, body.step_where_stuck)
    db.commit()
    return result


@router.get("/tutor/sessions")
def tutor_sessions(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(TutorSession)
        .filter(TutorSession.user_id == current_user.id)
        .order_by(TutorSession.id.desc())
        .limit(50)
        .all()
    )
    return {
        "items": [
            {"id": s.id, "created_at": s.created_at.isoformat() if s.created_at else None}
            for s in rows
        ]
    }
