"""Domain service — the Second Brain folder hierarchy as the canonical model.

Folders determine organization: a top-level vault folder is a Course, its
child folders are Domains/Topics, and the notes inside them are Documents.
This module makes that hierarchy *persisted and canonical* (``KbFolder``
rows) instead of recomputing folder paths on every page load:

- ``sync_all_folders`` — derived during course sync (the same watcher / job /
  manual-sync paths that already run ``derive_courses_from_tags``): scans
  every course's root folder, upserts one ``KbFolder`` per child folder, and
  deletes rows whose folder no longer resolves (rename/delete/move detected
  automatically on the next sync).
- ``domain_tree`` / ``domain_detail`` — the hierarchical view consumed by the
  course page (domains-first grid) and the domain detail page.
- ``domain_gaps`` — Gap Analysis scoped to ONE folder's documents, using the
  same actionable evidence engine as course gaps, with the same save-and-reuse
  persistence (``FolderGapAnalysis``): computed once, reused on every later
  view, recomputed only on explicit Re-analyze or after a reindex.

AI is only ever used for understanding content / gap analysis — never for
deciding which folder a note belongs to.
"""

from __future__ import annotations

from app.services.kb.gap_engine import normalize_gap_payload

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Course, KbDocument, KbEdge, KbFolder, KbSource, FolderGapAnalysis

# Reuse the course-derivation ignore list so folders that are organisational
# containers (attachments, templates, …) never become domains.
IGNORE = {
    ".obsidian", ".git", ".github", ".trash", "trash",
    "templates", "template", "attachments", "attachment", "assets",
    "images", "img", "icons", "files", "downloads", "exports", "export",
    "inbox", "archive", "archived", "daily", "journal", "journals",
    "notes", "docs", "documents", "misc", "miscellaneous", "private",
    "reference", "references", "resources", "scratch", "tmp", "temp",
}

MAX_SUBFOLDERS = 100  # safety cap on folders synced per course


# ---------------------------------------------------------------------------
# Folder derivation helpers
# ---------------------------------------------------------------------------

def _folder_title(folder: str) -> str:
    """Humanize a folder name (same rules as course derivation)."""
    title = folder.replace("_", " ").replace("-", " ").strip()
    if title.islower():
        title = title.title()
    return title[:300] or folder


def _folder_paths_below(path_rel: str | None, root: str) -> tuple[set[str], str | None]:
    """All non-ignored folder paths strictly below ``root`` for one document.

    ``Cybersecurity/Web Security/SQL Injection.md`` under root
    ``Cybersecurity`` → ``{"Cybersecurity/Web Security"}`` (the document's
    direct folder). ``…/Web Security/Deep/X.md`` → ``{"…/Web Security",
    "…/Web Security/Deep"}`` (ancestors included). Returns ``(paths,
    deepest)`` where ``deepest`` is the document's direct parent folder (the
    folder it is *inside*), or ``None`` when the document sits directly in the
    course root.
    """
    if not path_rel:
        return set(), None
    segments = [s for s in path_rel.split("/") if s and s.strip() != "."]
    if len(segments) < 2:
        return set(), None
    try:
        root_idx = next(i for i, seg in enumerate(segments[:-1]) if seg.strip() == root)
    except StopIteration:
        return set(), None

    paths: set[str] = set()
    cumulative = root
    deepest: str | None = None
    for seg in segments[root_idx + 1 : -1]:
        s = seg.strip()
        if not s or len(s) < 2 or s.startswith("."):
            continue
        if s.lower() in IGNORE:
            continue
        cumulative = f"{cumulative}/{s}"
        paths.add(cumulative)
        deepest = cumulative
    return paths, deepest


def _root_for_course(db: Session, course: Course) -> tuple[int | None, str] | None:
    """The course's root vault folder, or None.

    Folder-derived courses carry ``kb_source_id`` + ``kb_folder_path``
    directly. Tag-derived / manual courses whose title matches a top-level
    folder resolve to that folder (same rule as ``course_content``).
    """
    if course.source_type == "kb_folder" and course.kb_source_id and course.kb_folder_path:
        return course.kb_source_id, course.kb_folder_path

    target = course.title.casefold()
    rows = (
        db.query(KbDocument.source_id, KbDocument.path_rel)
        .filter(KbDocument.user_id == course.user_id, KbDocument.status != "deleted")
        .all()
    )
    for source_id, path_rel in rows:
        segments = [s for s in (path_rel or "").split("/") if s and s.strip() != "."]
        for seg in segments[:-1]:
            s = seg.strip()
            if not s or len(s) < 2 or s.startswith("."):
                continue
            if s.lower() in IGNORE:
                continue
            if _folder_title(s).casefold() == target:
                return source_id, s
    return None


def _folder_payload(folder: KbFolder) -> dict[str, Any]:
    return {
        "id": folder.id,
        "name": folder.name,
        "path": folder.path,
        "depth": folder.depth,
        "doc_count": folder.doc_count,
        "description": folder.description,
        "status": folder.status,
        "color": folder.color,
        "created_at": folder.created_at.isoformat() if folder.created_at else None,
        "updated_at": folder.updated_at.isoformat() if folder.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Canonical folder sync (folder hierarchy = source of truth)
# ---------------------------------------------------------------------------

def sync_all_folders(db: Session, user_id: int) -> dict[str, Any]:
    """Upsert ``KbFolder`` rows for every course's child folders; drop stale.

    Idempotent: existing rows are updated in place, new folders are created,
    and rows whose folder no longer resolves (renamed/deleted/moved) are
    removed together with any saved per-domain Gap Analysis. Cheap — bounded
    by the number of documents, and safe to run on every course sync.
    """
    created = updated = removed = 0
    courses = (
        db.query(Course)
        .filter(Course.user_id == user_id)
        .order_by(Course.title)
        .all()
    )
    seen_paths: set[tuple[int | None, str]] = set()

    for course in courses:
        root = _root_for_course(db, course)
        if root is None:
            continue
        source_id, root_folder = root
        paths, direct_counts = _scan_course_folders(db, user_id, source_id, root_folder)
        if not paths:
            continue

        # Upsert each folder path under this course's root.
        for path in sorted(paths):
            seen_paths.add((source_id, path))
            name = path.rsplit("/", 1)[-1]
            depth = path.count("/")  # root ``A/B`` → depth 1, ``A/B/C`` → 2
            parent_path = path.rsplit("/", 1)[0]
            parent = None
            if parent_path != root_folder:
                parent = (
                    db.query(KbFolder.id)
                    .filter(
                        KbFolder.user_id == user_id,
                        KbFolder.source_id == source_id,
                        KbFolder.path == parent_path,
                    )
                    .first()
                )
            parent_id = parent[0] if parent else None

            row = (
                db.query(KbFolder)
                .filter(
                    KbFolder.user_id == user_id,
                    KbFolder.source_id == source_id,
                    KbFolder.path == path,
                )
                .first()
            )
            if row is None:
                db.add(
                    KbFolder(
                        user_id=user_id,
                        source_id=source_id,
                        course_id=course.id,
                        parent_id=parent_id,
                        path=path,
                        name=name,
                        depth=depth,
                        doc_count=direct_counts.get(path, 0),
                    )
                )
                created += 1
            else:
                row.course_id = course.id
                row.name = name
                row.depth = depth
                row.parent_id = parent_id
                row.doc_count = direct_counts.get(path, 0)
                row.updated_at = datetime.now(timezone.utc)
                updated += 1
            # Flush after every row so the parent lookup for a deeper folder
            # (processed later in sorted order) can see the row it links to.
            db.flush()

    # Cleanup: folder rows whose path no longer resolves for this user.
    stale = (
        db.query(KbFolder)
        .filter(KbFolder.user_id == user_id)
        .all()
    )
    for folder in stale:
        key = (folder.source_id, folder.path)
        if key in seen_paths:
            continue
        db.query(FolderGapAnalysis).filter(
            FolderGapAnalysis.user_id == user_id,
            FolderGapAnalysis.folder_id == folder.id,
        ).delete()
        db.delete(folder)
        removed += 1

    db.commit()
    return {"created": created, "updated": updated, "removed": removed, "folders": len(seen_paths)}


def _scan_course_folders(
    db: Session, user_id: int, source_id: int | None, root_folder: str
) -> tuple[set[str], dict[str, int]]:
    """Folders below a course root + per-folder direct document counts."""
    paths: set[str] = set()
    direct: dict[str, int] = {}
    q = db.query(KbDocument.path_rel).filter(
        KbDocument.user_id == user_id, KbDocument.status != "deleted"
    )
    if source_id is not None:
        q = q.filter(KbDocument.source_id == source_id)
    for (path_rel,) in q.all():
        found, deepest = _folder_paths_below(path_rel, root_folder)
        paths |= found
        if deepest is not None:
            direct[deepest] = direct.get(deepest, 0) + 1
    return paths, direct


# ---------------------------------------------------------------------------
# Domain views
# ---------------------------------------------------------------------------

def domain_tree(db: Session, user_id: int, course_id: int) -> list[dict[str, Any]]:
    """Hierarchical domains for a course (top-level domains with children)."""
    rows = (
        db.query(KbFolder)
        .filter(KbFolder.user_id == user_id, KbFolder.course_id == course_id)
        .order_by(KbFolder.name)
        .all()
    )
    by_parent: dict[int | None, list[KbFolder]] = {}
    for r in rows:
        by_parent.setdefault(r.parent_id, []).append(r)

    def _node(folder: KbFolder) -> dict[str, Any]:
        return {
            **_folder_payload(folder),
            "children": [_node(c) for c in by_parent.get(folder.id, [])],
        }

    return [_node(r) for r in by_parent.get(None, [])]


def list_domains(db: Session, user_id: int) -> list[dict[str, Any]]:
    """Every top-level domain across all courses, with its live document count.

    Audit defect #83: non-study surfaces (the RPG Life-Areas grid, the habit
    tracker) need one flat domain list they can match by name against their own
    areas — no course id required. Only ``depth == 1`` folders (top-level
    domains) are returned so counts stay meaningful.
    """
    rows = (
        db.query(KbFolder)
        .filter(KbFolder.user_id == user_id, KbFolder.depth == 1)
        .order_by(KbFolder.name)
        .all()
    )
    return [
        {
            **_folder_payload(r),
            "course_id": r.course_id,
        }
        for r in rows
    ]


def domain_detail(db: Session, user_id: int, folder_id: int) -> dict[str, Any] | None:
    """A single domain: folder, breadcrumb, documents, subfolders."""
    folder = (
        db.query(KbFolder)
        .filter(KbFolder.id == folder_id, KbFolder.user_id == user_id)
        .first()
    )
    if folder is None:
        return None

    course = None
    if folder.course_id:
        course = db.query(Course).filter(Course.id == folder.course_id).first()

    # Breadcrumb: course → … → this folder (via parent chain).
    breadcrumb: list[dict[str, Any]] = []
    chain: list[KbFolder] = [folder]
    current = folder
    while current.parent_id is not None:
        parent = (
            db.query(KbFolder)
            .filter(KbFolder.id == current.parent_id, KbFolder.user_id == user_id)
            .first()
        )
        if parent is None:
            break
        chain.append(parent)
        current = parent
    for item in reversed(chain):
        breadcrumb.append({"id": item.id, "name": item.name, "path": item.path})

    subfolders = (
        db.query(KbFolder)
        .filter(KbFolder.parent_id == folder.id, KbFolder.user_id == user_id)
        .order_by(KbFolder.name)
        .all()
    )

    return {
        "id": folder.id,
        "name": folder.name,
        "path": folder.path,
        "depth": folder.depth,
        "doc_count": folder.doc_count,
        "description": folder.description,
        "status": folder.status,
        "color": folder.color,
        "course": {"id": course.id, "title": course.title} if course else None,
        "breadcrumb": breadcrumb,
        "documents": folder_documents(db, user_id, folder),
        "subfolders": [_folder_payload(s) for s in subfolders],
    }


def folder_documents(
    db: Session, user_id: int, folder: KbFolder, *, recursive: bool = False
) -> list[dict[str, Any]]:
    """Documents inside a folder — direct children, or recursive when asked."""
    prefix = f"{folder.path}/"
    q = db.query(KbDocument).filter(
        KbDocument.user_id == user_id,
        KbDocument.status != "deleted",
        KbDocument.path_rel.like(f"{prefix}%"),
    )
    if folder.source_id is not None:
        q = q.filter(KbDocument.source_id == folder.source_id)
    docs = q.order_by(KbDocument.title).all()
    out: list[dict[str, Any]] = []
    for doc in docs:
        rel = (doc.path_rel or "")[len(prefix) :]
        if not recursive and "/" in rel:
            continue  # deeper than the folder itself → not a direct child
        out.append(
            {
                "id": doc.id,
                "title": doc.title or doc.path_rel or f"doc {doc.id}",
                "doc_type": doc.doc_type,
                "path_rel": doc.path_rel,
                "char_count": doc.char_count,
                "quality_score": doc.quality_score,
                "reading_time_seconds": doc.reading_time_seconds,
                "author": doc.author,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Domain-scoped Gap Analysis (persisted, save-and-reuse)
# ---------------------------------------------------------------------------

def _domain_heading_names(db: Session, user_id: int, doc_ids: list[int]) -> tuple[list[str], dict[str, int]]:
    """Heading names + heading→document-count hints for a set of documents."""
    from app.services.kb import KbService

    names: list[str] = []
    counts: dict[str, int] = {}
    seen: set[str] = set()
    if not doc_ids:
        return names, counts
    for doc in db.query(KbDocument).filter(KbDocument.id.in_(doc_ids)).all():
        outline = KbService.json_loads(doc.outline_json) or []
        doc_seen: set[str] = set()
        for item in outline:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            norm = text.lower()
            if norm in doc_seen:
                continue
            doc_seen.add(norm)
            counts[text] = counts.get(text, 0) + 1
            if norm not in seen:
                seen.add(norm)
                names.append(text)
    return names, counts


def _domain_concept_names(db: Session, user_id: int, doc_ids: list[int]) -> list[str]:
    """Concept names mentioned (MENTIONS) by the folder's documents."""
    if not doc_ids:
        return []
    rows = (
        db.query(KbEdge.target_concept_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id.in_(doc_ids),
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.isnot(None),
        )
        .distinct()
        .all()
    )
    concept_ids = [r[0] for r in rows]
    if not concept_ids:
        return []
    from app.models import KbConcept

    return [
        c.canonical_name
        for c in db.query(KbConcept)
        .filter(KbConcept.id.in_(concept_ids), KbConcept.user_id == user_id)
        .all()
        if c.canonical_name
    ]


def domain_gaps(db: Session, user_id: int, folder: KbFolder) -> dict[str, Any]:
    """Gap analysis scoped to one folder's documents (recursive).

    Uses the same actionable evidence engine as course gaps — targets come
    from the curated domain catalog (matched by the folder name) plus the
    folder's own headings/mentioned concepts; evidence is scoped to the
    folder's documents only.
    """
    from app.services.kb.gap_engine import analyze_subject

    docs = folder_documents(db, user_id, folder, recursive=True)
    doc_ids = [d["id"] for d in docs]
    topic_names, doc_hints = _domain_heading_names(db, user_id, doc_ids)
    concept_names = _domain_concept_names(db, user_id, doc_ids)

    engine = analyze_subject(
        db,
        user_id,
        title=folder.name,
        doc_ids=doc_ids,
        topic_names=topic_names,
        concept_names=concept_names,
        doc_hints=doc_hints,
    )
    engine["document_count"] = len(docs)
    engine["folder"] = {"id": folder.id, "name": folder.name, "path": folder.path}
    return engine


def load_saved_domain_gaps(db: Session, user_id: int, folder_id: int) -> dict[str, Any] | None:
    """Return a previously saved domain analysis, or None (mirrors course gaps)."""
    saved = (
        db.query(FolderGapAnalysis)
        .filter(
            FolderGapAnalysis.user_id == user_id,
            FolderGapAnalysis.folder_id == folder_id,
        )
        .first()
    )
    if saved is None:
        return None
    payload = normalize_gap_payload(json.loads(saved.payload_json or "{}"))
    payload["cached"] = True
    analyzed = saved.analyzed_at
    if analyzed is not None and analyzed.tzinfo is None:
        analyzed = analyzed.replace(tzinfo=timezone.utc)
    payload["analyzed_at"] = analyzed.isoformat() if analyzed else None
    folder = (
        db.query(KbFolder)
        .filter(KbFolder.id == folder_id, KbFolder.user_id == user_id)
        .first()
    )
    if folder is not None and isinstance(payload.get("document_count"), int):
        payload["new_notes_since_analysis"] = max(
            0, len(folder_documents(db, user_id, folder, recursive=True)) - payload["document_count"]
        )
    return payload


def save_domain_gaps(db: Session, user_id: int, folder_id: int, payload: dict[str, Any]) -> None:
    """Upsert the analysis payload for a user + folder (one row)."""
    row = (
        db.query(FolderGapAnalysis)
        .filter(
            FolderGapAnalysis.user_id == user_id,
            FolderGapAnalysis.folder_id == folder_id,
        )
        .first()
    )
    if row is None:
        row = FolderGapAnalysis(user_id=user_id, folder_id=folder_id)
        db.add(row)
    row.payload_json = json.dumps(payload, default=str)
    row.analyzed_at = (
        datetime.fromisoformat(payload["analyzed_at"])
        if payload.get("analyzed_at")
        else datetime.now(timezone.utc)
    )
    db.commit()


def invalidate_domain_gaps(db: Session, user_id: int, folder_id: int | None = None) -> None:
    """Drop the cached domain analyses (after reindex/resync — data changed).

    Pass ``folder_id`` to drop a single domain's copy; otherwise clears every
    cached domain analysis for the user.
    """
    q = db.query(FolderGapAnalysis).filter(FolderGapAnalysis.user_id == user_id)
    if folder_id is not None:
        q = q.filter(FolderGapAnalysis.folder_id == folder_id)
    q.delete()
    db.commit()
