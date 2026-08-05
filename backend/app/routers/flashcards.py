"""Flashcard decks + cards CRUD."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Flashcard, FlashcardDeck
from app.schemas.flashcard import (
    FlashcardCreate,
    FlashcardDeckCreate,
    FlashcardDeckResponse,
    FlashcardDeckSummary,
    FlashcardDeckUpdate,
    FlashcardResponse,
    FlashcardUpdate,
)

router = APIRouter(prefix="/api/flashcard-decks", tags=["flashcards"])


# ---------------------------------------------------------------------------
# Decks
# ---------------------------------------------------------------------------

@router.get("", response_model=List[FlashcardDeckSummary])
def list_decks(db: Session = Depends(get_db)):
    decks = db.query(FlashcardDeck).order_by(FlashcardDeck.id).all()
    return [
        FlashcardDeckSummary(
            id=d.id, name=d.name, course_id=d.course_id, created_at=d.created_at,
            card_count=len(d.cards),
        )
        for d in decks
    ]


@router.get("/{deck_id}", response_model=FlashcardDeckResponse)
def get_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(404, "Deck not found")
    return deck


@router.post("", response_model=FlashcardDeckResponse)
def create_deck(data: FlashcardDeckCreate, db: Session = Depends(get_db)):
    deck = FlashcardDeck(**data.model_dump())
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


@router.put("/{deck_id}", response_model=FlashcardDeckResponse)
def update_deck(deck_id: int, data: FlashcardDeckUpdate, db: Session = Depends(get_db)):
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(404, "Deck not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(deck, key, val)
    db.commit()
    db.refresh(deck)
    return deck


@router.delete("/{deck_id}")
def delete_deck(deck_id: int, db: Session = Depends(get_db)):
    deck = db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(404, "Deck not found")
    db.delete(deck)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Cards (nested under a deck)
# ---------------------------------------------------------------------------

@router.get("/{deck_id}/cards", response_model=List[FlashcardResponse])
def list_cards(deck_id: int, db: Session = Depends(get_db)):
    if not db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first():
        raise HTTPException(404, "Deck not found")
    return db.query(Flashcard).filter(Flashcard.deck_id == deck_id).order_by(Flashcard.id).all()


@router.post("/{deck_id}/cards", response_model=FlashcardResponse)
def create_card(deck_id: int, data: FlashcardCreate, db: Session = Depends(get_db)):
    if not db.query(FlashcardDeck).filter(FlashcardDeck.id == deck_id).first():
        raise HTTPException(404, "Deck not found")
    card = Flashcard(deck_id=deck_id, **data.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/{deck_id}/cards/{card_id}", response_model=FlashcardResponse)
def update_card(deck_id: int, card_id: int, data: FlashcardUpdate, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.id == card_id, Flashcard.deck_id == deck_id).first()
    if not card:
        raise HTTPException(404, "Card not found")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(card, key, val)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{deck_id}/cards/{card_id}")
def delete_card(deck_id: int, card_id: int, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.id == card_id, Flashcard.deck_id == deck_id).first()
    if not card:
        raise HTTPException(404, "Card not found")
    db.delete(card)
    db.commit()
    return {"ok": True}
