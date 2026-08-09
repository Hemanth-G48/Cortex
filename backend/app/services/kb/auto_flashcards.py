"""Idea 85 — auto-create flashcards from new notes (Phase 9 Automation).

The nightly/periodic job selects *concept-bearing* documents (chunks with
``MENTIONS`` concept edges from Phase 2 Idea 15) that have no candidate rows
yet, and reuses the Phase 4 Idea 34 candidate generator verbatim — same Q/A
extraction, same review queue, same card-hash dedupe (phrases 41–44).

Eligibility gate (phrase 43): documents with zero ``MENTIONS`` concepts are
skipped — carding trivia has no value. Candidates are queued with
``source='auto'`` (phrase 44) so the review UI can mark them; nothing enters a
deck until the user approves.

Budget: ``budget_kind='flashcards'`` opts the job into ``KB_DAILY_GEN_LIMIT``;
``generate_candidates`` already raises 429 when the meter is empty, so the job
stops early rather than spending past the cap (phrase 49).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbEdge, KbFlashcardCandidate
from app.services.kb.automation import auto_job
from app.services.kb.flashcards import generate_candidates

logger = logging.getLogger(__name__)


def _concept_bearing_docs(
    db: Session, user_id: int, limit: int
) -> list[KbDocument]:
    """Newest documents that mention at least one concept AND have no
    candidates yet (pending/approved/rejected) — the phrase 43 gate."""
    doc_ids_with_concepts = {
        row[0]
        for row in db.query(KbEdge.source_document_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
            KbEdge.source_document_id.is_not(None),
        )
        .all()
    }
    if not doc_ids_with_concepts:
        return []

    carded = {
        row[0]
        for row in db.query(KbFlashcardCandidate.document_id)
        .filter(KbFlashcardCandidate.user_id == user_id)
        .all()
    }
    eligible = [
        d
        for d in (
            db.query(KbDocument)
            .filter(
                KbDocument.user_id == user_id,
                KbDocument.id.in_(doc_ids_with_concepts),
                KbDocument.status != "deleted",
            )
            .order_by(KbDocument.id.desc())
            .all()
        )
        if d.id not in carded
    ]
    return eligible[:limit]


@auto_job(
    "auto_flashcards",
    toggle="KB_AUTO_FLASHCARDS_ENABLED",
    cap="KB_AUTO_FLASHCARDS_PER_RUN",
    description=(
        "Queue flashcard candidates for concept-bearing notes (review before "
        "any deck write)."
    ),
    budget_kind="flashcards",
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Queue auto flashcard candidates for eligible documents (phrase 42)."""
    if limit is None:
        limit = settings.KB_AUTO_FLASHCARDS_PER_RUN
    docs = _concept_bearing_docs(db, user_id, limit)

    processed = 0
    generated = 0
    skipped_duplicates = 0
    budget_exhausted = False
    for doc in docs:
        try:
            result = generate_candidates(db, user_id, doc.id, source="auto")
        except HTTPException as exc:
            if exc.status_code == 429:
                budget_exhausted = True
                break  # stop early — the shared daily meter is empty
            if exc.status_code == 422:
                continue  # no chunks — not a real candidate source
            logger.warning(
                "auto_flashcards failed for doc %s: %s", doc.id, exc.detail
            )
            db.rollback()
            continue
        except Exception as exc:  # noqa: BLE001 — one bad doc never stops the job
            logger.warning("auto_flashcards failed for doc %s: %s", doc.id, exc)
            db.rollback()
            continue
        processed += 1
        generated += result.get("generated", 0)
        skipped_duplicates += result.get("skipped_duplicates", 0)

    return {
        "processed": processed,
        "generated": generated,
        "skipped_duplicates": skipped_duplicates,
        "budget_exhausted": budget_exhausted,
    }
