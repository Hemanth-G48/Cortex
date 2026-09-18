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
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import KbDocument, KbSource
from app.services.kb import KbService, NOISE_DIRS, utcnow
from app.services.kb import markdown_parser
from app.services.kb.pipeline import ingest_document
from app.services.text_extractor import EXTRACTABLE_TYPES

logger = logging.getLogger(__name__)


def _like_escape(text: str) -> str:
    """Escape LIKE wildcards so a folder name is matched literally.

    Vault folder names are user-controlled and can contain ``%`` / ``_``
    (e.g. ``50%_Notes``); unescaped they act as LIKE wildcards and the sweep
    / ingest scoping could match the wrong documents."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _ext_of(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext if ext in EXTRACTABLE_TYPES else None


def scan_source(db: Session, source: KbSource, subpath: str | None = None) -> dict:
    """Idempotently scan one source folder. Returns a summary dict.

    ``subpath`` (optional) restricts the scan to a folder inside the source
    root — a relative path such as ``"cybersecurity"``. Only that subtree is
    walked, and only documents under it are eligible for the removed-file
    sweep, so a folder-scoped "update from folder" never touches files
    elsewhere in the source. ``path_rel`` values always stay relative to the
    source root, matching stored rows.
    """
    summary = {
        "files_seen": 0,
        "added": 0,
        "changed": 0,
        "moved": 0,
        "removed": 0,
        "unchanged": 0,
        "duplicates_found": 0,
    }
    root = source.root_path
    scan_root = root
    if subpath:
        # Defense-in-depth: the router validates the path too, but direct
        # service callers (tests, other services) must not escape the root.
        if os.path.isabs(subpath) or ".." in Path(subpath).parts:
            raise ValueError(f"subpath must be relative and without '..': {subpath!r}")
        scan_root = os.path.join(root or "", subpath)
        if not os.path.isdir(scan_root):
            raise FileNotFoundError(f"folder not found inside source: {subpath}")
    seen: set[str] = set()
    # Hashes seen during THIS scan — with autoflush=False pending inserts are
    # invisible to queries, so same-scan duplicates must be tracked locally.
    seen_hashes: dict[str, KbDocument] = {}
    # Persistent {path_rel: canonical_document_id} of already-deduped files so
    # re-scans treat a known duplicate as stable instead of re-counting it as
    # new (Idea 8, phrase 73).
    duplicate_map = KbService.get_duplicate_map(source)
    if root and os.path.isdir(scan_root):
        for dirpath, dirnames, filenames in os.walk(scan_root):
            # daily-life is the non-knowledge area of a vault: never indexed.
            # Only filtered at the source root — a knowledge folder that
            # happens to be named ``daily-life`` deeper in the tree stays
            # indexable (the ``notes/``-root layout keeps it outside anyway).
            dirnames[:] = [
                d
                for d in dirnames
                if d not in NOISE_DIRS
                and not (dirpath == scan_root and d.casefold() == "daily-life")
            ]
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
                        # Same-scan new doc at another path → a true duplicate
                        # (both files exist on disk): keep the stable dedupe path.
                        if canonical.id in seen_hashes.values():
                            summary["duplicates_found"] += 1
                            KbService.record_duplicate(db, source.user_id, canonical.id)
                            duplicate_map[rel] = canonical.id
                            continue
                        # The canonical row already lives at this exact relative
                        # path in THIS source — it was repointed earlier in this
                        # scan (move detection below, autoflush=False hides the
                        # update): nothing new to do. (Cross-source same-path
                        # rows still dedupe below.)
                        if canonical.path_rel == rel and canonical.source_id == source.id:
                            summary["unchanged"] += 1
                            continue
                        # Move/rename detection: the canonical document's own
                        # file no longer exists on disk, so this is the SAME
                        # document at a new path — not a duplicate. Keep the
                        # document id, chunks and embeddings; update the path
                        # only ("changing a path is not changing the content").
                        if (
                            canonical.source_id == source.id
                            and not (
                                canonical.file_path
                                and os.path.exists(canonical.file_path)
                            )
                        ):
                            duplicate_map.pop(rel, None)
                            for k, v in list(duplicate_map.items()):
                                if v == canonical.id:
                                    duplicate_map.pop(k, None)
                            if canonical.status == "deleted":
                                canonical.status = "unchanged"
                            canonical.path_rel = rel
                            canonical.file_path = full
                            canonical.updated_at = utcnow()
                            db.add(canonical)
                            summary["moved"] += 1
                            continue
                        # Genuine duplicate (canonical still on disk): record it.
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

    # Files that vanished → status=deleted (phrase 25). For a subfolder scan
    # only documents under that subtree are candidates — files elsewhere in
    # the source are left exactly as they are.
    sweep = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == source.user_id,
            KbDocument.source_id == source.id,
        )
    )
    if subpath:
        sweep = sweep.filter(
            KbDocument.path_rel.like(
                f"{_like_escape(subpath.strip('/'))}/%", escape="\\"
            )
        )
    for doc in sweep.all():
        if doc.path_rel not in seen:
            summary["removed"] += 1
            doc.status = "deleted"
            doc.updated_at = utcnow()
            db.add(doc)

    db.commit()

    source.last_scanned_at = utcnow()
    if not subpath:
        # Aggregate counters describe the whole source — a folder-scoped scan
        # reports only its subtree, so don't clobber the source-wide numbers.
        source.files_seen = summary["files_seen"]
        source.files_added = summary["added"]
        source.files_changed = summary["changed"]
        source.files_removed = summary["removed"]
    KbService.save_duplicate_map(source, duplicate_map)
    db.add(source)
    db.commit()
    return summary


#: Cap on files walked by ``probe_root_path`` — a pre-flight check must stay
#: fast even when pointed at a huge directory tree.
PROBE_FILE_LIMIT = 20000
PROBE_SAMPLE_LIMIT = 5


def probe_root_path(db: Session, user_id: int, raw_path: str) -> dict:
    """Pre-flight validation for a candidate source root (audit defect #20).

    Powers ``GET /api/kb/sources/validate`` so the UI can confirm a folder is
    a usable knowledge root *before* submitting it, instead of only surfacing
    the server-side 400 from ``POST /api/kb/sources``. The path is resolved the
    same way ``create_source`` resolves it (``os.path.abspath``, no tilde
    expansion) so a path that validates here is accepted there.

    Reports what the scan would actually see: extractable document count,
    markdown count and a few sample relative paths, plus whether the folder is
    already registered or already covered by a registered source.
    """
    candidate = (raw_path or "").strip()
    result: dict = {
        "path": candidate,
        "absolute_path": None,
        "valid": False,
        "reason": None,
        "exists": False,
        "is_dir": False,
        "readable": False,
        "writable": False,
        "markdown_count": 0,
        "document_count": 0,
        "sample_files": [],
        "already_registered": None,
        "inside_source": None,
    }
    if not candidate:
        result["reason"] = "path is required"
        return result

    absolute = os.path.abspath(candidate)
    result["absolute_path"] = absolute
    result["exists"] = os.path.exists(absolute)
    result["is_dir"] = os.path.isdir(absolute)
    if not result["exists"]:
        result["reason"] = "path does not exist on disk"
        return result
    if not result["is_dir"]:
        result["reason"] = "path is not a directory"
        return result

    result["readable"] = os.access(absolute, os.R_OK)
    result["writable"] = os.access(absolute, os.W_OK)
    if not result["readable"]:
        result["reason"] = "path is not readable"
        return result

    # What the scan would index, mirroring ``scan_source``'s filters: noise
    # dirs are skipped and the vault's non-knowledge ``daily-life`` area is
    # excluded at the root.
    markdown_count = 0
    document_count = 0
    samples: list[str] = []
    for dirpath, dirnames, filenames in os.walk(absolute):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in NOISE_DIRS
            and not (dirpath == absolute and d.casefold() == "daily-life")
        ]
        for fname in filenames:
            if _ext_of(fname) is None:
                continue
            document_count += 1
            rel = os.path.relpath(os.path.join(dirpath, fname), absolute)
            if fname.lower().endswith(".md"):
                markdown_count += 1
            if len(samples) < PROBE_SAMPLE_LIMIT:
                samples.append(rel.replace(os.sep, "/"))
            if document_count >= PROBE_FILE_LIMIT:
                break
        if document_count >= PROBE_FILE_LIMIT:
            break
    result["markdown_count"] = markdown_count
    result["document_count"] = document_count
    result["sample_files"] = samples

    sources = db.query(KbSource).filter(KbSource.user_id == user_id).all()
    for source in sources:
        root = source.root_path or ""
        if not root:
            continue
        if os.path.abspath(root) == absolute:
            result["already_registered"] = {"id": source.id, "name": source.name}
            break
        try:
            inside = os.path.commonpath([absolute, os.path.abspath(root)]) == os.path.abspath(root)
        except ValueError:
            inside = False
        if inside:
            result["inside_source"] = {
                "id": source.id,
                "name": source.name,
                "root_path": source.root_path,
            }
            break

    if result["already_registered"] is not None:
        result["reason"] = "folder is already registered as a source"
        return result
    if document_count == 0:
        result["reason"] = "no indexable documents found (md, pdf, docx or txt)"
        return result

    result["valid"] = True
    return result


def scan_and_ingest(db: Session, source_id: int, subpath: str | None = None) -> dict:
    """Scan a source (optionally one folder inside it), then run the ingest
    pipeline on new/changed/failed docs.

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
    summary = scan_source(db, source, subpath=subpath)
    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.source_id == source.id,
            KbDocument.user_id == source.user_id,
            KbDocument.status.in_(["new", "changed", "failed"]),
        )
    )
    if subpath:
        # Ingest only the scanned subtree — a folder-scoped update must not
        # re-run the pipeline on unrelated pending docs elsewhere.
        docs = docs.filter(
            KbDocument.path_rel.like(
                f"{_like_escape(subpath.strip('/'))}/%", escape="\\"
            )
        )
    docs = docs.all()
    ingested = 0
    for doc in docs:
        result = ingest_document(db, doc)
        if result.get("status") == "ok":
            ingested += 1
    summary["ingested"] = ingested
    return summary
