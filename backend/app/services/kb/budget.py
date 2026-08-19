"""Phase 4 shared generation budget (``KB_DAILY_GEN_LIMIT``).

Every real LLM generation across Phase 4 features meters against one per-user
daily cap. The deterministic fallback paths never record a row, so
``AI_ENABLED=false`` (or offline use) is budget-exempt — mirroring the
``SUMMARY_DAILY_LIMIT`` demo exemption.

Usage: check ``budget_allows(db, user_id)`` *before* spending a generation,
then call ``record_generation(db, user_id, kind)`` after a successful real LLM
call (not after a fallback).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbGenerationLog
from app.services.kb import utcnow

# Kinds recorded by Phase 4/5/6 features (mirrors KbGenerationLog.kind values).
GEN_KINDS = (
    "summary", "explain", "quiz", "flashcards", "quality", "split",
    # Phase 5 (Subject Management Core, Ideas 41–50)
    "syllabus", "topics", "dependencies", "difficulty", "outcomes",
    # Phase 6 (Study Planning & Execution, Ideas 51–60)
    "plan", "subtasks",
    # Phase 7 (AI Tutor & Assessment, Ideas 61–70)
    "tutor", "doubt", "practice", "mocks", "interview", "grading",
    "mistake", "skills",
    # Phase 8 (Personalization & Learning Memory, Ideas 71–80)
    "contradiction", "suggestions", "adapt", "personalized_explain",
    # Book Knowledge Gap Analyzer (per-chapter concept refinement).
    "book",
)


def _day_start():
    return utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


def generation_budget(db: Session, user_id: int) -> dict:
    """Per-user daily generation meter for Phase 4 features."""
    count = (
        db.query(KbGenerationLog)
        .filter(
            KbGenerationLog.user_id == user_id,
            KbGenerationLog.created_at >= _day_start(),
        )
        .count()
    )
    limit = settings.KB_DAILY_GEN_LIMIT
    return {
        "today": count,
        "limit": limit,
        "remaining": max(0, limit - count),
    }


def budget_allows(db: Session, user_id: int, amount: int = 1) -> bool:
    """True when ``amount`` more real generations fit in today's cap."""
    return generation_budget(db, user_id)["remaining"] >= amount


def record_generation(db: Session, user_id: int, kind: str) -> None:
    """Record one real LLM generation against the daily cap (best-effort)."""
    if kind not in GEN_KINDS:
        kind = "summary"
    db.add(KbGenerationLog(user_id=user_id, kind=kind))
    try:
        db.flush()
    except Exception:  # noqa: BLE001 — budget meter must never break the flow
        db.rollback()
