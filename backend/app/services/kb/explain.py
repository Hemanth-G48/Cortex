"""Grounded AI explanations (Phase 4 Idea 32, Phase 8 Idea 73).

Pipeline: retrieve grounding chunks via ``KbSearcher`` (hybrid mode) → build a
depth-specific prompt demanding inline ``[n]`` citations → generate → verify the
response carries a ``citations`` list (regenerate once when missing, budget-aware)
→ deterministic fallback when AI is unavailable.

Phase 8 (Idea 73) adds ``explain_personalized``: the standard pipeline driven by
the user's ``user_memory`` anchors (Rule A — only concepts with strength > 0)
and their ``UserPreference`` profile (depth/style). When memory or preferences
are empty the personalized prompt degrades to the standard grounded prompt, so
both functions share one generation core (``_generate``).
"""

from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import KbConcept
from app.services.ai_fallback import demo_explain
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.memory import anchors
from app.services.kb.preferences import get_preferences, preferences_prompt
from app.services.kb.search import KbSearcher
from app.services.prompts import EXPLAIN_DEPTHS, explain_prompt, explain_prompt_personalized

logger = logging.getLogger(__name__)

MAX_GROUNDING_CHUNKS = 6


def _build_context(items: list[dict]) -> tuple[str, list[tuple[int, str]], list[dict]]:
    """Number the retrieved chunks and return (context_text, titles, chunk refs)."""
    parts: list[str] = []
    titles: list[tuple[int, str]] = []
    refs: list[dict] = []
    for i, item in enumerate(items, start=1):
        snippet = (item.get("snippet") or item.get("title") or "")[:500]
        heading = item.get("heading_path") or ""
        parts.append(f"[{i}] ({heading}) {snippet}".strip())
        titles.append((i, item.get("title") or f"doc {item.get('document_id')}"))
        refs.append(item)
    return "\n".join(parts), titles, refs


def _concept_definition(db: Session, user_id: int, concept: str) -> str | None:
    row = (
        db.query(KbConcept)
        .filter(KbConcept.user_id == user_id, KbConcept.canonical_name.ilike(concept))
        .first()
    )
    if row is None:
        row = (
            db.query(KbConcept)
            .filter(KbConcept.user_id == user_id, KbConcept.canonical_name.ilike(f"%{concept}%"))
            .first()
        )
    return row.definition if row else None


def _generate(
    db: Session,
    user_id: int,
    concept: str,
    depth: str,
    context: str,
    titles: list[tuple[int, str]],
    refs: list[dict],
    *,
    prompt_for: object,
) -> tuple[str, list[dict], bool]:
    """Budget-gated generation + citation verification + deterministic fallback.

    ``prompt_for`` is a zero-arg callable returning the (possibly personalized)
    prompt; ``_generate`` never decides what the prompt says. Returns
    ``(explanation, citations, used_fallback)`` and records nothing — callers
    own the generation-kind accounting so they can use the Phase 8 kind.
    """
    from app.services.ai_client import ai_available, generate_json

    used_fallback = not ai_available()
    if not used_fallback and not budget_allows(db, user_id, 2):
        raise HTTPException(429, "Daily generation budget exhausted — try again tomorrow.")

    explanation: str = ""
    citations: list[dict] = []

    if not used_fallback:
        try:
            parsed = generate_json(prompt_for(), max_tokens=2000, temperature=0.4)
            if isinstance(parsed, dict):
                explanation = str(parsed.get("explanation") or "").strip()
                raw_cites = parsed.get("citations")
                if isinstance(raw_cites, list):
                    citations = [
                        {"chunk_index": int(c), "chunk_id": refs[int(c) - 1]["chunk_id"]}
                        for c in raw_cites
                        if isinstance(c, (int, float)) and 1 <= int(c) <= len(refs)
                    ]
            # Mandatory-citation post-check: regenerate once if missing
            # (budget-aware — needs 1 more slot which the gate above reserved).
            if (not explanation) or not citations:
                parsed2 = generate_json(prompt_for(), max_tokens=2000, temperature=0.4)
                if isinstance(parsed2, dict):
                    explanation = str(parsed2.get("explanation") or explanation).strip()
                    raw2 = parsed2.get("citations")
                    if isinstance(raw2, list):
                        citations = [
                            {"chunk_index": int(c), "chunk_id": refs[int(c) - 1]["chunk_id"]}
                            for c in raw2
                            if isinstance(c, (int, float)) and 1 <= int(c) <= len(refs)
                        ]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Explanation generation failed for %r: %s", concept, exc)
            explanation = ""
            citations = []

    if not explanation:
        used_fallback = True
        definition = _concept_definition(db, user_id, concept)
        excerpt = refs[0].get("snippet") if refs else None
        fallback = demo_explain(concept, depth, definition, excerpt)
        explanation = fallback["explanation"]

    return explanation, citations, used_fallback


def _expand_citations(citations: list[dict], refs: list[dict]) -> list[dict]:
    """Attach document metadata to citation refs for the UI."""
    expanded = []
    for c in citations:
        ref = refs[c["chunk_index"] - 1] if 0 <= c["chunk_index"] - 1 < len(refs) else {}
        expanded.append(
            {
                "chunk_id": c["chunk_id"],
                "document_id": ref.get("document_id"),
                "title": ref.get("title"),
                "snippet": (ref.get("snippet") or "")[:300],
                "source_path": ref.get("source_path"),
                "heading_path": ref.get("heading_path"),
            }
        )
    return expanded


def _retrieve(db: Session, user_id: int, concept: str, document_ids: list[int] | None) -> tuple[str, list[tuple[int, str]], list[dict]]:
    searcher = KbSearcher(db, user_id)
    result = searcher.search(concept, mode="hybrid", limit=MAX_GROUNDING_CHUNKS * 3)
    items = result["items"]
    if document_ids:
        wanted = set(document_ids)
        items = [i for i in items if i["document_id"] in wanted]
    return _build_context(items[:MAX_GROUNDING_CHUNKS])


def explain(
    db: Session,
    user_id: int,
    concept: str,
    depth: str = "overview",
    document_ids: list[int] | None = None,
) -> dict:
    """Ground, generate, and verify an explanation of ``concept``."""
    concept = (concept or "").strip()
    if not concept:
        raise HTTPException(400, "concept must not be empty")
    if depth not in EXPLAIN_DEPTHS:
        raise HTTPException(400, f"depth must be one of {', '.join(EXPLAIN_DEPTHS)}")

    context, titles, refs = _retrieve(db, user_id, concept, document_ids)
    explanation, citations, used_fallback = _generate(
        db, user_id, concept, depth, context, titles, refs,
        prompt_for=lambda: explain_prompt(concept, depth, context, titles),
    )

    if not used_fallback:
        record_generation(db, user_id, "explain")
    db.commit()

    return {
        "concept": concept,
        "depth": depth,
        "explanation": explanation,
        "citations": _expand_citations(citations, refs),
        "fallback": used_fallback,
        "anchors": [],
        "personalized": False,
        "document_ids": sorted({c["document_id"] for c in _expand_citations(citations, refs) if c.get("document_id")}),
    }


def explain_personalized(
    db: Session,
    user_id: int,
    concept: str,
    depth: str | None = None,
    document_ids: list[int] | None = None,
) -> dict:
    """Grounded explanation anchored on known memory + style/depth preferences.

    ``depth`` defaults to the user's preferred depth. ``anchors`` are only
    ``user_memory`` concepts with strength > 0 (Rule A); ``profile_line`` is
    empty until onboarding completes, so an empty profile degrades to the
    standard grounded prompt (phrase 26).
    """
    concept = (concept or "").strip()
    if not concept:
        raise HTTPException(400, "concept must not be empty")

    profile = get_preferences(db, user_id)
    depth = (depth or profile.get("depth") or "overview")
    if depth not in EXPLAIN_DEPTHS:
        raise HTTPException(400, f"depth must be one of {', '.join(EXPLAIN_DEPTHS)}")

    context, titles, refs = _retrieve(db, user_id, concept, document_ids)
    known_anchors = anchors(db, user_id)
    profile_line = preferences_prompt(profile)

    explanation, citations, used_fallback = _generate(
        db, user_id, concept, depth, context, titles, refs,
        prompt_for=lambda: explain_prompt_personalized(
            concept, depth, context, titles,
            anchors=known_anchors,
            profile_line=profile_line,
        ),
    )

    if not used_fallback:
        record_generation(db, user_id, "personalized_explain")
    db.commit()

    return {
        "concept": concept,
        "depth": depth,
        "explanation": explanation,
        "citations": _expand_citations(citations, refs),
        "fallback": used_fallback,
        "anchors": known_anchors,
        "personalized": bool(known_anchors or profile_line),
        "document_ids": sorted({c["document_id"] for c in _expand_citations(citations, refs) if c.get("document_id")}),
    }
