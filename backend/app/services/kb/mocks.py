"""Phase 7 mock tests & exam simulations (Idea 64, phrases 31–40).

``build_paper`` assembles a MockTest from the subject's grading scheme
(section weights) and topic difficulty: approved bank questions are reused
first, missing ones are generated on demand (budget-capped, phrase 35).
``start``/``submit`` run a server-side-timed attempt (phrase 36) and return
per-section + per-topic accuracy analytics (phrase 37).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import MockTest, MockTestAttempt, PracticeQuestion, SubjectProfile, Topic
from app.services.kb import KbService, utcnow
from app.services.kb import questions as questions_service
from app.services.kb.mastery import log_event

logger = logging.getLogger(__name__)

PENDING, ACTIVE, COMPLETED = "draft", "active", "completed"


def _subject_topics(db: Session, user_id: int, subject_id: int) -> list[Topic]:
    return (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == subject_id)
        .all()
    )


def _topic_weight(topic: Topic) -> float:
    """Section/question weight from topic difficulty (E=1, M=2, H=3)."""
    return {"E": 1.0, "M": 2.0, "H": 3.0}.get(topic.difficulty, 2.0)


def _unit_sections(db: Session, user_id: int, subject_id: int, topics: list[Topic]) -> list[dict]:
    """Section titles from the subject's units (Phase 5 parsed structure)."""
    profile = (
        db.query(SubjectProfile)
        .filter(
            SubjectProfile.user_id == user_id,
            SubjectProfile.curriculum_subject_id == subject_id,
        )
        .first()
    )
    units: list[dict] = []
    if profile is not None:
        parsed = KbService.json_loads(profile.parsed_json) or {}
        units = parsed.get("units") or []
    if not units:
        return [{"title": f"Section {i + 1}", "topic_ids": []} for i in range(1)]
    return [{"title": u.get("title") or f"Unit {i + 1}", "topic_ids": []} for i, u in enumerate(units)]


def build_paper(
    db: Session,
    user_id: int,
    subject_id: int,
    *,
    title: str | None = None,
    question_count: int | None = None,
    duration_mins: int | None = None,
) -> MockTest:
    """Assemble a mock paper from the grading scheme + bank (phrases 34–35)."""
    topics = _subject_topics(db, user_id, subject_id)
    if not topics:
        raise HTTPException(400, "No topics found for this subject — generate topics first")

    total = max(3, min(50, question_count or settings.KB_MOCK_DEFAULT_QUESTIONS))
    duration = max(5, duration_mins or settings.KB_MOCK_DEFAULT_DURATION_MINS)

    # Weight topics by difficulty → question counts.
    weights = [_topic_weight(t) for t in topics]
    total_w = sum(weights) or 1.0
    counts = [max(1, round(total * w / total_w)) for w in weights]
    # Trim to exactly `total` by reducing the heaviest bucket.
    diff = sum(counts) - total
    for i in range(diff):
        counts[counts.index(max(counts))] -= 1

    sections = _unit_sections(db, user_id, subject_id, topics)
    section_questions: dict[int, list[int]] = {s["title"]: [] for s in sections}
    # Assign topics to the first section that shares a unit (or section 0).
    by_unit: dict[int, str] = {}
    for i, t in enumerate(topics):
        unit_title = sections[0]["title"] if sections else "Section 1"
        for s in sections:
            if s["title"] == (f"Unit {i + 1}"):
                unit_title = s["title"]
        by_unit[t.id] = unit_title

    qids: list[int] = []
    for topic, count in zip(topics, counts):
        bank = questions_service.approved_for_topic(db, user_id, topic.id)
        picked = 0
        for q in bank:
            if picked >= count:
                break
            qids.append(q.id)
            picked += 1
        # Generate missing on demand (phrase 35) and auto-approve for the paper.
        while picked < count:
            generated = questions_service.generate_for_topic(
                db, user_id, topic, count=count - picked, difficulty=topic.difficulty or "M"
            )
            if not generated:
                break
            for q in generated:
                q.status = "approved"
                qids.append(q.id)
                picked += 1

    questions = db.query(PracticeQuestion).filter(PracticeQuestion.id.in_(qids)).all()
    q_by_id = {q.id: q for q in questions}
    paper_questions = [
        {"id": q.id, "topic_id": q.topic_id, "question": q.question,
         "options": KbService.json_loads(q.options) or [], "answer": q.answer,
         "explanation": q.explanation, "difficulty": q.difficulty}
        for q in questions
    ]

    structure = {
        "sections": [
            {"title": s["title"], "question_ids": [qid for qid in qids if q_by_id.get(qid) and by_unit.get(q_by_id[qid].topic_id) == s["title"]]}
            for s in sections
        ],
        "questions": paper_questions,
    }
    # Fallback: put all questions in section 0 when unit mapping is empty.
    if not any(s["question_ids"] for s in structure["sections"]):
        structure["sections"] = [{"title": "Full Paper", "question_ids": qids}]

    mock = MockTest(
        user_id=user_id,
        subject_id=subject_id,
        title=(title or f"Mock {subject_id}").strip()[:300],
        structure_json=KbService.json_dumps(structure),
        duration_mins=duration,
        status=ACTIVE,
    )
    db.add(mock)
    db.flush()
    return mock


def start_attempt(db: Session, user_id: int, mock_test_id: int) -> MockTestAttempt:
    """Open a timed attempt (phrase 36)."""
    mock = _owned_mock(db, user_id, mock_test_id)
    attempt = MockTestAttempt(user_id=user_id, mock_test_id=mock.id)
    db.add(attempt)
    db.flush()
    return attempt


def submit_attempt(
    db: Session,
    user_id: int,
    attempt_id: int,
    answers: dict[int, str],
) -> dict:
    """Score an attempt with per-topic analytics (phrases 36–37)."""
    attempt = db.query(MockTestAttempt).get(attempt_id)
    if attempt is None or attempt.user_id != user_id:
        raise HTTPException(404, "Attempt not found")
    if attempt.finished_at is not None:
        raise HTTPException(400, "Attempt already submitted")

    mock = _owned_mock(db, user_id, attempt.mock_test_id)
    structure = KbService.json_loads(mock.structure_json) or {"questions": []}
    questions = {q["id"]: q for q in structure.get("questions", [])}

    score = 0
    total = 0
    per_topic: dict[int, dict] = {}
    for qid, selected in (answers or {}).items():
        qid = int(qid)
        q = questions.get(qid)
        if q is None:
            continue
        total += 1
        tid = q.get("topic_id")
        bucket = per_topic.setdefault(tid, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if str(selected).strip() == str(q.get("answer") or "").strip():
            score += 1
            bucket["correct"] += 1

    # Server-side duration check (phrase 36): late submissions are flagged.
    late = False
    if attempt.started_at is not None:
        elapsed = (utcnow() - attempt.started_at).total_seconds() / 60.0
        late = elapsed > (mock.duration_mins or settings.KB_MOCK_DEFAULT_DURATION_MINS)

    attempt.answers = KbService.json_dumps({str(k): v for k, v in (answers or {}).items()})
    attempt.score = score
    attempt.total = total
    attempt.per_topic = KbService.json_dumps(per_topic)
    attempt.finished_at = utcnow()

    # Learning events per topic (feeds mastery / progress).
    for tid, bucket in per_topic.items():
        acc = bucket["correct"] / bucket["total"] if bucket["total"] else 0.0
        log_event(db, user_id, event_type="quiz", topic_id=tid, value=acc)
    db.flush()

    return {
        "attempt_id": attempt.id,
        "mock_test_id": mock.id,
        "score": score,
        "total": total,
        "percentage": round(score / total * 100, 1) if total else 0.0,
        "late_submission": late,
        "per_topic": {
            str(tid): bucket for tid, bucket in per_topic.items()
        },
    }


def _owned_mock(db: Session, user_id: int, mock_test_id: int) -> MockTest:
    mock = db.query(MockTest).get(mock_test_id)
    if mock is None or mock.user_id != user_id:
        raise HTTPException(404, "Mock test not found")
    return mock


def mock_dict(mock: MockTest) -> dict:
    """Public shape of a mock paper (answers stay server-side until submit)."""
    structure = KbService.json_loads(mock.structure_json) or {}
    return {
        "id": mock.id,
        "subject_id": mock.subject_id,
        "title": mock.title,
        "duration_mins": mock.duration_mins,
        "status": mock.status,
        "sections": structure.get("sections", []),
        "question_count": len(structure.get("questions", [])),
        # Exam-run surface: id/topic/question/options/difficulty only — the
        # answer + explanation are stripped so the frontend can't leak them.
        "questions": [
            {k: q[k] for k in ("id", "topic_id", "question", "options", "difficulty") if k in q}
            for q in structure.get("questions", [])
        ],
        "created_at": mock.created_at.isoformat() if mock.created_at else None,
    }


def attempt_dict(attempt: MockTestAttempt) -> dict:
    return {
        "id": attempt.id,
        "mock_test_id": attempt.mock_test_id,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None,
        "score": attempt.score,
        "total": attempt.total,
        "per_topic": KbService.json_loads(attempt.per_topic) or {},
    }


__all__ = ["build_paper", "start_attempt", "submit_attempt", "mock_dict", "attempt_dict"]
