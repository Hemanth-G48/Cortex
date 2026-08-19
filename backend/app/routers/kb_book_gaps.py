"""Book Knowledge Gap Analyzer router — TOC-first, two-stage workflow.

Upload a cybersecurity book (via the existing ``/api/books/upload`` flow) and
compare its table of contents against the user's Second Brain:

Stage 1 (deterministic, NO LLM):
- ``POST /api/kb/books/{book_id}/analyze`` — extract the book's heading
  hierarchy (chapters → sections → subsections), semantically match every
  topic against the Second Brain (exact / alias / token / subset), persist
  one ``BookGapTopic`` row per topic.
- ``GET  /api/kb/books/{book_id}/topics`` — the persisted TOC topics with
  status (KNOWN / PARTIALLY_KNOWN / UNKNOWN / NEEDS_REVIEW) + deep state.

Stage 2 (explicit user action only, budget-gated LLM):
- ``POST /api/kb/books/{book_id}/topics/{topic_id}/analyze`` — deep
  topic-level analysis: extracts ONLY the topic's page range, retrieves the
  matching Second Brain documents, compares them, and persists the result
  (missing sub-concepts also become ``BookGapItem`` rows with page evidence).
- ``POST /api/kb/books/{book_id}/topics/{topic_id}/add-to-brain`` — create a
  Second Brain study note for an unknown topic.

Unchanged legacy endpoints (still useful for the deep items + queue):
- ``GET  /api/kb/books/{book_id}/dashboard`` — rollup + per-chapter counts.
- ``GET  /api/kb/books/{book_id}/items`` — concept items (deep missing
  sub-concepts), filterable by status/chapter.
- ``GET  /api/kb/books/{book_id}/queue`` — prioritized reading queue.
- ``POST /api/kb/books/{book_id}/items/{item_id}/status`` — learning/learned/
  mastered, mirrored to the cumulative cross-book store.
- ``GET  /api/kb/books/overview`` — all uploaded books + cumulative totals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Book, User
from app.services.kb import book_gaps
from app.services.kb.book_gaps import LEARNING, LEARNED, MASTERED
from app.services.text_extractor import NoExtractableTextError
from app.services.users import current_user

router = APIRouter(prefix="/api/kb/books", tags=["kb-book-gaps"])


def _book_or_404(db: Session, user_id: int, book_id: int) -> Book:
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if book is None:
        raise HTTPException(404, "Book not found")
    return book


@router.get("/overview")
def overview(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """All uploaded books with analysis state + cumulative topic totals."""
    return book_gaps.overview(db, current_user.id)


@router.post("/{book_id}/analyze")
def analyze(
    book_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Stage 1 — TOC-first analysis for one book (idempotent re-analysis).

    Deterministic (structure + Second Brain matching); never calls the LLM.
    """
    _book_or_404(db, current_user.id, book_id)
    try:
        result = book_gaps.analyze_book(db, current_user.id, book_id)
    except NoExtractableTextError as exc:
        raise HTTPException(400, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return result


@router.get("/{book_id}/topics")
def topics(
    book_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Persisted Stage-1 TOC topics for the book (reading order)."""
    _book_or_404(db, current_user.id, book_id)
    return {"topics": book_gaps.list_topics(db, current_user.id, book_id)}


@router.post("/{book_id}/topics/{topic_id}/analyze")
def analyze_topic_deep(
    book_id: int,
    topic_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Stage 2 — deep analysis of ONE topic (explicit user action)."""
    _book_or_404(db, current_user.id, book_id)
    try:
        return book_gaps.analyze_topic_deep(db, current_user.id, book_id, topic_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{book_id}/topics/{topic_id}/add-to-brain")
def add_topic_to_brain(
    book_id: int,
    topic_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Create a Second Brain study note for an unknown topic."""
    _book_or_404(db, current_user.id, book_id)
    try:
        return book_gaps.add_topic_to_brain(db, current_user.id, book_id, topic_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{book_id}/dashboard")
def dashboard(
    book_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _book_or_404(db, current_user.id, book_id)
    return book_gaps.dashboard(db, current_user.id, book_id)


@router.get("/{book_id}/items")
def items(
    book_id: int,
    status: str | None = None,
    chapter: str | None = None,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _book_or_404(db, current_user.id, book_id)
    if status and status not in (
        book_gaps.KNOWN,
        book_gaps.PARTIAL,
        book_gaps.UNKNOWN,
        book_gaps.NEEDS_REVIEW,
    ):
        raise HTTPException(
            400, "status must be KNOWN | PARTIALLY_KNOWN | UNKNOWN | NEEDS_REVIEW"
        )
    return {"items": book_gaps.list_items(db, current_user.id, book_id, status=status, chapter=chapter)}


@router.get("/{book_id}/queue")
def queue(
    book_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _book_or_404(db, current_user.id, book_id)
    return {"items": book_gaps.reading_queue(db, current_user.id, book_id)}


class SetStatusRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)

# Accept the UI's lowercase values and map to the service's constants.
_STATUS_MAP = {
    "learning": LEARNING,
    "learned": LEARNED,
    "mastered": MASTERED,
}


@router.post("/{book_id}/items/{item_id}/status")
def set_status(
    book_id: int,
    item_id: int,
    body: SetStatusRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    mapped = _STATUS_MAP.get((body.status or "").strip().lower())
    if mapped is None:
        raise HTTPException(400, "status must be learning | learned | mastered")
    _book_or_404(db, current_user.id, book_id)
    try:
        return book_gaps.mark_item_status(db, current_user.id, book_id, item_id, mapped)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
