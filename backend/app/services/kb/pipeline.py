"""Per-document ingestion pipeline (Idea 10, phrase 96).

Order: extract → OCR (if flagged) → version snapshot → chunk. Dedupe happens at
row-creation time (scan/upload); the embedding hook is reserved for Phase 2.
"""

from __future__ import annotations

import logging
import os
import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbChunk, KbDocument, KbVersion
from app.services.ingestion import MAX_EXTRACTED_CHARS
from app.services.kb import KbService, utcnow
from app.services.kb import chunker, markdown_parser, ocr
from app.services.text_extractor import NoExtractableTextError, extract, extract_pdf_pages

logger = logging.getLogger(__name__)

SNAPSHOT_DIR = "kb_snapshots"


# ---------------------------------------------------------------------------
# Chunking (Idea 7)
# ---------------------------------------------------------------------------

def re_chunk(db: Session, doc: KbDocument) -> int:
    """Delete existing chunks and insert new ones in a single transaction (phrase 67).

    NOTE: the FTS index + triggers are ensured once at scan/job *dispatch*
    (``scan_and_ingest``) — never inside this function, because FTS5 DDL opens
    its own ``engine.begin()`` connection which, on SQLite, would commit/pin the
    outer transaction mid-ingest and lose the version snapshot added just before.
    """
    db.query(KbChunk).filter(KbChunk.document_id == doc.id).delete()
    outline = KbService.json_loads(doc.outline_json) or None
    if outline:
        outline = [
            markdown_parser.OutlineItem(
                level=o["level"], text=o["text"], char_start=o["char_start"]
            )
            for o in outline
        ]
    chunks = chunker.chunk_text(doc.extracted_text, outline=outline)
    for i, c in enumerate(chunks):
        db.add(
            KbChunk(
                user_id=doc.user_id,
                document_id=doc.id,
                seq=i,
                content=c.content,
                char_start=c.char_start,
                char_end=c.char_end,
                heading_path=c.heading_path,
                token_estimate=c.token_estimate,
            )
        )
    return len(chunks)


# ---------------------------------------------------------------------------
# Version snapshots (Idea 9)
# ---------------------------------------------------------------------------

def _snapshot_to_disk(doc: KbDocument, version_seq: int, text: str) -> str:
    directory = os.path.join(settings.UPLOAD_DIR, SNAPSHOT_DIR)
    os.makedirs(directory, exist_ok=True)
    name = f"kb_{doc.id}_v{version_seq}_{uuid.uuid4().hex[:8]}.txt"
    target = os.path.join(directory, name)
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(text)
    return target


def _current_hash(text: str) -> str:
    return KbService.content_hash(text.encode("utf-8"))


def _enforce_version_cap(db: Session, doc: KbDocument) -> None:
    """Keep only the latest ``KB_MAX_VERSIONS`` snapshots (phrase 85)."""
    versions = (
        db.query(KbVersion)
        .filter(KbVersion.document_id == doc.id)
        .order_by(KbVersion.version_seq.asc())
        .all()
    )
    # Guard against negative excess: ``versions[:-1]`` would delete everything
    # but the newest when below the cap.
    excess = len(versions) - settings.KB_MAX_VERSIONS
    if excess > 0:
        for version in versions[:excess]:
            db.delete(version)


def snapshot_version(db: Session, doc: KbDocument) -> KbVersion | None:
    """Snapshot the document's current content unless it is unchanged.

    Only snapshots when the content hash actually changed — metadata-only
    rescans must not create versions (phrase 87).
    """
    if not doc.extracted_text:
        return None
    digest = _current_hash(doc.extracted_text)
    latest = (
        db.query(KbVersion)
        .filter(KbVersion.document_id == doc.id)
        .order_by(KbVersion.version_seq.desc())
        .first()
    )
    if latest and latest.content_hash == digest:
        return None

    new_seq = (latest.version_seq if latest else 0) + 1
    snapshot_text = doc.extracted_text
    if len(snapshot_text) > settings.KB_SNAPSHOT_DISK_CHARS:
        snapshot_text = _snapshot_to_disk(doc, new_seq, snapshot_text)

    version = KbVersion(
        user_id=doc.user_id,
        document_id=doc.id,
        version_seq=new_seq,
        content_hash=digest,
        snapshot_text=snapshot_text,
    )
    db.add(version)
    db.flush()  # make the new version visible to the cap query
    _enforce_version_cap(db, doc)
    return version


def _parse_markdown_meta(db: Session, doc: KbDocument, text: str) -> None:
    md = markdown_parser.parse_markdown(text)
    doc.frontmatter_json = KbService.json_dumps(md.frontmatter) if md.frontmatter else None
    doc.outline_json = KbService.json_dumps(
        [{"level": o.level, "text": o.text, "char_start": o.char_start} for o in md.outline]
    )
    if md.wikilinks:
        doc.metadata_json = KbService.json_dumps(
            {"wikilinks": md.wikilinks, "tags": md.tags, "callouts": md.callouts}
        )


# ---------------------------------------------------------------------------
# Document ingest
# ---------------------------------------------------------------------------

def ingest_document(db: Session, doc: KbDocument) -> dict:
    """Run the per-document pipeline. Never raises for content errors."""
    result: dict = {"status": "ok", "chunks": 0}
    path = doc.file_path
    if not path or not os.path.isfile(path):
        doc.status = "failed"
        db.add(doc)
        db.commit()
        return {**result, "status": "failed", "error": "file missing on disk"}

    try:
        # Snapshot the OLD content before overwriting (Idea 9, phrase 81).
        if doc.status == "changed" and doc.extracted_text:
            snapshot_version(db, doc)

        # Re-extract when there is no cached text OR the file changed (a
        # 'changed' doc must not keep its stale extracted_text).
        if not doc.extracted_text or doc.status == "changed":
            # Phase 9 (Idea 86, phrase 51): content (re)written → the cached
            # summary (if any) is stale; the nightly summary job reselects it.
            doc.summary_dirty = True
            text = ""
            if doc.doc_type == "pdf":
                try:
                    pages = extract_pdf_pages(path)
                except Exception:  # noqa: BLE001 — corrupt PDFs
                    pages = []
                doc.needs_ocr = ocr.needs_ocr(pages)
                text = "\n".join(pages)
                if doc.needs_ocr:
                    if ocr.ocr_available():
                        try:
                            ocr_text = ocr.ocr_pdf(path)
                            if ocr_text:
                                text = f"{text}\n\n{ocr_text}" if text.strip() else ocr_text
                                doc.ocr_used = True
                        except ocr.OcrUnavailableError:
                            doc.status = "failed"
                            db.add(doc)
                            db.commit()
                            return {**result, "status": "failed", "error": "OCR unavailable"}
                    elif settings.KB_OCR_ENABLED:
                        # OCR expected but deps/binary missing — degrade (phrase 56).
                        doc.status = "failed"
                        db.add(doc)
                        db.commit()
                        return {**result, "status": "failed", "error": "OCR deps missing"}
            else:
                try:
                    text = extract(path, doc.doc_type)
                except NoExtractableTextError:
                    text = ""

            text = (text or "").strip()
            if not text:
                doc.status = "failed"
                db.add(doc)
                db.commit()
                return {**result, "status": "failed", "error": "no extractable text"}

            doc.extracted_text = text[:MAX_EXTRACTED_CHARS]
            doc.char_count = len(doc.extracted_text)
            if doc.doc_type == "md":
                _parse_markdown_meta(db, doc, doc.extracted_text)

        result["chunks"] = re_chunk(db, doc)
        doc.status = "unchanged"
        doc.indexed_at = utcnow()
        db.add(doc)
        db.commit()
        # Phase 4 post-ingest hooks (each best-effort; never fail the job):
        # daily-note auto-tag (Idea 35), citation parsing (Idea 36), and
        # quality recompute (Idea 39) since content changed.
        run_post_ingest_hooks(db, doc)
        return result
    except Exception as exc:  # noqa: BLE001 — never crash the job
        logger.exception("Ingest failed for document %s", doc.id)
        doc.status = "failed"
        db.add(doc)
        db.commit()
        return {**result, "status": "failed", "error": str(exc)[:500]}


def run_post_ingest_hooks(db: Session, doc: KbDocument) -> None:
    """Phase 4 best-effort hooks after a successful ingest (phrases 42, 56, 84).

    Phase 7 (Idea 69, phrase 82): a *new* daily-note document (``doc_date``
    set, first time seen) awards ``daily_note`` capture XP — once per document.
    """
    try:
        from app.services.kb.daily_notes import tag_daily_note

        tag_daily_note(db, doc)
        if doc.doc_date is not None:
            from app.models import User
            from app.services.kb.capture_xp import award_capture_xp

            user = db.query(User).get(doc.user_id)
            if user is not None:
                award_capture_xp(db, user, "daily_note", f"doc:{doc.id}")
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Daily-note tag hook failed for doc %s: %s", doc.id, exc)
        db.rollback()

    try:
        from app.services.kb.citation_registry import extract_for_document

        extract_for_document(db, doc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Citation hook failed for doc %s: %s", doc.id, exc)
        db.rollback()

    try:
        from app.services.kb.quality import recompute_for_document

        recompute_for_document(db, doc)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Quality recompute hook failed for doc %s: %s", doc.id, exc)
        db.rollback()
