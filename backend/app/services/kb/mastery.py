"""Phase 6 mastery + learning-event spine (Ideas 57–58).

``log_event`` is the single write path every study surface calls (reviews,
labs, sessions, outcomes, Phase 7 quizzes). Each event recomputes the owning
topic's ``mastery_score``/``mastery_classification`` immediately (recompute-on-
write, phrase 79) so reads stay cheap. Aggregation for the per-subject progress
dashboard (Idea 57) lives in ``progress_payload``.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import LearningEvent, Topic
from app.services.kb import utcnow

# Classification thresholds (phrase 73).
WEAK_MAX = 0.4
STRONG_MIN = 0.75
# A topic needs at least this many evidence events to leave ``unknown``.
MIN_EVIDENCE = 2
# Mastery decays toward the prior after this many idle days.
DECAY_DAYS = 14


def log_event(
    db: Session,
    user_id: int,
    *,
    event_type: str,
    topic_id: int | None = None,
    value: float = 1.0,
) -> LearningEvent:
    """Append a learning event and recompute the topic's mastery (phrase 72)."""
    event = LearningEvent(
        user_id=user_id,
        topic_id=topic_id,
        event_type=event_type,
        value=max(0.0, float(value)),
    )
    db.add(event)
    if topic_id is not None:
        recompute_mastery(db, user_id, topic_id)
    db.flush()
    return event


def topic_events(db: Session, user_id: int, topic_id: int, limit: int = 200) -> list[LearningEvent]:
    return (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == user_id, LearningEvent.topic_id == topic_id)
        .order_by(LearningEvent.created_at.asc())
        .limit(limit)
        .all()
    )


def recompute_mastery(db: Session, user_id: int, topic_id: int) -> float:
    """Recalculate a topic's mastery score from its events (phrase 71)."""
    events = topic_events(db, user_id, topic_id)
    score = _mastery_from_events(events)
    classification = classify(score, len(events))
    topic = db.get(Topic, topic_id)
    if topic is not None and topic.user_id == user_id:
        topic.mastery_score = round(score, 4)
        topic.mastery_classification = classification
    return score


def _mastery_from_events(events: list[LearningEvent]) -> float:
    """Bayesian-ish 0–1 score from attempts, accuracy, and recency.

    - ``quiz`` events carry accuracy (0–1): posterior = prior + (acc − prior)·w.
    - ``revision`` events carry grade/5: same update, slightly lower weight.
    - ``session``/``study`` events carry minutes: small positive boost.
    - ``lab``/``outcome`` completion markers give a fixed bump.
    - Idle decay pulls the score back toward the prior.
    """
    if not events:
        return 0.0
    prior = 0.3
    score = prior
    evidence = 0
    last = events[-1].created_at or utcnow()

    for e in events:
        kind = e.event_type
        v = float(e.value or 0.0)
        if kind == "quiz":
            acc = max(0.0, min(1.0, v))
            score = score + (acc - score) * 0.45
            evidence += 1
        elif kind == "revision":
            g = max(0.0, min(1.0, v))
            score = score + (g - score) * 0.35
            evidence += 1
        elif kind == "session":
            score = score + 0.03 * min(1.0, v / 25.0)
            evidence += 1
        elif kind == "study":
            score = score + 0.02 * min(1.0, v / 30.0)
            evidence += 1
        elif kind in ("lab", "outcome"):
            score = score + 0.08
            evidence += 1
    score = max(0.0, min(1.0, score))

    # Recency decay toward the prior (phrase 71: recency factor).
    age_days = max(0, (utcnow() - last).total_seconds() / 86400.0)
    if age_days > DECAY_DAYS:
        decay = min(0.5, (age_days - DECAY_DAYS) / 60.0)
        score = score - (score - prior) * decay
        score = max(0.0, min(1.0, score))
    return score


def classify(score: float, evidence: int) -> str:
    """Weak / strong / unknown with a minimum-evidence guard (phrase 73)."""
    if evidence < MIN_EVIDENCE:
        return "unknown"
    if score < WEAK_MAX:
        return "weak"
    if score >= STRONG_MIN:
        return "strong"
    return "medium"


def mastery_by_topic(db: Session, user_id: int, topic_ids: list[int]) -> dict[int, dict]:
    """``{topic_id: {score, classification, evidence}}`` for many topics."""
    out: dict[int, dict] = {}
    for tid in topic_ids:
        events = topic_events(db, user_id, tid)
        out[tid] = {
            "score": round(_mastery_from_events(events), 4),
            "classification": classify(_mastery_from_events(events), len(events)),
            "evidence": len(events),
        }
    return out


# ---------------------------------------------------------------------------
# Aggregation for the progress dashboard (Idea 57)
# ---------------------------------------------------------------------------


def subject_events(db: Session, user_id: int, topic_ids: list[int], since: datetime | None = None) -> list[LearningEvent]:
    if not topic_ids:
        return []
    q = db.query(LearningEvent).filter(
        LearningEvent.user_id == user_id,
        LearningEvent.topic_id.in_(topic_ids),
    )
    if since is not None:
        q = q.filter(LearningEvent.created_at >= since)
    return q.order_by(LearningEvent.created_at.asc()).all()


def hours_logged(db: Session, user_id: int, topic_ids: list[int]) -> float:
    """Sum of ``session``/``study`` minutes ÷ 60 (Idea 57: hours logged)."""
    total = 0.0
    for e in subject_events(db, user_id, topic_ids):
        if e.event_type in ("session", "study"):
            total += float(e.value or 0.0)
    return round(total / 60.0, 2)


def quiz_trend(db: Session, user_id: int, topic_ids: list[int]) -> list[dict]:
    """Per-day average quiz accuracy for the sparkline (Idea 57)."""
    acc: dict[str, list[float]] = {}
    for e in subject_events(db, user_id, topic_ids):
        if e.event_type == "quiz":
            day = (e.created_at or utcnow()).date().isoformat()
            acc.setdefault(day, []).append(max(0.0, min(1.0, float(e.value or 0.0))))
    return [
        {"date": day, "accuracy": round(sum(v) / len(v), 3)}
        for day, v in sorted(acc.items())
    ]


def progress_payload(db: Session, user_id: int, topic_ids: list[int]) -> dict:
    """Per-subject dashboard payload (Idea 57, phrase 65)."""
    mastery = mastery_by_topic(db, user_id, topic_ids)
    mastered = sum(1 for m in mastery.values() if m["classification"] == "strong")
    weak = sum(1 for m in mastery.values() if m["classification"] == "weak")
    unknown = sum(1 for m in mastery.values() if m["classification"] == "unknown")
    hours = hours_logged(db, user_id, topic_ids)
    events = subject_events(db, user_id, topic_ids)
    by_type: dict[str, int] = {}
    for e in events:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
    covered = sum(1 for m in mastery.values() if m["score"] >= 0.5)
    return {
        "topics_total": len(topic_ids),
        "topics_mastered": mastered,
        "topics_weak": weak,
        "topics_unknown": unknown,
        "coverage_pct": round(covered / len(topic_ids) * 100, 1) if topic_ids else 0.0,
        "hours_logged": hours,
        "events": by_type,
        "quiz_trend": quiz_trend(db, user_id, topic_ids),
        "mastery": mastery,
    }
