"""Idea 97 — recommendation engine router.

- ``GET /api/kb/recommendations`` — ranked cross-domain items with explainable
  reasons (phrase 65).
- ``POST /api/kb/recommendations/feedback`` — accept/skip logged (phrase 66).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import recommendations as rec_service
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-recommendations"])


@router.get("/recommendations")
def list_recommendations(
    limit: int = Query(default=8, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rec_service.list_recommendations(db, current_user.id, limit=limit)


class RecommendationFeedbackRequest(BaseModel):
    action: str = Field(pattern="^(accept|skip)$")


@router.post("/recommendations/{item_id}/feedback")
def recommendation_feedback(
    item_id: str,
    body: RecommendationFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = rec_service.record_feedback(
            db, current_user.id, item_id, body.action
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return result
