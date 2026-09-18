"""Course content aggregate (Subject Details page payload).

Resolves the subject's documents, assembles the Second Brain section
(documents, topic tree, domains, unorganized docs, concepts, graph),
and attaches Classroom assignment signals.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Assignment, Course
from app.schemas.course import CourseResponse
from sqlalchemy import func

from app.services.kb.gaps import concept_gaps as _concept_gaps
from app.services.kb.gap_engine import analyze_subject as _analyze_subject
from app.services.course_content_topics import (
    _course_folder_data,
    course_graph,
    _folder_segments,
    _heading_doc_counts,
    _heading_names,
    _topic_coverage_gaps,
    TOPIC_GAP_THRESHOLD,
    build_topic_tree,
    course_concepts,
    course_documents,
    course_document_count,
    resolve_course_document_ids,
)


def course_gaps(db, user_id: int, course: Course) -> dict[str, Any]:
    """Gap analysis for the subject — kept as a re-export for router + test call sites.

    Delegates to the gap pipeline defined in ``course_content_topics`` so the
    Subject Details page gets a single combined payload (topic gaps, concept
gaps, actionable engine output, Classroom assignment signals).
    """
    from app.services.kb.gaps import concept_gaps as _concept_gaps
    from app.services.kb.gap_engine import analyze_subject as _analyze_subject

    folder_root = course.kb_folder_path if course.source_type == "kb_folder" else None
    folder_data = None
    if folder_root is None:
        folder_data = _course_folder_data(db, user_id, course.title)
        roots = folder_data[0]
        folder_root = roots[0] if roots else None

    documents = course_documents(db, user_id, course, folder_data=folder_data)
    doc_ids = [d["id"] for d in documents]

    topic_gaps = _topic_coverage_gaps(documents, folder_root=folder_root)

    from app.models import KbConcept, KbDocument, KbDocumentTag, KbEdge, KbTag

    concept_ids: set = set()
    if doc_ids:
        concept_ids = {
            r[0]
            for r in db.query(KbEdge.target_concept_id)
            .filter(
                KbEdge.user_id == user_id,
                KbEdge.source_document_id.in_(doc_ids),
                KbEdge.relation == "MENTIONS",
                KbEdge.target_type == "concept",
                KbEdge.target_concept_id.isnot(None),
            )
            .all()
        }

    concepts = _concept_gaps(
        db, user_id, limit=20, concept_ids=concept_ids
    )

    mentioned_names = [c["concept"] for c in concepts]
    engine = _analyze_subject(
        db,
        user_id,
        title=course.title,
        doc_ids=doc_ids,
        topic_names=_heading_names(documents, folder_root=folder_root),
        concept_names=mentioned_names,
        doc_hints=_heading_doc_counts(documents, folder_root=folder_root),
    )

    from app.models import Assignment

    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course.id)
        .order_by(Assignment.due_date)
        .all()
    )
    classroom_items = [
        {
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "due_date": a.due_date.isoformat() if a.due_date else None,
        }
        for a in assignments
    ]

    return {
        "topics": topic_gaps,
        "concepts": concepts,
        "classroom": {
            "assignments": classroom_items,
            "total": len(assignments),
            "pending": sum(1 for a in assignments if a.status != "Completed"),
        },
        "threshold": TOPIC_GAP_THRESHOLD,
        "document_count": len(documents),
        "summary": engine.get("summary"),
        "strengths": engine.get("strengths"),
        "gaps": engine.get("gaps"),
        "path": engine.get("path"),
        "next": engine.get("next"),
        "domain": engine.get("domain"),
        "coverage": engine.get("coverage"),
    }


def _is_organized(doc: dict[str, Any], folder_root: str | None) -> bool:
    """True when the document lands in at least one topic.

    A document is organized when it has an outline (heading topics) or, for
    folder subjects, sits under a nested folder (folder topics).
    """
    if doc.get("outline"):
        return True
    rel = doc.get("path_rel") or ""
    # For folder subjects, a document is organized when it lives under a nested
    # sub-folder (not directly in the subject root). "Operating Systems/flat.md"
    # (root, no heading) is unorganized; "Operating Systems/Memory/note.md" is
    # organized by the folder topic "Memory".
    if folder_root and rel:
        rel_stripped = rel.strip("/")
        prefix = folder_root.strip("/")
        # Under the root folder but not directly in it → organized by folder topic.
        if rel_stripped.startswith(prefix + "/") and "/" in rel_stripped[len(prefix)+1:]:
            return True
    return False


def course_content(db: Session, user_id: int, course: Course) -> dict[str, Any]:
    """Aggregate payload for the Subject Details page."""
    # Folder-derived subjects reflect their vault structure in the topic tree:
    # nested folders below the subject root become topics/subtopics. A
    # tag-derived (or manual) subject whose title matches a vault folder gets
    # the same treatment -- its nested domain subfolders surface as topics.
    folder_root = course.kb_folder_path if course.source_type == "kb_folder" else None
    folder_data = None
    if folder_root is None:
        folder_data = _course_folder_data(db, user_id, course.title)
        roots = folder_data[0]
        folder_root = roots[0] if roots else None

    documents = course_documents(db, user_id, course, folder_data=folder_data)
    doc_ids = [d["id"] for d in documents]

    # Canonical folder-hierarchy domains (the Second Brain folder tree below
    # the course root). Folders determine organization -- the UI shows these
    # domains first, then the heading-derived topic tree below them.
    from app.services.kb.domain_service import domain_tree, sync_all_folders

    domains: list[dict[str, Any]] = []
    try:
        domains = domain_tree(db, user_id, course.id)
        if not domains and (course.source_type == "kb_folder" or folder_root):
            # First view after an upgrade: ensure canonical folder rows exist.
            sync_all_folders(db, user_id)
            domains = domain_tree(db, user_id, course.id)
    except Exception:  # noqa: BLE001 -- domains are additive; never break content
        domains = []

    return {
        "course": CourseResponse.model_validate(course).model_dump(),
        "second_brain": {
            "documents": documents,
            "topics": build_topic_tree(documents, folder_root=folder_root),
            "domains": domains,
            "unorganized_documents": [
                d for d in documents if not _is_organized(d, folder_root=folder_root)
            ],
            "concepts": course_concepts(db, user_id, doc_ids),
            "graph": course_graph(db, user_id, course, doc_ids=doc_ids),
            "document_count": len(documents),
        },
        "classroom": {
            "linked": course.source_type == "classroom",
            "google_id": course.google_id,
            "course_url": course.classroom_url,
            "assignments": [
                {
                    "id": a.id,
                    "title": a.title,
                    "description": a.description,
                    "status": a.status,
                    "due_date": a.due_date.isoformat() if a.due_date else None,
                }
                for a in db.query(Assignment).filter(Assignment.course_id == course.id).order_by(Assignment.due_date).all()
            ],
            "total_assignments": course_document_count(db, user_id, course),
        },
    }
