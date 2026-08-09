"""Phase 7 adaptive question difficulty (Idea 67, phrases 61–70).

Mastery (Phase 6 Group 8) gates the next question's difficulty tier; an
IRT-lite accuracy-threshold rule adjusts the tier after each answer
(phrase 63); state persists per (user, topic) in ``practice_adaptive_state``
(phrase 66). Tiers clamp to the difficulty of available approved questions
(phrase 67).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AdaptiveState, PracticeQuestion, Topic
from app.services.kb import KbService
from app.services.kb.mastery import log_event

TIERS = ("E", "M", "H")
_ORDER = {"E": 0, "M": 1, "H": 2}


def _state(db: Session, user_id: int, topic_id: int) -> AdaptiveState:
    row = (
        db.query(AdaptiveState)
        .filter(AdaptiveState.user_id == user_id, AdaptiveState.topic_id == topic_id)
        .first()
    )
    if row is None:
        row = AdaptiveState(user_id=user_id, topic_id=topic_id, tier="M")
        db.add(row)
        db.flush()
    return row


def _attempts(row: AdaptiveState) -> dict:
    return KbService.json_loads(row.attempts_json) or {}


def _save_attempts(row: AdaptiveState, attempts: dict) -> None:
    row.attempts_json = KbService.json_dumps(attempts)


def _available_tiers(db: Session, user_id: int, topic_id: int) -> list[str]:
    """Distinct difficulty tiers among approved questions (phrase 67)."""
    rows = (
        db.query(PracticeQuestion.difficulty)
        .filter(
            PracticeQuestion.user_id == user_id,
            PracticeQuestion.topic_id == topic_id,
            PracticeQuestion.status == "approved",
        )
        .distinct()
        .all()
    )
    tiers = [r[0] for r in rows if r[0] in TIERS]
    return tiers or list(TIERS)


def _clamp(tier: str, available: list[str]) -> str:
    if tier not in available:
        # Nearest available tier; default to M when nothing fits.
        if "M" in available:
            return "M"
        return min(available, key=lambda t: abs(_ORDER[t] - _ORDER[tier]))
    return tier


def select_tier(db: Session, user_id: int, topic_id: int) -> dict:
    """Pick the next difficulty tier from mastery + state (phrases 61, 67)."""
    topic = db.query(Topic).get(topic_id)
    if topic is None or topic.user_id != user_id:
        from fastapi import HTTPException

        raise HTTPException(404, "Topic not found")

    state = _state(db, user_id, topic_id)
    available = _available_tiers(db, user_id, topic_id)

    if not _attempts(state):
        # Mastery gates the starting tier (phrase 61).
        cls = topic.mastery_classification or "unknown"
        if cls == "strong":
            base = "H"
        elif cls == "weak":
            base = "E"
        else:
            base = "M"
        reason = f"started from mastery classification '{cls}'"
    else:
        base = state.tier
        reason = "continuing at the last difficulty tier"

    tier = _clamp(base, available)
    return {
        "topic_id": topic_id,
        "tier": tier,
        "reason": reason,
        "available_tiers": available,
        "streak": state.streak,
    }


def record_answer(db: Session, user_id: int, topic_id: int, tier: str, correct: bool) -> dict:
    """Record one answer and apply the IRT-lite tier update (phrases 63–65)."""
    topic = db.query(Topic).get(topic_id)
    if topic is None or topic.user_id != user_id:
        from fastapi import HTTPException

        raise HTTPException(404, "Topic not found")
    tier = tier if tier in TIERS else "M"

    state = _state(db, user_id, topic_id)
    attempts = _attempts(state)
    bucket = attempts.setdefault(tier, {"correct": 0, "total": 0})
    bucket["total"] = int(bucket.get("total", 0)) + 1
    if correct:
        bucket["correct"] = int(bucket.get("correct", 0)) + 1
    _save_attempts(state, attempts)

    # Streak + tier movement (phrase 63).
    state.streak = state.streak + 1 if correct else 0
    acc = bucket["correct"] / bucket["total"]
    moved = False
    new_tier = tier
    if acc >= settings.KB_ADAPTIVE_RAISE_ACC and _ORDER[tier] < 2:
        new_tier = TIERS[_ORDER[tier] + 1]
        moved = True
    elif acc <= settings.KB_ADAPTIVE_LOWER_ACC and _ORDER[tier] > 0:
        new_tier = TIERS[_ORDER[tier] - 1]
        moved = True
    state.tier = _clamp(new_tier, _available_tiers(db, user_id, topic_id))
    state.last_result = KbService.json_dumps(
        {"last_correct": bool(correct), "last_tier": tier, "accuracy": round(acc, 3), "tier_moved": moved}
    )

    # Learning event (phrase 65): value = accuracy-ish correctness signal.
    log_event(db, user_id, event_type="practice", topic_id=topic_id, value=1.0 if correct else 0.0)
    db.flush()
    return {
        "topic_id": topic_id,
        "tier": state.tier,
        "streak": state.streak,
        "tier_moved": moved,
        "accuracy_at_tier": round(acc, 3),
    }


__all__ = ["select_tier", "record_answer"]
