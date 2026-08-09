"""Phase 7 practice-question bank (Idea 63, phrases 21–30).

``generate_for_topic`` produces reviewable candidates (``status=pending``,
nothing auto-committed), hash-deduped per user. ``approve``/``reject`` move
questions in and out of the reusable bank consumed by mock tests (Idea 64)
and adaptive practice (Idea 67). Deterministic fallback builds template
questions from the topic's learning outcomes (phrase 27).
"""

from __future__ import annotations

import hashlib
import logging
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.models import PracticeQuestion, Topic
from app.services import ai_client, ai_fallback
from app.services.kb import KbService
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.tutor import retrieve_chunks

logger = logging.getLogger(__name__)

PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"

BLOOM_LEVELS = ("Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create")
DIFFICULTY_TIERS = ("E", "M", "H")


def question_hash(question: str) -> str:
    """Normalized question-text hash — the dedupe key (phrase 25)."""
    norm = re.sub(r"\s+", " ", (question or "").strip().lower())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _topic_chunks(db: Session, user_id: int, topic: Topic, limit: int = 4) -> str:
    """Retrieved vault context for the topic (used by LLM + fallback alike)."""
    items = retrieve_chunks(db, user_id, topic.name, limit=limit)
    if not items:
        outcomes = KbService.json_loads(topic.outcomes) or []
        lines = [o.get("text", "") for o in outcomes] or [f"Study topic: {topic.name}"]
        return "\n".join(f"- {l}" for l in lines)
    return "\n".join(f"- {(i.get('snippet') or '')[:300]}" for i in items)


def _normalize_candidates(raw: object) -> list[dict]:
    """Validate + normalize LLM output into candidate dicts."""
    out: list[dict] = []
    if isinstance(raw, dict):
        raw = raw.get("questions")
    if not isinstance(raw, list):
        return out
    for q in raw:
        if not isinstance(q, dict):
            continue
        question = str(q.get("q") or "").strip()
        options = q.get("options")
        if not question or not isinstance(options, list) or len(options) < 2:
            continue
        answer = str(q.get("answer") or (options[0] if options else "")).strip()
        bloom = str(q.get("bloom_level") or "Understand").capitalize()
        if bloom not in BLOOM_LEVELS:
            bloom = "Understand"
        out.append(
            {
                "question": question[:1000],
                "options": [str(o).strip()[:500] for o in options[:6]],
                "answer": answer[:500],
                "explanation": str(q.get("explanation") or "")[:800],
                "bloom_level": bloom,
                "difficulty": str(q.get("difficulty") or "M").upper()[:1] or "M",
            }
        )
    return out


def generate_for_topic(
    db: Session,
    user_id: int,
    topic: Topic,
    *,
    count: int | None = None,
    difficulty: str | None = None,
) -> list[PracticeQuestion]:
    """Generate candidate questions for a topic (phrases 23–24).

    Candidates are persisted as ``pending`` — nothing enters the reusable
    bank until approved (phrase 24). Duplicate question hashes are skipped.
    """
    count = max(1, min(20, count or settings.KB_PRACTICE_DEFAULT_COUNT))
    difficulty = (difficulty or "M").upper()[:1]
    if difficulty not in DIFFICULTY_TIERS:
        difficulty = "M"

    candidates: list[dict] = []
    used_ai = False
    if ai_client.ai_available() and budget_allows(db, user_id):
        from app.services.prompts import practice_questions_prompt

        chunks = _topic_chunks(db, user_id, topic)
        outcomes = [o.get("text", "") for o in (KbService.json_loads(topic.outcomes) or [])]
        parsed = ai_client.generate_json(
            practice_questions_prompt(topic.name, outcomes, count, difficulty, chunks),
            max_tokens=2000,
            temperature=0.6,
        )
        candidates = _normalize_candidates(parsed)
        if candidates:
            used_ai = True
            record_generation(db, user_id, "practice")

    if not candidates:
        candidates = _fallback_candidates(topic, count, difficulty)

    created: list[PracticeQuestion] = []
    existing_hashes = {
        row.question_hash
        for row in db.query(PracticeQuestion)
        .filter(PracticeQuestion.user_id == user_id)
        .all()
    }
    for c in candidates[:count]:
        h = question_hash(c["question"])
        if h in existing_hashes:
            continue
        row = PracticeQuestion(
            user_id=user_id,
            topic_id=topic.id,
            question=c["question"],
            options=KbService.json_dumps(c["options"]),
            answer=c["answer"],
            explanation=c["explanation"],
            bloom_level=c["bloom_level"],
            difficulty=c["difficulty"],
            status=PENDING,
            question_hash=h,
        )
        db.add(row)
        existing_hashes.add(h)
        created.append(row)
    db.flush()
    return created


def _fallback_candidates(topic: Topic, count: int, difficulty: str) -> list[dict]:
    """Template questions from outcomes (phrase 27)."""
    return ai_fallback.demo_practice_questions(topic.name, count, difficulty)[:count]


def approve_question(db: Session, user_id: int, question_id: int) -> PracticeQuestion:
    row = _owned(db, user_id, question_id)
    row.status = APPROVED
    db.flush()
    return row


def reject_question(db: Session, user_id: int, question_id: int) -> PracticeQuestion:
    row = _owned(db, user_id, question_id)
    row.status = REJECTED
    db.flush()
    return row


def _owned(db: Session, user_id: int, question_id: int) -> PracticeQuestion:
    row = db.query(PracticeQuestion).get(question_id)
    if row is None or row.user_id != user_id:
        from fastapi import HTTPException

        raise HTTPException(404, "Question not found")
    return row


def list_questions(
    db: Session,
    user_id: int,
    *,
    topic_id: int | None = None,
    status: str | None = None,
) -> list[PracticeQuestion]:
    q = db.query(PracticeQuestion).filter(PracticeQuestion.user_id == user_id)
    if topic_id:
        q = q.filter(PracticeQuestion.topic_id == topic_id)
    if status:
        q = q.filter(PracticeQuestion.status == status)
    return q.order_by(PracticeQuestion.id.desc()).limit(200).all()


def question_dict(row: PracticeQuestion, topic: Topic | None = None) -> dict:
    return {
        "id": row.id,
        "topic_id": row.topic_id,
        "topic_name": topic.name if topic else None,
        "question": row.question,
        "options": KbService.json_loads(row.options) or [],
        "answer": row.answer,
        "explanation": row.explanation,
        "bloom_level": row.bloom_level,
        "difficulty": row.difficulty,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def approved_for_topic(db: Session, user_id: int, topic_id: int) -> list[PracticeQuestion]:
    return (
        db.query(PracticeQuestion)
        .filter(
            PracticeQuestion.user_id == user_id,
            PracticeQuestion.topic_id == topic_id,
            PracticeQuestion.status == APPROVED,
        )
        .all()
    )


__all__ = [
    "generate_for_topic",
    "approve_question",
    "reject_question",
    "list_questions",
    "question_dict",
    "approved_for_topic",
    "question_hash",
]
