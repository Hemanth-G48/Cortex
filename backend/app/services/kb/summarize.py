"""Document summaries (Phase 4, Idea 31).

Cache-then-generate mirroring ``app.services.summaries``: the cache key is the
document's ``content_hash`` so a content change invalidates the summary
(phrase 4). Deterministic fallback when AI is disabled (phrase 8). Budget-capped
by ``KB_DAILY_GEN_LIMIT`` (phrase 1/27 shared meter).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import KbChunk, KbDocument, KbSummary
from app.services.ai_fallback import demo_kb_summary
from app.services.kb import KbService, utcnow
from app.services.kb.budget import budget_allows, record_generation

logger = logging.getLogger(__name__)


def document_content(db: Session, doc: KbDocument) -> str:
    """Joined, heading-prefixed chunk text — the content source (phrase 6)."""
    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc.id, KbChunk.user_id == doc.user_id)
        .order_by(KbChunk.seq.asc())
        .all()
    )
    if not chunks:
        return doc.extracted_text or ""
    parts = []
    for c in chunks:
        if c.heading_path:
            parts.append(f"## {c.heading_path}\n{c.content}")
        else:
            parts.append(c.content)
    return "\n\n".join(parts)


def _content_hash(doc: KbDocument) -> str:
    return KbService.content_hash((doc.extracted_text or "").encode("utf-8"))


def _parse_summary(parsed: object) -> dict | None:
    """Normalize the LLM response into {summary, key_points, definitions, open_questions}."""
    if not isinstance(parsed, dict):
        return None
    key_points = parsed.get("key_points")
    definitions = parsed.get("definitions")
    open_questions = parsed.get("open_questions")
    return {
        "summary": str(parsed.get("summary") or "").strip(),
        "key_points": (
            [str(k) for k in key_points if str(k).strip()]
            if isinstance(key_points, list)
            else []
        ),
        "definitions": (
            [
                {"term": str(d.get("term", "")).strip(), "definition": str(d.get("definition", "")).strip()}
                for d in definitions
                if isinstance(d, dict) and str(d.get("term", "")).strip()
            ]
            if isinstance(definitions, list)
            else []
        ),
        "open_questions": (
            [str(q) for q in open_questions if str(q).strip()]
            if isinstance(open_questions, list)
            else []
        ),
    }


def get_or_generate_summary(
    db: Session, user_id: int, doc: KbDocument, regenerate: bool = False
) -> dict:
    """Return a structured summary, generating only on miss/content change."""
    digest = _content_hash(doc)
    row = (
        db.query(KbSummary)
        .filter(KbSummary.user_id == user_id, KbSummary.document_id == doc.id)
        .first()
    )

    if row is not None and not regenerate and row.content_hash == digest:
        return {
            "summary": {
                "content": row.content,
                "key_points": KbService.json_loads(row.key_points) or [],
                "definitions": KbService.json_loads(row.definitions) or [],
                "open_questions": KbService.json_loads(row.open_questions) or [],
            },
            "cached": True,
            "document_id": doc.id,
        }

    # Generate path — budget gate only when a real LLM call is possible.
    from app.services.ai_client import ai_available

    used_fallback = not ai_available()
    if not used_fallback and not budget_allows(db, user_id):
        raise HTTPException(429, "Daily generation budget exhausted — try again tomorrow.")

    content = document_content(db, doc)
    parsed: dict | None = None
    model: str | None = None
    if not used_fallback:
        try:
            from app.config import settings
            from app.services.ai_client import generate_json
            from app.services.prompts import kb_summary_prompt

            model = settings.AI_MODEL
            parsed = _parse_summary(generate_json(kb_summary_prompt(content), max_tokens=2000, temperature=0.4))
        except Exception as exc:  # noqa: BLE001 — degrade to fallback
            logger.warning("Summary generation failed for doc %s: %s", doc.id, exc)
            parsed = None

    if parsed is None or not (parsed["summary"] or parsed["key_points"]):
        used_fallback = True
        fallback = demo_kb_summary(content)
        parsed = {
            "summary": fallback["summary"],
            "key_points": fallback["key_points"],
            "definitions": fallback["definitions"],
            "open_questions": fallback["open_questions"],
        }
        model = "demo"

    if not used_fallback:
        record_generation(db, user_id, "summary")

    # Upsert the cache row.
    if row is None:
        row = KbSummary(
            user_id=user_id,
            document_id=doc.id,
            content_hash=digest,
            model=model,
        )
        db.add(row)
    else:
        row.content_hash = digest
        row.model = model
        row.updated_at = utcnow()
    row.content = parsed["summary"]
    row.key_points = KbService.json_dumps(parsed["key_points"])
    row.definitions = KbService.json_dumps(parsed["definitions"])
    row.open_questions = KbService.json_dumps(parsed["open_questions"])
    db.commit()
    db.refresh(row)

    return {
        "summary": {
            "content": row.content,
            "key_points": parsed["key_points"],
            "definitions": parsed["definitions"],
            "open_questions": parsed["open_questions"],
        },
        "cached": False,
        "document_id": doc.id,
    }
