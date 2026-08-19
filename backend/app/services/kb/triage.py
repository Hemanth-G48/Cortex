"""Workflow glue — new-note triage queue.

When the folder watcher or the manual "update from folder" action ingests new
files, they land in the vault with no course link. This queue gives the user a
single place to triage them:

- ``queue`` — recent documents that have never been triaged (no
  ``triage/done`` rule tag), each with auto-detected subjects (reusing the
  Phase 9 auto-subject detector) and any pending folder-move proposals.
- ``apply_subjects`` — accept the detected subjects: attach ``course:X`` tags
  (which triggers course derivation, so the note surfaces under a course) and
  mark the doc as triaged.
- ``dismiss`` — mark the doc as triaged without tagging (it stays in the
  vault but leaves the queue).
- ``manual_tag`` — apply a specific tag name to a queued document.

Deterministic — the subject detection is rule/regex based (no LLM cost).
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CategorizeSuggestion, KbDocument, KbDocumentTag, KbTag
from app.services.kb import utcnow
from app.services.kb.auto_subject_detect import detect_subjects_from_document
from app.services.kb.tagger import create_document_tag

# Rule-tag name marking a document as already triaged (never re-queued).
TRIAGE_DONE_TAG = "triage/done"
# How far back "new" documents go (created within this window, newest first).
TRIAGE_WINDOW_DAYS = 30


def _has_triage_done(db: Session, user_id: int, doc_id: int) -> bool:
    return (
        db.query(KbDocumentTag.id)
        .join(KbTag, KbTag.id == KbDocumentTag.tag_id)
        .filter(
            KbDocumentTag.document_id == doc_id,
            KbDocumentTag.user_id == user_id,
            KbTag.name == TRIAGE_DONE_TAG,
        )
        .first()
        is not None
    )


def _resolve_triage_tag(db: Session, user_id: int) -> KbTag:
    """Fetch (or create) the single ``triage/done`` rule tag for a user."""
    tag = (
        db.query(KbTag)
        .filter(KbTag.user_id == user_id, KbTag.name == TRIAGE_DONE_TAG)
        .first()
    )
    if tag is None:
        tag = KbTag(user_id=user_id, name=TRIAGE_DONE_TAG, kind="rule")
        db.add(tag)
        db.flush()
    return tag


def _mark_triage_done(db: Session, doc: KbDocument, tag: KbTag | None = None) -> None:
    """Attach the ``triage/done`` rule tag (idempotent).

    ``tag`` may be passed in when the caller already resolved it (bulk paths)
    so we don't re-query it once per document.
    """
    if tag is None:
        tag = _resolve_triage_tag(db, doc.user_id)
    exists = (
        db.query(KbDocumentTag.id)
        .filter(
            KbDocumentTag.document_id == doc.id,
            KbDocumentTag.user_id == doc.user_id,
            KbDocumentTag.tag_id == tag.id,
        )
        .first()
    )
    if exists is None:
        db.add(
            KbDocumentTag(
                user_id=doc.user_id,
                document_id=doc.id,
                tag_id=tag.id,
                provenance="rule",
            )
        )
        db.flush()


def _doc_tags(db: Session, user_id: int, doc_id: int) -> list[str]:
    rows = (
        db.query(KbTag.name)
        .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
        .filter(KbDocumentTag.document_id == doc_id, KbDocumentTag.user_id == user_id)
        .order_by(KbTag.name)
        .all()
    )
    return [name for (name,) in rows]


def _pending_categorize(db: Session, user_id: int, doc_id: int) -> dict | None:
    proposal = (
        db.query(CategorizeSuggestion)
        .filter(
            CategorizeSuggestion.document_id == doc_id,
            CategorizeSuggestion.user_id == user_id,
            CategorizeSuggestion.status == "pending",
        )
        .first()
    )
    if proposal is None:
        return None
    return {
        "id": proposal.id,
        "proposed_path": proposal.proposed_path,
        "rule": proposal.rule,
    }


def _item(db: Session, doc: KbDocument) -> dict:
    return {
        "id": doc.id,
        "title": doc.title or doc.path_rel or f"doc {doc.id}",
        "path_rel": doc.path_rel,
        "doc_type": doc.doc_type,
        "status": doc.status,
        "char_count": doc.char_count,
        "quality_score": doc.quality_score,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "detected_subjects": detect_subjects_from_document(doc),
        "tags": _doc_tags(db, doc.user_id, doc.id),
        "categorize": _pending_categorize(db, doc.user_id, doc.id),
    }


def _triaged_ids(db: Session, user_id: int, since: datetime) -> set[int]:
    """Document ids marked ``triage/done`` within the given time window."""
    rows = (
        db.query(KbDocumentTag.document_id)
        .join(KbTag, KbTag.id == KbDocumentTag.tag_id)
        .join(KbDocument, KbDocument.id == KbDocumentTag.document_id)
        .filter(
            KbDocumentTag.user_id == user_id,
            KbTag.name == TRIAGE_DONE_TAG,
            KbDocument.created_at >= since,
        )
        .all()
    )
    return {doc_id for (doc_id,) in rows}


def _untriaged_docs(
    db: Session, user_id: int, limit: int, window_days: int
) -> list[KbDocument]:
    """Untriaged documents from the ingestion window, newest first (shared by
    ``queue`` and the bulk accept/dismiss paths).

    Uses a SQL anti-join (NOT EXISTS on ``triage/done``) rather than an
    oversample-then-filter: with thousands of notes, the newest ``limit*2``
    rows can all already be triaged while untriaged ones sit further back —
    the oversample would silently return nothing and stall bulk cleanup.
    """
    since = utcnow() - timedelta(days=window_days)
    triaged = (
        db.query(KbDocumentTag.document_id)
        .join(KbTag, KbTag.id == KbDocumentTag.tag_id)
        .filter(KbDocumentTag.user_id == user_id, KbTag.name == TRIAGE_DONE_TAG)
        .subquery()
    )
    return (
        db.query(KbDocument)
        .outerjoin(triaged, KbDocument.id == triaged.c.document_id)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status.in_(("new", "changed", "unchanged", "draft")),
            KbDocument.created_at >= since,
            triaged.c.document_id.is_(None),
        )
        .order_by(KbDocument.created_at.desc(), KbDocument.id.desc())
        .limit(limit)
        .all()
    )


def queue(db: Session, user_id: int, limit: int = 50, window_days: int = TRIAGE_WINDOW_DAYS) -> list[dict]:
    """Untriaged documents from the recent ingestion window, newest first."""
    docs = _untriaged_docs(db, user_id, limit, window_days)
    return [_item(db, d) for d in docs]


def apply_subjects(db: Session, user_id: int, document_id: int) -> dict:
    """Accept the detected subjects: ``course:X`` tags + triage/done."""
    doc = _doc_or_404(db, user_id, document_id)
    subjects = detect_subjects_from_document(doc)
    applied = 0
    for subject in subjects:
        name = f"{settings.COURSE_TAG_PREFIX}{subject}"
        _, count = create_document_tag(db, doc, name)
        applied += count
    _mark_triage_done(db, doc)
    db.flush()
    # A `course:` tag may now identify a course — refresh derivation.
    if subjects:
        try:
            from app.services.course_derivation import derive_courses_from_tags

            derive_courses_from_tags(db, user_id)
        except Exception:  # noqa: BLE001 — tagging must still succeed
            pass
    return {"ok": True, "subjects_applied": applied, "subjects": subjects}


def manual_tag(db: Session, user_id: int, document_id: int, name: str) -> dict:
    """Attach a specific tag (e.g. ``course:Cybersecurity``) + triage/done."""
    doc = _doc_or_404(db, user_id, document_id)
    name = (name or "").strip()
    if not name:
        return {"ok": False, "error": "Tag name is empty"}
    _, applied = create_document_tag(db, doc, name)
    _mark_triage_done(db, doc)
    db.flush()
    if name.startswith(settings.COURSE_TAG_PREFIX):
        try:
            from app.services.course_derivation import derive_courses_from_tags

            derive_courses_from_tags(db, user_id)
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "applied": applied}


def dismiss(db: Session, user_id: int, document_id: int) -> dict:
    """Mark a document as triaged without tagging it."""
    doc = _doc_or_404(db, user_id, document_id)
    _mark_triage_done(db, doc)
    db.flush()
    return {"ok": True}


def accept_all_subjects(
    db: Session,
    user_id: int,
    limit: int = 200,
    window_days: int = TRIAGE_WINDOW_DAYS,
) -> dict:
    """Bulk accept: apply the detected subjects of every untriaged doc in the
    window (up to ``limit``) and mark those docs triaged.

    Docs with no detected subjects are **left in the queue** (they need a
    manual tag or a dismiss). Returns counts so the caller can loop until
    ``remaining_pending`` reaches the number of subject-less docs.
    """
    docs = _untriaged_docs(db, user_id, limit, window_days)
    if not docs:
        return {
            "ok": True,
            "processed": 0,
            "accepted": 0,
            "skipped_no_subjects": 0,
            "subjects_applied": 0,
            "remaining_pending": triage_stats(db, user_id, window_days)["pending"],
        }
    tag = _resolve_triage_tag(db, user_id)
    processed = accepted = skipped = applied = 0
    for doc in docs:
        processed += 1
        subjects = detect_subjects_from_document(doc)
        if not subjects:
            skipped += 1
            continue
        for subject in subjects:
            name = f"{settings.COURSE_TAG_PREFIX}{subject}"
            _, count = create_document_tag(db, doc, name)
            applied += count
        _mark_triage_done(db, doc, tag=tag)
        accepted += 1
    db.flush()
    if accepted:
        try:
            from app.services.course_derivation import derive_courses_from_tags

            derive_courses_from_tags(db, user_id)
        except Exception:  # noqa: BLE001 — tagging must still succeed
            pass
    return {
        "ok": True,
        "processed": processed,
        "accepted": accepted,
        "skipped_no_subjects": skipped,
        "subjects_applied": applied,
        "remaining_pending": triage_stats(db, user_id, window_days)["pending"],
    }


def dismiss_all(
    db: Session,
    user_id: int,
    limit: int = 200,
    window_days: int = TRIAGE_WINDOW_DAYS,
) -> dict:
    """Bulk dismiss: mark every untriaged doc in the window (up to ``limit``)
    as triaged without tagging, so it leaves the queue."""
    docs = _untriaged_docs(db, user_id, limit, window_days)
    if not docs:
        return {
            "ok": True,
            "dismissed": 0,
            "remaining_pending": triage_stats(db, user_id, window_days)["pending"],
        }
    tag = _resolve_triage_tag(db, user_id)
    for doc in docs:
        _mark_triage_done(db, doc, tag=tag)
    db.flush()
    return {
        "ok": True,
        "dismissed": len(docs),
        "remaining_pending": triage_stats(db, user_id, window_days)["pending"],
    }


def _doc_or_404(db: Session, user_id: int, document_id: int) -> KbDocument:
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        from fastapi import HTTPException

        raise HTTPException(404, "Document not found")
    return doc


def triage_stats(db: Session, user_id: int, window_days: int = TRIAGE_WINDOW_DAYS) -> dict:
    """Quick counts for the queue header (pending / total / window).

    Both ``total`` and ``triaged`` are scoped to the same window so
    ``pending`` never undercounts from old triaged docs.
    """
    since = utcnow() - timedelta(days=window_days)
    total = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status.in_(("new", "changed", "unchanged", "draft")),
            KbDocument.created_at >= since,
        )
        .count()
    )
    done = len(_triaged_ids(db, user_id, since))
    return {
        "pending": max(0, total - done),
        "total_in_window": total,
        "triaged": done,
        "window_days": window_days,
    }
