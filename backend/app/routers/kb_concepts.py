"""Concept extraction endpoints (Phase 2, Idea 15)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbConcept, KbDocument, KbEdge, User
from app.schemas.kb import KbConceptResponse
from app.services.kb import KbService
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-concepts"])


@router.get("/concepts", response_model=dict)
def list_concepts(
    q: str = Query(default="", min_length=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Per-user concept index with document counts (phrase 49)."""
    query = db.query(KbConcept).filter(KbConcept.user_id == current_user.id)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (KbConcept.canonical_name.ilike(like))
            | (KbConcept.definition.ilike(like))
        )

    total = query.count()
    items = (
        query.order_by(KbConcept.canonical_name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result_items = []
    for c in items:
        doc_count = (
            db.query(KbEdge)
            .filter(
                KbEdge.target_concept_id == c.id,
                KbEdge.relation == "MENTIONS",
                KbEdge.user_id == current_user.id,
            )
            .join(KbDocument, KbEdge.source_document_id == KbDocument.id)
            .filter(KbDocument.user_id == current_user.id)
            .count()
        )
        result_items.append(KbConceptResponse(
            id=c.id,
            canonical_name=c.canonical_name,
            definition=c.definition,
            aliases=KbService.json_loads(c.aliases) if c.aliases else [],
            document_count=doc_count,
            created_at=c.created_at,
            updated_at=c.updated_at,
        ))

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
