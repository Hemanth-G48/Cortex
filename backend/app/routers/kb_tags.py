"""Auto-tagging endpoints (Phase 2, Idea 14, phrases 37-38)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbDocument, User
from app.schemas.kb import (
    KbApplyTags,
    KbDocumentTagsResponse,
    KbRejectTags,
    KbTagSuggestion,
)
from app.services.kb.tagger import apply_tags, propose_tags, reject_tags
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-tags"])


def _doc_or_404(db: Session, user_id: int, document_id: int) -> KbDocument:
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/documents/{document_id}/tags", response_model=KbDocumentTagsResponse)
def get_document_tags(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KbDocumentTagsResponse:
    """Return rule + ai suggestions for a document, excluding already-applied
    manual tags.
    """
    doc = _doc_or_404(db, current_user.id, document_id)
    suggestions = propose_tags(db, doc)

    # Collect manual tag ids so we can exclude them from suggestions.
    manual_tag_ids = {
        dt.tag_id
        for dt in doc.document_tags
        if dt.provenance == "manual"
    }

    filtered = [
        KbTagSuggestion.model_validate(s)
        for s in suggestions
        if s["tag_id"] not in manual_tag_ids
    ]
    return KbDocumentTagsResponse(document_id=doc.id, tags=filtered)


@router.post("/documents/{document_id}/tags", response_model=KbDocumentTagsResponse)
def apply_document_tags(
    document_id: int,
    body: KbApplyTags,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KbDocumentTagsResponse:
    """Apply (promote) suggested tags to manual/authoritative."""
    doc = _doc_or_404(db, current_user.id, document_id)
    apply_tags(db, doc, body.tag_ids)
    db.commit()

    # Re-propose to get the updated suggestion list (manual tags excluded).
    suggestions = propose_tags(db, doc)
    manual_tag_ids = {
        dt.tag_id
        for dt in doc.document_tags
        if dt.provenance == "manual"
    }
    filtered = [
        KbTagSuggestion.model_validate(s)
        for s in suggestions
        if s["tag_id"] not in manual_tag_ids
    ]
    return KbDocumentTagsResponse(document_id=doc.id, tags=filtered)


@router.delete("/documents/{document_id}/tags/{tag_id}")
def reject_document_tag(
    document_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Reject (remove) a single AI or manual tag suggestion.

    Rule tags are never removed.
    """
    doc = _doc_or_404(db, current_user.id, document_id)
    removed = reject_tags(db, doc, [tag_id])
    db.commit()
    return {"ok": True, "removed": removed}