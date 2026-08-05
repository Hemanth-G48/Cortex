"""Summary generation service with caching and fallback."""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Summary


def _unit_key(unit_ids: list[int]) -> str:
    return ":".join(sorted(map(str, unit_ids)))


def find_cached(db: Session, unit_ids: list[int]) -> Optional[Summary]:
    key = _unit_key(unit_ids)
    return db.query(Summary).filter(Summary.key == key).first()


def generate_summary(db: Session, unit_ids: list[int]) -> dict:
    """Generate or retrieve a cached summary for the given unit IDs."""
    key = _unit_key(unit_ids)

    # Check cache first.
    cached = db.query(Summary).filter(Summary.key == key).first()
    if cached is not None:
        return {
            "summary": {
                "content": cached.content,
                "key_points": cached.key_points or [],
            },
            "cached": True,
        }

    # Gather content from units.
    from app.services.ingestion import extract_text_for_units

    content = extract_text_for_units(db, unit_ids)

    # Build the prompt.
    from app.services.prompts import summary_prompt, multi_unit_summary_prompt
    from app.services.ai_client import generate_json

    if len(unit_ids) == 1:
        prompt = summary_prompt(content or "")
    else:
        # For multi-unit, we pass unit names and content.
        # extract_text_for_units returns a single string; we pass it as one unit.
        prompt = multi_unit_summary_prompt([("units", content or "")])

    parsed = generate_json(prompt, max_tokens=3000, temperature=0.5)

    # Parse the result — handle both direct and wrapped formats.
    summary_text: str = ""
    key_points: list[str] = []

    if parsed is not None:
        if isinstance(parsed, dict):
            # Handle wrapped format {"summary": {"summary": ..., "key_points": ...}}
            inner = parsed.get("summary") if isinstance(parsed.get("summary"), dict) else parsed
            summary_text = inner.get("summary", "") if isinstance(inner, dict) else str(parsed.get("summary", ""))
            key_points = inner.get("key_points", []) if isinstance(inner, dict) else parsed.get("key_points", [])
        elif isinstance(parsed, list):
            key_points = parsed

    # Fallback if AI returned nothing usable.
    if not summary_text and not key_points:
        summary_text = _demo_summary(content or "")
        key_points = _demo_key_points(content or "")

    # Persist the summary row. ``content`` holds the generated summary text
    # (not the raw source), matching the Summary model/schema contract.
    row = Summary(
        key=key,
        unit_ids=unit_ids,
        content=summary_text,
        key_points=key_points,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "summary": {
            "content": row.content,
            "key_points": row.key_points or [],
        },
        "cached": False,
    }


def list_summaries(db: Session) -> list[Summary]:
    return db.query(Summary).order_by(Summary.created_at.desc()).all()


def delete_summary(db: Session, summary_id: int) -> bool:
    row = db.query(Summary).filter(Summary.id == summary_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def _demo_summary(content: str) -> str:
    sentences = [s.strip() for s in content.split(".") if s.strip()]
    if sentences:
        return ". ".join(sentences[:3]) + "."
    return "No summary available."


def _demo_key_points(content: str) -> list[str]:
    sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20]
    return sentences[:5] if sentences else ["No key points available."]
