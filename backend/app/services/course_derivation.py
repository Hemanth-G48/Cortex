"""Derive Course rows from Second Brain tags + Google Classroom resources.

The Courses section is populated from three origins:
- ``manual``    — created by the user through the courses CRUD API
- ``classroom`` — merged from Google Classroom by ``google_id``
- ``kb_tag``    — derived from Second Brain documents tagged ``course:<name>``

This module holds the tag→course derivation (idempotent upsert + cleanup), the
sync-status payload, and the resource list (KB source folders + Classroom
course links) consumed by the dynamic Academic Resources grid. Mirrors the
classroom router's merge-by-id pattern so a re-sync never duplicates rows.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Course,
    CourseGapAnalysis,
    CourseSyncLog,
    KbDocument,
    KbDocumentTag,
    KbSource,
    KbTag,
)

# Fallback resource cards (mirrors frontend AcademicResourcesGrid defaults) used
# when there is nothing to derive yet, so the grid never renders empty.
_DEFAULT_RESOURCES: list[dict[str, str]] = [
    {"id": "lib", "title": "Library Portal", "type": "link", "url": "#", "description": "Access journals and books"},
    {"id": "scholar", "title": "Google Scholar", "type": "link", "url": "#", "description": "Research papers & citations"},
    {"id": "drive", "title": "Course Drive", "type": "link", "url": "#", "description": "Shared lecture materials"},
    {"id": "github", "title": "Code Repos", "type": "code", "url": "#", "description": "Project templates & examples"},
]


def _tag_doc_count(db: Session, user_id: int, tag_id: int) -> int:
    """Count non-deleted KB documents linked to a tag (per owner)."""
    return (
        db.query(KbDocumentTag)
        .join(KbDocument, KbDocumentTag.document_id == KbDocument.id)
        .filter(
            KbDocumentTag.user_id == user_id,
            KbDocumentTag.tag_id == tag_id,
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
        )
        .count()
    )


def _course_for_tag(db: Session, user_id: int, tag_id: int) -> Course | None:
    return (
        db.query(Course)
        .filter(Course.user_id == user_id, Course.kb_tag_id == tag_id)
        .first()
    )


def _delete_courses(db: Session, courses: list[Course]) -> int:
    """Delete Course rows together with any saved Gap Analysis for them.

    Every path that removes a course (manual delete, stale tag/folder cleanup,
    title-collision drop) must go through here so ``course_gap_analysis`` rows
    never outlive the course they belong to.
    """
    removed = 0
    for course in courses:
        db.query(CourseGapAnalysis).filter(
            CourseGapAnalysis.user_id == course.user_id,
            CourseGapAnalysis.course_id == course.id,
        ).delete()
        db.delete(course)
        removed += 1
    return removed


# Top-level vault folders that are organisational containers rather than
# subjects. A document's *first meaningful* folder segment is used, so generic
# containers are skipped and their children win: ``notes/Operating Systems/``
# still derives the subject "Operating Systems", while files at the vault root
# derive nothing. Extend this set in code to tune what counts as a subject.
FOLDER_DERIVATION_IGNORE = {
    ".obsidian", ".git", ".github", ".trash", "trash",
    "templates", "template", "attachments", "attachment", "assets",
    "images", "img", "icons", "files", "downloads", "exports", "export",
    "inbox", "archive", "archived", "daily", "journal", "journals",
    "notes", "docs", "documents", "misc", "miscellaneous", "private",
    "reference", "references", "resources", "scratch", "tmp", "temp",
}


def _folder_key(source_id: int | None, path_rel: str | None) -> tuple[int | None, str] | None:
    """First meaningful top-level folder segment for a document path.

    ``None`` when the document sits at the vault root or inside only generic
    containers (``notes``, ``templates``, …) — root-level files are not a
    subject and generic containers are skipped so ``notes/Subject/`` works.
    """
    segments = [s for s in (path_rel or "").split("/") if s and s.strip() != "."]
    for seg in segments[:-1]:  # everything but the final filename segment
        s = seg.strip()
        if len(s) < 2 or s.startswith("."):
            continue
        if s.lower() in FOLDER_DERIVATION_IGNORE:
            continue
        return source_id, s
    return None


def _folder_title(folder: str) -> str:
    """Humanize a folder name into a course title.

    ``operating-systems`` → ``Operating Systems``, but ``OS`` stays ``OS``
    (``.title()`` would mangle acronyms)."""
    title = folder.replace("_", " ").replace("-", " ").strip()
    if title.islower():
        title = title.title()
    return title[:200] or folder


# Folder-level metadata: a folder may carry an ``index.md`` (or ``_index.md``)
# whose YAML frontmatter drives the *derived subject's* description, status and
# color. Anything not recognised falls back to the folder-derivation defaults
# (status ``In progress``, no description/color).
_STATUS_MAP = {
    "not started": "Not started",
    "todo": "Not started",
    "planned": "Not started",
    "planning": "Not started",
    "backlog": "Not started",
    "in progress": "In progress",
    "active": "In progress",
    "ongoing": "In progress",
    "wip": "In progress",
    "doing": "In progress",
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "finished": "Completed",
    "archive": "Completed",
    "archived": "Completed",
}

# Named colors the frontend can consume directly as CSS color values (the
# Tailwind-ish palette used across the app's badges/chips).
_NAMED_COLORS = {
    "red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal",
    "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink",
    "rose", "slate", "gray", "grey", "zinc", "neutral", "stone",
}

# Optional keys tried (in order) when looking up a metadata field, so common
# Obsidian frontmatter naming variants all work.
_DESCRIPTION_KEYS = ("description", "summary", "subtitle", "about")
_STATUS_KEYS = ("status", "state")
_COLOR_KEYS = ("color", "colour", "accent")


def _normalize_status(value: Any) -> str:
    """Map arbitrary frontmatter status text onto the app's three statuses.

    Unknown values (and missing frontmatter) fall back to the folder
    derivation default (``In progress``).
    """
    if isinstance(value, str):
        key = value.strip().lower()
        if key in _STATUS_MAP:
            return _STATUS_MAP[key]
    return "In progress"


def _normalize_color(value: Any) -> str | None:
    """Accept a hex color (``#abc`` / ``#aabbcc`` / ``#aabbccdd``) or a named
    CSS color; anything else is ignored so junk frontmatter can't leak into the
    UI as an invalid inline style."""
    if not isinstance(value, str):
        return None
    color = value.strip()
    if not color:
        return None
    if color.lower() in _NAMED_COLORS:
        return color.lower()
    if re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?", color):
        return color.lower()
    return None


def _meta_description(meta: dict[str, Any]) -> str | None:
    """First non-empty string among the description-ish frontmatter keys."""
    for key in _DESCRIPTION_KEYS:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:2000]
    return None


def _like_escape(text: str) -> str:
    """Escape LIKE wildcards so a folder name is matched literally.

    Vault folder names are user-controlled and can contain ``%`` / ``_``
    (e.g. ``50%_Notes``); unescaped they act as LIKE wildcards and the index
    lookup could match the wrong document."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _folder_index_frontmatter(
    db: Session, user_id: int, source_id: int | None, folder: str
) -> dict[str, Any]:
    """Frontmatter of the folder's ``index.md`` / ``_index.md``, if present.

    Matches the document whose path ends with ``/<folder>/index.md`` (or
    ``_index.md``) inside the source — this also covers the generic-container
    case (``notes/Operating Systems/index.md``). Returns ``{}`` when no index
    document exists or it has no frontmatter, so derivation just uses defaults.
    """
    if not source_id:
        return {}
    base = _like_escape(folder.strip("/"))
    for name in ("index.md", "_index.md"):
        # Matches both ``Operating Systems/index.md`` (folder root) and
        # ``notes/Operating Systems/index.md`` (inside a generic container).
        # LIKE wildcards in the folder name are escaped (ESCAPE '\').
        doc = (
            db.query(KbDocument)
            .filter(
                KbDocument.user_id == user_id,
                KbDocument.source_id == source_id,
                KbDocument.status != "deleted",
                or_(
                    KbDocument.path_rel.ilike(f"{base}/{name}", escape="\\"),
                    KbDocument.path_rel.ilike(f"%/{base}/{name}", escape="\\"),
                ),
            )
            .first()
        )
        if doc is None or not doc.frontmatter_json:
            continue
        try:
            data = json.loads(doc.frontmatter_json)
        except (TypeError, ValueError):
            continue
        if isinstance(data, dict):
            return data
    return {}


def _folder_metadata(db: Session, user_id: int, source_id: int | None, folder: str) -> dict[str, Any]:
    """The derived-subject metadata for a folder: description/status/color.

    ``status`` always returns one of the app's three canonical statuses (the
    default is ``In progress``); description/color are ``None`` when the
    folder's index frontmatter does not provide them.
    """
    meta = _folder_index_frontmatter(db, user_id, source_id, folder)
    status_value = next((meta.get(k) for k in _STATUS_KEYS if meta.get(k)), None)
    color_value = next((meta.get(k) for k in _COLOR_KEYS if meta.get(k)), None)
    return {
        "description": _meta_description(meta),
        "status": _normalize_status(status_value),
        "color": _normalize_color(color_value),
    }


def _course_for_folder(db: Session, user_id: int, source_id: int | None, folder: str) -> Course | None:
    return (
        db.query(Course)
        .filter(
            Course.user_id == user_id,
            Course.source_type == "kb_folder",
            Course.kb_source_id == source_id,
            Course.kb_folder_path == folder,
        )
        .first()
    )


def _derive_courses_from_folders(db: Session, user_id: int) -> dict[str, Any]:
    """Create/update one Course per top-level vault folder; drop stale rows.

    Counts are derived from the documents' ``path_rel`` (folder prefix) within
    their source, so subjects appear without any tagging. Idempotent: a folder
    with an existing ``Course`` row is only updated, and a folder-derived row
    whose folder no longer resolves is removed. Explicitly named courses (a
    ``course:`` tag, a manual or Classroom row) win over folder derivation
    when titles collide — the folder is skipped, and any previously-derived
    ``kb_folder`` row for that folder is deleted so a later ``course:`` tag
    never leaves a stale duplicate behind. Title matching is
    case-insensitive, so ``course:linux`` and a ``linux/`` folder dedupe.

    Returns ``{created, updated, removed, course_folders}``.
    """
    counts: dict[tuple[int | None, str], int] = defaultdict(int)
    valid_keys: set[tuple[int | None, str]] = set()

    rows = (
        db.query(KbDocument.source_id, KbDocument.path_rel)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .all()
    )
    for source_id, path_rel in rows:
        key = _folder_key(source_id, path_rel)
        if key is not None:
            counts[key] += 1
            valid_keys.add(key)

    created = updated = removed = 0
    for (source_id, folder) in sorted(counts.keys()):
        title = _folder_title(folder)
        count = counts[(source_id, folder)]
        # Explicit sources win: skip a folder whose title already belongs to a
        # tag/manual/classroom course (or another folder-derived subject).
        # Compared case-insensitively so ``course:linux`` (title "linux") and a
        # ``linux/`` folder (title "Linux") are recognised as the same subject.
        collision = (
            db.query(Course.id)
            .filter(
                Course.user_id == user_id,
                func.lower(Course.title) == title.casefold(),
            )
            .filter(
                ~(
                    (Course.source_type == "kb_folder")
                    & (Course.kb_source_id == source_id)
                    & (Course.kb_folder_path == folder)
                )
            )
            .first()
        )
        if collision:
            # An explicit course (tag/manual/classroom/other folder) owns this
            # title — drop any previously-derived kb_folder row for this folder
            # so a later ``course:`` tag never leaves a stale duplicate behind.
            stale = _course_for_folder(db, user_id, source_id, folder)
            if stale is not None:
                removed += _delete_courses(db, [stale])
            continue
        # Folder-level metadata (index.md frontmatter) overrides the derivation
        # defaults on every run, so editing the index file then resyncing
        # refreshes the subject's description/status/color.
        meta = _folder_metadata(db, user_id, source_id, folder)
        existing = _course_for_folder(db, user_id, source_id, folder)
        if existing:
            existing.title = title
            existing.kb_document_count = count
            existing.total_assignments = count
            existing.status = meta["status"]
            existing.description = meta["description"]
            existing.color = meta["color"]
            updated += 1
        else:
            db.add(Course(
                title=title,
                status=meta["status"],
                source_type="kb_folder",
                kb_source_id=source_id,
                kb_folder_path=folder,
                user_id=user_id,
                kb_document_count=count,
                total_assignments=count,
                description=meta["description"],
                color=meta["color"],
            ))
            created += 1

    # Cleanup: drop folder-derived courses whose folder no longer resolves.
    stale_folders = [
        course
        for course in (
            db.query(Course)
            .filter(Course.user_id == user_id, Course.source_type == "kb_folder")
            .all()
        )
        if (course.kb_source_id, course.kb_folder_path) not in valid_keys
    ]
    removed += _delete_courses(db, stale_folders)

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "removed": removed,
        "course_folders": len(valid_keys),
    }


def derive_courses_from_tags(db: Session, user_id: int) -> dict[str, Any]:
    """Create/update one Course per ``course:*`` tag AND per top-level vault
    folder; drop stale derived rows.

    Tag derivation: one Course per ``course:`` tag (explicit tagging wins over
    folder derivation when titles collide). Folder derivation: one Course per
    top-level vault folder (``source_type='kb_folder'``) so subjects appear
    without any tagging. Idempotent — re-running after a sync only updates
    changed titles/counters. Returns a diagnostic summary:

    ``{created, updated, removed, courses, sources, documents, course_tags,
    course_folders, errors, synced_at}``
    """
    prefix = settings.COURSE_TAG_PREFIX
    tags = (
        db.query(KbTag)
        .filter(KbTag.user_id == user_id, KbTag.name.like(f"{prefix}%"))
        .order_by(KbTag.name)  # deterministic order for reproducible counts
        .all()
    )

    created = updated = removed = 0
    valid_tag_ids: list[int] = []
    errors: list[str] = []

    for tag in tags:
        valid_tag_ids.append(tag.id)
        title = tag.name[len(prefix):].strip() or tag.name
        try:
            doc_count = _tag_doc_count(db, user_id, tag.id)
        except Exception as exc:  # noqa: BLE001 — one bad tag must not kill the run
            errors.append(f"tag {tag.name!r}: {exc}")
            continue
        status = "In progress" if doc_count > 0 else "Not started"

        existing = _course_for_tag(db, user_id, tag.id)
        if existing:
            existing.title = title
            existing.kb_document_count = doc_count
            # Back-compat: keep total_assignments mirrored so older UI surfaces
            # that render assignment counts still show the linked-note count.
            existing.total_assignments = doc_count
            existing.status = status
            existing.source_type = "kb_tag"
            updated += 1
        else:
            db.add(Course(
                title=title,
                status=status,
                source_type="kb_tag",
                kb_tag_id=tag.id,
                user_id=user_id,
                kb_document_count=doc_count,
                total_assignments=doc_count,
            ))
            created += 1

    # Cleanup: drop kb-derived courses whose `course:` tag no longer resolves.
    stale = (
        db.query(Course)
        .filter(
            Course.user_id == user_id,
            Course.source_type == "kb_tag",
        )
        .filter(~Course.kb_tag_id.in_(valid_tag_ids))
        .all()
    )
    removed += _delete_courses(db, stale)

    db.commit()

    # Backfill for rows derived before kb_document_count existed: a kb_tag row
    # with a legacy doc count stored in total_assignments and no doc count yet.
    for course in (
        db.query(Course)
        .filter(
            Course.user_id == user_id,
            Course.source_type == "kb_tag",
            Course.kb_document_count == 0,
            Course.total_assignments > 0,
        )
        .all()
    ):
        course.kb_document_count = course.total_assignments
    db.commit()

    # Folder derivation (subjects without tagging) — merged into the same
    # summary so the UI shows one combined sync result.
    folders = _derive_courses_from_folders(db, user_id)

    # The Second Brain folder hierarchy is the canonical organization model:
    # persist one KbFolder per course child folder (domains/topics) so every
    # surface references the same folder entity. Runs on every course sync
    # (watcher, jobs, automation, manual) so renames/moves/deletes propagate
    # automatically. Never breaks the course sync if it hiccups.
    try:
        from app.services.kb.domain_service import sync_all_folders

        folder_sync = sync_all_folders(db, user_id)
    except Exception:  # noqa: BLE001 — folder sync is best-effort
        folder_sync = {"created": 0, "updated": 0, "removed": 0, "folders": 0}

    summary = {
        "created": created + folders["created"],
        "updated": updated + folders["updated"],
        "removed": removed + folders["removed"],
        "courses": db.query(Course).filter(Course.user_id == user_id).count(),
        "sources": db.query(KbSource).filter(KbSource.user_id == user_id).count(),
        "documents": db.query(KbDocument).filter(
            KbDocument.user_id == user_id, KbDocument.status != "deleted"
        ).count(),
        "course_tags": len(tags),
        "course_folders": folders["course_folders"],
        # Canonical folder/domain entities persisted by the folder sync.
        "domains": folder_sync["folders"],
        "errors": errors,
        "synced_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_sync_log(db, user_id, summary)
    return summary


def _write_sync_log(db: Session, user_id: int, summary: dict[str, Any]) -> None:
    """Upsert the latest sync log row for a user (one row, rewritten each run)."""
    log = db.query(CourseSyncLog).filter(CourseSyncLog.user_id == user_id).first()
    if log is None:
        log = CourseSyncLog(user_id=user_id)
        db.add(log)
    log.created = int(summary.get("created", 0))
    log.updated = int(summary.get("updated", 0))
    log.removed = int(summary.get("removed", 0))
    log.courses = int(summary.get("courses", 0))
    log.sources = int(summary.get("sources", 0))
    log.documents = int(summary.get("documents", 0))
    log.course_tags = int(summary.get("course_tags", 0))
    log.course_folders = int(summary.get("course_folders", 0))
    log.errors_json = json.dumps(summary.get("errors") or [])
    log.synced_at = datetime.now(timezone.utc)
    db.commit()


def course_sync_status(db: Session, user_id: int) -> dict[str, Any]:
    """Health payload for the Courses page (explains *why* a sync is empty).

    Combines KB counters, the last sync log, and Google connection state so the
    UI can guide the user instead of showing a bare ``0 created`` line.
    """
    from app.services import google_oauth

    log = db.query(CourseSyncLog).filter(CourseSyncLog.user_id == user_id).first()

    course_tags = (
        db.query(KbTag)
        .filter(
            KbTag.user_id == user_id,
            KbTag.name.like(f"{settings.COURSE_TAG_PREFIX}%"),
        )
        .count()
    )
    course_folders = (
        db.query(Course)
        .filter(Course.user_id == user_id, Course.source_type == "kb_folder")
        .count()
    )
    google = google_oauth.status(db)

    last_sync = None
    if log is not None:
        last_sync = {
            "created": log.created,
            "updated": log.updated,
            "removed": log.removed,
            "courses": log.courses,
            "sources": log.sources,
            "documents": log.documents,
            "course_tags": log.course_tags,
            "course_folders": log.course_folders,
            "errors": json.loads(log.errors_json) if log.errors_json else [],
            "synced_at": log.synced_at.isoformat() if log.synced_at else None,
        }

    return {
        "sources": db.query(KbSource).filter(KbSource.user_id == user_id).count(),
        "documents": db.query(KbDocument).filter(
            KbDocument.user_id == user_id, KbDocument.status != "deleted"
        ).count(),
        "course_tags": course_tags,
        "course_folders": course_folders,
        "last_sync": last_sync,
        "google": {
            "configured": bool(google.get("configured")),
            "connected": bool(google.get("connected")),
            "email": google.get("email"),
        },
    }


def list_course_resources(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Combine KB source folders + Classroom course links into resource cards.

    Falls back to ``_DEFAULT_RESOURCES`` when nothing is derived.
    """
    resources: list[dict[str, Any]] = []

    for src in (
        db.query(KbSource)
        .filter(KbSource.user_id == user_id, KbSource.enabled.is_(True))
        .order_by(KbSource.name)
        .all()
    ):
        resources.append({
            "id": f"sb-{src.id}",
            "title": src.name,
            "type": "folder",
            "url": src.root_path,
            "description": f"{src.source_type} source",
        })

    for course in (
        db.query(Course)
        .filter(
            Course.user_id == user_id,
            Course.source_type == "classroom",
            Course.classroom_url.isnot(None),
        )
        .order_by(Course.title)
        .all()
    ):
        resources.append({
            "id": f"gc-{course.google_id}",
            "title": course.title,
            "type": "classroom",
            "url": course.classroom_url,
            "description": "Google Classroom",
        })

    return resources if resources else list(_DEFAULT_RESOURCES)
