"""Idea 82 — scheduled auto-tag of untagged documents (Phase 9 Automation).

The nightly job selects documents with ``tags_dirty`` set (new or re-changed
docs), seeds their inline/frontmatter rule tags (authoritative, applied
immediately), and proposes AI (or deterministic TF-IDF fallback) tags as
``provenance="ai"`` rows that stay in the review queue until the user applies
them. Nothing AI-derived is committed without review.

``budget_kind`` is unset — tag proposals reuse the Phase 2 tagger, which is
already budget-aware via the embedding budget.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbDocumentTag
from app.services.kb.automation import auto_job
from app.services.kb.tagger import auto_tag_document

logger = logging.getLogger(__name__)


def _tag_count(db: Session, doc_id: int) -> int:
    return (
        db.query(KbDocumentTag.id)
        .filter(KbDocumentTag.document_id == doc_id)
        .count()
    )


def _dirty_docs(db: Session, user_id: int, limit: int) -> list[KbDocument]:
    """Untagged or re-changed docs, newest first."""
    return (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.tags_dirty == True,  # noqa: E712
        )
        .order_by(KbDocument.id.desc())
        .limit(limit)
        .all()
    )


@auto_job(
    "auto_tag",
    toggle="KB_AUTO_TAG_ENABLED",
    cap="KB_AUTO_TAG_PER_NIGHT",
    description="Seed rule tags and propose AI tags for dirty documents nightly.",
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Process dirty documents: seed rule tags + queue AI tag proposals."""
    if limit is None:
        limit = settings.KB_AUTO_TAG_PER_NIGHT
    docs = _dirty_docs(db, user_id, limit)

    processed = 0
    tags_added = 0
    for doc in docs:
        try:
            before = _tag_count(db, doc.id)
            # ``auto_tag_document`` seeds rules, proposes AI rows, clears the
            # dirty flag, and commits — reusing the Phase 2 tagger verbatim.
            auto_tag_document(db, doc)
            after = _tag_count(db, doc.id)
            tags_added += max(0, after - before)
            processed += 1
        except Exception as exc:  # noqa: BLE001 — one bad doc never stops the job
            logger.warning("auto_tag failed for doc %s: %s", doc.id, exc)
            db.rollback()

    return {"processed": processed, "tags_added": tags_added}
