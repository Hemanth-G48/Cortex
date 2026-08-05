"""Quiz generation and scoring service."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Quiz


def generate_quiz(
    db: Session,
    unit_id: int,
    num_questions: int = 10,
    difficulty: str = "medium",
) -> Quiz:
    """Generate a quiz for a curriculum unit, with fallback."""
    from app.services.ingestion import extract_text_for_units
    from app.services.ai_client import generate_json
    from app.services.ai_fallback import demo_quiz
    from app.services.prompts import quiz_prompt

    # Check the unit has enough material.
    content = extract_text_for_units(db, [unit_id])
    if len(content or "") < 50:
        raise HTTPException(422, "Not enough material to generate a quiz")

    prompt = quiz_prompt(content, num_questions, difficulty)
    parsed = generate_json(prompt, max_tokens=4000, temperature=0.7)

    questions: list[dict] = []

    if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
        raw_questions = parsed["questions"]
    elif isinstance(parsed, list):
        raw_questions = parsed
    else:
        raw_questions = []

    for q in raw_questions:
        if not isinstance(q, dict):
            continue
        question_text = q.get("question", "")
        options = q.get("options", [])
        if not isinstance(options, list) or len(options) != 4:
            # Pad or trim to exactly 4.
            options = list(options)[:4]
            while len(options) < 4:
                options.append("")
        correct_index = q.get("correct_index", 0)
        try:
            correct_index = int(correct_index)
        except (TypeError, ValueError):
            correct_index = 0
        correct_index = max(0, min(3, correct_index))
        explanation = q.get("explanation", "")

        questions.append(
            {
                "question": question_text,
                "options": options,
                "correct_index": correct_index,
                "explanation": explanation,
            }
        )

    # If AI returned nothing usable, fall back to demo quiz.
    if not questions:
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

    quiz = Quiz(
        unit_id=unit_id,
        questions=questions,
        difficulty=difficulty,
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    return quiz


def score_attempt(db: Session, quiz: Quiz, answers: list[int]) -> dict:
    """Score a quiz attempt and return detailed results."""
    questions = quiz.questions or []
    total = len(questions)
    results = []
    score = 0

    for i, q in enumerate(questions):
        correct_index = q.get("correct_index", 0)
        selected = answers[i] if i < len(answers) else None
        correct = selected is not None and selected == correct_index
        if correct:
            score += 1
        results.append(
            {
                "question_index": i,
                "selected": selected,
                "correct": correct,
                "correct_index": correct_index,
                "explanation": q.get("explanation", ""),
            }
        )

    percentage = round((score / total) * 100, 1) if total > 0 else 0.0

    return {
        "score": score,
        "total": total,
        "percentage": percentage,
        "results": results,
    }
