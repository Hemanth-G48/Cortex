"""Subject topic-tree assembly from document outlines.

Builds the nested topic/subtopic tree shown on the Subject Details page,
computes topic coverage gaps, and resolves which documents belong to a
course (folder path, tag, or legacy fuzzy tag-name match).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Assignment, Course, KbConcept, KbDocument, KbDocumentTag, KbEdge, KbTag
from app.services.course_derivation import FOLDER_DERIVATION_IGNORE, _folder_key, _folder_title
from app.services.kb import KbService

# Topics whose coverage (fraction of outlined docs mentioning the heading)
# falls below this are flagged as knowledge gaps.
TOPIC_GAP_THRESHOLD = 0.5
# How many related concepts / concept gaps to return.
MAX_CONCEPTS = 40
MAX_CONCEPT_GAPS = 20

_WS_RE = re.compile(r"\s+")


def _normalize_heading(text: str) -> str:
    """Lowercase + collapse whitespace so headings merge across documents."""
    return _WS_RE.sub(" ", text.strip().lower()).strip(" .:-\"")


def _doc_payload(doc: KbDocument) -> dict[str, Any]:
    """Document payload with outline + metadata for the UI.

    ``outline_json`` / ``metadata_json`` are stored JSON text; parse them here
    (the model exposes no ``outline``/``metadata`` attributes).
    """
    outline = KbService.json_loads(doc.outline_json) or []
    metadata = KbService.json_loads(doc.metadata_json) or {}
    return {
        "id": doc.id,
        "title": doc.title or "Untitled",
        "doc_type": doc.doc_type,
        "path_rel": doc.path_rel,
        "char_count": doc.char_count,
        "outline": outline,
        "tags": metadata.get("tags", []) if isinstance(metadata, dict) else [],
        "wikilinks": metadata.get("wikilinks", []) if isinstance(metadata, dict) else [],
        "quality_score": doc.quality_score,
        "reading_time_seconds": doc.reading_time_seconds,
        "author": doc.author,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def _course_folder_data(db: Session, user_id: int, course_title: str) -> tuple[list[str], set[int]]:
    """Top-level vault folders matching a course title, plus their documents.

    The tag->course derivation suppresses a folder course when a ``course:*``
    tag already owns the title (explicit tags win over folder derivation), so
    a tag-derived course would otherwise miss every document that lives in the
    matching vault folder -- including notes in nested domain subfolders. This
    resolves that association directly from ``path_rel`` using the same
    first-meaningful-segment rule as the derivation itself.

    Returns ``(roots, doc_ids)`` where ``roots`` are the RAW folder segments
    (e.g. ``["cybersecurity"]`` -- usable as a topic-tree folder root, since
    ``_folder_segments`` prefix-matches raw paths) and ``doc_ids`` are the ids
    of every non-deleted document under one of them (nested subfolders
    included). ``roots`` is deterministic; ``doc_ids`` is empty when no folder
    matches the title.
    """
    target = course_title.casefold()
    roots: list[str] = []
    seen: set[str] = set()
    doc_ids: set[int] = set()
    rows = (
        db.query(KbDocument.id, KbDocument.path_rel)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .all()
    )
    for doc_id, path_rel in rows:
        key = _folder_key(None, path_rel)
        if key is None:
            continue
        raw_root = key[1]
        if _folder_title(raw_root).casefold() != target:
            continue
        doc_ids.add(doc_id)
        norm = raw_root.casefold()
        if norm not in seen:
            seen.add(norm)
            roots.append(raw_root)
    return roots, doc_ids


def resolve_course_document_ids(
    db: Session,
    user_id: int,
    course: Course,
    *,
    folder_data: tuple[list[str], set[int]] | None = None,
) -> set[int]:
    """Set of KB document ids linked to this course.

    Resolution order:
    1. ``Course.kb_source_id`` + ``kb_folder_path`` → documents under the
       top-level vault folder the subject was derived from.
    2. ``Course.kb_tag_id`` → documents tagged with that tag, UNION documents
       under a top-level vault folder whose name matches the course title
       (nested subfolders included) -- the tag and the folder are two views of
       the same subject, so both contribute.
    3. Fallback: ``course:<title>``-style tag name match (same union).

    ``folder_data`` may be passed in (computed once by ``course_content`` /
    ``course_gaps``) to avoid re-scanning the user's documents.
    """
    if course.source_type == "kb_folder" and course.kb_source_id and course.kb_folder_path:
        return {
            r[0]
            for r in db.query(KbDocument.id)
            .filter(
                KbDocument.user_id == user_id,
                KbDocument.source_id == course.kb_source_id,
                KbDocument.path_rel.like(f"{course.kb_folder_path}/%"),
                KbDocument.status != "deleted",
            )
            .all()
        }

    if folder_data is None:
        folder_data = _course_folder_data(db, user_id, course.title)
    doc_ids: set[int] = set(folder_data[1])

    if course.kb_tag_id:
        doc_ids.update(
            r[0]
            for r in db.query(KbDocumentTag.document_id)
            .filter(
                KbDocumentTag.user_id == user_id,
                KbDocumentTag.tag_id == course.kb_tag_id,
            )
            .all()
        )
    else:
        # Legacy fallback: fuzzy ``course:<title>`` tag-name match.
        course_name = course.title.lower()
        matching_tags = (
            db.query(KbTag)
            .filter(KbTag.user_id == user_id, KbTag.name.like(f"course:%{course_name}%"))
            .all()
        )
        if matching_tags:
            tag_ids = [t.id for t in matching_tags]
            doc_ids.update(
                r[0]
                for r in db.query(KbDocumentTag.document_id)
                .filter(KbDocumentTag.tag_id.in_(tag_ids))
                .distinct()
                .all()
            )
    return doc_ids


def course_documents(
    db: Session,
    user_id: int,
    course: Course,
    *,
    folder_data: tuple[list[str], set[int]] | None = None,
) -> list[dict[str, Any]]:
    """Return the Second Brain documents linked to this course (as payloads).

    Mirrors ``resolve_course_document_ids`` and additionally fetches the
    ``_doc_payload`` for each matched document.
    """
    doc_ids = resolve_course_document_ids(db, user_id, course, folder_data=folder_data)
    if not doc_ids:
        return []
    docs = db.query(KbDocument).filter(KbDocument.id.in_(doc_ids)).all()
    return [_doc_payload(doc) for doc in docs]


def course_document_count(db: Session, user_id: int, course: Course) -> int:
    """Count of Second Brain documents linked to this course (no payloads).

    Mirrors ``resolve_course_document_ids`` exactly -- folder path, ``kb_tag_id``
    tag (unioned with docs under a matching vault folder), or ``course:<title>``
    tag-name fallback -- so the count always matches ``len(course_documents(...))``.
    Used for the "new notes since analysis" staleness check on cached gap
    analyses (avoids parsing every outline).
    """
    return len(resolve_course_document_ids(db, user_id, course))


def _folder_segments(path_rel: str | None, folder_root: str) -> list[str]:
    """Folder segments of a document below the subject's root folder.

    ``Operating Systems/Memory/01.md`` under root ``Operating Systems`` ->
    ``["Memory"]``. Generic containers (``notes``, ``attachments``, …) and
    dot/1-char names are skipped so they never become topics, mirroring the
    top-level derivation (``FOLDER_DERIVATION_IGNORE``).
    """
    rel = (path_rel or "").strip("/")
    prefix = folder_root.strip("/")
    if not rel.startswith(prefix + "/"):
        return []
    parts = rel[len(prefix) + 1 :].split("/")
    segments: list[str] = []
    for part in parts[:-1]:  # everything but the final filename segment
        s = part.strip()
        if not s or len(s) < 2 or s.startswith("."):
            continue
        if s.lower() in FOLDER_DERIVATION_IGNORE:
            continue
        segments.append(s)
    return segments


def _foldered_outline(doc: dict[str, Any], folder_root: str) -> list[dict[str, Any]]:
    """Prepend a document's folder segments to its outline as leading topics.

    ``Operating Systems/Memory/01.md`` with heading "Paging" becomes the
    outline ``[Memory (level 1), Paging (level 2), …]`` so the folder appears
    as a topic and the heading nests beneath it. Documents directly in the
    subject root (no subfolders) keep their outline unchanged.
    """
    segments = _folder_segments(doc.get("path_rel"), folder_root)
    outline = doc.get("outline") or []
    if not segments:
        return outline
    depth = len(segments)
    prepend = [
        {"level": i + 1, "text": _folder_title(seg), "char_start": 0, "origin": "folder"}
        for i, seg in enumerate(segments)
    ]
    shifted = [
        {**item, "level": max(1, int(item.get("level") or 1)) + depth}
        for item in outline
    ]
    return prepend + shifted


def build_topic_tree(
    documents: list[dict[str, Any]],
    *,
    folder_root: str | None = None,
) -> list[dict[str, Any]]:
    """Build a nested topic tree from document outlines, merging by heading.

    Each document's outline is a flat ``[{level, text, char_start}, ...]`` list
    where level 1 is a top-level topic and deeper levels are subtopics. The
    tree is merged across all of the subject's documents by normalized heading
    text, and every topic carries the documents that actually contain that
    heading -- so the UI can show the documents *under* their topic.

    For folder-derived subjects, ``folder_root`` is the subject's top-level
    vault folder: each document's nested folders below it are prepended as
    leading topics (``Memory/Virtual Memory/01.md`` -> "Memory" -> "Virtual
    Memory" -> headings), so the vault structure is reflected in the topic
    tree and documents without headings still appear under their folder.

    Every node carries ``origin``: ``"folder"`` when the topic is a vault
    folder under the subject (so the UI can show a folder path breadcrumb),
    ``"heading"`` when built from document headings. A topic that exists as
    both a root heading and a folder resolves to ``"folder"`` -- the folder
    reading wins.

    Documents that end up in no topic (no outline AND no folder segments)
    are excluded here -- they surface in the ``unorganized_documents`` bucket.
    """
    roots: list[dict[str, Any]] = []
    counter = 0

    def _node(
        container: list[dict[str, Any]], name: str, level: int, origin: str = "heading"
    ) -> dict[str, Any]:
        nonlocal counter
        node = {
            "id": f"t{counter}",
            "name": name,
            "level": level,
            "origin": origin,
            "documents": [],
            "children": [],
        }
        counter += 1
        container.append(node)
        return node

    for doc in documents:
        outline = (
            _foldered_outline(doc, folder_root) if folder_root else (doc.get("outline") or [])
        )
        stack: list[tuple[list[dict[str, Any]], int]] = [(roots, 0)]
        for item in outline:
            level = max(1, int(item.get("level") or 1))
            name = (item.get("text") or "").strip()
            if not name or not _normalize_heading(name):
                continue
            while stack and stack[-1][1] >= level:
                stack.pop()
            container = stack[-1][0] if stack else roots

            norm = _normalize_heading(name)
            origin = item.get("origin", "heading")
            node = next(
                (n for n in container if _normalize_heading(n["name"]) == norm),
                None,
            )
            if node is None:
                node = _node(container, name, level, origin=origin)
            elif origin == "folder":
                node["origin"] = "folder"

            node["documents"].append(doc)
            stack.append((node["children"], level))

    def _sort(nodes: list[dict[str, Any]]) -> None:
        nodes.sort(key=lambda n: _normalize_heading(n["name"]))
        for n in nodes:
            seen: set[int] = set()
            unique = []
            for d in n["documents"]:
                if d["id"] not in seen:
                    seen.add(d["id"])
                    unique.append(d)
            n["documents"] = unique
            _sort(n["children"])

    _sort(roots)
    return roots


def _effective_outline(
    doc: dict[str, Any], folder_root: str | None
) -> list[dict[str, Any]]:
    """The outline used for topic/coverage purposes.

    For folder-derived subjects the document's folder segments are prepended
    (via ``_foldered_outline``), so vault folders surface as topics exactly as
    they do in the topic tree; otherwise the raw stored outline is used.
    """
    if folder_root:
        return _foldered_outline(doc, folder_root)
    return doc.get("outline") or []


def _topic_coverage_gaps(
    documents: list[dict[str, Any]], *, folder_root: str | None = None
) -> list[dict[str, Any]]:
    """Topics whose coverage is below the threshold (thin materials).

    ``folder_root`` (folder-derived subjects) includes the vault's nested
    folders as topics -- mirroring ``build_topic_tree`` -- so folder topics
    surface as knowledge targets with coverage equal to the share of subject
    documents inside them. A document counts toward a topic when its effective
    outline (folders prepended) mentions it, matching the topic tree exactly.
    Heading topics are measured against the SAME denominator (all organized
    docs: folder-nested docs included), so a heading in 1 of many folder docs
    is thin -- the same rule folders get.
    """
    outlined = [d for d in documents if _effective_outline(d, folder_root)]
    total = len(outlined)
    if total == 0:
        return []

    heading_counts: Counter[str] = Counter()
    first_spelling: dict[str, str] = {}
    for doc in outlined:
        seen: set[str] = set()
        for item in _effective_outline(doc, folder_root):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            norm = _normalize_heading(text)
            if norm in seen:
                continue
            seen.add(norm)
            heading_counts[norm] += 1
            first_spelling.setdefault(norm, text)

    gaps = []
    for norm, count in heading_counts.items():
        coverage = count / total
        gaps.append(
            {
                "topic": first_spelling.get(norm, norm),
                "normalized": norm,
                "coverage": round(coverage, 4),
                "documents": count,
                "is_gap": coverage < TOPIC_GAP_THRESHOLD,
            }
        )
    gaps.sort(key=lambda g: g["coverage"])
    return gaps


def _heading_names(
    documents: list[dict[str, Any]], *, folder_root: str | None = None
) -> list[str]:
    """Unique topic texts across the subject's documents (topic targets).

    Includes folder-derived topics when ``folder_root`` is given, so the
    actionable engine also treats vault folders as knowledge targets.
    """
    seen: set[str] = set()
    names: list[str] = []
    for doc in documents:
        for item in _effective_outline(doc, folder_root):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            norm = _normalize_heading(text)
            if norm in seen:
                continue
            seen.add(norm)
            names.append(text)
    return names


def _heading_doc_counts(
    documents: list[dict[str, Any]], *, folder_root: str | None = None
) -> dict[str, int]:
    """topic text -> number of subject documents whose outline contains it.

    Used by the gap engine as *document-presence* evidence for subject topics
    (a heading or vault folder in the user's notes is weak evidence of
    familiarity -- never more, since it isn't a worked example or explanation).
    """
    counts: dict[str, int] = {}
    for doc in documents:
        seen: set[str] = set()
        for item in _effective_outline(doc, folder_root):
            text = (item.get("text") or "").strip()
            if not text:
                continue
            norm = _normalize_heading(text)
            if norm in seen:
                continue
            seen.add(norm)
            counts[text] = counts.get(text, 0) + 1
    return counts


def course_concepts(
    db: Session, user_id: int, doc_ids: list[int], limit: int = MAX_CONCEPTS
) -> list[dict[str, Any]]:
    """Concepts mentioned by the subject's documents, ranked by frequency.

    Each entry carries the mention count, the number of source documents, and
    up to 3 suggested capture sources (documents that mention the concept).
    The source documents are fetched in a single batched query.
    """
    if not doc_ids:
        return []

    rows = (
        db.query(
            KbEdge.target_concept_id,
            func.count(KbEdge.id),
            func.count(func.distinct(KbEdge.source_document_id)),
        )
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id.in_(doc_ids),
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.isnot(None),
        )
        .group_by(KbEdge.target_concept_id)
        .order_by(func.count(KbEdge.id).desc())
        .limit(limit)
        .all()
    )
    if not rows:
        return []

    concept_ids = [r[0] for r in rows]
    concepts = {
        c.id: c
        for c in db.query(KbConcept)
        .filter(KbConcept.id.in_(concept_ids), KbConcept.user_id == user_id)
        .all()
    }

    # One batched query for all source documents, then group + slice per concept.
    source_rows = (
        db.query(
            KbEdge.target_concept_id,
            KbDocument.id,
            KbDocument.title,
            KbDocument.path_rel,
        )
        .join(KbDocument, KbEdge.source_document_id == KbDocument.id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.target_concept_id.in_(concept_ids),
            KbEdge.relation == "MENTIONS",
        )
        .order_by(KbDocument.title)
        .all()
    )
    sources_by_concept: dict[int, list[dict[str, Any]]] = {}
    for concept_id, doc_id, title, path_rel in source_rows:
        sources_by_concept.setdefault(concept_id, []).append(
            {"document_id": doc_id, "title": title or path_rel or f"doc {doc_id}"}
        )

    out: list[dict[str, Any]] = []
    for concept_id, mentions, doc_count in rows:
        concept = concepts.get(concept_id)
        if concept is None:
            continue
        out.append(
            {
                "concept_id": concept.id,
                "name": concept.canonical_name,
                "definition": concept.definition,
                "mentions": mentions,
                "document_count": doc_count,
                "sources": (sources_by_concept.get(concept_id) or [])[:3],
            }
        )
    return out


def course_graph(
    db: Session,
    user_id: int,
    course: Course,
    limit: int = 120,
    doc_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Subject-scoped knowledge graph (nodes + edges touching its documents).

    ``doc_ids`` may be passed in to avoid re-resolving the documents when the
    caller (``course_content``) already fetched them.
    """
    if doc_ids is None:
        doc_ids = [d["id"] for d in course_documents(db, user_id, course)]
    if not doc_ids:
        return {
            "nodes": [],
            "edges": [],
            "truncated": False,
            "total_nodes": 0,
            "total_edges": 0,
        }
    from app.services.kb.graph import build_graph

    return build_graph(db, user_id, doc_ids=set(doc_ids), limit=limit)
