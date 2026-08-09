"""Note-quality endpoints (Phase 4, Idea 39)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import KbService
from app.services.kb.quality import (
    dismiss_suggestion,
    generate_suggestions,
    get_or_compute,
    list_by_score,
    list_suggestions,
)
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-quality"])


@router.get("/documents/{document_id}/quality")
def document_quality(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return {
        "document_id": doc.id,
        **get_or_compute(db, doc),
        "suggestions": list_suggestions(db, current_user.id, doc.id),
    }


@router.get("/quality")
def quality_list(
    sort: str = "score",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return list_by_score(db, current_user.id, sort=sort)


@router.post("/documents/{document_id}/quality/suggestions")
def quality_suggestions_generate(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    items = generate_suggestions(db, doc)
    return {"document_id": doc.id, "generated": len(items), "items": items}


@router.post("/quality/suggestions/{suggestion_id}/dismiss")
def quality_suggestion_dismiss(
    suggestion_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ok = dismiss_suggestion(db, current_user.id, suggestion_id)
    if not ok:
        raise HTTPException(404, "Suggestion not found")
    return {"ok": True}
