"""Second Brain folder/domain endpoints — the folder hierarchy as source of truth.

- ``GET /api/kb/folders?course_id=X`` — canonical domain tree for a course
  (folder-derived, no LLM, no computation on load: reads persisted rows).
- ``GET /api/kb/folders/{folder_id}`` — one domain: breadcrumb, documents,
  subfolders.
- ``GET /api/kb/folders/{folder_id}/gaps`` — saved domain Gap Analysis
  (``cached: True`` + ``analyzed_at``) or computed once on the very first
  request. Opening a domain page never re-runs the analysis.
- ``POST /api/kb/folders/{folder_id}/gaps/analyze`` — the explicit
  Re-analyze action that recomputes and saves.

Documents belong to domains by folder path — no manual assignment anywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbFolder, User
from app.services.kb.domain_service import (
    domain_detail,
    domain_gaps,
    domain_tree,
    load_saved_domain_gaps,
    save_domain_gaps,
)
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/folders", tags=["kb-folders"])


def _folder_or_404(db: Session, user_id: int, folder_id: int) -> KbFolder:
    folder = (
        db.query(KbFolder)
        .filter(KbFolder.id == folder_id, KbFolder.user_id == user_id)
        .first()
    )
    if folder is None:
        raise HTTPException(404, "Domain not found")
    return folder


@router.get("")
def list_domains(
    course_id: int | None = Query(default=None),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Canonical domain tree for a course (or all domains when unscoped)."""
    if course_id is not None:
        return {"items": domain_tree(db, current_user.id, course_id)}
    rows = (
        db.query(KbFolder)
        .filter(KbFolder.user_id == current_user.id)
        .order_by(KbFolder.course_id, KbFolder.name)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "path": r.path,
                "depth": r.depth,
                "doc_count": r.doc_count,
                "course_id": r.course_id,
            }
            for r in rows
        ]
    }


@router.get("/{folder_id}")
def get_domain(
    folder_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """One domain: breadcrumb, its documents (direct children), subfolders."""
    detail = domain_detail(db, current_user.id, folder_id)
    if detail is None:
        raise HTTPException(404, "Domain not found")
    return detail


@router.get("/{folder_id}/gaps")
def domain_gaps_endpoint(
    folder_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Saved domain Gap Analysis, or computed once on the first request.

    Persisted per folder (``FolderGapAnalysis``): later requests return the
    stored copy (``cached: True`` + ``analyzed_at`` + staleness) without
    recomputing — navigation never triggers the analysis.
    """
    _folder_or_404(db, current_user.id, folder_id)
    saved = load_saved_domain_gaps(db, current_user.id, folder_id)
    if saved is not None:
        return saved
    folder = _folder_or_404(db, current_user.id, folder_id)
    payload = domain_gaps(db, current_user.id, folder)
    payload["cached"] = False
    payload["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    save_domain_gaps(db, current_user.id, folder.id, payload)
    return payload


@router.post("/{folder_id}/gaps/analyze")
def domain_gaps_reanalyze(
    folder_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Force a fresh domain Gap Analysis and save it (the only recompute path)."""
    folder = _folder_or_404(db, current_user.id, folder_id)
    payload = domain_gaps(db, current_user.id, folder)
    payload["cached"] = False
    payload["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    save_domain_gaps(db, current_user.id, folder.id, payload)
    return payload
