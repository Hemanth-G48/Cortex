"""Idea 84 — nightly duplicate scan (Phase 9 Automation).

Reuses the Phase 2 near-duplicate machinery: ``candidate_pairs`` already
filters by ``KB_NEARDUP_THRESHOLD`` and skips pairs already linked by a
``DUPLICATE_OF`` edge. The job writes those pairs as ``provenance="auto"``
edges (capped per night) and surfaces them in the existing duplicate review
queue — nothing is merged or archived without the user.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbEdge
from app.services.kb import KbService
from app.services.kb.automation import auto_job
from app.services.kb.neardup import candidate_pairs

logger = logging.getLogger(__name__)


@auto_job(
    "auto_duplicates",
    toggle="KB_AUTO_DUPE_ENABLED",
    cap="KB_AUTO_DUPE_PER_NIGHT",
    description="Scan for near-duplicate documents nightly; pairs surface for review.",
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Record near-duplicate pairs as DUPLICATE_OF edges, capped per night."""
    if limit is None:
        limit = settings.KB_AUTO_DUPE_PER_NIGHT

    pairs = candidate_pairs(db, user_id)
    written = 0
    for emb_a, emb_b, sim in pairs:
        if written >= limit:
            break
        a = emb_a.chunk.document_id
        b = emb_b.chunk.document_id
        if a == b:
            continue
        # The later document (higher id) is the duplicate; earlier is canonical.
        source_id, target_id = (a, b) if a > b else (b, a)
        # Mark the canonical side so its duplicate map stays persistent.
        KbService.record_duplicate(db, user_id, target_id)
        db.add(
            KbEdge(
                user_id=user_id,
                source_document_id=source_id,
                target_document_id=target_id,
                relation="DUPLICATE_OF",
                weight=sim,
                provenance="auto",
            )
        )
        written += 1
    db.commit()
    return {"processed": written, "duplicates": written}
