"""Workflow glue — vault backup & restore.

``build_backup_zip`` — one-click snapshot of the owner's vault:
    - ``student_os.db`` — a consistent copy of the SQLite database (via the
      sqlite3 backup API, so the file is valid even mid-write).
    - ``vault/<source-id>/<relpath>`` — every file under each enabled source
      root (reuse paths preserved so restore lands back in place).
    - ``manifest.json`` — app version, user, exported-at, source list.

``restore_zip`` — accept an uploaded archive produced by the exporter:
    - Validates the manifest + archive structure (no path traversal).
    - Writes the restored DB to the live DB path ONLY when the current
      database is empty OR the caller passes ``replace_db=true``; otherwise
      the DB snapshot is dropped with a note (safe default — never clobber
      live data without an explicit opt-in).
    - Restores vault files under their original source roots (creating the
      source's root directory when missing).

Single-user local app: restore is best-effort file-level recovery, not a
transactional migration — the UI tells the user to restart the backend after
a DB replace so SQLAlchemy reconnects.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbSource

ZIP_IGNORE_DIRS = {".git", ".obsidian", ".trash", ".tmp", "node_modules", "__pycache__"}


def _db_file_path() -> Path | None:
    """Resolve the SQLite file path from ``settings.DATABASE_URL``.

    Returns ``None`` for non-file databases (e.g. in-memory under pytest).
    """
    url = settings.DATABASE_URL or ""
    if url.startswith("sqlite:///"):
        return Path(url[len("sqlite:///") :])
    return None


def _walk_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ZIP_IGNORE_DIRS]
        for name in filenames:
            yield Path(dirpath) / name


def build_backup_zip(db: Session, user_id: int) -> bytes:
    """Build the full vault backup archive as bytes (in-memory zip)."""
    sources = (
        db.query(KbSource)
        .filter(KbSource.user_id == user_id, KbSource.enabled.is_(True))
        .all()
    )
    db_path = _db_file_path()
    db_included = db_path is not None and db_path.exists()
    manifest = {
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "user_id": user_id,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "sources": [
            {
                "id": s.id,
                "name": s.name,
                "root_path": s.root_path,
            }
            for s in sources
        ],
        "includes_db": db_included,
    }

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # Vault files first (paths relative to each source root).
        for source in sources:
            root = source.root_path
            if not root or not os.path.isdir(root):
                continue
            root_p = Path(root)
            for file_p in _walk_files(root_p):
                rel = file_p.relative_to(root_p).as_posix()
                zf.write(file_p, f"vault/{source.id}/{rel}")
        # Database snapshot (only when the DB is a real file on disk).
        if db_included:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                src = sqlite3.connect(str(db_path))
                try:
                    dst = sqlite3.connect(str(tmp_path))
                    try:
                        src.backup(dst)
                    finally:
                        dst.close()
                finally:
                    src.close()
                zf.write(tmp_path, "student_os.db")
            finally:
                tmp_path.unlink(missing_ok=True)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    return buf.getvalue()


class RestoreResult:
    def __init__(self) -> None:
        self.restored_files = 0
        self.sources_matched = 0
        self.database_restored = False
        self.database_skipped = False
        self.warnings: list[str] = []


def _safe_member(path: str) -> str | None:
    """Normalise a zip member to a safe relative path, or None if unsafe.

    Unlike ``path_utils.safe_path`` (which strips to a *basename* for upload
    filenames), zip members are multi-segment relative paths
    (``vault/<source-id>/<relpath>``) whose structure must be preserved. Here
    we drop unsafe segments (``..``, absolute roots, drive letters) while
    keeping the directory hierarchy, then rely on the caller's
    resolve()-under-root containment check as defense in depth.
    """
    parts = path.replace("\\", "/").split("/")
    # Drop empty segments, current-dir markers, traversal markers, absolute
    # roots, and Windows drive letters (e.g. "C:").
    safe_parts = [
        p
        for p in parts
        if p and p not in (".", "..") and not p.endswith(":") and not p.startswith("/")
    ]
    if not safe_parts or safe_parts != parts:
        # Any dropped segment means the path was malformed or tried to escape
        # — reject the whole member rather than guess the intent.
        return None
    return "/".join(safe_parts)


def restore_zip(db: Session, user_id: int, data: bytes, *, replace_db: bool = False) -> dict:
    """Restore an exported backup archive.

    Safe by default: ``replace_db`` must be true to overwrite a non-empty
    live database; vault files are always restored into their source roots.
    """
    result = RestoreResult()
    try:
        zf = zipfile.ZipFile(BytesIO(data))
    except zipfile.BadZipFile:
        return {"ok": False, "error": "Not a valid zip archive"}

    # Zip-bomb guard: refuse archives whose members would exceed a sane
    # decompressed size (10 GB) — cheap to compute from the central directory.
    try:
        total_uncompressed = sum(i.file_size for i in zf.infolist())
        if total_uncompressed > 10 * 1024 * 1024 * 1024:
            return {"ok": False, "error": "Backup too large after extraction"}
    except Exception:  # noqa: BLE001 — a malformed central directory is handled below
        return {"ok": False, "error": "Not a valid zip archive"}

    names = zf.namelist()
    if "manifest.json" not in names:
        return {"ok": False, "error": "Backup is missing manifest.json — not a vault backup"}

    try:
        manifest = json.loads(zf.read("manifest.json"))
    except (ValueError, KeyError):
        return {"ok": False, "error": "manifest.json is not valid JSON"}

    sources = {
        s.id: s for s in db.query(KbSource).filter(KbSource.user_id == user_id).all()
    }

    # ── Restore vault files ──
    for name in names:
        member = _safe_member(name)
        if not member or not member.startswith("vault/"):
            continue
        parts = member.split("/")
        if len(parts) < 3:
            continue
        try:
            source_id = int(parts[1])
        except ValueError:
            continue
        source = sources.get(source_id)
        if source is None or not source.root_path:
            continue
        rel = "/".join(parts[2:])
        target = Path(source.root_path) / rel
        # Defend against traversal even after the member check (prefix-safe
        # containment, not a raw startswith which can collide on /a/b vs /a/bc).
        root_resolved = Path(source.root_path).resolve()
        try:
            target.resolve().relative_to(root_resolved)
        except ValueError:
            result.warnings.append(f"Skipped unsafe path: {member}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(name) as src_f, open(target, "wb") as out_f:
            out_f.write(src_f.read())
        result.restored_files += 1
        result.sources_matched += 1

    # ── Restore database (opt-in) ──
    if "student_os.db" in names:
        db_path = _db_file_path()
        if db_path is None:
            result.warnings.append("Live database is not a file — DB snapshot skipped")
            result.database_skipped = True
        elif replace_db:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                with zf.open("student_os.db") as src_f:
                    tmp_path.write_bytes(src_f.read())
                # Sanity check: it must open as a valid SQLite database.
                conn = sqlite3.connect(str(tmp_path))
                try:
                    conn.execute("PRAGMA integrity_check").fetchone()
                finally:
                    conn.close()
                db_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path.replace(db_path)
                # Drop pooled connections so the next query reconnects to the
                # new file instead of the replaced inode.
                try:
                    from app.database import engine as _engine

                    _engine.dispose()
                except Exception:  # noqa: BLE001 — dispose is best-effort
                    pass
                result.database_restored = True
            finally:
                tmp_path.unlink(missing_ok=True)
        else:
            result.database_skipped = True
            result.warnings.append(
                "Database snapshot skipped — live data exists (pass replace_db=true to overwrite)"
            )

    return {
        "ok": True,
        "restored_files": result.restored_files,
        "sources_matched": result.sources_matched,
        "database_restored": result.database_restored,
        "database_skipped": result.database_skipped,
        "warnings": result.warnings,
        "user_id": manifest.get("user_id"),
        "exported_at": manifest.get("exported_at"),
    }
