"""Knowledge source registry (Idea 2, phrases 11–20)."""

from __future__ import annotations

import os
from sqlalchemy import func, or_

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbDocument, KbEdge, KbSource, User
from app.schemas.kb import KbScanResult, KbSourceCreate, KbSourceResponse, KbSourceUpdate
from app.services.kb import KbService
from app.services.kb import auto_sync, jobs
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-sources"])


def _normalize_scan_subpath(path: str | None) -> str | None:
    """Validate + normalize an optional scan subfolder path.

    Returns ``None`` when omitted/blank (whole-source scan). Rejects absolute
    paths and any ``..`` traversal; returns the cleaned relative path (no
    leading/trailing slashes) otherwise.
    """
    if path is None:
        return None
    raw = path.strip()
    if not raw:
        return None
    if os.path.isabs(raw):
        raise HTTPException(400, "path must be relative to the source root")
    parts = Path(raw).parts
    if not parts or ".." in parts:
        raise HTTPException(400, "path must be a relative folder inside the source")
    return "/".join(parts)


def _with_counts(db: Session, user_id: int, sources: list[KbSource]) -> list[KbSourceResponse]:
    counts = dict(
        db.query(KbDocument.source_id, func.count(KbDocument.id))
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.source_id.isnot(None),
        )
        .group_by(KbDocument.source_id)
        .all()
    )
    items = []
    for source in sources:
        resp = KbSourceResponse.model_validate(source)
        resp.document_count = counts.get(source.id, 0)
        items.append(resp)
    return items


@router.post("/sources", response_model=KbSourceResponse, status_code=201)
def create_source(
    body: KbSourceCreate,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Register a source; ``root_path`` must exist on disk (phrase 13)."""
    if not body.root_path or not os.path.isdir(body.root_path):
        raise HTTPException(400, "root_path does not exist or is not a directory")
    source = KbSource(
        user_id=current_user.id,
        name=body.name,
        source_type=body.source_type,
        root_path=os.path.abspath(body.root_path),
        enabled=body.enabled,
        sync_type=body.sync_type,
        sync_source_path=body.sync_source_path,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return _with_counts(db, current_user.id, [source])[0]


@router.get("/sources", response_model=dict)
def list_sources(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    sources = (
        db.query(KbSource)
        .filter(KbSource.user_id == current_user.id)
        .order_by(KbSource.created_at.desc())
        .all()
    )
    items = _with_counts(db, current_user.id, sources)
    return {"items": items, "total": len(items)}


@router.get("/sources/{source_id}", response_model=KbSourceResponse)
def get_source(
    source_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    source = KbService.get_source(db, current_user.id, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    return _with_counts(db, current_user.id, [source])[0]


@router.put("/sources/{source_id}", response_model=KbSourceResponse)
def update_source(
    source_id: int,
    body: KbSourceUpdate,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    source = KbService.get_source(db, current_user.id, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    if body.root_path is not None:
        if not os.path.isdir(body.root_path):
            raise HTTPException(400, "root_path does not exist or is not a directory")
        source.root_path = os.path.abspath(body.root_path)
    if body.name is not None:
        source.name = body.name
    if body.source_type is not None:
        source.source_type = body.source_type
    if body.enabled is not None:
        source.enabled = body.enabled
    if body.sync_type is not None:
        source.sync_type = body.sync_type
    if body.sync_source_path is not None:
        if not os.path.isdir(body.sync_source_path):
            raise HTTPException(400, "sync_source_path does not exist or is not a directory")
        source.sync_source_path = os.path.abspath(body.sync_source_path)
    db.add(source)
    db.commit()
    db.refresh(source)
    return _with_counts(db, current_user.id, [source])[0]


@router.delete("/sources/{source_id}")
def delete_source(
    source_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Hard-delete the source, its documents, chunks, versions and edges in one
    transaction (phrase 16)."""
    source = KbService.get_source(db, current_user.id, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    doc_ids = [
        d.id
        for d in db.query(KbDocument)
        .filter(KbDocument.source_id == source.id, KbDocument.user_id == current_user.id)
        .all()
    ]
    if doc_ids:
        db.query(KbEdge).filter(
            KbEdge.user_id == current_user.id,
            or_(
                KbEdge.source_document_id.in_(doc_ids),
                KbEdge.target_document_id.in_(doc_ids),
            ),
        ).delete(synchronize_session=False)
    db.delete(source)  # ORM cascade → documents → chunks/versions
    db.commit()
    return {"ok": True, "deleted_documents": len(doc_ids)}


@router.post("/sources/{source_id}/scan", response_model=KbScanResult)
def scan_source(
    source_id: int,
    path: str | None = Query(
        default=None,
        description="Optional folder inside the source root to scan (relative path, e.g. 'cybersecurity'). Omit to scan the whole source.",
    ),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Enqueue a scan job and return it (phrase 17). Synchronous runs include
    the summary so the UI can show dedupe stats immediately.

    ``path`` scopes the scan to one folder inside the source root — a
    manual "update from folder" so updated and newly created files in that
    folder are ingested without re-scanning the whole vault. The path must
    be relative (no ``..``, no leading slash) and exist on disk.
    """
    source = KbService.get_source(db, current_user.id, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    subpath = _normalize_scan_subpath(path)
    if subpath is not None:
        target = os.path.join(source.root_path or "", subpath)
        if not os.path.isdir(target):
            raise HTTPException(
                400, f"Folder not found inside source: {path}"
            )
    job = jobs.submit_scan_job(db, source.id, subpath=subpath)
    return KbScanResult(
        job=job,
        summary=KbService.json_loads(job.summary_json),
    )


@router.post("/sources/{source_id}/sync", response_model=dict)
def sync_source(
    source_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Manual sync trigger for an external source (Idea 89, phrase 87).

    Bypasses the KB_SYNC_ENABLED toggle (explicit user action) but still
    requires a configured adapter (git | drive | clip).
    """
    source = KbService.get_source(db, current_user.id, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    return auto_sync.sync_source(db, source, force=True)


@router.get("/sources/{source_id}/sync-status", response_model=dict)
def sync_status(
    source_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Last-sync state for one source (Idea 89, phrase 87)."""
    source = KbService.get_source(db, current_user.id, source_id)
    if source is None:
        raise HTTPException(404, "Source not found")
    return auto_sync.sync_status(source)
