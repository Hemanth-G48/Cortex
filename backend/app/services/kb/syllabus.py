"""Phase 5 syllabus parsing pipeline (Idea 42, phrases 11–20).

Extract → chunk → LLM parse (budget-capped) → merge → strict schema. Always
falls back to ``ai_fallback.demo_syllabus_parse`` so ``AI_ENABLED=false`` stays
fully functional. The parsed dict is stored on ``SubjectProfile.parsed_json``.
"""

from __future__ import annotations

import re

from app.services import ai_client, ai_fallback
from app.services.kb.budget import budget_allows, record_generation
from app.services.prompts import syllabus_parse_prompt

# Cap raw text fed to the parser (bytes of chars, not tokens).
MAX_PARSE_CHARS = 60_000
# Slice size for the per-chunk LLM parse (phrase 14).
PARSE_CHUNK_CHARS = 12_000

UNIT_KEYS = ("title", "description", "topics", "deadlines")
TOPIC_KEYS = ("name", "outcomes")


def _slice_text(text: str, size: int = PARSE_CHUNK_CHARS) -> list[str]:
    """Split long syllabi at paragraph boundaries near ``size`` characters."""
    text = (text or "").strip()
    if len(text) <= size:
        return [text] if text else []
    slices: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            # back off to the nearest paragraph break
            window = text[start:end]
            cut = window.rfind("\n\n")
            if cut > size // 2:
                end = start + cut
            else:
                cut = window.rfind("\n")
                if cut > size // 2:
                    end = start + cut
        slices.append(text[start:end])
        start = end
    return slices


def _normalise_parse(parsed: object | None) -> dict:
    """Coerce the LLM output into the strict schema (phrase 12)."""
    if not isinstance(parsed, dict):
        return {}
    result: dict = {}
    for key in ("title", "semester", "grading"):
        value = parsed.get(key)
        result[key] = value if isinstance(value, str) else None
    credits = parsed.get("credits")
    try:
        result["credits"] = int(credits) if credits not in (None, "") else None
    except (TypeError, ValueError):
        result["credits"] = None
    units: list[dict] = []
    for u in parsed.get("units") or []:
        if not isinstance(u, dict):
            continue
        title = str(u.get("title") or "").strip()
        if not title:
            continue
        topics: list[dict] = []
        for t in u.get("topics") or []:
            if not isinstance(t, dict):
                continue
            name = str(t.get("name") or "").strip()
            if not name:
                continue
            outcomes = [
                str(o).strip()
                for o in (t.get("outcomes") or [])
                if isinstance(o, str) and o.strip()
            ]
            topics.append({"name": name, "outcomes": outcomes})
        deadlines = [
            str(d).strip()
            for d in (u.get("deadlines") or [])
            if isinstance(d, str) and d.strip()
        ]
        units.append(
            {
                "title": title,
                "description": str(u.get("description") or "").strip() or None,
                "topics": topics,
                "deadlines": deadlines,
            }
        )
    result["units"] = units
    return result


def _merge_parses(parses: list[dict]) -> dict:
    """Merge per-chunk parses, deduping units by title and topics by name."""
    if not parses:
        return {}
    base = dict(parses[0])
    base["units"] = list(parses[0].get("units") or [])
    seen_units: set[str] = {u["title"].lower() for u in base["units"]}
    for chunk in parses[1:]:
        for u in chunk.get("units") or []:
            key = u["title"].lower()
            if key in seen_units:
                # merge topics into the existing unit
                for existing in base["units"]:
                    if existing["title"].lower() == key:
                        seen_topics = {t["name"].lower() for t in existing["topics"]}
                        for t in u["topics"]:
                            if t["name"].lower() not in seen_topics:
                                existing["topics"].append(t)
                                seen_topics.add(t["name"].lower())
                        existing["deadlines"] = list(
                            dict.fromkeys(existing["deadlines"] + u["deadlines"])
                        )
                continue
            seen_units.add(key)
            base["units"].append(u)
    if not base.get("title"):
        base["title"] = parses[0].get("title")
    return base


def parse_syllabus(text: str | None, filename: str | None = None, *, db=None, user_id: int | None = None) -> dict:
    """Parse syllabus text into the strict schema.

    Returns ``{"parsed": {...}, "fallback": bool}``. When ``db``/``user_id`` are
    given the LLM call is budget-capped against ``KB_DAILY_GEN_LIMIT``.
    """
    text = (text or "").strip()[:MAX_PARSE_CHARS]
    ai_ok = bool(db is not None and user_id is not None and budget_allows(db, user_id))

    if ai_client.ai_available() and ai_ok:
        chunks = _slice_text(text)
        parses: list[dict] = []
        for chunk in chunks:
            raw = ai_client.generate_json(syllabus_parse_prompt(chunk), max_tokens=2048)
            normalised = _normalise_parse(raw)
            if normalised.get("units"):
                parses.append(normalised)
        if parses:
            merged = _merge_parses(parses)
            record_generation(db, user_id, "syllabus")
            return {"parsed": merged, "fallback": False}

    fallback = ai_fallback.demo_syllabus_parse(text, filename)
    return {"parsed": fallback, "fallback": True}


def syllabus_ai_budget(db, user_id: int) -> dict:
    """Expose the Phase 5 parse budget for the UI (phrases 18)."""
    from app.services.kb.budget import generation_budget

    return generation_budget(db, user_id)


# Regexes reused by topic extraction (Idea 44) and unit matching (Idea 45).
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
