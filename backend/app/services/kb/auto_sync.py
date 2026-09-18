"""Idea 89 — auto-sync external repositories (Phase 9 Automation).

``kb_sources`` gained ``sync_type`` (``git | drive | clip | none``) and a
per-source ``sync_cursor_json`` (phrase 81–82). This module dispatches to the
right adapter, imports only delta files since the cursor (phrase 82), and runs
them through the normal ingest pipeline so they get chunks, tags, summaries,
versions — everything a scanned file gets (phrase 83).

Conflict policy (phrase 86): newest ``mtime`` wins. A change whose mtime is
older than the local document's ``updated_at`` is skipped (local is newer);
a newer change overwrites the content *after* ``pipeline.ingest_document``
snapshots the superseded version into ``kb_versions``.

Adapters are plain functions returning ``(changes, new_cursor)`` where each
change is ``{\"rel_path\", \"content\", \"mtime\", \"doc_type\"}`` — git shells out
to the ``git`` binary (best-effort), drive/clip are provider stubs that return
no changes until a real transport is configured. Tests monkeypatch the
adapter functions directly (phrase 88).

``KB_SYNC_ENABLED`` gates the scheduled run; the manual
``POST /api/kb/sources/{id}/sync`` endpoint calls ``sync_source`` with
``force=True`` (phrase 87).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbSource
from app.services.kb import KbService, NOISE_DIRS, utcnow
from app.services.kb.automation import auto_job
from app.services.kb.pipeline import ingest_document
from app.services.text_extractor import EXTRACTABLE_TYPES

logger = logging.getLogger(__name__)

# Sync staging root — changed files are written here before ingest so the
# pipeline can read them from disk like any scanned file.
SYNC_STAGING = os.path.join(settings.UPLOAD_DIR, "kb_sync")


def _ext_of(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext if ext in EXTRACTABLE_TYPES else None


def _stage(source: KbSource, rel_path: str, content: str | bytes) -> str:
    """Write ``content`` under the sync staging dir; returns the file path."""
    from app.services.path_utils import safe_path
    directory = Path(SYNC_STAGING) / str(source.id)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / safe_path(rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    target.write_bytes(data)
    return str(target)


def _git_changes(source: KbSource, cursor: dict) -> tuple[list[dict], dict]:
    """Git adapter: list files changed since the cursor commit (phrase 83).

    Best-effort — if the repo cannot be read (no git binary, not a repo, or
    the cursor commit vanished), returns no changes and keeps the cursor so the
    job never fails the whole sync.
    """
    if not source.root_path:
        return [], cursor
    try:
        subprocess.run(
            ["git", "-C", source.root_path, "fetch", "--quiet"],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except Exception:  # noqa: BLE001 — no git available
        return [], cursor

    base = cursor.get("commit")
    try:
        if base:
            files = subprocess.run(
                [
                    "git", "-C", source.root_path, "diff", "--name-only",
                    "--diff-filter=ACMRT", f"{base}..HEAD",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout.splitlines()
        else:
            # First sync: everything tracked by HEAD is a delta.
            files = subprocess.run(
                ["git", "-C", source.root_path, "ls-files"],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout.splitlines()
        head = subprocess.run(
            ["git", "-C", source.root_path, "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout.strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("auto_sync git diff failed for %s: %s", source.id, exc)
        return [], cursor

    changes: list[dict] = []
    for rel in files:
        rel = rel.strip()
        ext = _ext_of(rel)
        if not ext:
            continue
        try:
            content = subprocess.run(
                ["git", "-C", source.root_path, "show", f"HEAD:{rel}"],
                check=True,
                capture_output=True,
                timeout=60,
            ).stdout
        except Exception:  # noqa: BLE001 — deleted/renamed away file
            continue
        mtime = None
        try:
            raw = subprocess.run(
                [
                    "git", "-C", source.root_path, "log", "-1",
                    "--format=%cI", "--", rel,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            ).stdout.strip()
            if raw:
                mtime = datetime.fromisoformat(raw)
        except Exception:  # noqa: BLE001
            pass
        changes.append(
            {"rel_path": rel, "content": content, "mtime": mtime, "doc_type": ext}
        )
    return changes, {"commit": head}


def _drive_changes(source: KbSource, cursor: dict) -> tuple[list[dict], dict]:
    """Drive adapter stub (phrase 84).

    Requires a configured transport (OAuth token + Drive API). Returns no
    changes until one is wired; tests monkeypatch this function directly.
    """
    return [], cursor


def _clip_changes(source: KbSource, cursor: dict) -> tuple[list[dict], dict]:
    """Clip adapter stub (phrase 85) — same contract as ``_drive_changes``."""
    return [], cursor


ADAPTERS: dict[str, Callable[[KbSource, dict], tuple[list[dict], dict]]] = {
    "git": _git_changes,
    "drive": _drive_changes,
    "clip": _clip_changes,
}


# ---------------------------------------------------------------------------
# "local" adapter — Copy Recent Notes (external Obsidian vault → notes/)
# ---------------------------------------------------------------------------
# Mirrors the *knowledge Markdown files* of a configured external vault
# (``sync_source_path``) into this source's knowledge root (``notes/``),
# preserving the folder hierarchy. Only genuinely changed files are copied
# (content-hash compare); unchanged files are never re-copied and their
# embeddings are reused as-is by the scanner. Deletions only ever apply to
# files this adapter previously synced (tracked in the cursor) — pre-existing
# vault files are never removed.


def _local_sync(db: Session, source: KbSource) -> dict:
    from app.services.kb.scanner import scan_and_ingest

    external = source.sync_source_path
    if not external or not os.path.isdir(external):
        return {
            "source_id": source.id,
            "sync_type": "local",
            "skipped": True,
            "reason": "sync_source_path is not a directory",
        }
    target_root = source.root_path
    if not target_root or not os.path.isdir(target_root):
        return {
            "source_id": source.id,
            "sync_type": "local",
            "skipped": True,
            "reason": "source root_path is not a directory",
        }

    cursor = KbService.json_loads(source.sync_cursor_json) or {}
    # rel_path → sha256 of the last file WE synced (deletion scope = only ours).
    external_files: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(external):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in NOISE_DIRS and d.casefold() != "daily-life"
        ]
        for fname in filenames:
            if fname.startswith("."):
                continue
            ext = _ext_of(fname)
            if ext is None:
                continue
            rel = os.path.relpath(os.path.join(dirpath, fname), external)
            if ".." in rel.split(os.sep):
                continue  # defensive: never follow symlink escapes
            external_files[rel] = ext

    copied = unchanged = 0
    for rel in sorted(external_files):
        src = os.path.join(external, rel)
        dst = os.path.join(target_root, rel)
        try:
            with open(src, "rb") as fh:
                digest = KbService.content_hash(fh.read())
        except OSError as exc:
            logger.warning("local sync cannot read %s: %s", src, exc)
            continue
        try:
            with open(dst, "rb") as fh:
                target_digest = KbService.content_hash(fh.read())
        except OSError:
            target_digest = None
        if digest == target_digest:
            unchanged += 1
            cursor[rel] = digest
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        cursor[rel] = digest
        copied += 1

    # Delete ONLY files we previously synced that no longer exist externally.
    removed = 0
    for rel in [r for r in cursor if r not in external_files]:
        dst = os.path.join(target_root, rel)
        try:
            if os.path.isfile(dst) and os.path.dirname(dst).startswith(target_root):
                os.remove(dst)
                removed += 1
        except OSError as exc:
            logger.warning("local sync cannot remove %s: %s", dst, exc)
        cursor.pop(rel, None)

    source.sync_cursor_json = KbService.json_dumps(cursor)
    source.last_scanned_at = utcnow()
    db.add(source)
    db.commit()

    # Reconcile the index: new/changed files get ingested, deleted files get
    # swept — unchanged files are untouched (embeddings reused).
    scanned: dict = {}
    try:
        scanned = scan_and_ingest(db, source.id)
    except Exception as exc:  # noqa: BLE001 — one failed sync must not kill the loop
        logger.exception("local sync scan failed for source %s", source.id)
        scanned = {"error": str(exc)}

    return {
        "source_id": source.id,
        "sync_type": "local",
        "copied": copied,
        "unchanged": unchanged,
        "removed": removed,
        "scanned": scanned,
    }


def sync_source(
    db: Session, source: KbSource, *, force: bool = False
) -> dict:
    """Run one source's adapter and import deltas through the ingest pipeline."""
    if source.sync_type == "local":
        # Local vaults (Copy Recent Notes) are gated by their own toggle —
        # KB_AUTO_LOCAL_SYNC_ENABLED — so the scheduled job is independent of
        # remote repository sync. The manual button always passes force=True.
        if not force and not settings.KB_AUTO_LOCAL_SYNC_ENABLED:
            return {
                "source_id": source.id,
                "skipped": True,
                "reason": "KB_AUTO_LOCAL_SYNC_ENABLED is disabled",
            }
        return _local_sync(db, source)
    if source.sync_type not in ADAPTERS:
        return {"source_id": source.id, "skipped": True, "reason": f"no adapter for {source.sync_type!r}"}
    if not force and not settings.KB_SYNC_ENABLED:
        return {"source_id": source.id, "skipped": True, "reason": "KB_SYNC_ENABLED is disabled"}

    cursor = KbService.json_loads(source.sync_cursor_json) or {}
    adapter = ADAPTERS[source.sync_type]
    changes, new_cursor = adapter(source, cursor)

    imported = 0
    unchanged = 0
    skipped_stale = 0
    failed = 0
    for change in changes:
        outcome = _import_change(db, source, change)
        if outcome == "imported":
            imported += 1
        elif outcome == "unchanged":
            unchanged += 1
        elif outcome == "stale":
            skipped_stale += 1
        else:
            failed += 1

    source.sync_cursor_json = KbService.json_dumps(new_cursor)
    source.last_scanned_at = utcnow()
    db.add(source)
    db.commit()

    return {
        "source_id": source.id,
        "sync_type": source.sync_type,
        "changes": len(changes),
        "imported": imported,
        "unchanged": unchanged,
        "skipped_stale": skipped_stale,
        "failed": failed,
    }


def _import_change(db: Session, source: KbSource, change: dict) -> str:
    """Import one delta file, newest-wins (phrase 86). Returns an outcome tag."""
    rel_path = str(change.get("rel_path") or "").strip()
    if not rel_path:
        return "failed"
    content = change.get("content")
    if content is None:
        return "failed"
    digest = KbService.content_hash(
        content.encode("utf-8") if isinstance(content, str) else content
    )

    doc = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == source.user_id,
            KbDocument.source_id == source.id,
            KbDocument.path_rel == rel_path,
        )
        .first()
    )

    if doc is not None:
        if doc.content_hash == digest:
            return "unchanged"
        # Conflict policy: local newer than the incoming change → keep local.
        mtime = change.get("mtime")
        if mtime is not None and doc.updated_at is not None:
            if doc.updated_at > mtime:
                return "stale"
        doc.content_hash = digest
        doc.status = "changed"
        doc.updated_at = utcnow()
    else:
        doc = KbDocument(
            user_id=source.user_id,
            source_id=source.id,
            path_rel=rel_path,
            title=os.path.splitext(os.path.basename(rel_path))[0],
            doc_type=change.get("doc_type") or _ext_of(rel_path) or "txt",
            content_hash=digest,
            status="new",
        )
        db.add(doc)

    # Stage + run the standard pipeline (extract → snapshot → chunk) (83).
    path = _stage(source, rel_path, content)
    doc.file_path = path
    db.add(doc)
    db.commit()
    db.refresh(doc)
    result = ingest_document(db, doc)
    if result.get("status") == "ok":
        return "imported"
    doc.status = "failed"
    db.add(doc)
    db.commit()
    return "failed"


@auto_job(
    "auto_sync",
    toggle="KB_SYNC_ENABLED",
    cap="",  # delta-only by cursor; per-source config bounds the work
    description="Sync changed files from git/drive/clip sources through ingest.",
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Sync every enabled git/drive/clip source (phrase 89).

    ``sync_type='local'`` sources are deliberately excluded — they belong to
    the dedicated ``auto_local_sync`` job (Copy Recent Notes) so the two
    toggles never double-sync the same external vault.
    """
    sources = (
        db.query(KbSource)
        .filter(
            KbSource.user_id == user_id,
            KbSource.enabled == True,  # noqa: E712
            KbSource.sync_type.in_(("git", "drive", "clip")),
        )
        .order_by(KbSource.id.asc())
        .all()
    )
    results = []
    imported = 0
    for source in sources:
        res = sync_source(db, source, force=False)
        results.append(res)
        imported += res.get("imported", 0)
    return {"sources": len(sources), "imported": imported, "results": results}


@auto_job(
    "auto_local_sync",
    toggle="KB_AUTO_LOCAL_SYNC_ENABLED",
    cap="",  # delta-only by cursor; per-source config bounds the work
    description="Copy recent notes from external vaults (sync_type='local') into notes/.",
)
def run_local(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Scheduled Copy Recent Notes: mirror every enabled ``local`` source.

    Each ``sync_type='local'`` source mirrors a configured external vault
    (``sync_source_path``) into its knowledge root — only changed knowledge
    Markdown files are copied, so unchanged notes reuse their embeddings.
    This is the same delta-only path the manual
    ``POST /api/kb/sources/{id}/sync`` endpoint calls with ``force=True``.
    """
    sources = (
        db.query(KbSource)
        .filter(
            KbSource.user_id == user_id,
            KbSource.enabled == True,  # noqa: E712
            KbSource.sync_type == "local",
        )
        .order_by(KbSource.id.asc())
        .all()
    )
    results = []
    copied = unchanged = removed = 0
    for source in sources:
        res = sync_source(db, source, force=False)
        results.append(res)
        copied += res.get("copied", 0)
        unchanged += res.get("unchanged", 0)
        removed += res.get("removed", 0)
    return {
        "sources": len(sources),
        "copied": copied,
        "unchanged": unchanged,
        "removed": removed,
        "results": results,
    }


def sync_status(source: KbSource) -> dict:
    """Per-source sync state for the UI (phrase 87)."""
    return {
        "source_id": source.id,
        "name": source.name,
        "sync_type": source.sync_type,
        "last_scanned_at": source.last_scanned_at.isoformat() if source.last_scanned_at else None,
        "cursor": KbService.json_loads(source.sync_cursor_json) or {},
        "sync_source_path": source.sync_source_path,
    }
