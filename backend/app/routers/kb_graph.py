"""Knowledge-graph endpoints (Phase 2, Idea 16/18)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbDocument, User
from app.schemas.kb import KbGraphResponse
from app.services.kb.graph import build_graph, neighbors
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-graph"])

MAX_GRAPH_LIMIT = 1000
DEFAULT_GRAPH_LIMIT = 200


@router.get("/graph", response_model=KbGraphResponse)
def get_graph(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    source: str | None = None,
    tag: str | None = None,
    concept: str | None = None,
    relation: str | None = None,
    limit: int = DEFAULT_GRAPH_LIMIT,
) -> KbGraphResponse:
    limit = min(max(limit, 1), MAX_GRAPH_LIMIT)
    return build_graph(
        db,
        current_user.id,
        source=source,
        tag=tag,
        concept=concept,
        relation=relation,
        limit=limit,
    )


@router.get("/documents/{document_id}/neighbors")
def get_neighbors(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == current_user.id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return neighbors(db, current_user.id, document_id)
