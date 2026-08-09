"""Knowledge metadata enrichment endpoints (Idea 13, phrases 22-27)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.kb import KbMetadataProposal, KbMetadataUpdate
from app.services.kb.metadata import apply_metadata_update, propose_metadata
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-metadata"])


@router.get("/documents/{document_id}/metadata-proposal", response_model=KbMetadataProposal)
def get_metadata_proposal(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a metadata proposal for the given document (per-user 404)."""
    from app.services.kb import KbService

    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return propose_metadata(db, doc)


@router.put("/documents/{document_id}/metadata", response_model=dict)
def update_metadata(
    document_id: int,
    body: KbMetadataUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apply a manual metadata override to a document.

    Provided fields are flagged as ``manual`` in metadata_json and
    will never be overwritten by re-ingest. Returns the updated
    document response.
    """
    from app.services.kb import KbService
    from app.schemas.kb import KbDocumentResponse

    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    apply_metadata_update(db, doc, body)
    return KbDocumentResponse.model_validate(doc).model_dump()
