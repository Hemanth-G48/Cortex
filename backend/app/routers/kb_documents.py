"""Knowledge documents — upload, list, chunks, versions, restore, diff
(Ideas 5, 7, 9)."""

from __future__ import annotations

import difflib
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import KbChunk, KbDocument, KbEdge, KbVersion, User
from app.schemas.kb import (
    KbChunkResponse,
    KbDiffResponse,
    KbDocumentListResponse,
    KbDocumentResponse,
    KbJobResponse,
    KbRestoreResponse,
    KbUploadResult,
    KbVersionResponse,
)
from app.services.ingestion import MAX_EXTRACTED_CHARS
from app.services.kb import KbService, utcnow
from app.services.kb import jobs, braindump_draft
from app.services.kb.pipeline import _parse_markdown_meta, ingest_document, re_chunk, snapshot_version
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-documents"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}


def _allowed_extension(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext if ext in ALLOWED_EXTENSIONS else None


def _rejects_path_traversal(filename: str) -> bool:
    return ".." in filename or "/" in filename or "\\" in filename


def _mime_sniff_rejects(ext: str, data: bytes) -> bool:
    if not data:
        return False
    if ext == "pdf" and not data.startswith(b"%PDF"):
        return True
    if ext == "docx" and not data.startswith(b"PK"):
        return True
    if ext in ("txt", "md") and (
        data.startswith(b"\x89PNG") or data.startswith(b"%PDF") or data.startswith(b"PK")
    ):
        return True
    return False


def _doc_response(db: Session, doc: KbDocument) -> KbDocumentResponse:
    resp = KbDocumentResponse.model_validate(doc)
    resp.chunk_count = (
        db.query(func.count(KbChunk.id))
        .filter(KbChunk.document_id == doc.id, KbChunk.user_id == doc.user_id)
        .scalar()
        or 0
    )
    return resp


# ---------------------------------------------------------------------------
# List / detail / delete
# ---------------------------------------------------------------------------

@router.get("/documents", response_model=KbDocumentListResponse)
def list_documents(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    source_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    query = db.query(KbDocument).filter(KbDocument.user_id == current_user.id)
    if source_id is not None:
        query = query.filter(KbDocument.source_id == source_id)
    if status:
        query = query.filter(KbDocument.status == status)
    if q:
        query = query.filter(
            or_(
                KbDocument.title.ilike(f"%{q}%"),
                KbDocument.path_rel.ilike(f"%{q}%"),
            )
        )
    total = query.count()
    docs = (
        query.order_by(KbDocument.updated_at.desc(), KbDocument.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_doc_response(db, d) for d in docs]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/documents/{document_id}", response_model=KbDocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return _doc_response(db, doc)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    db.query(KbEdge).filter(
        KbEdge.user_id == current_user.id,
        or_(KbEdge.source_document_id == doc.id, KbEdge.target_document_id == doc.id),
    ).delete(synchronize_session=False)
    db.delete(doc)  # cascade → chunks + versions
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Upload (Idea 5, phrases 42–44 + Idea 8 dedupe)
# ---------------------------------------------------------------------------

@router.post("/documents/upload", response_model=KbUploadResult, status_code=201)
def upload_document(
    file: UploadFile,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
    source_id: int | None = Query(default=None),
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

    source = None
    if source_id is not None:
        source = KbService.get_source(db, current_user.id, source_id)
        if source is None:
            raise HTTPException(404, "Source not found")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    target = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(target, "wb") as out:
        out.write(data)

    # Content-hash dedupe before creating a row (Idea 8, phrases 72–74).
    digest = KbService.content_hash(data)
    canonical = KbService.find_canonical(db, current_user.id, digest)
    if canonical is not None:
        KbService.record_duplicate(db, current_user.id, canonical.id)
        db.commit()
        return KbUploadResult(deduped=True, duplicate_of_id=canonical.id)

    doc = KbDocument(
        user_id=current_user.id,
        source_id=source.id if source else None,
        path_rel=stored_name,
        file_path=target,
        title=os.path.splitext(file.filename or stored_name)[0],
        doc_type=ext,
        content_hash=digest,
        status="new",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ingest_document(db, doc)  # extract + OCR + chunk inline (phrase 44/98)
    return KbUploadResult(document=_doc_response(db, doc), deduped=False)


# ---------------------------------------------------------------------------
# Chunks (Idea 7, phrase 70)
# ---------------------------------------------------------------------------

@router.get("/documents/{document_id}/chunks", response_model=list[KbChunkResponse])
def list_chunks(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc.id, KbChunk.user_id == current_user.id)
        .order_by(KbChunk.seq.asc())
        .all()
    )


@router.post("/documents/{document_id}/reindex", response_model=KbJobResponse)
def reindex_document(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Re-run the ingest pipeline for one document via the job queue."""
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    job = jobs.submit_ingest_job(
        db, current_user.id, [doc.id], job_type="reindex"
    )
    return job


# ---------------------------------------------------------------------------
# Quick-file a braindump draft (Idea 40, phrase 94)
# ---------------------------------------------------------------------------

class KbFileDraftRequest(BaseModel):
    title: str | None = None
    source_id: int | None = None
    tags: list[str] | None = None


@router.post("/documents/{document_id}/file", response_model=KbDocumentResponse)
def file_braindump_draft(
    document_id: int,
    body: KbFileDraftRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """File a draft: set title, attach to a source/folder, add tags,
    move ``draft`` → ``new`` (phrase 94)."""
    doc = braindump_draft.file_draft(
        db,
        current_user.id,
        document_id,
        title=body.title,
        source_id=body.source_id,
        tags=body.tags,
    )
    # Phase 7 (Idea 69, phrase 83): quick-filing a draft awards dump XP,
    # once per document.
    from app.services.kb.capture_xp import award_capture_xp

    xp_granted = award_capture_xp(db, current_user, "dump_filed", f"doc:{doc.id}")
    db.commit()
    resp = _doc_response(db, doc)
    resp_dict = resp.model_dump() if hasattr(resp, "model_dump") else dict(resp)
    resp_dict["xp_granted"] = xp_granted
    return resp_dict


# ---------------------------------------------------------------------------
# Versions (Idea 9)
# ---------------------------------------------------------------------------

def _version_text(version: KbVersion) -> str:
    if not version.snapshot_text:
        return ""
    if os.path.isfile(version.snapshot_text):
        with open(version.snapshot_text, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return version.snapshot_text


@router.get("/documents/{document_id}/versions", response_model=list[KbVersionResponse])
def list_versions(
    document_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Version history, newest first (phrase 82)."""
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return (
        db.query(KbVersion)
        .filter(KbVersion.document_id == doc.id, KbVersion.user_id == current_user.id)
        .order_by(KbVersion.version_seq.desc())
        .all()
    )


@router.get("/documents/{document_id}/diff", response_model=KbDiffResponse)
def diff_versions(
    document_id: int,
    from_version: int,
    to_version: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Unified diff between two version snapshots (phrase 84)."""
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    v_from = (
        db.query(KbVersion)
        .filter(
            KbVersion.document_id == doc.id,
            KbVersion.user_id == current_user.id,
            KbVersion.version_seq == from_version,
        )
        .first()
    )
    v_to = (
        db.query(KbVersion)
        .filter(
            KbVersion.document_id == doc.id,
            KbVersion.user_id == current_user.id,
            KbVersion.version_seq == to_version,
        )
        .first()
    )
    if v_from is None or v_to is None:
        raise HTTPException(404, "Version not found")
    a = _version_text(v_from)
    b = _version_text(v_to)
    lines = difflib.unified_diff(
        a.splitlines(),
        b.splitlines(),
        fromfile=f"v{from_version}",
        tofile=f"v{to_version}",
        lineterm="",
    )
    diff = "\n".join(lines)
    return KbDiffResponse(
        from_version=from_version,
        to_version=to_version,
        changed=a != b,
        diff=diff,
    )


@router.post("/documents/{document_id}/restore", response_model=KbRestoreResponse)
def restore_version(
    document_id: int,
    version_id: int = Query(description="kb_versions.id to restore"),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Restore content from a version; the rollback itself is versioned
    (phrase 83)."""
    doc = KbService.get_document(db, current_user.id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    version = (
        db.query(KbVersion)
        .filter(
            KbVersion.id == version_id,
            KbVersion.document_id == doc.id,
            KbVersion.user_id == current_user.id,
        )
        .first()
    )
    if version is None:
        raise HTTPException(404, "Version not found")
    restored = _version_text(version)
    if not restored:
        raise HTTPException(400, "Version has no content to restore")

    # Version the PRE-restore state first, so the rollback itself is recorded
    # (phrase 83). Snapshotting after overwriting would be a no-op when the
    # restored content matches the restored version's hash.
    snapshot = None
    if doc.extracted_text:
        snapshot = snapshot_version(db, doc)

    doc.extracted_text = restored[:MAX_EXTRACTED_CHARS]
    doc.char_count = len(doc.extracted_text)
    if doc.doc_type == "md":
        _parse_markdown_meta(db, doc, doc.extracted_text)
    re_chunk(db, doc)
    doc.status = "unchanged"
    doc.indexed_at = utcnow()
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return KbRestoreResponse(
        document=_doc_response(db, doc),
        new_version_seq=snapshot.version_seq if snapshot else 0,
    )
