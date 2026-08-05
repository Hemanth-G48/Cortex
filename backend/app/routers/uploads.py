"""Document upload endpoints.

Serves both the STUDENT-PLANAR upload flow (multipart ``file`` + optional
``kind`` form field, returns ``url``/``filename``/``size``/``kind``) and the
Zenith-Study-Planner document-QA flow (G1 Phase 6). Files are validated
(extension allowlist + size cap), stored under ``UPLOAD_DIR``, and served
back from ``/uploads`` (mounted in ``main.py``).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.security import get_current_user

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

# Documents (Zenith) + images/office files (STUDENT-PLANAR avatar/attachments).
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx", ".pptx", ".xlsx", ".csv",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
}


def _upload_dir() -> Path:
    directory = Path(settings.UPLOAD_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# ---------------------------------------------------------------------------
# Phase 86: magic-byte sniffing (defense in depth against MIME spoofing)
# ---------------------------------------------------------------------------
# The extension allowlist already blocks executable payloads; this check goes
# one step further and rejects files whose declared extension does not match
# the content's magic bytes (e.g. a .pdf that is really a shell script).

_OXML_MAGIC = b"PK\x03\x04"  # zip container used by docx/pptx/xlsx


def _sniff_matches(suffix: str, data: bytes) -> bool:
    """Return True when the payload's magic bytes match the declared extension."""
    head = data[:512]
    if suffix == ".pdf":
        return data.startswith(b"%PDF")
    if suffix == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if suffix in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if suffix == ".gif":
        return head.startswith((b"GIF87a", b"GIF89a"))
    if suffix == ".webp":
        return head.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if suffix in (".docx", ".pptx", ".xlsx"):
        return head.startswith(_OXML_MAGIC)
    if suffix == ".svg":
        return b"<svg" in head.lower()
    if suffix in (".txt", ".md", ".csv"):
        # Plain text must not contain NUL bytes (binary disguised as text).
        return b"\x00" not in head
    return True


@router.post("", status_code=201)
def upload(
    file: UploadFile = File(...),
    kind: str = Form(default="attachment"),
) -> dict:
    """Store an uploaded file and return its public URL + metadata."""
    original = Path(file.filename or "file.txt").name  # strip any path
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, detail={"error": "File type not allowed"})

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, detail={"error": "File too large"})
    if not data:
        raise HTTPException(400, detail={"error": "File is empty"})
    if not _sniff_matches(suffix, data):
        raise HTTPException(400, detail={"error": "File content does not match its type"})

    # Persist with a random name (extension preserved so static serving works).
    directory = _upload_dir()
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = directory / stored_name
    with target.open("wb") as out:
        out.write(data)

    return {
        "name": original,
        "filename": original,
        "kind": kind,
        "content_type": file.content_type or "application/octet-stream",
        "url": f"/uploads/{stored_name}",
        "size": len(data),
        "size_bytes": len(data),
    }


@router.get("")
def list_uploads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List previously uploaded files (metadata only). Authenticated."""
    directory = _upload_dir()
    items = []
    for path in sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if path.is_file():
            items.append({
                "name": path.name,
                "filename": path.name,
                "kind": path.suffix.lstrip("."),
                "url": f"/uploads/{path.name}",
                "size": path.stat().st_size,
                "size_bytes": path.stat().st_size,
            })
    return items


@router.delete("/{name}")
def delete_upload(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete an uploaded file by its stored name. Authenticated."""
    safe = Path(name).name
    target = _upload_dir() / safe
    if not target.exists():
        raise HTTPException(404, "File not found")
    if target.is_file():
        target.unlink()
        return {"ok": True}
    raise HTTPException(400, "Not a file")
