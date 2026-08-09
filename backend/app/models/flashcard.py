from sqlalchemy import Column, Float, Integer, String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base


class FlashcardDeck(Base):
    __tablename__ = "flashcard_decks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    cards = relationship(
        "Flashcard",
        back_populates="deck",
        cascade="all, delete-orphan",
        order_by="Flashcard.id",
    )


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("flashcard_decks.id", ondelete="CASCADE"), nullable=False, index=True)
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    difficulty = Column(String(20), default="basic")
    streak = Column(Integer, default=0)
    next_review = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # ── FSRS spaced-repetition state (Idea 52 — vendored py-fsrs) ──
    # ``next_review`` is the FSRS ``due`` datetime. New cards start with
    # ``state=None`` = Learning/never reviewed (due immediately).
    state = Column(Integer, nullable=True)
    step = Column(Integer, nullable=True)
    stability = Column(Float, nullable=True)
    # FSRS difficulty (1–10). Named ``fsrs_difficulty`` because the existing
    # ``difficulty`` column is the display tier (easy/basic/medium/hard).
    fsrs_difficulty = Column(Float, nullable=True)
    # Successful reviews (legacy repetition counter, display only).
    reps = Column(Integer, default=0)
    # Failed reviews since last success (display only).
    lapses = Column(Integer, default=0)

    deck = relationship("FlashcardDeck", back_populates="cards")
