"""Mind-map endpoints (Phase 4, Idea 38)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import KbService
from app.services.kb.mindmap import build_tree, export_markdown, export_opml
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-mindmap"])


@router.get("/documents/{document_id}/mindmap")
def document_mindmap(
    document_id: int,
    format: str = Query(default="json"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mind-map tree for a document (json | markdown | opml)."""
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")

    tree = build_tree(db, current_user.id, doc)
    if format == "json":
        return tree
    if format == "markdown":
        return Response(
            content=export_markdown(tree),
            media_type="text/markdown",
            headers={"Content-Disposition": 'attachment; filename="mindmap.md"'},
        )
    if format == "opml":
        return Response(
            content=export_opml(tree),
            media_type="text/x-opml",
            headers={"Content-Disposition": 'attachment; filename="mindmap.opml"'},
        )
    raise HTTPException(400, "format must be json | markdown | opml")
