"""FSRS-powered flashcard scheduling (Idea 52 — vendored py-fsrs).

The ``Flashcard`` rows already carried ``next_review`` / ``streak`` fields but
nothing ever scheduled them. This service gives every card a real spaced-
repetition state machine: ``review_card`` grades a card 0–5 (mapped to FSRS
Again/Hard/Good/Easy), and ``due_cards`` returns the cards due now.

New cards start with ``state=None`` (never reviewed → due immediately).
Intervals follow the same day-granularity, deterministic scheduler used by the
topic revision flow (see ``app/services/srs.py``).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Flashcard
from app.services.srs import (
    card_from_state,
    grade_to_rating,
    interval_days,
    make_scheduler,
    update_legacy_ease,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def review_card(db: Session, card: Flashcard, grade: int) -> Flashcard:
    """Grade a flashcard 0–5, advance its FSRS schedule, persist and return it."""
    grade = max(0, min(5, int(grade)))
    reviewed_at = _now_utc()

    fsrs_card = card_from_state(
        card_id=card.id,
        state=card.state,
        step=card.step,
        stability=card.stability,
        difficulty=card.fsrs_difficulty,
        due=card.next_review,
        last_review=None,  # Flashcard model has no last-review column; due is authoritative.
    )
    rating = grade_to_rating(grade)
    max_interval = getattr(settings, "revision_max_interval", 365)
    fsrs_card, _ = make_scheduler(max_interval).review_card(
        fsrs_card, rating, review_datetime=reviewed_at
    )

    # Persist FSRS state (naive UTC to match the app's storage convention).
    card.state = fsrs_card.state.value
    card.step = fsrs_card.step
    card.stability = fsrs_card.stability
    card.fsrs_difficulty = fsrs_card.difficulty
    card.next_review = fsrs_card.due.replace(tzinfo=None)
    # Legacy counters (display only).
    if grade >= 3:
        card.reps = (card.reps or 0) + 1
        card.streak = (card.streak or 0) + 1
        card.lapses = 0
    else:
        card.lapses = (card.lapses or 0) + 1
        card.streak = 0
    db.flush()
    return card


def review_payload(card: Flashcard) -> dict:
    """API-friendly snapshot of a card's schedule after a review."""
    return {
        "card_id": card.id,
        "next_review": card.next_review.isoformat() if card.next_review else None,
        "interval_days": _interval_from_next(card),
        "state": card.state,
        "stability": round(card.stability, 4) if card.stability is not None else None,
        "fsrs_difficulty": round(card.fsrs_difficulty, 4) if card.fsrs_difficulty is not None else None,
        "reps": card.reps or 0,
        "lapses": card.lapses or 0,
        "streak": card.streak or 0,
    }


def _interval_from_next(card: Flashcard) -> int:
    """Whole days until due — rounded so sub-second drift never drops a day."""
    if not card.next_review:
        return 0
    due = card.next_review
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return max(0, round((due - _now_utc()).total_seconds() / 86400))


def due_cards(db: Session, deck_id: int | None = None) -> list[dict]:
    """Cards due now or earlier (``state`` is None for never-reviewed cards)."""
    q = db.query(Flashcard).filter(
        (Flashcard.state.is_(None)) | (Flashcard.next_review <= _now_utc().replace(tzinfo=None))
    )
    if deck_id is not None:
        q = q.filter(Flashcard.deck_id == deck_id)
    rows = q.order_by(Flashcard.id.asc()).limit(200).all()
    return [
        {
            "id": c.id,
            "deck_id": c.deck_id,
            "front": c.front,
            "back": c.back,
            "difficulty": c.difficulty,
            "next_review": c.next_review.isoformat() if c.next_review else None,
            "interval_days": _interval_from_next(c),
            "streak": c.streak or 0,
        }
        for c in rows
    ]


def due_count_by_deck(db: Session) -> dict[int, int]:
    """deck_id → number of due cards (for deck-list badges)."""
    due = due_cards(db)
    counts: dict[int, int] = {}
    for row in due:
        counts[row["deck_id"]] = counts.get(row["deck_id"], 0) + 1
    return counts
