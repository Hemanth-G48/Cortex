"""Idea 88 — auto-update study plans on new materials (Phase 9 Automation).

When material coverage for a Phase 5 topic shifts (new chunks mention it), the
topic's time estimate should refresh — better coverage can shrink
``first_pass_mins`` (phrase 72). This job reruns that mapper over each
subject's topics, recomputes estimates from the covered volume, and revises
the roadmap *only* when the per-topic delta exceeds ``KB_PLAN_DELTA_THRESHOLD``
(phrase 73) — small deltas are a no-op (phrase 80).

Revision reuses the Phase 8 Idea 80 ``adapt.adapt_roadmap`` machinery verbatim
(phrase 74): same versioned roadmap update + explainable diff. Meaningful
changes write a ``Notification`` (kind ``plan_sync``) so the user sees \"plan
updated for X\" (phrase 75).

Deterministic: no LLM calls, so no budget spend and no ``budget_kind``.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CurriculumSubject, KbChunk, KbDocument, Notification, Topic
from app.services.kb import KbService
from app.services.kb.adapt import adapt_roadmap
from app.services.kb.automation import auto_job
from app.services.kb.topics import estimate_times

logger = logging.getLogger(__name__)


def _topic_chars(db: Session, user_id: int, topic: Topic) -> int:
    """Total characters of the user's chunks that mention the topic name.

    Coverage proxy (phrase 71): more mentioning material → higher volume, which
    flows into the Phase 5 estimate formula.
    """
    needle = (topic.normalized_name or topic.name or "").lower()
    if not needle:
        return 0
    rows = (
        db.query(KbChunk, KbDocument)
        .join(KbDocument, KbDocument.id == KbChunk.document_id)
        .filter(
            KbChunk.user_id == user_id,
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
        )
        .all()
    )
    total = 0
    for chunk, _doc in rows:
        if needle in (chunk.content or "").lower():
            total += chunk.char_end - chunk.char_start
    return total


def _recompute_estimate(topic: Topic, chars: int) -> int:
    """Fresh ``first_pass_mins`` from covered volume (phrase 72)."""
    first, _, _ = estimate_times(
        chars, topic.difficulty or "M", multiplier=1.0
    )
    return first


def _delta_ratio(current: int, proposed: int) -> float:
    """|proposed − current| ÷ max(current, 1) — the phrase 73 threshold test."""
    base = max(current, 1)
    return abs(proposed - current) / base


def _sync_subject(
    db: Session, user_id: int, subject_id: int
) -> dict:
    """Rerun coverage mapping + estimate refresh for one subject's topics.

    Returns ``{"revised": bool, "topic_changes": n, "delta_ratio": float}``.
    """
    topics = (
        db.query(Topic)
        .filter(
            Topic.user_id == user_id,
            Topic.subject_id == subject_id,
            Topic.status.in_(("pending", "confirmed")),
        )
        .all()
    )
    changes = 0
    max_delta = 0.0
    for topic in topics:
        chars = _topic_chars(db, user_id, topic)
        proposed = _recompute_estimate(topic, chars)
        current = topic.first_pass_mins or 0
        ratio = _delta_ratio(current, proposed)
        max_delta = max(max_delta, ratio)
        if ratio >= settings.KB_PLAN_DELTA_THRESHOLD:
            topic.first_pass_mins = proposed
            topic.review_mins = max(5, round(proposed * 0.4))
            topic.mastery_mins = max(5, round(proposed * 0.6))
            db.add(topic)
            changes += 1

    if changes:
        db.commit()
        # Phase 8 adapt machinery: versioned roadmap update + diff (phrase 74).
        adapt_roadmap(db, user_id, subject_id)
        return {"revised": True, "topic_changes": changes, "delta_ratio": round(max_delta, 4)}
    return {"revised": False, "topic_changes": 0, "delta_ratio": round(max_delta, 4)}


def _subject_names(db: Session, user_id: int) -> dict[int, str]:
    return {
        s.id: s.name
        for s in db.query(CurriculumSubject)
        .join(Topic, Topic.subject_id == CurriculumSubject.id)
        .filter(Topic.user_id == user_id)
        .all()
    }


@auto_job(
    "auto_plan_sync",
    toggle="KB_AUTO_PLAN_SYNC_ENABLED",
    cap="",  # subjects are few; the threshold bounds revision churn
    description=(
        "Refresh topic time estimates from material coverage and revise study "
        "plans when deltas pass a threshold."
    ),
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Sync plans for every subject with topics (phrase 71)."""
    subject_ids = {
        t.subject_id
        for t in db.query(Topic).filter(Topic.user_id == user_id).all()
        if t.subject_id
    }
    names = _subject_names(db, user_id)

    processed = 0
    revised = 0
    topic_changes = 0
    notifications = 0
    for subject_id in sorted(subject_ids):
        result = _sync_subject(db, user_id, subject_id)
        processed += 1
        topic_changes += result["topic_changes"]
        if result["revised"]:
            revised += 1
            # Phrase 75: notify on meaningful plan changes.
            subject_name = names.get(subject_id, f"subject {subject_id}")
            db.add(
                Notification(
                    user_id=user_id,
                    kind="plan_sync",
                    title=f"Study plan updated for {subject_name}",
                    body=(
                        "New material changed your time estimates, so your "
                        "roadmap was revised."
                    ),
                    ref_type="subject",
                    ref_id=subject_id,
                )
            )
            db.commit()
            notifications += 1

    return {
        "processed": processed,
        "revised": revised,
        "topic_changes": topic_changes,
        "notifications": notifications,
    }
