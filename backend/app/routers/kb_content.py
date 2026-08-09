"""Phase 4 content endpoints (Ideas 31–34, 40-split).

Summaries, grounded explanations, note quizzes, flashcard candidates + review
queue, and brain-dump AI splitting. Every route is per-user; every generation
is budget-capped by ``KB_DAILY_GEN_LIMIT`` and falls back deterministically.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas.kb import KbDocumentResponse
from app.services.kb import KbService
from app.services.kb import flashcards as flashcards_service
from app.services.kb import note_quizzes as note_quiz_service
from app.services.kb import summarize, explain, braindump_draft
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-content"])


def _doc_or_404(db: Session, user_id: int, document_id: int):
    doc = KbService.get_document(db, user_id, document_id)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return doc


# ---------------------------------------------------------------------------
# Idea 31 — summaries
# ---------------------------------------------------------------------------

@router.get("/documents/{document_id}/summary")
def get_document_summary(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = _doc_or_404(db, current_user.id, document_id)
    return summarize.get_or_generate_summary(db, current_user.id, doc)


@router.post("/documents/{document_id}/summary")
def regenerate_document_summary(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    doc = _doc_or_404(db, current_user.id, document_id)
    return summarize.get_or_generate_summary(db, current_user.id, doc, regenerate=True)


# ---------------------------------------------------------------------------
# Idea 32 — grounded explanations
# ---------------------------------------------------------------------------

class ExplainRequest(BaseModel):
    concept: str = Field(..., min_length=1, max_length=300)
    depth: str = "overview"
    document_ids: list[int] | None = None


@router.post("/explain")
def post_explain(
    body: ExplainRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return explain.explain(
        db,
        current_user.id,
        body.concept,
        depth=body.depth,
        document_ids=body.document_ids,
    )


# ---------------------------------------------------------------------------
# Idea 33 — quizzes from notes
# ---------------------------------------------------------------------------

class NoteQuizRequest(BaseModel):
    document_id: int
    num_questions: int = 10
    difficulty: str = "medium"


@router.post("/quizzes")
def create_note_quiz(
    body: NoteQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    quiz = note_quiz_service.generate_note_quiz(
        db,
        current_user.id,
        body.document_id,
        num_questions=body.num_questions,
        difficulty=body.difficulty,
    )
    return {
        "id": quiz.id,
        "unit_id": quiz.unit_id,
        "document_id": body.document_id,
        "questions": quiz.questions,
        "difficulty": quiz.difficulty,
        "created_at": quiz.created_at.isoformat() if quiz.created_at else None,
    }


@router.get("/quizzes/{quiz_id}/document", response_model=KbDocumentResponse | None)
def quiz_source_document(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reverse provenance: which note generated this quiz (phrase 26)."""
    return note_quiz_service.quiz_source_document(db, current_user.id, quiz_id)


# ---------------------------------------------------------------------------
# Idea 34 — flashcard candidates + review queue
# ---------------------------------------------------------------------------

@router.post("/documents/{document_id}/flashcards")
def generate_flashcards(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return flashcards_service.generate_candidates(db, current_user.id, document_id)


@router.get("/flashcards/candidates")
def list_flashcard_candidates(
    status: str = Query(default="pending"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"items": flashcards_service.list_candidates(db, current_user.id, status)}


class FlashcardReviewRequest(BaseModel):
    approve: list[int] = Field(default_factory=list)
    reject: list[int] = Field(default_factory=list)
    deck_id: int | None = None


@router.post("/flashcards/review")
def review_flashcards(
    body: FlashcardReviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return flashcards_service.review_candidates(
        db,
        current_user.id,
        approve=body.approve,
        reject=body.reject,
        deck_id=body.deck_id,
    )


# ---------------------------------------------------------------------------
# Idea 40 — brain-dump draft splitting
# ---------------------------------------------------------------------------

@router.post("/documents/{document_id}/split")
def split_braindump_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return braindump_draft.split_draft(db, current_user.id, document_id)
