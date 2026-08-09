"""Citation registry endpoints (Phase 4, Idea 36)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbCitation, User
from app.services.kb import KbService
from app.services.kb.citation_registry import (
    build_bibtex,
    list_citations,
)
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-citations"])


@router.get("/citations")
def citations(
    year: int | None = Query(default=None),
    venue: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items = list_citations(
        db, current_user.id, year=year, venue=venue
    )
    return {"items": items, "total": len(items)}


@router.get("/documents/{document_id}/citations")
def document_citations(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    rows = (
        db.query(KbCitation)
        .filter(
            KbCitation.user_id == current_user.id,
            KbCitation.document_id == document_id,
        )
        .order_by(KbCitation.created_at.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "cite_key": r.cite_key,
                "title": r.title,
                "authors": KbService.json_loads(r.authors) or [],
                "year": r.year,
                "venue": r.venue,
                "doi": r.doi,
                "arxiv_id": r.arxiv_id,
                "raw_text": r.raw_text,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.get("/citations/export")
def export_citations(
    format: str = Query(default="bibtex"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if format != "bibtex":
        raise HTTPException(400, "Only format=bibtex is supported")
    items = list_citations(db, current_user.id)
    bibtex = build_bibtex(items)
    return Response(
        content=bibtex,
        media_type="application/x-bibtex",
        headers={"Content-Disposition": 'attachment; filename="citations.bib"'},
    )
