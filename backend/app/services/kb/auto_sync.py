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
import subprocess
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbSource
from app.services.kb import KbService, utcnow
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
    directory = os.path.join(SYNC_STAGING, str(source.id))
    os.makedirs(directory, exist_ok=True)
    # Flatten nested rel paths safely (no traversal).
    safe = rel_path.replace("..", "_").lstrip("/")
    target = os.path.join(directory, safe)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    data = content.encode("utf-8") if isinstance(content, str) else content
    with open(target, "wb") as fh:
        fh.write(data)
    return target


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


def sync_source(
    db: Session, source: KbSource, *, force: bool = False
) -> dict:
    """Run one source's adapter and import deltas through the ingest pipeline."""
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
    """Sync every enabled source with a non-``none`` sync_type (phrase 89)."""
    sources = (
        db.query(KbSource)
        .filter(
            KbSource.user_id == user_id,
            KbSource.enabled == True,  # noqa: E712
            KbSource.sync_type != "none",
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


def sync_status(source: KbSource) -> dict:
    """Per-source sync state for the UI (phrase 87)."""
    return {
        "source_id": source.id,
        "name": source.name,
        "sync_type": source.sync_type,
        "last_scanned_at": source.last_scanned_at.isoformat() if source.last_scanned_at else None,
        "cursor": KbService.json_loads(source.sync_cursor_json) or {},
    }
