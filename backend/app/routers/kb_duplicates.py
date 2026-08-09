"""Near-duplicate endpoints (Phase 2, G9). Filled in by G9 agent."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.kb import KbDuplicateItem, KbMergeRequest
from app.services.kb.neardup import (
    archive_document,
    list_duplicates,
    merge_documents,
    scan_duplicates,
)
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-duplicates"])


class ScanResult(BaseModel):
    items: list[KbDuplicateItem]
    total: int
    method: str


@router.get("/duplicates", response_model=ScanResult)
def get_duplicates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = list_duplicates(db, current_user.id)
    return ScanResult(items=items, total=len(items), method="embedding")


@router.post("/duplicates/scan", response_model=ScanResult)
def post_scan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pairs = scan_duplicates(db, current_user.id)
    items = [
        KbDuplicateItem(
            document_id=p["document_id"],
            duplicate_of_id=p["duplicate_of_id"],
            similarity=p["similarity"],
            method=p["method"],
            created_at=None,
        )
        for p in pairs
    ]
    return ScanResult(items=items, total=len(items), method="embedding")


@router.post("/duplicates/merge")
def post_merge(
    body: KbMergeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = merge_documents(db, current_user.id, body.keep_id, body.merge_ids)
    return {"ok": True, "merged": result["merged"]}


@router.post("/duplicates/{document_id}/archive")
def post_archive(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        archive_document(db, current_user.id, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"ok": True}
