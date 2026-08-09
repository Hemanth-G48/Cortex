"""Folder watcher scanning (Idea 3).

``scan_source`` is the core idempotent scan routine: walks a source root,
filters to extractable types, computes SHA-256 content hashes, upserts
documents with new/changed/unchanged/deleted status transitions, and detects
duplicates via the dedupe helpers (Idea 8).
"""

from __future__ import annotations

import logging
import os
from datetime import date

from sqlalchemy.orm import Session

from app.models import KbDocument, KbSource
from app.services.kb import KbService, NOISE_DIRS, utcnow
from app.services.kb import markdown_parser
from app.services.kb.pipeline import ingest_document
from app.services.text_extractor import EXTRACTABLE_TYPES

logger = logging.getLogger(__name__)


def _ext_of(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext if ext in EXTRACTABLE_TYPES else None


def scan_source(db: Session, source: KbSource) -> dict:
    """Idempotently scan one source folder. Returns a summary dict."""
    summary = {
        "files_seen": 0,
        "added": 0,
        "changed": 0,
        "removed": 0,
        "unchanged": 0,
        "duplicates_found": 0,
    }
    root = source.root_path
    seen: set[str] = set()
    # Hashes seen during THIS scan — with autoflush=False pending inserts are
    # invisible to queries, so same-scan duplicates must be tracked locally.
    seen_hashes: dict[str, KbDocument] = {}
    # Persistent {path_rel: canonical_document_id} of already-deduped files so
    # re-scans treat a known duplicate as stable instead of re-counting it as
    # new (Idea 8, phrase 73).
    duplicate_map = KbService.get_duplicate_map(source)
    if root and os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in NOISE_DIRS]
            for fname in filenames:
                ext = _ext_of(fname)
                if ext is None:
                    continue
                full = os.path.join(dirpath, fname)
                rel = os.path.relpath(full, root)
                summary["files_seen"] += 1
                seen.add(rel)
                try:
                    with open(full, "rb") as fh:
                        data = fh.read()
                except OSError as exc:
                    logger.warning("Cannot read %s: %s", full, exc)
                    continue
                digest = KbService.content_hash(data)

                doc = (
                    db.query(KbDocument)
                    .filter(
                        KbDocument.user_id == source.user_id,
                        KbDocument.source_id == source.id,
                        KbDocument.path_rel == rel,
                    )
                    .first()
                )

                if doc is None:
                    # A known-duplicate path whose canonical still carries this
                    # hash is stable — don't re-count it on every scan.
                    known_id = duplicate_map.get(rel)
                    if known_id is not None:
                        known = (
                            db.query(KbDocument)
                            .filter(
                                KbDocument.id == known_id,
                                KbDocument.user_id == source.user_id,
                            )
                            .first()
                        )
                        if known is not None and known.content_hash == digest:
                            summary["unchanged"] += 1
                            continue
                        # Canonical gone or hash diverged → fall through and
                        # re-evaluate the file as if it were new.
                        duplicate_map.pop(rel, None)

                    # New file → dedupe first (Idea 8, phrase 72).
                    canonical = seen_hashes.get(digest) or KbService.find_canonical(
                        db, source.user_id, digest
                    )
                    if canonical is not None:
                        summary["duplicates_found"] += 1
                        KbService.record_duplicate(db, source.user_id, canonical.id)
                        duplicate_map[rel] = canonical.id
                        continue
                    doc = KbDocument(
                        user_id=source.user_id,
                        source_id=source.id,
                        path_rel=rel,
                        file_path=full,
                        title=os.path.splitext(fname)[0],
                        doc_type=ext,
                        content_hash=digest,
                        status="new",
                    )
                    if ext == "md":
                        daily = markdown_parser.daily_note_date(fname)
                        if daily:
                            doc.doc_date = date.fromisoformat(daily)
                    db.add(doc)
                    # Flush so the row has an id for same-scan dedupe edges.
                    db.flush()
                    seen_hashes[digest] = doc
                    summary["added"] += 1
                elif doc.content_hash != digest:
                    # The file changed — but if its new content already exists
                    # under another document, the unique (user, hash) index would
                    # be violated by overwriting. Dedupe it away instead: record
                    # the DUPLICATE_OF edge and drop this now-redundant row so
                    # future scans take the stable new-file dedupe path.
                    canonical = seen_hashes.get(digest) or KbService.find_canonical(
                        db, source.user_id, digest
                    )
                    if canonical is not None and canonical.id != doc.id:
                        summary["duplicates_found"] += 1
                        summary["removed"] += 1
                        KbService.record_duplicate(db, source.user_id, canonical.id)
                        duplicate_map[rel] = canonical.id
                        db.delete(doc)  # ORM cascade → chunks + versions
                    else:
                        summary["changed"] += 1
                        doc.content_hash = digest
                        doc.status = "changed"
                        doc.updated_at = utcnow()
                        db.add(doc)
                        # No longer a known duplicate — forget the stale mapping.
                        duplicate_map.pop(rel, None)
                else:
                    summary["unchanged"] += 1
                    if doc.status == "deleted":
                        # File reappeared with identical content.
                        doc.status = "unchanged"
                        doc.updated_at = utcnow()
                        db.add(doc)
                    # failed stays failed (retried by an explicit reindex).

    # Files that vanished → status=deleted (phrase 25).
    for doc in (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == source.user_id,
            KbDocument.source_id == source.id,
        )
        .all()
    ):
        if doc.path_rel not in seen:
            summary["removed"] += 1
            doc.status = "deleted"
            doc.updated_at = utcnow()
            db.add(doc)

    db.commit()

    source.last_scanned_at = utcnow()
    source.files_seen = summary["files_seen"]
    source.files_added = summary["added"]
    source.files_changed = summary["changed"]
    source.files_removed = summary["removed"]
    KbService.save_duplicate_map(source, duplicate_map)
    db.add(source)
    db.commit()
    return summary


def scan_and_ingest(db: Session, source_id: int) -> dict:
    """Scan a source, then run the ingest pipeline on new/changed/failed docs.

    Used by the job queue (Idea 10) and the watcher so a single "Scan now"
    produces parsed, chunked documents.
    """
    source = db.query(KbSource).filter(KbSource.id == source_id).first()
    if source is None:
        return {}
    # Ensure the FTS index + sync triggers exist before any chunk is written
    # (Phase 3, Idea 21). Runs here — at scan dispatch, before the ingest
    # transaction opens — so the FTS5 DDL (which uses its own engine connection
    # on SQLite) never commits/pins the outer transaction mid-ingest.
    try:
        from app.services.kb import fts

        fts.ensure_fts_schema_for(db.bind)
    except Exception:  # noqa: BLE001 — never let FTS setup break a scan
        pass
    summary = scan_source(db, source)
    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.source_id == source.id,
            KbDocument.user_id == source.user_id,
            KbDocument.status.in_(["new", "changed", "failed"]),
        )
        .all()
    )
    ingested = 0
    for doc in docs:
        result = ingest_document(db, doc)
        if result.get("status") == "ok":
            ingested += 1
    summary["ingested"] = ingested
    return summary
