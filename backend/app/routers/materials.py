"""Materials CRUD endpoints for SyllabusAI."""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Character, Material, CurriculumUnit, User
from app.schemas.material import MaterialCreate, MaterialResponse
from app.services.security import get_current_user
from app.services.text_extractor import NoExtractableTextError
from app.services.ingestion import text_for_material

router = APIRouter(prefix="/api", tags=["materials"])

# G13 (Phase 86): XP for a user's first upload to a given unit.
MATERIAL_UPLOAD_XP = 15


def _grant_first_upload_xp(db: Session, user: User, unit_id: int, material_id: int) -> int:
    """Grant XP once per (user, unit) — duplicates earn nothing.

    ``material_id`` is excluded from the count so the guard is self-contained
    regardless of when the caller commits the new row.
    """
    existing = (
        db.query(Material)
        .filter(
            Material.unit_id == unit_id,
            Material.uploaded_by_id == user.id,
            Material.is_active == True,  # noqa: E712
            Material.id != material_id,
        )
        .count()
    )
    if existing > 0:
        return 0

    user.total_xp = (user.total_xp or 0) + MATERIAL_UPLOAD_XP
    char = db.query(Character).filter(Character.user_id == user.id).first()
    if char:
        char.xp = (char.xp or 0) + MATERIAL_UPLOAD_XP
    db.commit()
    return MATERIAL_UPLOAD_XP

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


def _allowed_extension(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    if ext in ALLOWED_EXTENSIONS:
        return ext
    return None


def _rejects_path_traversal(filename: str) -> bool:
    """Reject client filenames that could traverse the upload dir.

    Storage always uses a fresh UUID name, so this is defense in depth — but
    suspicious names (path separators, '..', or any path component) are still
    refused so the original filename is never echoed into a path.
    """
    if ".." in filename or "/" in filename or "\\" in filename:
        return True
    return os.path.basename(filename) != filename


def _mime_sniff_rejects(ext: str, data: bytes) -> bool:
    """Reject content that clearly does not match the claimed extension."""
    if not data:
        return False
    if ext == "pdf" and not data.startswith(b"%PDF"):
        return True
    if ext == "docx" and not data.startswith(b"PK"):
        return True
    if ext in ("txt", "md") and (
        data.startswith(b"\x89PNG")
        or data.startswith(b"%PDF")
        or data.startswith(b"PK")
    ):
        # Text files shouldn't carry binary magic headers.
        return True
    return False


@router.get("/curriculum/units/{unit_id}/materials", response_model=dict)
def list_unit_materials(
    unit_id: int,
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Material).filter(Material.unit_id == unit_id, Material.is_active == True)  # noqa: E712
    if q:
        query = query.filter(Material.title.ilike(f"%{q}%"))
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [MaterialResponse.model_validate(m) for m in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/materials/{material_id}", response_model=MaterialResponse)
def get_material(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    material.view_count += 1
    db.add(material)
    db.commit()
    db.refresh(material)
    return MaterialResponse.model_validate(material)


@router.get("/materials/{material_id}/download")
def download_material(material_id: int, db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(404, "Material not found")
    file_path = material.file_path_on_disk()
    if not os.path.isfile(file_path):
        raise HTTPException(404, "File not found")
    material.download_count += 1
    db.add(material)
    db.commit()
    return FileResponse(file_path, filename=material.original_file_name)


@router.post("/curriculum/units/{unit_id}/materials", response_model=MaterialResponse)
def upload_material(
    unit_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    ext = _allowed_extension(file.filename or "")
    if ext is None:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    if _rejects_path_traversal(file.filename or ""):
        raise HTTPException(400, "Invalid file name")

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"File too large (max {settings.MAX_UPLOAD_MB} MB)")

    if _mime_sniff_rejects(ext, data):
        raise HTTPException(400, "File content does not match its extension")

    directory = settings.UPLOAD_DIR
    os.makedirs(directory, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    target = os.path.join(directory, stored_name)
    with open(target, "wb") as out:
        out.write(data)

    material = Material(
        unit_id=unit_id,
        uploaded_by_id=current_user.id,
        title=file.filename or stored_name,
        file_type=ext,
        file_url=f"/uploads/{stored_name}",
        file_size=len(data),
        original_file_name=file.filename or stored_name,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    # G13 (Phase 86): reward the user's first upload to this unit.
    _grant_first_upload_xp(db, current_user, unit_id, material.id)

    # Extract text asynchronously (graceful on failure).
    try:
        text_for_material(db, material)
    except Exception:
        db.rollback()
        # Re-fetch to avoid stale state after rollback.
        db.refresh(material)

    return MaterialResponse.model_validate(material)
