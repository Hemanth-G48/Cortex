"""Idea 86 — auto-create summaries, scheduled (Phase 9 Automation).

The nightly job scans ``summary_dirty=true`` documents (set on content-hash
change, phrase 51) and reuses the Phase 4 Idea 31 ``summarize`` service
verbatim — same hash-cache invalidation, same budget meter, same
deterministic fallback (phrases 52, 54, 60).

Priority (phrase 53): changed documents first (most valuable), then the
largest documents, capped at ``KB_AUTO_SUMMARY_PER_NIGHT`` and stopping early
once ``KB_DAILY_GEN_LIMIT`` is exhausted. A successful generation clears the
``summary_dirty`` flag so the doc is a cheap no-op on the next run (phrase 54).

``budget_kind='summary'`` opts the job into the shared daily meter.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument
from app.services.kb.automation import auto_job
from app.services.kb.summarize import get_or_generate_summary

logger = logging.getLogger(__name__)


def _dirty_docs(db: Session, user_id: int, limit: int) -> list[KbDocument]:
    """``summary_dirty`` docs — changed first, then largest (phrase 53)."""
    rows = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.summary_dirty == True,  # noqa: E712
            KbDocument.status != "deleted",
        )
        .all()
    )
    rows.sort(
        key=lambda d: (d.status != "changed", -(d.char_count or 0), d.id)
    )
    return rows[:limit]


@auto_job(
    "auto_summary",
    toggle="KB_AUTO_SUMMARY_ENABLED",
    cap="KB_AUTO_SUMMARY_PER_NIGHT",
    description=(
        "Regenerate summaries for documents whose content changed since their "
        "last summary."
    ),
    budget_kind="summary",
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Summarize dirty documents, honoring the per-night cap + daily budget."""
    if limit is None:
        limit = settings.KB_AUTO_SUMMARY_PER_NIGHT
    docs = _dirty_docs(db, user_id, limit)

    processed = 0
    summarized = 0
    cached = 0
    budget_exhausted = False
    for doc in docs:
        try:
            result = get_or_generate_summary(db, user_id, doc)
        except HTTPException as exc:
            if exc.status_code == 429:
                budget_exhausted = True
                break  # stop early — the shared daily meter is empty
            logger.warning(
                "auto_summary failed for doc %s: %s", doc.id, exc.detail
            )
            db.rollback()
            continue
        except Exception as exc:  # noqa: BLE001 — one bad doc never stops the job
            logger.warning("auto_summary failed for doc %s: %s", doc.id, exc)
            db.rollback()
            continue
        processed += 1
        if result.get("cached"):
            cached += 1
        else:
            summarized += 1
        doc.summary_dirty = False
        db.add(doc)
    db.commit()

    return {
        "processed": processed,
        "summarized": summarized,
        "cached": cached,
        "budget_exhausted": budget_exhausted,
    }
