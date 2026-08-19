"""Manual concept linking + document links panel (Phase 4, Idea 37).

- ``POST /api/kb/edges`` — create a manual edge (``provenance=manual``).
- ``DELETE /api/kb/edges/{id}`` — remove auto or manual edges.
- ``GET /api/kb/documents/{id}/links`` — aggregated concepts + related notes
  for the reader sidebar.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbConcept, KbDocument, KbEdge, User
from app.services.kb import KbService
from app.services.kb.graph import (
    add_edge,
    concepts_of,
    related_docs,
)
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-edges"])

ALLOWED_RELATIONS = {
    "MENTIONS", "RELATED", "SHARES_CONCEPT", "WIKILINK", "BACKLINK", "CITES",
    "SYNONYM_OF", "DEPENDS_ON", "DUPLICATE_OF",
}


class EdgeCreate(BaseModel):
    source_document_id: int
    target_id: int = Field(..., description="document id or concept id (see target_type)")
    relation: str = "RELATED"
    target_type: str = "document"  # document | concept


@router.post("/edges")
def create_edge(
    body: EdgeCreate,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a manual edge (phrase 62). Rejects self-edges / bad targets."""
    source = KbService.get_document(db, current_user.id, body.source_document_id)
    if source is None:
        raise HTTPException(404, "Source document not found")

    relation = body.relation.upper()
    if relation not in ALLOWED_RELATIONS:
        raise HTTPException(400, f"relation must be one of {', '.join(sorted(ALLOWED_RELATIONS))}")

    target_type = body.target_type
    target_document_id = None
    target_concept_id = None
    if target_type == "concept":
        concept = (
            db.query(KbConcept)
            .filter(KbConcept.id == body.target_id, KbConcept.user_id == current_user.id)
            .first()
        )
        if concept is None:
            raise HTTPException(404, "Concept not found")
        target_concept_id = concept.id
    elif target_type == "document":
        target = KbService.get_document(db, current_user.id, body.target_id)
        if target is None:
            raise HTTPException(404, "Target document not found")
        if target.id == source.id:
            raise HTTPException(400, "Self-edges are not allowed")
        target_document_id = target.id
    else:
        raise HTTPException(400, "target_type must be 'document' or 'concept'")

    edge = add_edge(
        db,
        current_user.id,
        source.id,
        target_document_id=target_document_id,
        relation=relation,
        weight=1.0,
        provenance="manual",
        target_type=target_type,
        target_concept_id=target_concept_id,
    )
    db.commit()
    if edge is None:
        raise HTTPException(400, "Edge could not be created")
    return {"id": edge.id, "ok": True}


@router.delete("/edges/{edge_id}")
def delete_edge(
    edge_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete any edge the user owns — manual or auto-inferred (phrase 63)."""
    edge = (
        db.query(KbEdge)
        .filter(KbEdge.id == edge_id, KbEdge.user_id == current_user.id)
        .first()
    )
    if edge is None:
        raise HTTPException(404, "Edge not found")
    db.delete(edge)
    db.commit()
    return {"ok": True}


@router.get("/documents/{document_id}/links")
def document_links(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Aggregated sidebar data: concepts + related notes (phrase 64)."""
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return {
        "document_id": document_id,
        "concepts": concepts_of(db, current_user.id, document_id),
        "related": related_docs(db, current_user.id, document_id),
    }
