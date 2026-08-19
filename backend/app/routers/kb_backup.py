"""Vault backup & restore endpoints (workflow glue)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import backup as backup_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-backup"])


@router.post("/backup/export")
def export_backup(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Build and download the full vault backup zip."""
    data = backup_service.build_backup_zip(db, current_user.id)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="vault-backup-{stamp}.zip"'
        },
    )


@router.post("/backup/restore")
def restore_backup(
    file: UploadFile = File(...),
    replace_db: bool = Query(default=False),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Restore a vault backup zip.

    Vault files are restored into their original source roots. The database
    snapshot is only applied when ``?replace_db=true`` (default safe).
    """
    data = file.file.read()
    if len(data) > 200 * 1024 * 1024:
        raise HTTPException(413, "Backup file too large (max 200 MB)")
    result = backup_service.restore_zip(
        db, current_user.id, data, replace_db=replace_db
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Restore failed"))
    db.commit()
    return result
