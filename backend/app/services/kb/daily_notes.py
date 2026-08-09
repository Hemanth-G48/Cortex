"""Daily-note integration (Phase 4, Idea 35).

- ``tag_daily_note`` — auto-tag ``YYYY-MM-DD.md`` vault docs with a
  ``daily/YYYY-MM-DD`` rule tag at ingest (phrase 42).
- ``get_daily_notes`` — aggregate a day's vault captures + schedule blocks +
  journal entries (phrases 43–44).
- ``get_today`` — convenience wrapper using the server date (phrase 45).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    DailyScheduleItem,
    JournalEntry,
    KbDocument,
    KbDocumentTag,
    KbTag,
)

# The ``kind`` stored on the auto-created KbTag (rules survive re-tagging).
_DAILY_KIND = "rule"


def tag_daily_note(db: Session, doc: KbDocument) -> bool:
    """Attach a ``daily/YYYY-MM-DD`` tag to a daily-note document (phrase 42).

    Idempotent and cheap — no AI. Returns True when the tag was created.
    """
    if doc.doc_type != "md" or doc.doc_date is None:
        return False
    name = f"daily/{doc.doc_date.isoformat()}"
    tag = (
        db.query(KbTag)
        .filter(KbTag.user_id == doc.user_id, KbTag.name == name)
        .first()
    )
    if tag is None:
        tag = KbTag(user_id=doc.user_id, name=name, kind=_DAILY_KIND)
        db.add(tag)
        db.flush()
    exists = (
        db.query(KbDocumentTag)
        .filter(
            KbDocumentTag.user_id == doc.user_id,
            KbDocumentTag.document_id == doc.id,
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
        return True
    return False


def get_daily_notes(
    db: Session, user_id: int, day: date
) -> dict:
    """Aggregate one day's vault documents, schedule blocks, and journal entries."""
    docs = (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.doc_date == day)
        .order_by(KbDocument.id.asc())
        .all()
    )
    schedule = (
        db.query(DailyScheduleItem)
        .filter(DailyScheduleItem.user_id == user_id, DailyScheduleItem.date == day)
        .order_by(DailyScheduleItem.time_range.asc())
        .all()
    )
    journal = (
        db.query(JournalEntry)
        .filter(JournalEntry.user_id == user_id, JournalEntry.date == day)
        .order_by(JournalEntry.id.asc())
        .all()
    )
    return {
        "date": day.isoformat(),
        "documents": [
            {
                "id": d.id,
                "title": d.title or d.path_rel or f"doc {d.id}",
                "doc_type": d.doc_type,
                "char_count": d.char_count,
                "reading_time_seconds": d.reading_time_seconds,
                "quality_score": d.quality_score,
            }
            for d in docs
        ],
        "schedule": [
            {
                "id": s.id,
                "time_range": s.time_range,
                "activity": s.activity,
                "category": s.category,
                "done": s.done,
            }
            for s in schedule
        ],
        "journal": [
            {
                "id": j.id,
                "mood": j.mood,
                "content": (j.content or "")[:400],
                "tags": j.tags,
            }
            for j in journal
        ],
    }


def get_today(db: Session, user_id: int) -> dict:
    """Server-date convenience wrapper (phrase 45)."""
    return get_daily_notes(db, user_id, date.today())
