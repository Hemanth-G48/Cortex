"""One-time Second Brain vault migration — ``notes/`` + ``daily-life/`` separation.

The migration is a **filesystem reorganization** plus a **source-root repoint**:

- ``second_brain/<top-level knowledge folders + extractable files>``
  → ``second_brain/notes/``
- ``second_brain/daily-life/`` is created (empty) — the non-knowledge area.
- Every ``KbSource`` whose ``root_path`` is the vault root is repointed at
  ``notes/``.

Why this never re-embeds anything (the non-negotiable rule):

``KbDocument.path_rel`` is stored **relative to the source root**. Moving the
files into ``notes/`` and repointing the root keeps every existing ``path_rel``
byte-identical, so the next scan sees zero new / changed / removed files →
zero embedding work. ``daily-life/`` sits outside the source root and is
structurally excluded from indexing, retrieval, gap analysis and stats.

A timestamped tarball of the vault **and** a SQLite online backup of the DB
are written before any file is moved.

Safety: if two ``KbSource`` rows point at the same vault root but belong to
*different users* (leftover seed data), the migration repoints both but only
**disables** the non-primary one (watcher stops scanning it; nothing is
deleted — the owner's data stays intact and reversible).
"""

from __future__ import annotations

import logging
import os
import shutil
import tarfile
from datetime import datetime, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import (
    CategorizeSuggestion,
    Course,
    FolderGapAnalysis,
    KbChunk,
    KbCitation,
    KbDocument,
    KbEdge,
    KbEmbedding,
    KbFlashcardCandidate,
    KbFolder,
    KbQualitySuggestion,
    KbQuizLink,
    KbSource,
    KbSummary,
    MicroSession,
    OutdatedNote,
)
from app.services.text_extractor import EXTRACTABLE_TYPES

logger = logging.getLogger(__name__)

# Top-level vault folders that are structural, never knowledge.
_STRUCTURAL_TOP_LEVEL = {"notes", "daily-life"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ext_of(filename: str) -> str | None:
    ext = os.path.splitext(filename)[1].lstrip(".").lower()
    return ext if ext in EXTRACTABLE_TYPES else None


# ---------------------------------------------------------------------------
# Backups (vault tarball + DB online backup)
# ---------------------------------------------------------------------------

def backup_vault(vault_root: str, backups_dir: str | None = None) -> str:
    """Timestamped tarball of the whole vault; returns the archive path."""
    vault_root = os.path.abspath(vault_root)
    if not os.path.isdir(vault_root):
        raise FileNotFoundError(f"vault root not found: {vault_root}")
    backups_dir = backups_dir or os.path.join(os.path.dirname(vault_root), "backups")
    os.makedirs(backups_dir, exist_ok=True)
    stamp = _utcnow().strftime("%Y%m%d_%H%M%S")
    arc = os.path.join(backups_dir, f"{os.path.basename(vault_root)}_{stamp}.tar.gz")
    with tarfile.open(arc, "w:gz") as tf:
        tf.add(vault_root, arcname=os.path.basename(vault_root))
    logger.info("Vault backup written: %s", arc)
    return arc


def backup_db(db: Session, backups_dir: str | None = None) -> str:
    """SQLite online backup of the app database; returns the backup path."""
    import sqlite3

    url = db.bind.url if getattr(db.bind, "url", None) is not None else None
    db_path = url.database if url else None
    if not db_path:
        raise RuntimeError("cannot resolve sqlite database path from engine")
    db_path = os.path.abspath(db_path) if not os.path.isabs(db_path) else db_path
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"database file not found: {db_path}")
    backups_dir = backups_dir or os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backups_dir, exist_ok=True)
    stamp = _utcnow().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(backups_dir, f"{os.path.basename(db_path)}_{stamp}.db")
    src = sqlite3.connect(db_path)
    try:
        out = sqlite3.connect(dst)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    logger.info("DB backup written: %s", dst)
    return dst


# ---------------------------------------------------------------------------
# Filesystem reorganization
# ---------------------------------------------------------------------------

def reorganize_vault(vault_root: str, *, dry_run: bool = False) -> dict:
    """Move knowledge folders/files into ``notes/``; create ``daily-life/``.

    Only top-level **directories** (whole subtrees — hierarchy preserved) and
    **extractable files** (md/txt/pdf/docx) are moved. Non-extractable root
    files (images, canvases, scripts) are skipped and reported — they are not
    indexed anyway and Obsidian may reference them.
    """
    vault_root = os.path.abspath(vault_root)
    notes_root = os.path.join(vault_root, "notes")
    daily_life = os.path.join(vault_root, "daily-life")
    report: dict = {
        "notes_root": notes_root,
        "daily_life": daily_life,
        "created": [],
        "moved_dirs": 0,
        "moved_dirs_list": [],
        "moved_files": 0,
        "moved_files_list": [],
        "skipped": [],
    }

    for name in ("notes", "daily-life"):
        target = os.path.join(vault_root, name)
        if not os.path.isdir(target):
            if dry_run:
                report["created"].append(target)
                continue
            os.makedirs(target)
            report["created"].append(target)

    for entry in sorted(os.listdir(vault_root)):
        if entry.startswith("."):
            continue
        full = os.path.join(vault_root, entry)
        if entry.casefold() in _STRUCTURAL_TOP_LEVEL:
            continue
        if os.path.isdir(full):
            dest = os.path.join(notes_root, entry)
            if dry_run:
                report["moved_dirs"] += 1
                report["moved_dirs_list"].append(entry)
                continue
            shutil.move(full, dest)
            report["moved_dirs"] += 1
            report["moved_dirs_list"].append(entry)
        elif _ext_of(entry):
            dest = os.path.join(notes_root, entry)
            if dry_run:
                report["moved_files"] += 1
                report["moved_files_list"].append(entry)
                continue
            shutil.move(full, dest)
            report["moved_files"] += 1
            report["moved_files_list"].append(entry)
        else:
            report["skipped"].append(entry)

    report["knowledge_root"] = notes_root
    return report


# ---------------------------------------------------------------------------
# Source registry updates
# ---------------------------------------------------------------------------

def repoint_source_roots(db: Session, vault_root: str) -> dict:
    """Point every source rooted at the vault at ``vault_root/notes``."""
    vault_root = os.path.abspath(vault_root)
    notes_root = os.path.join(vault_root, "notes")
    rows = db.query(KbSource).all()
    changed = []
    for source in rows:
        if not source.root_path:
            continue
        root = os.path.abspath(source.root_path)
        if root == vault_root and root != notes_root:
            source.root_path = notes_root
            changed.append(
                {"id": source.id, "user_id": source.user_id, "old_root": root, "new_root": notes_root}
            )
    db.commit()
    return {"repointed": changed}


def refresh_file_paths(db: Session, source: KbSource) -> int:
    """Recompute ``file_path`` for the source's documents after a root move.

    The scan treats path-only moves as unchanged (path_rel is byte-identical
    relative to the new root), so it never touches ``file_path`` — which would
    otherwise keep pointing at the pre-migration absolute location and break
    the next content-change ingest ("file missing on disk").
    """
    updated = 0
    if not source.root_path or not os.path.isdir(source.root_path):
        return updated
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.source_id == source.id, KbDocument.status != "deleted")
        .all()
    )
    for doc in docs:
        if not doc.path_rel:
            continue
        candidate = os.path.join(source.root_path, doc.path_rel)
        if os.path.isfile(candidate) and candidate != doc.file_path:
            doc.file_path = candidate
            updated += 1
    db.commit()
    return updated


def disable_cross_user_duplicates(db: Session, vault_root: str) -> dict:
    """Disable duplicate sources from *other* users on the same vault root.

    The watcher scans every enabled source (all users); a leftover seed source
    from another user on the same vault double-scans and double-indexes the
    same files. We keep the lowest-id source enabled and disable the rest —
    no rows are deleted, so it is fully reversible.
    """
    vault_root = os.path.abspath(vault_root)
    notes_root = os.path.join(vault_root, "notes")
    rows = (
        db.query(KbSource)
        .filter(
            KbSource.root_path.in_([vault_root, notes_root]),
            KbSource.enabled == True,  # noqa: E712
        )
        .order_by(KbSource.id.asc())
        .all()
    )
    disabled = []
    if len(rows) > 1:
        keeper, others = rows[0], rows[1:]
        for source in others:
            if source.user_id == keeper.user_id:
                continue  # same user → keep both (may be intentional split)
            source.enabled = False
            disabled.append(
                {"id": source.id, "user_id": source.user_id, "root": source.root_path}
            )
    db.commit()
    return {"disabled": disabled, "kept": rows[0].id if rows else None}


# ---------------------------------------------------------------------------
# Hard-delete a source (leftover duplicate index cleanup)
# ---------------------------------------------------------------------------

# Per-document tables with a hard FK to kb_documents that the ORM cascade does
# NOT cover (SQLite FK enforcement is off, so they would otherwise dangle as
# orphaned rows). All of them are deleted together with their documents.
_DOC_TABLES = (
    KbSummary,
    KbCitation,
    KbQuizLink,
    KbFlashcardCandidate,
    CategorizeSuggestion,
    OutdatedNote,
    KbQualitySuggestion,
)


def purge_source(db: Session, source_id: int, *, dry_run: bool = False) -> dict:
    """Hard-delete one source and every row that references its index.

    Mirrors the ``DELETE /api/kb/sources/{id}`` router semantics (edges +
    ORM cascade documents → chunks/versions/tags) and additionally removes
    what that router leaves behind: ``kb_embeddings`` (no ORM cascade), the
    per-document FK tables, ``kb_folders`` + their saved gap analyses, and
    any ``courses.kb_source_id`` references.

    ``dry_run=True`` reports exactly what would be deleted without touching
    anything.
    """
    source = db.get(KbSource, source_id)
    if source is None:
        raise ValueError(f"source {source_id} not found")

    doc_ids = [
        d.id for d in db.query(KbDocument).filter(KbDocument.source_id == source_id).all()
    ]
    chunk_ids = []
    if doc_ids:
        chunk_ids = [
            c.id
            for c in db.query(KbChunk).filter(KbChunk.document_id.in_(doc_ids)).all()
        ]
    folder_ids = [
        f.id for f in db.query(KbFolder).filter(KbFolder.source_id == source_id).all()
    ]

    report: dict = {
        "source_id": source_id,
        "user_id": source.user_id,
        "name": source.name,
        "root_path": source.root_path,
        "documents": len(doc_ids),
        "chunks": len(chunk_ids),
        "folders": len(folder_ids),
        "embeddings": (
            db.query(KbEmbedding)
            .filter(KbEmbedding.chunk_id.in_(chunk_ids))
            .count()
            if chunk_ids
            else 0
        ),
        "edges": (
            db.query(KbEdge)
            .filter(
                or_(
                    KbEdge.source_document_id.in_(doc_ids),
                    KbEdge.target_document_id.in_(doc_ids),
                )
            )
            .count()
            if doc_ids
            else 0
        ),
        "folder_gap_analyses": (
            db.query(FolderGapAnalysis)
            .filter(FolderGapAnalysis.folder_id.in_(folder_ids))
            .count()
            if folder_ids
            else 0
        ),
        "courses_linked": (
            db.query(Course).filter(Course.kb_source_id == source_id).count()
        ),
    }
    per_doc_counts: dict[str, int] = {}
    for model in _DOC_TABLES:
        per_doc_counts[model.__tablename__] = (
            db.query(model).filter(model.document_id.in_(doc_ids)).count()
            if doc_ids
            else 0
        )
    micro_sessions = (
        db.query(MicroSession).filter(MicroSession.chunk_id.in_(chunk_ids)).count()
        if chunk_ids
        else 0
    )
    report["per_document_rows"] = per_doc_counts
    report["micro_sessions"] = micro_sessions

    if dry_run:
        report["dry_run"] = True
        return report

    # 1) chunk embeddings (no ORM cascade) + chunk-referencing micro sessions.
    if chunk_ids:
        db.query(KbEmbedding).filter(KbEmbedding.chunk_id.in_(chunk_ids)).delete(
            synchronize_session=False
        )
        db.query(MicroSession).filter(MicroSession.chunk_id.in_(chunk_ids)).delete(
            synchronize_session=False
        )
    # 2) graph edges touching the documents.
    if doc_ids:
        db.query(KbEdge).filter(
            or_(
                KbEdge.source_document_id.in_(doc_ids),
                KbEdge.target_document_id.in_(doc_ids),
            )
        ).delete(synchronize_session=False)
    # 3) per-document FK tables not covered by the ORM cascade.
    for model in _DOC_TABLES:
        db.query(model).filter(model.document_id.in_(doc_ids)).delete(
            synchronize_session=False
        )
    # 4) folders + their saved domain gap analyses.
    if folder_ids:
        db.query(FolderGapAnalysis).filter(
            FolderGapAnalysis.folder_id.in_(folder_ids)
        ).delete(synchronize_session=False)
    db.query(KbFolder).filter(KbFolder.source_id == source_id).delete(
        synchronize_session=False
    )
    # 5) detach courses that pointed at this source.
    db.query(Course).filter(Course.kb_source_id == source_id).update(
        {Course.kb_source_id: None}, synchronize_session=False
    )
    # 6) the source itself (ORM cascade → documents → chunks/versions/tags).
    db.delete(source)
    db.commit()
    report["dry_run"] = False
    report["deleted"] = True
    return report


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_migration(
    db: Session,
    vault_root: str,
    *,
    backup: bool = True,
    scan: bool = True,
    dry_run: bool = False,
) -> dict:
    """Backup → reorganize → repoint roots → disable cross-user duplicates → rescan."""
    report: dict = {"vault_root": os.path.abspath(vault_root), "dry_run": dry_run}

    if backup and not dry_run:
        report["backup"] = {
            "vault_tarball": backup_vault(vault_root),
            "db_backup": backup_db(db),
        }
    else:
        report["backup"] = {"note": "skipped (dry_run or backup=False)"}

    report["reorganize"] = reorganize_vault(vault_root, dry_run=dry_run)
    if dry_run:
        return report

    repointed = repoint_source_roots(db, vault_root)
    dup = disable_cross_user_duplicates(db, vault_root)
    # After repointing, refresh every document's absolute file_path so the
    # next content-change ingest resolves the file at its new location.
    file_paths_fixed = 0
    for entry in repointed.get("repointed", []):
        source = db.get(KbSource, entry["id"])
        if source is not None:
            file_paths_fixed += refresh_file_paths(db, source)
    report["sources"] = {
        **repointed,
        **dup,
        "file_paths_refreshed": file_paths_fixed,
    }

    if scan:
        # Re-scan the kept (lowest-id) enabled source so the index reconciles
        # with the new root. path_rel values are unchanged → everything is
        # reused; this also proves the migration caused zero re-embedding.
        from app.services.kb.scanner import scan_and_ingest

        keeper = report["sources"].get("kept")
        summary: dict = {}
        if keeper is not None:
            summary = scan_and_ingest(db, keeper)
        report["scan"] = summary

    return report
