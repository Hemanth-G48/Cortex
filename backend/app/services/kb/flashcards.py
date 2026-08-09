"""Flashcard candidates from notes (Phase 4, Idea 34).

Candidates are generated from a document's concept-rich chunks into a review
queue (``KbFlashcardCandidate``, status=pending). Nothing enters a
``FlashcardDeck`` until the user approves it (phrase 33). Dedupe normalizes
questions so already-covered ideas are skipped (phrase 34).
"""

from __future__ import annotations

import logging
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import (
    Flashcard,
    FlashcardDeck,
    KbChunk,
    KbConcept,
    KbDocument,
    KbEdge,
    KbFlashcardCandidate,
)
from app.services.ai_fallback import demo_kb_flashcards
from app.services.kb import KbService
from app.services.kb.budget import budget_allows, record_generation

logger = logging.getLogger(__name__)

DEFAULT_DECK_NAME = "From notes"


def _normalize_question(question: str) -> str:
    """Lowercase, strip punctuation/whitespace — the dedupe key (phrase 34)."""
    return re.sub(r"[^a-z0-9]+", " ", (question or "").lower()).strip()


def _existing_questions(db: Session, user_id: int, document_id: int) -> set[str]:
    """Questions already covered by candidates or committed cards for this doc."""
    covered: set[str] = set()
    candidates = (
        db.query(KbFlashcardCandidate)
        .filter(
            KbFlashcardCandidate.user_id == user_id,
            KbFlashcardCandidate.document_id == document_id,
        )
        .all()
    )
    for c in candidates:
        covered.add(_normalize_question(c.question))
    # Cards in decks created for this user's note flashcards (best-effort scan).
    deck_ids = [c.deck_id for c in candidates if c.deck_id]
    if deck_ids:
        for card in (
            db.query(Flashcard)
            .filter(Flashcard.deck_id.in_(deck_ids))
            .all()
        ):
            covered.add(_normalize_question(card.front))
    return covered


def _concepts_for_document(db: Session, user_id: int, doc: KbDocument) -> list[dict]:
    """MENTIONS concepts with definitions — used by the fallback generator."""
    rows = (
        db.query(KbConcept)
        .join(KbEdge, KbEdge.target_concept_id == KbConcept.id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == doc.id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
            KbConcept.user_id == user_id,
        )
        .all()
    )
    return [{"name": c.canonical_name, "definition": c.definition} for c in rows]


def generate_candidates(
    db: Session, user_id: int, document_id: int, *, source: str = "manual"
) -> dict:
    """Generate pending flashcard candidates for a document (phrase 32).

    ``source`` is "manual" (user-triggered) or "auto" (Phase 9 Idea 85
    background job) — recorded on the candidate so the review UI can mark
    auto-generated rows (phrase 44).
    """
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")

    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc.id, KbChunk.user_id == user_id)
        .order_by(KbChunk.seq.asc())
        .all()
    )
    if not chunks:
        raise HTTPException(422, "Document has no chunks to build cards from")

    covered = _existing_questions(db, user_id, doc.id)

    from app.services.ai_client import ai_available

    used_fallback = not ai_available()
    if not used_fallback and not budget_allows(db, user_id):
        raise HTTPException(429, "Daily generation budget exhausted — try again tomorrow.")

    raw_cards: list[dict] = []
    if not used_fallback:
        try:
            from app.services.ai_client import generate_json
            from app.services.prompts import kb_flashcards_prompt

            chunk_lines = "\n".join(
                f"[{c.id}] {c.content[:600]}" for c in chunks[:12]
            )
            parsed = generate_json(kb_flashcards_prompt(chunk_lines), max_tokens=2500, temperature=0.6)
            cards = parsed.get("cards") if isinstance(parsed, dict) else parsed
            if isinstance(cards, list):
                for c in cards:
                    if not isinstance(c, dict):
                        continue
                    q = str(c.get("question") or "").strip()
                    a = str(c.get("answer") or "").strip()
                    if q and a:
                        raw_cards.append(
                            {
                                "question": q[:500],
                                "answer": a[:1000],
                                "source_chunk_id": int(c.get("source_chunk_id") or 0) or None,
                            }
                        )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Flashcard generation failed for doc %s: %s", doc.id, exc)

    if not raw_cards:
        used_fallback = True
        raw_cards = demo_kb_flashcards(_concepts_for_document(db, user_id, doc))

    # Dedupe against covered questions, then persist pending candidates.
    added: list[KbFlashcardCandidate] = []
    for card in raw_cards:
        norm = _normalize_question(card["question"])
        if not norm or norm in covered:
            continue
        covered.add(norm)
        candidate = KbFlashcardCandidate(
            user_id=user_id,
            document_id=doc.id,
            source_chunk_id=card.get("source_chunk_id"),
            question=card["question"],
            answer=card["answer"],
            status="pending",
            source=source,
        )
        db.add(candidate)
        added.append(candidate)

    if not used_fallback:
        record_generation(db, user_id, "flashcards")
    db.commit()
    for c in added:
        db.refresh(c)

    return {
        "document_id": doc.id,
        "generated": len(added),
        "skipped_duplicates": len(raw_cards) - len(added),
        "fallback": used_fallback,
        "candidates": [
            {
                "id": c.id,
                "question": c.question,
                "answer": c.answer,
                "source_chunk_id": c.source_chunk_id,
                "status": c.status,
                "source": c.source,
            }
            for c in added
        ],
    }


def list_candidates(db: Session, user_id: int, status: str = "pending") -> list[dict]:
    """Review queue for the current user (phrase 39)."""
    rows = (
        db.query(KbFlashcardCandidate)
        .filter(KbFlashcardCandidate.user_id == user_id, KbFlashcardCandidate.status == status)
        .order_by(KbFlashcardCandidate.id.desc())
        .limit(200)
        .all()
    )
    doc_titles = {
        d.id: d.title or d.path_rel
        for d in db.query(KbDocument).filter(KbDocument.user_id == user_id).all()
    }
    return [
        {
            "id": c.id,
            "document_id": c.document_id,
            "document_title": doc_titles.get(c.document_id) or "",
            "question": c.question,
            "answer": c.answer,
            "source_chunk_id": c.source_chunk_id,
            "status": c.status,
            "source": c.source,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]


def review_candidates(
    db: Session,
    user_id: int,
    approve: list[int] | None = None,
    reject: list[int] | None = None,
    deck_id: int | None = None,
) -> dict:
    """Approve (→ Flashcard rows in a deck) or reject candidates in bulk."""
    approve = [int(i) for i in (approve or [])]
    reject = [int(i) for i in (reject or [])]
    if not approve and not reject:
        raise HTTPException(400, "Provide approve and/or reject candidate ids")

    approved_count = 0
    rejected_count = 0
    deck: FlashcardDeck | None = None

    if approve:
        candidates = (
            db.query(KbFlashcardCandidate)
            .filter(
                KbFlashcardCandidate.user_id == user_id,
                KbFlashcardCandidate.id.in_(approve),
                KbFlashcardCandidate.status == "pending",
            )
            .all()
        )
        if not candidates:
            raise HTTPException(404, "No pending candidates match the approve ids")
        # Auto-select or create the target deck (phrase 35).
        deck = None
        if deck_id is not None:
            deck = (
                db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
            )
            if deck is None:
                raise HTTPException(404, "Deck not found")
        else:
            deck = (
                db.query(FlashcardDeck)
                .filter(FlashcardDeck.name == DEFAULT_DECK_NAME)
                .order_by(FlashcardDeck.id.asc())
                .first()
            )
        if deck is None:
            deck = FlashcardDeck(name=DEFAULT_DECK_NAME)
            db.add(deck)
            db.flush()

        for c in candidates:
            db.add(
                Flashcard(
                    deck_id=deck.id,
                    front=c.question,
                    back=c.answer,
                    difficulty="basic",
                )
            )
            c.status = "approved"
            c.deck_id = deck.id
            db.add(c)
            approved_count += 1

    if reject:
        rejected = (
            db.query(KbFlashcardCandidate)
            .filter(
                KbFlashcardCandidate.user_id == user_id,
                KbFlashcardCandidate.id.in_(reject),
                KbFlashcardCandidate.status == "pending",
            )
            .all()
        )
        for c in rejected:
            c.status = "rejected"
            db.add(c)
            rejected_count += len(rejected)

    db.commit()
    return {
        "approved": approved_count,
        "rejected": rejected_count,
        "deck_id": deck.id if deck else None,
    }
