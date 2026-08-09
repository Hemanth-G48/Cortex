"""Phase 7 interview preparation (Idea 65, phrases 41–50).

``start`` generates conceptual + problem-style questions for a skill's topics
via the question generator (budget-capped); answers are graded through the
extended ``grade-answer`` service (phrase 43) with cited feedback (phrase 44);
the session aggregate feeds the skill-level computation (phrase 47).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import InterviewSession, Topic
from app.services import ai_client, ai_fallback
from app.services.kb import KbService
from app.services.kb import questions as questions_service
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.grading import grade_answer
from app.services.kb.skills import _keyword_match

logger = logging.getLogger(__name__)

LEVELS = ("beginner", "intermediate", "advanced")


def _topics_for_skill(db: Session, user_id: int, skill: str) -> list[Topic]:
    """Topics matching the skill's taxonomy keywords (phrase 42)."""
    matches = _keyword_match(skill)
    hay = set()
    for sid in matches:
        try:
            from app.services.kb.skills import load_taxonomy

            for s in load_taxonomy().get("skills", []):
                if s["id"] == sid:
                    hay.update(k.lower() for k in s.get("keywords", []))
        except Exception:  # noqa: BLE001
            continue
    hay.add(skill.lower())
    out = []
    for t in db.query(Topic).filter(Topic.user_id == user_id).all():
        blob = f"{t.name} {' '.join(o.get('text', '') for o in (KbService.json_loads(t.outcomes) or []))}".lower()
        if any(k and k in blob for k in hay):
            out.append(t)
    return out[:6]


def _build_questions(db: Session, user_id: int, skill: str, level: str, topics: list[Topic]) -> list[dict]:
    """Generate 4–6 interview questions (phrases 42, 44)."""
    out: list[dict] = []
    if topics and ai_client.ai_available() and budget_allows(db, user_id):
        from app.services.prompts import practice_questions_prompt

        for topic in topics[:3]:
            parsed = ai_client.generate_json(
                practice_questions_prompt(topic.name, [], 2, "M", f"- {topic.name}\n- {topic.bloom_level or 'Understand'} level"),
                max_tokens=1400,
                temperature=0.6,
            )
            cands = questions_service._normalize_candidates(parsed)
            for c in cands[:2]:
                out.append(
                    {
                        "question": c["question"],
                        "topic_id": topic.id,
                        "expected": c["answer"],
                        "model_solution": c["explanation"] or c["answer"],
                    }
                )
        if out:
            record_generation(db, user_id, "interview")
    if not out:
        # Template questions from the skill + matched topics (no LLM).
        names = ", ".join(t.name for t in topics) or skill
        for i in range(4):
            out.append(
                {
                    "question": f"Explain how you would approach a {level} problem about {skill} (related topic: {names}).",
                    "topic_id": topics[i].id if i < len(topics) else None,
                    "expected": f"A clear, structured explanation covering the key ideas of {skill}.",
                    "model_solution": f"Cover the core ideas of {skill}; define key terms; give a concrete example; note common pitfalls.",
                }
            )
    return out


def start(db: Session, user_id: int, skill: str, level: str | None = None) -> InterviewSession:
    """Open an interview session (phrase 41)."""
    level = level if level in LEVELS else "intermediate"
    topics = _topics_for_skill(db, user_id, skill)
    questions = _build_questions(db, user_id, skill, level, topics)
    session = InterviewSession(
        user_id=user_id,
        skill=skill[:200],
        level=level,
        questions=KbService.json_dumps(questions),
        answers=KbService.json_dumps({}),
        total_score=0,
        status="in_progress",
    )
    db.add(session)
    db.flush()
    return session


def answer(db: Session, user_id: int, session_id: int, index: int, answer_text: str) -> dict:
    """Grade one answer via the advanced grader + cited feedback (phrases 43–44)."""
    session = _owned(db, user_id, session_id)
    questions = KbService.json_loads(session.questions) or []
    answers = KbService.json_loads(session.answers) or {}
    if index < 0 or index >= len(questions):
        raise HTTPException(400, "Question index out of range")
    if str(index) in answers:
        raise HTTPException(400, "Question already answered")

    q = questions[index]
    graded = grade_answer(
        db,
        user_id,
        q.get("question", ""),
        q.get("expected", ""),
        answer_text,
        topic_id=q.get("topic_id"),
    )
    result = graded["grade"]
    answers[str(index)] = {
        "answer": answer_text,
        "score": result["score"],
        "strengths": result["strengths"],
        "misconceptions": result["misconceptions"],
        "action_items": result["action_items"],
    }
    session.answers = KbService.json_dumps(answers)
    scores = [a.get("score", 0) for a in answers.values()]
    session.total_score = round(sum(scores) / len(scores)) if scores else 0
    db.flush()

    return {
        "index": index,
        "score": result["score"],
        "strengths": result["strengths"],
        "misconceptions": result["misconceptions"],
        "action_items": result["action_items"],
        "ai_used": graded["ai_used"],
    }


def finish(db: Session, user_id: int, session_id: int) -> dict:
    """Mark completed; feed the aggregate into the skill map (phrase 47)."""
    session = _owned(db, user_id, session_id)
    session.status = "completed"
    answers = KbService.json_loads(session.answers) or {}
    total = len(answers)
    if total:
        from app.services.kb.skills import apply_interview_score

        apply_interview_score(db, user_id, session.skill, session.total_score)
    db.flush()
    return {
        "session_id": session.id,
        "skill": session.skill,
        "level": session.level,
        "answered": total,
        "total_score": session.total_score,
        "status": session.status,
    }


def _owned(db: Session, user_id: int, session_id: int) -> InterviewSession:
    session = db.query(InterviewSession).get(session_id)
    if session is None or session.user_id != user_id:
        raise HTTPException(404, "Interview session not found")
    return session


def session_dict(session: InterviewSession) -> dict:
    return {
        "id": session.id,
        "skill": session.skill,
        "level": session.level,
        "questions": KbService.json_loads(session.questions) or [],
        "answers": KbService.json_loads(session.answers) or {},
        "total_score": session.total_score,
        "status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
    }


__all__ = ["start", "answer", "finish", "session_dict"]
