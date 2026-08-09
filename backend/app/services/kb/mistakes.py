"""Phase 7 explain-my-mistake analysis (Idea 68, phrases 71–80).

``analyze`` compares a student answer against the model solution, pinpoints
the divergence (LLM, budget-capped; keyword-diff fallback), recommends the
note to re-read + concept to review, creates a scheduled revision task
(phrase 75), and logs a ``mistake`` learning event. Persists the walkthrough
in ``mistake_analyses`` (phrase 76).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import KbConcept, MistakeAnalysis, PracticeQuestion, Topic
from app.services import ai_client, ai_fallback
from app.services.kb import KbService, utcnow
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.mastery import log_event
from app.services.kb.revision import first_review
from app.services.kb.tutor import retrieve_chunks

logger = logging.getLogger(__name__)


def _owned_question(db: Session, user_id: int, question_id: int) -> PracticeQuestion:
    row = db.query(PracticeQuestion).get(question_id)
    if row is None or row.user_id != user_id:
        from fastapi import HTTPException

        raise HTTPException(404, "Question not found")
    return row


def analyze(
    db: Session,
    user_id: int,
    question_id: int,
    student_answer: str,
) -> dict:
    """Full mistake walkthrough (phrases 72–77)."""
    question = _owned_question(db, user_id, question_id)
    model_solution = question.answer or question.explanation or ""
    topic = db.query(Topic).get(question.topic_id)

    # Recommendation chunk (phrase 73): most relevant vault note.
    items = retrieve_chunks(db, user_id, question.question, limit=3)
    recommended_chunk_id = items[0].get("chunk_id") if items else None

    # Recommendation concept (phrase 74): kb_concepts matching the question.
    recommended_concept_id = None
    concept_def = None
    for concept in db.query(KbConcept).filter(KbConcept.user_id == user_id).all():
        names = [concept.canonical_name or ""] + (KbService.json_loads(concept.aliases) or [])
        if any(str(n).strip().lower() and str(n).strip().lower() in question.question.lower() for n in names):
            recommended_concept_id = concept.id
            concept_def = concept.definition
            break

    chunks = "\n".join(f"- {(i.get('snippet') or '')[:300]}" for i in items) or model_solution[:1000]
    used_ai = False
    analysis: dict | None = None

    if ai_client.ai_available() and budget_allows(db, user_id):
        from app.services.prompts import mistake_analysis_prompt

        parsed = ai_client.generate_json(
            mistake_analysis_prompt(question.question, model_solution, student_answer, chunks),
            max_tokens=700,
            temperature=0.3,
        )
        if isinstance(parsed, dict) and parsed.get("divergence"):
            used_ai = True
            record_generation(db, user_id, "mistake")
            analysis = {
                "divergence": str(parsed["divergence"]),
                "missed_points": [str(p) for p in parsed.get("missed_points") or []][:6],
                "recommendation": str(parsed.get("recommendation") or ""),
            }

    if analysis is None:
        fb = ai_fallback.demo_mistake_analysis(question.question, model_solution, student_answer)
        analysis = fb

    # Create a scheduled revision task (phrase 75) — due today, enters SM-2.
    revision_created = 0
    if topic is not None and topic.user_id == user_id:
        schedule = first_review(db, user_id, topic)
        schedule.due_date = utcnow()
        revision_created = 1

    # Persist the walkthrough (phrase 76).
    row = MistakeAnalysis(
        user_id=user_id,
        question_id=question_id,
        student_answer=student_answer,
        walkthrough=analysis["divergence"],
        missed_points=KbService.json_dumps(analysis["missed_points"]),
        recommended_chunk_id=recommended_chunk_id,
        recommended_concept_id=recommended_concept_id,
        revision_task_created=revision_created,
    )
    db.add(row)

    # Learning event (phrase 76).
    log_event(
        db, user_id, event_type="mistake",
        topic_id=question.topic_id if topic else None, value=0.0,
    )
    db.flush()

    return {
        "analysis_id": row.id,
        "divergence": analysis["divergence"],
        "missed_points": analysis["missed_points"],
        "recommendation": analysis["recommendation"],
        "recommended_chunk_id": recommended_chunk_id,
        "recommended_concept_id": recommended_concept_id,
        "concept_definition": concept_def,
        "revision_task_created": bool(revision_created),
        "ai_used": used_ai,
    }


__all__ = ["analyze"]
