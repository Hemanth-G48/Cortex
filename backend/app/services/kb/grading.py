"""Phase 7 advanced answer grading (Idea 66, phrases 51–60).

Extends the existing ``grade-answer`` endpoint with an ``advanced`` mode that
returns partial credit + structured feedback: ``{score (0–100), strengths[],
misconceptions[], action_items[]}``. The rubric is built from the topic's
retrieved chunks (Phase 3 search); key-point coverage drives the score, not
binary right/wrong (phrase 54). Results persist to ``learning_events`` as
``event_type=grade`` (phrase 55). Budget-capped with a keyword-overlap
fallback (phrase 56).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import Topic
from app.services import ai_client, ai_fallback
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.mastery import log_event
from app.services.kb.tutor import retrieve_chunks

logger = logging.getLogger(__name__)


def build_rubric(db: Session, user_id: int, topic_id: int | None, question: str) -> str:
    """Key-point rubric from the topic's chunks (phrase 52)."""
    if topic_id is not None:
        topic = db.query(Topic).get(topic_id)
        if topic is not None and topic.user_id == user_id:
            items = retrieve_chunks(db, user_id, topic.name, limit=4)
            if items:
                return "\n".join(f"- {(i.get('snippet') or '')[:300]}" for i in items)
    return "Cover the main idea of the question; full credit requires the key points of the expected answer."


def grade_answer(
    db: Session,
    user_id: int,
    question: str,
    expected: str,
    answer: str,
    *,
    topic_id: int | None = None,
) -> dict:
    """Advanced partial-credit grading (phrases 53–55)."""
    rubric = build_rubric(db, user_id, topic_id, question)
    used_ai = False
    result: dict | None = None

    if ai_client.ai_available() and budget_allows(db, user_id):
        from app.services.prompts import grading_prompt

        parsed = ai_client.generate_json(
            grading_prompt(question, expected, answer, rubric),
            max_tokens=700,
            temperature=0.2,
        )
        if isinstance(parsed, dict) and isinstance(parsed.get("score"), (int, float)):
            used_ai = True
            record_generation(db, user_id, "grading")
            result = {
                "score": max(0, min(100, int(parsed["score"]))),
                "strengths": [str(s) for s in parsed.get("strengths") or []][:5],
                "misconceptions": [str(s) for s in parsed.get("misconceptions") or []][:5],
                "action_items": [str(s) for s in parsed.get("action_items") or []][:5],
            }

    if result is None:
        fb = ai_fallback.demo_grade_advanced(question, expected, answer)
        result = {
            "score": fb["score"],
            "strengths": fb["strengths"],
            "misconceptions": fb["misconceptions"],
            "action_items": fb["action_items"],
        }

    # Persist to learning events (phrase 55) — feeds mastery + progress.
    log_event(db, user_id, event_type="grade", topic_id=topic_id, value=result["score"] / 100.0)
    db.flush()
    return {"grade": result, "ai_used": used_ai}


__all__ = ["grade_answer", "build_rubric"]
