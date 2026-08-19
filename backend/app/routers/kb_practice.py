"""Phase 7 — Practice & Assessment router (Ideas 63–68).

- ``POST /api/kb/practice/generate|approve|reject|list`` — question bank (Idea 63)
- ``POST /api/kb/practice/session|answer`` — adaptive practice (Idea 67)
- ``POST /api/kb/practice/mistake-analysis`` — explain-my-mistake (Idea 68)
- ``/api/kb/mocks/...`` — mock tests & exam simulations (Idea 64)
- ``/api/kb/interview/...`` — interview prep (Idea 65)

Every endpoint is user-scoped and budget-capped.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MockTest, MockTestAttempt, PracticeQuestion, Topic, User
from app.services.kb import adaptive as adaptive_service
from app.services.kb import interview as interview_service
from app.services.kb import mistakes as mistakes_service
from app.services.kb import mocks as mocks_service
from app.services.kb import questions as questions_service
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-practice"])


def _topic_or_404(db: Session, user_id: int, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None or topic.user_id != user_id:
        raise HTTPException(404, "Topic not found")
    return topic


# --------------------------------------------------------------------------- #
# Idea 63 — practice question bank
# --------------------------------------------------------------------------- #
class GenerateRequest(BaseModel):
    topic_id: int
    count: int | None = Field(default=None, ge=1, le=20)
    difficulty: str | None = Field(default=None, pattern="^[EMH]$")


@router.post("/practice/generate")
def generate_questions(
    body: GenerateRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    topic = _topic_or_404(db, current_user.id, body.topic_id)
    created = questions_service.generate_for_topic(
        db, current_user.id, topic, count=body.count, difficulty=body.difficulty
    )
    db.commit()
    return {
        "items": [questions_service.question_dict(q, topic) for q in created],
        "generated": len(created),
        "deduped_skipped": True,
    }


@router.get("/practice/questions")
def list_questions(
    topic_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = questions_service.list_questions(db, current_user.id, topic_id=topic_id, status=status)
    topic_names = {
        t.id: t.name
        for t in db.query(Topic).filter(Topic.user_id == current_user.id).all()
    }
    items = []
    for q in rows:
        d = questions_service.question_dict(q)
        d["topic_name"] = topic_names.get(q.topic_id)
        items.append(d)
    return {"items": items}


@router.post("/practice/{question_id}/approve")
def approve_question(
    question_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = questions_service.approve_question(db, current_user.id, question_id)
    topic = db.get(Topic, row.topic_id)
    db.commit()
    return {"ok": True, "question": questions_service.question_dict(row, topic)}


@router.post("/practice/{question_id}/reject")
def reject_question(
    question_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    row = questions_service.reject_question(db, current_user.id, question_id)
    db.commit()
    return {"ok": True, "question": questions_service.question_dict(row)}


# --------------------------------------------------------------------------- #
# Idea 67 — adaptive practice
# --------------------------------------------------------------------------- #
@router.post("/practice/session")
def practice_session(
    body: GenerateRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    _topic_or_404(db, current_user.id, body.topic_id)
    tier = adaptive_service.select_tier(db, current_user.id, body.topic_id)
    bank = questions_service.approved_for_topic(db, current_user.id, body.topic_id)
    tiered = [q for q in bank if q.difficulty == tier["tier"]]
    pool = tiered or bank
    question = questions_service.question_dict(pool[0], _topic_or_404(db, current_user.id, body.topic_id)) if pool else None
    db.commit()
    return {"session": tier, "question": question}


@router.post("/practice/answer")
def practice_answer(
    body: dict,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    topic_id = int(body.get("topic_id") or 0)
    tier = str(body.get("tier") or "M")
    correct = bool(body.get("correct"))
    result = adaptive_service.record_answer(db, current_user.id, topic_id, tier, correct)
    db.commit()
    return result


# --------------------------------------------------------------------------- #
# Idea 68 — mistake analysis
# --------------------------------------------------------------------------- #
class MistakeRequest(BaseModel):
    question_id: int
    student_answer: str = Field(min_length=1, max_length=4000)


@router.post("/practice/mistake-analysis")
def mistake_analysis(
    body: MistakeRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = mistakes_service.analyze(db, current_user.id, body.question_id, body.student_answer)
    db.commit()
    return result


# --------------------------------------------------------------------------- #
# Idea 64 — mock tests
# --------------------------------------------------------------------------- #
class BuildPaperRequest(BaseModel):
    subject_id: int
    title: str | None = None
    question_count: int | None = Field(default=None, ge=3, le=50)
    duration_mins: int | None = Field(default=None, ge=5, le=240)


@router.post("/mocks/build")
def build_mock(
    body: BuildPaperRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    mock = mocks_service.build_paper(
        db, current_user.id, body.subject_id,
        title=body.title, question_count=body.question_count, duration_mins=body.duration_mins,
    )
    db.commit()
    return {"mock": mocks_service.mock_dict(mock)}


@router.get("/mocks")
def list_mocks(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(MockTest)
        .filter(MockTest.user_id == current_user.id)
        .order_by(MockTest.id.desc())
        .limit(50)
        .all()
    )
    return {"items": [mocks_service.mock_dict(m) for m in rows]}


@router.post("/mocks/{mock_id}/start")
def start_mock(
    mock_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    attempt = mocks_service.start_attempt(db, current_user.id, mock_id)
    db.commit()
    return {"attempt": mocks_service.attempt_dict(attempt)}


class SubmitRequest(BaseModel):
    answers: dict[int, str]


@router.post("/mocks/attempts/{attempt_id}/submit")
def submit_mock(
    attempt_id: int,
    body: SubmitRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = mocks_service.submit_attempt(db, current_user.id, attempt_id, body.answers)
    db.commit()
    return result


@router.get("/mocks/{mock_id}/attempts")
def mock_attempts(
    mock_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(MockTestAttempt)
        .filter(
            MockTestAttempt.user_id == current_user.id,
            MockTestAttempt.mock_test_id == mock_id,
        )
        .order_by(MockTestAttempt.id.desc())
        .all()
    )
    return {"items": [mocks_service.attempt_dict(a) for a in rows]}


# --------------------------------------------------------------------------- #
# Idea 65 — interview prep
# --------------------------------------------------------------------------- #
class InterviewStartRequest(BaseModel):
    skill: str = Field(min_length=1, max_length=200)
    level: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")


@router.post("/interview/start")
def interview_start(
    body: InterviewStartRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    session = interview_service.start(db, current_user.id, body.skill, body.level)
    db.commit()
    return {"session": interview_service.session_dict(session)}


class InterviewAnswerRequest(BaseModel):
    index: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=6000)


@router.post("/interview/{session_id}/answer")
def interview_answer(
    session_id: int,
    body: InterviewAnswerRequest,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = interview_service.answer(db, current_user.id, session_id, body.index, body.answer)
    db.commit()
    return result


@router.post("/interview/{session_id}/finish")
def interview_finish(
    session_id: int,
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    result = interview_service.finish(db, current_user.id, session_id)
    db.commit()
    return result
