"""Auto-tagging endpoints (Phase 2, Idea 14, phrases 37-38)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import KbDocument, KbDocumentTag, KbTag, User
from app.schemas.kb import (
    KbApplyTags,
    KbDocumentTagsResponse,
    KbRejectTags,
    KbTagSuggestion,
)
from app.services.kb.tagger import (
    apply_tags,
    create_document_tag,
    persist_ai_suggestions,
    persisted_suggestions,
    reject_tags,
)
from app.services.users import current_user

logger = logging.getLogger(__name__)

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


def _applied_tags(db: Session, doc: KbDocument) -> list[KbTagSuggestion]:
    """Rule + manual tags already linked to *doc* (the tag editor's applied
    chips). Ordered by name for a stable UI.
    """
    rows = (
        db.query(KbTag, KbDocumentTag.provenance)
        .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
        .filter(
            KbDocumentTag.document_id == doc.id,
            KbDocumentTag.user_id == doc.user_id,
            KbDocumentTag.provenance.in_(["rule", "manual"]),
        )
        .order_by(KbTag.name)
        .all()
    )
    return [
        KbTagSuggestion(tag_id=tag.id, name=tag.name, provenance=prov, confidence=1.0)
        for tag, prov in rows
    ]


def _tags_response(db: Session, doc: KbDocument) -> KbDocumentTagsResponse:
    """Build the tag panel payload: suggestions (rule + ai, manual excluded)
    plus the applied chips.

    Reads persisted suggestions only — never calls the LLM (opening a
    document must not spend a model call). The explicit
    ``POST /documents/{id}/tags/propose`` endpoint is the only path that
    re-runs the AI proposal.
    """
    suggestions = persisted_suggestions(db, doc)
    manual_tag_ids = {
        dt.tag_id for dt in doc.document_tags if dt.provenance == "manual"
    }
    filtered = [
        KbTagSuggestion.model_validate(s)
        for s in suggestions
        if s["tag_id"] not in manual_tag_ids
    ]
    return KbDocumentTagsResponse(
        document_id=doc.id, tags=filtered, applied=_applied_tags(db, doc)
    )


@router.get("/documents/{document_id}/tags", response_model=KbDocumentTagsResponse)
def get_document_tags(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> KbDocumentTagsResponse:
    """Return rule + ai suggestions for a document, excluding already-applied
    manual tags (which surface in ``applied``).
    """
    doc = _doc_or_404(db, current_user.id, document_id)
    return _tags_response(db, doc)


@router.post("/documents/{document_id}/tags/propose", response_model=KbDocumentTagsResponse)
def propose_document_tags(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> KbDocumentTagsResponse:
    """Explicit user action: run the AI (or deterministic-fallback) tag
    proposal for a document, persist the result, and return the panel.

    This is the ONLY endpoint that calls the LLM for tag suggestions — the
    ``GET`` endpoint reads the persisted rows, so browsing never re-derives
    them.
    """
    doc = _doc_or_404(db, current_user.id, document_id)
    persist_ai_suggestions(db, doc)
    db.commit()
    return _tags_response(db, doc)


@router.post("/documents/{document_id}/tags", response_model=KbDocumentTagsResponse)
def apply_document_tags(
    document_id: int,
    body: KbApplyTags,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> KbDocumentTagsResponse:
    """Apply (promote) suggested tags to manual/authoritative."""
    doc = _doc_or_404(db, current_user.id, document_id)
    apply_tags(db, doc, body.tag_ids)
    db.commit()
    return _tags_response(db, doc)


class KbCreateTagRequest(BaseModel):
    # Matches KbTag.name (String(100)); course: tags may hold readable titles.
    name: str = Field(min_length=1, max_length=100)


@router.post(
    "/documents/{document_id}/tags/create", response_model=KbDocumentTagsResponse
)
def create_document_tag_endpoint(
    document_id: int,
    body: KbCreateTagRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> KbDocumentTagsResponse:
    """Create-or-reuse a tag by name and attach it to the document as manual.

    ``course:<name>`` tags also trigger course derivation, so a freshly
    tagged note immediately surfaces as a course on the Courses page.
    """
    doc = _doc_or_404(db, current_user.id, document_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Tag name is empty")

    create_document_tag(db, doc, name)
    db.commit()

    # Event hook: a `course:` tag may now identify a course.
    if name.startswith(settings.COURSE_TAG_PREFIX):
        try:
            from app.services.course_derivation import derive_courses_from_tags

            derive_courses_from_tags(db, current_user.id)
        except Exception:  # noqa: BLE001 — tag must still apply if sync hiccups
            logger.exception(
                "Course derivation after tag create failed for doc %s", doc.id
            )

    return _tags_response(db, doc)


@router.delete("/documents/{document_id}/tags/{tag_id}")
def reject_document_tag(
    document_id: int,
    tag_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Reject (remove) a single AI or manual tag suggestion.

    Rule tags are never removed.
    """
    doc = _doc_or_404(db, current_user.id, document_id)
    removed = reject_tags(db, doc, [tag_id])
    db.commit()
    return {"ok": True, "removed": removed}