"""Note-generated quizzes (Phase 4, Idea 33).

A content adapter over the existing ``Quiz`` machinery: gathers the document's
chunk text (heading-prefixed), reuses ``quiz_prompt`` + ``demo_quiz``, applies
the same <50-char gateway, and records a ``KbQuizLink`` for provenance
(phrases 22–26). Budget-capped via ``KB_DAILY_GEN_LIMIT``.
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import KbDocument, KbQuizLink, Quiz
from app.services.ai_fallback import demo_quiz
from app.services.kb import KbService
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.summarize import document_content

logger = logging.getLogger(__name__)


def generate_note_quiz(
    db: Session,
    user_id: int,
    document_id: int,
    num_questions: int = 10,
    difficulty: str = "medium",
) -> Quiz:
    """Generate a quiz from a vault document and record the provenance link."""
    doc = (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )
    if doc is None:
        raise HTTPException(404, "Document not found")

    content = document_content(db, doc)
    if len(content or "") < 50:
        raise HTTPException(422, "Not enough material to generate a quiz")

    num_questions = max(1, min(int(num_questions), 20))

    from app.services.ai_client import ai_available

    used_fallback = not ai_available()
    if not used_fallback and not budget_allows(db, user_id):
        raise HTTPException(429, "Daily generation budget exhausted — try again tomorrow.")

    questions: list[dict] = []
    if not used_fallback:
        try:
            from app.services.ai_client import generate_json
            from app.services.prompts import quiz_prompt

            parsed = generate_json(
                quiz_prompt(content, num_questions, difficulty),
                max_tokens=4000,
                temperature=0.7,
            )
            raw = parsed.get("questions") if isinstance(parsed, dict) else parsed
            for q in raw if isinstance(raw, list) else []:
                if not isinstance(q, dict):
                    continue
                options = q.get("options", [])
                if not isinstance(options, list):
                    options = []
                options = list(options)[:4]
                while len(options) < 4:
                    options.append("")
                try:
                    correct_index = max(0, min(3, int(q.get("correct_index", 0))))
                except (TypeError, ValueError):
                    correct_index = 0
                questions.append(
                    {
                        "question": str(q.get("question", "")),
                        "options": options,
                        "correct_index": correct_index,
                        "explanation": str(q.get("explanation", "")),
                    }
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Note-quiz generation failed for doc %s: %s", doc.id, exc)

    if not questions:
        used_fallback = True
        demo = demo_quiz(content)
        questions = [
            {
                "question": q.get("q", ""),
                "options": q.get("opts", []),
                "correct_index": q.get("ans", 0),
                "explanation": "",
            }
            for q in demo
        ]

    if not used_fallback:
        record_generation(db, user_id, "quiz")

    quiz = Quiz(
        unit_id=None,
        questions=questions,
        difficulty=difficulty,
    )
    db.add(quiz)
    db.flush()

    # Provenance link (phrase 26): the generating note stays traceable.
    db.add(
        KbQuizLink(user_id=user_id, quiz_id=quiz.id, document_id=document_id)
    )
    db.commit()
    db.refresh(quiz)
    return quiz


def quiz_source_document(db: Session, user_id: int, quiz_id: int) -> KbDocument | None:
    """Reverse lookup: the document a quiz was generated from (phrase 26)."""
    link = (
        db.query(KbQuizLink)
        .filter(KbQuizLink.user_id == user_id, KbQuizLink.quiz_id == quiz_id)
        .first()
    )
    if link is None:
        return None
    return (
        db.query(KbDocument)
        .filter(KbDocument.id == link.document_id, KbDocument.user_id == user_id)
        .first()
    )
