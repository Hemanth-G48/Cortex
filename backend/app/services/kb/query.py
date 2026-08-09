"""Query normalization + expansion (Idea 24).

``expand`` runs before every retrieval mode: normalizes the query (lowercase,
punctuation-stripped), maps tokens to canonical concepts via
``kb_concepts.aliases`` (synonyms + abbreviations), and — when nothing else
hit — offers an LLM rewrite (budget-capped, ``AI_ENABLED`` guarded). The
result is a single expansion string fed to both FTS and semantic retrievers.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbConcept

logger = logging.getLogger(__name__)

# Abbreviation dictionary seeded with common CS/ML terms (phrase 34). Concept
# aliases in kb_concepts take precedence over this static table.
ABBREVIATIONS: dict[str, str] = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ds": "data science",
    "nn": "neural network",
    "rl": "reinforcement learning",
    "llm": "large language model",
    "dbms": "database management system",
    "os": "operating system",
    "cnn": "convolutional neural network",
    "rnn": "recurrent neural network",
}


def _normalize(query: str) -> str:
    """Lowercase + strip punctuation, keep word boundaries (phrase 32)."""
    q = (query or "").lower().strip()
    q = re.sub(r"[^\w\s]", " ", q)
    return re.sub(r"\s+", " ", q).strip()


def _load_aliases(db: Session, user_id: int) -> dict[str, str]:
    """Flatten kb_concepts aliases → {alias: canonical_name} (phrase 33).

    Returns {} when Phase 2 concepts aren't populated yet — expansion then
    falls back to the static abbreviation table only.
    """
    rows = (
        db.query(KbConcept)
        .filter(KbConcept.user_id == user_id)
        .all()
    )
    out: dict[str, str] = {}
    for concept in rows:
        aliases: list[str] = []
        if concept.aliases:
            try:
                aliases = json.loads(concept.aliases)
            except (ValueError, TypeError):
                aliases = []
        for alias in aliases:
            a = (alias or "").strip().lower()
            if a:
                out[a] = concept.canonical_name.lower()
    return out


def _expand_tokens(tokens: list[str], alias_map: dict[str, str]) -> str:
    """Map tokens to canonical names and OR them into the expansion."""
    expanded_terms = list(tokens)
    for tok in tokens:
        canonical = alias_map.get(tok)
        if canonical and canonical != tok:
            expanded_terms.append(canonical)
        abbr = ABBREVIATIONS.get(tok)
        if abbr and abbr not in expanded_terms:
            expanded_terms.append(abbr)
    # Dedupe preserving order.
    seen: set[str] = set()
    terms: list[str] = []
    for t in expanded_terms:
        if t not in seen:
            seen.add(t)
            terms.append(t)
    return " ".join(terms)


def _llm_rewrite(db: Session, user_id: int, query: str) -> str | None:
    """Optional LLM query rewrite (phrase 36).

    Budget-capped via ``KB_INFER_DAILY_BUDGET`` and skipped when ``AI_ENABLED``
    is false. Returns a rewritten query or None (never raises).
    """
    if not settings.AI_ENABLED:
        return None
    try:
        from app.services.ai_client import generate

        rewritten = generate(
            (
                "Rewrite this search query into 2–4 searchable keywords "
                f"joined by spaces, no explanation: {query}"
            )
        )
        text = (rewritten or "").strip()
        return _normalize(text) if text and len(text) >= 2 else None
    except Exception as exc:  # noqa: BLE001 — never fail retrieval on AI flake
        logger.warning("LLM query rewrite failed: %s", exc)
        return None


def expand(db: Session, user_id: int, query: str) -> str:
    """Full expansion pipeline applied before retrieval (phrase 31)."""
    normalized = _normalize(query)
    if not normalized:
        return query

    tokens = normalized.split()
    alias_map = _load_aliases(db, user_id)
    expanded = _expand_tokens(tokens, alias_map)

    if expanded == normalized:
        return normalized
    # Append the original tokens too so FTS can still match literal phrases.
    return f"{expanded} {query.strip()}".strip()


def should_llm_rewrite(expanded: str, normalized: str) -> bool:
    """Return True when expansion didn't change anything (zero-hit risk)."""
    return expanded == normalized
