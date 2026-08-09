"""Metadata extraction & enrichment (Idea 13, phrases 22-27, 30).

Provides deterministic heuristics for language detection and reading-time
estimation, LLM-based enrichment with graceful fallback, manual-override
persistence, and SQLAlchemy filter helpers for the document list endpoint.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbDocumentTag, KbTag
from app.services.ai_client import generate_json
from app.services.kb import KbService
from app.schemas.kb import KbMetadataProposal, KbMetadataUpdate

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Deterministic language detection (phrase 25)
# ---------------------------------------------------------------------------

_STOPWORDS: dict[str, set[str]] = {
    "en": {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i",
        "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her",
        "she", "or", "an", "will", "my", "one", "all", "would", "there",
        "their", "what", "so", "up", "out", "if", "about", "who", "get",
        "which", "go", "me", "when", "make", "can", "like", "time", "no",
        "just", "him", "know", "take", "people", "into", "year", "your",
        "good", "some", "could", "them", "see", "other", "than", "then",
        "now", "look", "only", "come", "its", "over", "think", "also",
        "back", "after", "use", "two", "how", "our", "work", "first",
        "well", "way", "even", "new", "want", "because", "any", "these",
        "give", "day", "most", "us", "is", "was", "are", "been", "has",
        "had", "were", "does", "did", "should", "would", "could", "might",
    },
    "es": {
        "el", "la", "de", "que", "y", "en", "un", "una", "los", "las",
        "del", "al", "es", "se", "no", "por", "con", "para", "su",
        "como", "más", "pero", "sus", "le", "ya", "todo", "esta", "está",
        "sobre", "entre", "cuando", "muy", "sin", "también",
        "desde", "hasta", "cada", "bien", "puede", "donde", "cuál",
        "eso", "ese", "esa", "usted", "ustedes", "nos", "nosotros",
        "me", "te", "se", "lo", "la", "le", "les", "lo", "él", "ella",
        "ellos", "ellas", "haber", "ha", "han", "si", "no",
        "sí", "porque", "aunque", "mientras", "cuando", "después",
        "antes", "siempre", "nunca", "también", "muy", "mucho", "poco",
        "gran", "grande", "pequeño", "pequeña",
    },
    "fr": {
        "le", "la", "les", "de", "du", "des", "et", "est", "dans",
        "avec", "pour", "sur", "une", "un", "ce", "qui", "que", "au",
        "aux", "se", "son", "sa", "ses", "il", "elle", "ils", "elles",
        "nous", "vous", "ne", "pas", "plus", "bien", "très", "aussi",
        "mais", "ou", "donc", "si", "comme", "tout", "tous", "cette",
        "ces", "cela", "être", "avoir", "faire", "pouvoir", "vouloir",
        "devoir", "savoir", "prendre", "donner", "dire", "mettre",
        "venir", "aller", "sont", "est", "été", "suis", "es", "sommes",
        "êtes", "avait", "avaient", "sera", "seront", "fait", "faites",
        "quand", "où", "comment", "pourquoi", "ici", "là", "encore",
        "toujours", "jamais", "peut", "peut-être", "même", "autre", "autres",
    },
    "de": {
        "der", "die", "das", "und", "in", "von", "zu", "den", "mit",
        "sich", "des", "auf", "für", "ist", "ein", "eine", "nicht",
        "auch", "wird", "es", "an", "als", "oder", "aus", "er", "sie",
        "das", "dass", "nach", "bei", "war", "hat", "haben",
        "werden", "können", "müssen", "soll", "kann", "sind", "warum",
        "wie", "wann", "wo", "welche", "welcher", "welches", "diese",
        "dieser", "dieses", "man", "noch", "nur", "selbst", "sonst",
        "über", "unter", "vor", "nach", "neben", "zwischen", "durch",
        "ohne", "während", "weil", "obwohl", "trotz", "genau", "so",
        "noch", "viel", "mehr", "wenig", "gut", "schlecht", "groß",
        "klein", "lang", "kurz", "neu", "alt", "jeder", "jede", "jedes",
    },
}

_ACCENT_CHARS = set("àáâãäåèéêëìíîïòóôõöùúûüçñß")
_UMLAUT_CHARS = set("äöüß")
_ESPECIAL_CHARS = set("áéíóúñ¿¡")


def detect_language(text: str) -> str | None:
    """Return a 2-letter language code or None using deterministic heuristics.

    Tokenizes the text into words, scores against a small stopword table
    for en/es/fr/de, then confirms with character-level signals
    (accents, umlauts). The language with the highest stopword match
    ratio wins, provided it clears a minimum confidence threshold.
    """
    if not text or not text.strip():
        return None

    words = re.findall(r"[a-zA-Z]+", text.lower())
    if not words:
        return None

    total = len(words)
    scores: dict[str, int] = {}
    for lang, stopwords in _STOPWORDS.items():
        scores[lang] = sum(1 for w in words if w in stopwords)

    ratios = {lang: count / total for lang, count in scores.items()}

    text_chars = set(text)
    if text_chars & _UMLAUT_CHARS:
        ratios["de"] = ratios.get("de", 0) + 0.15
    if text_chars & _ACCENT_CHARS - _UMLAUT_CHARS:
        ratios["fr"] = ratios.get("fr", 0) + 0.10
        ratios["es"] = ratios.get("es", 0) + 0.05
    if text_chars & _ESPECIAL_CHARS:
        ratios["es"] = ratios.get("es", 0) + 0.10

    best_lang: str | None = None
    best_score = 0.0
    for lang, ratio in ratios.items():
        if ratio > best_score and ratio >= 0.03:
            best_score = ratio
            best_lang = lang

    return best_lang


# ---------------------------------------------------------------------------
# Reading time estimation (phrase 24)
# ---------------------------------------------------------------------------

_WPM = 200


def estimate_reading_time(text: str) -> int:
    """Return estimated reading time in seconds (words / 200 wpm, min 0)."""
    if not text:
        return 0
    word_count = len(re.findall(r"\b\w+\b", text))
    minutes = word_count / _WPM
    return max(0, int(minutes * 60))


# ---------------------------------------------------------------------------
# Frontmatter extraction (phrase 22)
# ---------------------------------------------------------------------------

_FRONTMATTER_KEY_MAP = {
    "author": "author",
    "source_url": "source_url",
    "url": "source_url",
    "language": "language",
    "date": "doc_date",
    "tags": "tags",
    "title": "title",
}


def extract_frontmatter(db: Session, doc: KbDocument) -> dict:
    """Pull metadata fields from ``doc.frontmatter_json``.

    Frontmatter always wins (phrase 22). Returns a dict with keys
    ``author``, ``source_url``, ``language``, ``doc_date``, ``tags``.
    """
    frontmatter = KbService.json_loads(doc.frontmatter_json)
    if not isinstance(frontmatter, dict):
        return {}

    result: dict[str, Any] = {}
    for fm_key, target_key in _FRONTMATTER_KEY_MAP.items():
        if fm_key in frontmatter and frontmatter[fm_key] is not None:
            value = frontmatter[fm_key]
            if target_key == "doc_date" and isinstance(value, str):
                try:
                    result[target_key] = date.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
            elif target_key == "tags" and isinstance(value, list):
                result[target_key] = [str(t) for t in value]
            else:
                result[target_key] = str(value)

    return result


# ---------------------------------------------------------------------------
# Metadata proposal (phrase 23)
# ---------------------------------------------------------------------------

def propose_metadata(db: Session, doc: KbDocument) -> KbMetadataProposal:
    """Propose metadata for a document, merging frontmatter + LLM + heuristics.

    Start from frontmatter values; for missing fields, if AI is
    available, call ``generate_json`` with a strict schema requesting
    ``{author, language, source_url}``. When AI is disabled/unreachable
    or parsing fails, fall back to deterministic heuristics
    (``detect_language``, ``estimate_reading_time``) with confidence
    0.3. Never raises — always returns a valid ``KbMetadataProposal``.
    """
    frontmatter = extract_frontmatter(db, doc)
    fm_author = frontmatter.get("author")
    fm_source_url = frontmatter.get("source_url")
    fm_language = frontmatter.get("language")

    needs_author = not fm_author
    needs_source_url = not fm_source_url
    needs_language = not fm_language

    ai_used = False
    ai_confidence = 0.0
    ai_reason = ""
    llm_author: str | None = None
    llm_source_url: str | None = None
    llm_language: str | None = None

    if settings.AI_ENABLED and (needs_author or needs_source_url or needs_language):
        try:
            prompt = (
                "Extract metadata from the following document text. "
                "Respond with a JSON object containing ONLY the fields: "
                "author (string or null), language (2-letter ISO code or null), "
                "source_url (string or null). Do not include any other fields "
                "or explanatory text.\n\n"
                f"Title: {doc.title or '(untitled)'}\n"
                f"Text (first 2000 chars): {(doc.extracted_text or '')[:2000]}"
            )
            result = generate_json(prompt, max_tokens=500, temperature=0.2)
            if isinstance(result, dict):
                llm_author = result.get("author") or None
                llm_language = result.get("language") or None
                llm_source_url = result.get("source_url") or None
                ai_used = True
                ai_confidence = 0.7
                ai_reason = "llm_proposal"
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM metadata proposal failed for doc %s: %s", doc.id, exc)

    # Resolve each field: frontmatter > LLM > deterministic heuristic
    resolved_author = fm_author or llm_author
    resolved_source_url = fm_source_url or llm_source_url
    resolved_language = fm_language or llm_language

    # For fields not resolved by frontmatter or LLM, use heuristics
    if not resolved_language:
        resolved_language = detect_language(doc.extracted_text or "")
        if not ai_used:
            ai_confidence = 0.3
            ai_reason = "deterministic_fallback"

    if not resolved_author and not ai_used:
        ai_confidence = 0.3
        ai_reason = "deterministic_fallback"

    if not resolved_source_url and not ai_used:
        ai_confidence = 0.3
        ai_reason = "deterministic_fallback"

    # Reading time is always computed deterministically
    reading_time = estimate_reading_time(doc.extracted_text or "")

    # Confidence is the max of any applied method
    final_confidence = max(ai_confidence, 0.3 if resolved_language else 0.0)

    return KbMetadataProposal(
        author=resolved_author,
        source_url=resolved_source_url,
        language=resolved_language,
        reading_time_seconds=reading_time,
        confidence=final_confidence,
        reason=ai_reason or ("frontmatter_only" if not ai_used else "llm_proposal"),
    )


# ---------------------------------------------------------------------------
# Enrichment (phrase 27)
# ---------------------------------------------------------------------------

def _provenance_ai(provenance: dict[str, str]) -> bool:
    """Return True if any field's provenance indicates AI involvement."""
    return any(
        p in ("ai", "llm_proposal", "deterministic_fallback")
        for p in provenance.values()
    )


def enrich_metadata(db: Session, doc: KbDocument) -> None:
    """Enrich a document's metadata in-place and commit.

    Merge rule: manual > frontmatter > LLM > defaults (phrase 26/27).
    Manual-override values stored in ``doc.metadata_json["manual"]`` are
    never overwritten by re-ingest — a user's explicit edit beats even
    frontmatter. Per-field provenance is recorded in
    ``doc.metadata_json`` under ``"manual"``, ``"ai"``, and ``"rule"`` keys.
    Sets ``doc.author``, ``doc.source_url``, ``doc.language``,
    ``doc.reading_time_seconds``, ``doc.doc_date`` from resolved values.
    """
    existing_meta = KbService.json_loads(doc.metadata_json) or {}
    manual_overrides = existing_meta.get("manual") or {}

    proposal = propose_metadata(db, doc)
    fm = extract_frontmatter(db, doc)

    resolved: dict[str, Any] = {}
    provenance: dict[str, str] = {}

    # author
    if manual_overrides.get("author"):
        resolved["author"] = manual_overrides["author"]
        provenance["author"] = "manual"
    elif fm.get("author"):
        resolved["author"] = fm["author"]
        provenance["author"] = "frontmatter"
    elif proposal.author:
        resolved["author"] = proposal.author
        provenance["author"] = proposal.reason or "ai"
    else:
        provenance["author"] = "none"

    # source_url
    if manual_overrides.get("source_url"):
        resolved["source_url"] = manual_overrides["source_url"]
        provenance["source_url"] = "manual"
    elif fm.get("source_url"):
        resolved["source_url"] = fm["source_url"]
        provenance["source_url"] = "frontmatter"
    elif proposal.source_url:
        resolved["source_url"] = proposal.source_url
        provenance["source_url"] = proposal.reason or "ai"
    else:
        provenance["source_url"] = "none"

    # language
    if manual_overrides.get("language"):
        resolved["language"] = manual_overrides["language"]
        provenance["language"] = "manual"
    elif fm.get("language"):
        resolved["language"] = fm["language"]
        provenance["language"] = "frontmatter"
    elif proposal.language:
        resolved["language"] = proposal.language
        provenance["language"] = proposal.reason or "ai"
    else:
        provenance["language"] = "none"

    # doc_date — not in KbMetadataProposal; handled via frontmatter only
    fm_date = fm.get("doc_date")
    if manual_overrides.get("doc_date"):
        resolved["doc_date"] = manual_overrides["doc_date"]
        provenance["doc_date"] = "manual"
    elif fm_date:
        resolved["doc_date"] = fm_date
        provenance["doc_date"] = "frontmatter"
    else:
        provenance["doc_date"] = "none"

    # reading_time_seconds (always deterministic)
    resolved["reading_time_seconds"] = proposal.reading_time_seconds or 0
    provenance["reading_time_seconds"] = "rule"

    # tags — manual overrides win (consistent with the other fields)
    if manual_overrides.get("tags"):
        resolved["tags"] = manual_overrides["tags"]
        provenance["tags"] = "manual"
    elif fm.get("tags"):
        resolved["tags"] = fm["tags"]
        provenance["tags"] = "frontmatter"
    elif existing_meta.get("tags"):
        resolved["tags"] = existing_meta["tags"]
        provenance["tags"] = "existing"
    else:
        provenance["tags"] = "none"

    # Build the new metadata_json preserving manual overrides and adding
    # ai/rule provenance
    new_meta: dict[str, Any] = {}
    if manual_overrides:
        new_meta["manual"] = manual_overrides
    if _provenance_ai(provenance):
        new_meta["ai"] = {
            k: v
            for k, v in resolved.items()
            if provenance.get(k) not in ("frontmatter", "manual", "rule", "existing", "none")
        }
    new_meta["rule"] = provenance

    doc.author = resolved.get("author")
    doc.source_url = resolved.get("source_url")
    doc.language = resolved.get("language")
    doc.reading_time_seconds = resolved.get("reading_time_seconds")
    doc.doc_date = resolved.get("doc_date")
    doc.metadata_json = KbService.json_dumps(new_meta)

    db.add(doc)
    db.commit()


# ---------------------------------------------------------------------------
# Manual override (phrase 26)
# ---------------------------------------------------------------------------

def apply_metadata_update(db: Session, doc: KbDocument, update: KbMetadataUpdate) -> KbDocument:
    """Apply a manual metadata override to a document.

    Writes provided fields into the document row and stores them in
    ``metadata_json["manual"]`` so they are flagged as manual and never
    overwritten by re-ingest. Merges ``update.metadata`` dict into
    ``metadata_json``. Returns the updated doc.
    """
    existing_meta = KbService.json_loads(doc.metadata_json) or {}
    manual = existing_meta.get("manual") or {}

    if update.author is not None:
        doc.author = update.author
        manual["author"] = update.author
    if update.source_url is not None:
        doc.source_url = update.source_url
        manual["source_url"] = update.source_url
    if update.language is not None:
        doc.language = update.language
        manual["language"] = update.language
    if update.reading_time_seconds is not None:
        doc.reading_time_seconds = update.reading_time_seconds
        manual["reading_time_seconds"] = update.reading_time_seconds

    # Merge update.metadata into metadata_json (not into manual)
    if update.metadata is not None:
        existing_custom = existing_meta.get("metadata") or {}
        for key, value in update.metadata.items():
            if key not in manual:
                existing_custom[key] = value
        existing_meta["metadata"] = existing_custom

    existing_meta["manual"] = manual
    doc.metadata_json = KbService.json_dumps(existing_meta)

    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Filter helper (phrase 30)
# ---------------------------------------------------------------------------

def metadata_filters(
    query: Any,
    *,
    author: str | None = None,
    tag: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    language: str | None = None,
) -> Any:
    """Apply metadata filters to a ``KbDocument`` SQLAlchemy query.

    Each non-None filter is applied as an AND condition:
    - ``author`` — case-insensitive partial match on ``KbDocument.author``
    - ``language`` — exact match on ``KbDocument.language``
    - ``date_from`` / ``date_to`` — range filter on ``KbDocument.doc_date``
    - ``tag`` — subquery through ``document_tags`` → ``kb_tags`` where
      ``KbTag.name == tag`` and ``KbDocumentTag.user_id`` matches the
      document's ``user_id`` (per-user scoping).

    Returns the (possibly modified) SQLAlchemy query object.
    """
    if author is not None:
        query = query.filter(KbDocument.author.ilike(f"%{author}%"))

    if language is not None:
        query = query.filter(KbDocument.language == language)

    if date_from is not None:
        query = query.filter(KbDocument.doc_date >= date_from)

    if date_to is not None:
        query = query.filter(KbDocument.doc_date <= date_to)

    if tag is not None:
        tag_subq = (
            query.session.query(KbDocumentTag.document_id)
            .join(KbTag, KbDocumentTag.tag_id == KbTag.id)
            .filter(
                KbTag.name == tag,
                KbDocumentTag.user_id == KbDocument.user_id,
            )
            .subquery()
        )
        query = query.filter(KbDocument.id.in_(tag_subq))

    return query
