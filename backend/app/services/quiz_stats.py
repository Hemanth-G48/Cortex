"""Quiz attempt aggregation for reviewer analytics + gamification hooks."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Character, QuizAttempt, Quiz, User

# G13 (Phase 85): XP awarded for a passing attempt (>= 70%), once per quiz.
QUIZ_PASS_XP = 25
QUIZ_PASS_THRESHOLD = 70.0


def grant_quiz_xp(db: Session, user: User, quiz_id: int, percentage: float) -> int:
    """Grant XP for a passing quiz attempt.

    No double-award: XP is credited only on the *first* passing attempt for a
    given quiz; retries that also pass are ignored. Below-threshold attempts
    grant nothing. Returns the amount of XP granted (0 if none).
    """
    if percentage < QUIZ_PASS_THRESHOLD:
        return 0

    prior = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user.id,
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.score.isnot(None),
            QuizAttempt.total_questions.isnot(None),
        )
        .all()
    )
    for a in prior:
        if a.total_questions and (a.score / a.total_questions) * 100 >= QUIZ_PASS_THRESHOLD:
            return 0

    # Credit the shared wallet (mirrors quests/missions convention: character
    # XP for levels, user.total_xp for reward claims / quest-centre display).
    user.total_xp = (user.total_xp or 0) + QUIZ_PASS_XP
    char = db.query(Character).filter(Character.user_id == user.id).first()
    if char:
        char.xp = (char.xp or 0) + QUIZ_PASS_XP
    db.commit()
    return QUIZ_PASS_XP


def reviewer_summary(db: Session, user_id: int) -> dict:
    """Aggregate stats from the last 50 quiz attempts for a user."""
    attempts = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.created_at.desc())
        .limit(50)
        .all()
    )

    if not attempts:
        return {
            "avg_score": 0,
            "best_score": 0,
            "total_attempts": 0,
            "per_unit": {},
        }

    scores = [a.score for a in attempts if a.score is not None]
    best = max(scores) if scores else 0
    avg = round(sum(scores) / len(scores), 1) if scores else 0

    per_unit: dict[int, int] = {}
    for a in attempts:
        quiz = db.query(Quiz).filter(Quiz.id == a.quiz_id).first()
        if quiz is not None:
            uid = quiz.unit_id
            per_unit[uid] = per_unit.get(uid, 0) + 1

    return {
        "avg_score": avg,
        "best_score": best,
        "total_attempts": len(attempts),
        "per_unit": per_unit,
    }
