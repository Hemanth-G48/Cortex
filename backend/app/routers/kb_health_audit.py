"""Vault Health Audit workflow endpoints.

``GET /api/kb/health-audit`` aggregates the existing health signals (missing
notes, outdated notes, near-duplicates, low-quality docs, dead links) — read
only, no LLM calls on navigation. All mutations are explicit POST actions:
``/rescan`` (refresh detectors), ``/missing/{id}/dismiss``,
``/outdated/{id}/resolve``, ``/duplicates/{document_id}/archive``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import health_audit as audit_svc
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/health-audit", tags=["kb-health-audit"])


@router.get("")
def health_audit(
    limit: int = Query(default=12, ge=1, le=50),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only aggregate snapshot (never mutates, never calls the LLM)."""
    return audit_svc.audit(db, current_user.id, limit=limit)


@router.post("/rescan")
def rescan(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Explicit user action: re-run the cheap detectors + health score."""
    result = audit_svc.rescan(db, current_user.id)
    return result


class ResolveOutdatedRequest(BaseModel):
    action: str = Field(pattern="^(updated|archived|dismissed)$")


@router.post("/outdated/{note_id}/resolve")
def resolve_outdated(
    note_id: int,
    body: ResolveOutdatedRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = audit_svc.resolve_outdated(db, current_user.id, note_id, body.action)
    except ValueError as e:
        raise HTTPException(404, str(e))
    db.commit()
    return result


@router.post("/missing/{suggestion_id}/dismiss")
def dismiss_missing(
    suggestion_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = audit_svc.dismiss_missing(db, current_user.id, suggestion_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    db.commit()
    return result


@router.post("/duplicates/{document_id}/archive")
def archive_duplicate(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        result = audit_svc.archive_duplicate(db, current_user.id, document_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result
