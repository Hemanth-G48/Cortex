"""Re-index endpoints (Phase 2, Idea 20, phrases 96-99).

``POST /api/kb/admin/reindex`` triggers the incremental re-index coordinator
as a ``KbJob`` (job_type=reindex).  Both endpoints are fully user-scoped —
they only ever touch the current user's own sources/documents — so any
authenticated user may reindex their own knowledge base.  The ``/admin/``
path prefix is kept for backward compatibility with the frontend.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbSource, User
from app.schemas.kb import KbJobResponse
from app.services.kb import jobs
from app.services.kb.reindex import dirty_documents
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-reindex"])


@router.post("/admin/reindex", response_model=KbJobResponse)
def admin_reindex(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    source_id: int | None = Query(default=None),
    document_ids: list[int] | None = Query(default=None),
):
    """Trigger an incremental reindex (phrase 97).

    ``?source_id=`` scopes the rebuild to one source; otherwise all dirty
    documents for the current user are processed.  Returns the queued job.
    """
    if source_id is not None:
        source = (
            db.query(KbSource)
            .filter(
                KbSource.id == source_id,
                KbSource.user_id == current_user.id,
            )
            .first()
        )
        if source is None:
            raise HTTPException(404, "Source not found")
        job = jobs.submit_reindex_job(db, current_user.id, source_id=source_id)
    else:
        # No source scope → process the user's dirty documents. Gather the
        # dirty id set so the job iterates per document (the UI progress bar
        # reads processed_items/total_items) instead of submitting an empty
        # list, which would complete instantly without doing any work.
        doc_ids = document_ids or [
            d.id for d in dirty_documents(db, current_user.id)
        ]
        job = jobs.submit_reindex_job(db, current_user.id, document_ids=doc_ids)
    return KbJobResponse.model_validate(job)


@router.post("/admin/backfill", response_model=KbJobResponse)
def admin_backfill(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    source_id: int | None = Query(default=None),
):
    """Mark every document dirty then run a full reindex (phrase 99)."""
    if source_id is not None:
        source = (
            db.query(KbSource)
            .filter(
                KbSource.id == source_id,
                KbSource.user_id == current_user.id,
            )
            .first()
        )
        if source is None:
            raise HTTPException(404, "Source not found")
        from app.services.kb import reindex as reindex_service

        marked = reindex_service.mark_dirty(
            db, current_user.id, source_id=source_id
        )
    else:
        from app.services.kb import reindex as reindex_service

        marked = reindex_service.mark_dirty(db, current_user.id)

    if source_id is not None:
        job = jobs.submit_reindex_job(db, current_user.id, source_id=source_id)
    else:
        # Reindex the freshly-marked dirty set as a per-document job so the
        # UI shows real progress (see admin_reindex).
        job = jobs.submit_reindex_job(
            db,
            current_user.id,
            document_ids=[d.id for d in dirty_documents(db, current_user.id)],
        )
    # Merge marked_dirty into whatever summary the job runner produced/set
    # (don't clobber the reindex summary in sync mode, where the job already
    # completed inline).
    prev = json.loads(job.summary_json) if job.summary_json else {}
    prev["marked_dirty"] = marked
    job.summary_json = json.dumps(prev)
    db.add(job)
    db.commit()
    db.refresh(job)
    return KbJobResponse.model_validate(job)
