"""Quiz generation, attempts, and analytics router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Quiz, QuizAttempt
from app.schemas.quiz import (
    QuizCreate,
    QuizResponse,
    QuizAttemptRequest,
    QuizAttemptResult,
    HistoryItem,
)
from app.services.security import get_current_user
from app.services.quizzes import generate_quiz, score_attempt
from app.services.quiz_stats import grant_quiz_xp, reviewer_summary

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


@router.post("")
def create_quiz(
    data: QuizCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizResponse:
    quiz = generate_quiz(db, data.unit_id, data.num_questions, data.difficulty)
    return QuizResponse(
        id=quiz.id,
        unit_id=quiz.unit_id,
        questions=quiz.questions,
        difficulty=quiz.difficulty,
        created_at=quiz.created_at,
    )


@router.post("/{quiz_id}/attempt", response_model=QuizAttemptResult)
def attempt_quiz(
    quiz_id: int,
    data: QuizAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if quiz is None:
        raise HTTPException(404, "Quiz not found")

    result = score_attempt(db, quiz, data.answers)

    # G13 (Phase 85): grant XP for a passing attempt, once per quiz.
    # Runs before persisting so the fresh attempt doesn't count as "prior".
    xp_awarded = grant_quiz_xp(db, current_user, quiz.id, result["percentage"])
    result["xp_awarded"] = xp_awarded

    # Persist the attempt.
    attempt = QuizAttempt(
        user_id=current_user.id,
        quiz_id=quiz.id,
        answers=data.answers,
        score=result["score"],
        total_questions=result["total"],
    )
    db.add(attempt)
    db.commit()

    return result


@router.get("/history", response_model=list[HistoryItem])
def quiz_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == current_user.id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(50)
        .all()
    )
    return attempts


@router.get("/analytics")
def quiz_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return reviewer_summary(db, current_user.id)
