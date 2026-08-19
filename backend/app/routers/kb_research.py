"""Idea 96 — research assistant router.

- ``POST /api/kb/research/explain`` — full paper workflow for a document
  (summary + contributions + related + optional cited synthesis) (phrase 56).
- ``GET /api/kb/research/related`` — related-paper ranking (phrase 54).

Per-user; every LLM step is budget-capped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import research as research_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-research"])


class ResearchExplainRequest(BaseModel):
    document_id: int | None = None
    arxiv_id: str | None = None
    question: str | None = Field(default=None, max_length=2000)


@router.post("/research/explain")
def research_explain(
    body: ResearchExplainRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if body.document_id is None and not body.arxiv_id:
        raise HTTPException(400, "document_id or arxiv_id is required")
    if body.document_id is None:
        # Ingest-by-arxiv is handled by the papers router; here we resolve the
        # arxiv id to an existing document for this user.
        from app.models import KbDocument

        doc = (
            db.query(KbDocument)
            .filter(
                KbDocument.user_id == current_user.id,
                KbDocument.metadata_json.contains(body.arxiv_id),
            )
            .first()
        )
        if doc is None:
            raise HTTPException(404, "No vault document for that arXiv ID")
        body = body.model_copy(update={"document_id": doc.id})
    try:
        result = research_service.explain(
            db, current_user.id, body.document_id, body.question
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    db.commit()
    return result


@router.get("/research/related")
def research_related(
    document_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    items = research_service.related_papers(
        db, current_user.id, document_id, limit=limit
    )
    return {"document_id": document_id, "items": items}
