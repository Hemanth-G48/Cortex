"""Related-documents endpoints (Phase 2, Idea 17, phrases 68-70).

``GET /api/kb/documents/{id}/related`` wraps the incremental related-doc
inference: the target document is compared against the user's index and the
resulting ``RELATED``/``BACKLINK``/``WIKILINK`` neighbors are returned with
weights.  Every query is user-scoped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbDocument, User
from app.schemas.kb import KbRelatedResponse
from app.services.kb.related import related_documents
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-related"])


@router.get("/documents/{document_id}/related", response_model=KbRelatedResponse)
def get_related(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    relation: str | None = None,
    infer: bool = True,
) -> KbRelatedResponse:
    """Related documents for *document_id* (per-user 404).

    ``relation`` filters the returned neighbors (RELATED | WIKILINK |
    BACKLINK | SHARES_CONCEPT | …).  ``infer=false`` skips the similarity
    pass and returns only edges already stored in ``kb_edges``.
    """
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == current_user.id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")

    data = related_documents(
        db, current_user.id, document_id, relation=relation, infer=infer
    )
    return KbRelatedResponse(**data)
