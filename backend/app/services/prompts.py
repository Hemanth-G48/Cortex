"""Prompt templates for AI-generated summaries and quizzes."""
from __future__ import annotations


def summary_prompt(content: str) -> str:
    """Prompt for a single-unit summary. Returns strict JSON only."""
    snippet = content[:15000]
    return (
        "Summarize the following educational content. Return STRICT JSON only, "
        "no markdown, no extra text. The JSON must be an object with exactly "
        "two keys: \"summary\" (a concise paragraph) and \"key_points\" "
        "(an array of 3-6 short bullet strings).\n\n"
        f"Content:\n{snippet}"
    )


def multi_unit_summary_prompt(units: list[tuple[str, str]]) -> str:
    """Prompt for a multi-unit summary. Returns strict JSON only."""
    parts = []
    for name, content in units:
        snippet = content[:15000]
        parts.append(f"## Unit: {name}\n\n{snippet}")
    combined = "\n\n".join(parts)
    return (
        "Summarize the following educational units. Return STRICT JSON only, "
        "no markdown, no extra text. The JSON must be an object with three keys: "
        "\"summary\" (a concise paragraph covering all units), \"key_points\" "
        "(an array of 3-6 short bullet strings), and \"sections\" (an array of "
        "objects, each with \"unit\" (the unit name) and \"summary\" (a short "
        "paragraph for that unit)).\n\n"
        f"Units:\n{combined}"
    )


def quiz_prompt(content: str, num_questions: int, difficulty: str) -> str:
    """Prompt for quiz generation. Returns strict JSON only."""
    snippet = content[:15000]
    return (
        f"Generate exactly {num_questions} multiple-choice questions from the "
        f"following content at {difficulty} difficulty. Return STRICT JSON only, "
        "no markdown, no extra text. The JSON must be an object with one key "
        "\"questions\" which is an array of objects. Each object must have: "
        "\"question\" (string), \"options\" (array of exactly 4 strings), "
        "\"correct_index\" (integer 0-3), and \"explanation\" (string).\n\n"
        f"Content:\n{snippet}"
    )
