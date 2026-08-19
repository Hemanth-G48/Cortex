"""API endpoint for auto-detecting course subjects from Second Brain."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb.auto_subject_detect import auto_tag_documents, get_detection_preview
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-auto-subjects"])


@router.get("/auto-subjects/preview")
def preview_subjects(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    sample_size: int = Query(100, ge=10, le=1000),
) -> dict:
    """Preview what subjects would be detected from your documents.
    
    This does NOT create any tags - just shows what would be detected.
    """
    return get_detection_preview(db, current_user.id, sample_size)


@router.post("/auto-subjects/detect")
def detect_and_tag_subjects(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    dry_run: bool = Query(False),
    limit: int = Query(0, ge=0),
) -> dict:
    """Auto-detect course subjects and tag documents.
    
    Args:
        dry_run: If True, only analyze without creating tags
        limit: Max documents to process (0 = all)
    
    Returns:
        Summary of detection results
    """
    return auto_tag_documents(db, current_user.id, dry_run=dry_run, limit=limit)
