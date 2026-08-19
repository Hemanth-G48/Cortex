"""New-note triage queue endpoints (workflow glue)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import triage as triage_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-triage"])


@router.get("/triage")
def triage_queue(
    limit: int = Query(default=50, ge=1, le=200),
    window_days: int = Query(default=triage_service.TRIAGE_WINDOW_DAYS, ge=1, le=365),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Untriaged documents from the recent ingestion window, newest first.

    Each item carries auto-detected ``course:`` subjects, its current tags,
    and any pending folder-move proposal — everything needed to file it.
    """
    return {
        "items": triage_service.queue(db, current_user.id, limit=limit, window_days=window_days),
        "stats": triage_service.triage_stats(db, current_user.id, window_days=window_days),
    }


@router.get("/triage/stats")
def triage_stats(
    window_days: int = Query(default=triage_service.TRIAGE_WINDOW_DAYS, ge=1, le=365),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Lightweight pending/triaged counts (no document payload).

    Used by the dashboard reminder banner to decide whether new notes need
    filing, without shipping the queue items.
    """
    return triage_service.triage_stats(db, current_user.id, window_days=window_days)


@router.post("/triage/{document_id}/apply-subjects")
def apply_detected_subjects(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Accept the auto-detected subjects for a queued document.

    Attaches ``course:<subject>`` tags (refreshing course derivation) and
    marks the document as triaged so it leaves the queue.
    """
    result = triage_service.apply_subjects(db, current_user.id, document_id)
    db.commit()
    return result


class ManualTagRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@router.post("/triage/{document_id}/tag")
def manual_tag(
    document_id: int,
    body: ManualTagRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Attach a specific tag name (e.g. ``course:Cybersecurity``) and file it."""
    result = triage_service.manual_tag(db, current_user.id, document_id, body.name)
    db.commit()
    return result


@router.post("/triage/{document_id}/dismiss")
def dismiss_document(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark the document as triaged without tagging it."""
    result = triage_service.dismiss(db, current_user.id, document_id)
    db.commit()
    return result


@router.post("/triage/accept-all")
def accept_all_subjects(
    limit: int = Query(default=200, ge=1, le=2000),
    window_days: int = Query(default=triage_service.TRIAGE_WINDOW_DAYS, ge=1, le=365),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Bulk accept: apply detected ``course:`` subjects to every untriaged doc
    in the window (up to ``limit``) and file them out of the queue.

    Docs with no detected subjects stay queued — run again or dismiss them.
    """
    result = triage_service.accept_all_subjects(
        db, current_user.id, limit=limit, window_days=window_days
    )
    db.commit()
    return result


@router.post("/triage/dismiss-all")
def dismiss_all_documents(
    limit: int = Query(default=200, ge=1, le=2000),
    window_days: int = Query(default=triage_service.TRIAGE_WINDOW_DAYS, ge=1, le=365),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Bulk dismiss: mark every untriaged doc in the window (up to ``limit``)
    as triaged without tagging, clearing the queue in batches."""
    result = triage_service.dismiss_all(
        db, current_user.id, limit=limit, window_days=window_days
    )
    db.commit()
    return result
