"""Auto-tagging service (Phase 2, Idea 14, phrases 31-40).

Seeds inline/rule tags, proposes AI or deterministic-fallback tags,
and manages the apply/reject lifecycle — all per-user scoped.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import TYPE_CHECKING

from app.config import settings
from app.services.ai_client import ai_available, generate_json
from app.services.embeddings import embedding_budget
from app.services.kb import KbService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.models import KbChunk, KbDocument, KbDocumentTag, KbTag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stopword list (small, deterministic — no external dependency).
# ---------------------------------------------------------------------------

STOPWORDS = frozenset(
    "a an the and or but in on at to for of with by from as is are was were "
    "be been being have has had do does did will would shall should may might "
    "can could must need dare not no nor so if then than too very just about "
    "also into over after before between under again further once here there "
    "when where why how all each every both few more most other some such "
    "only own same the this that these those it its he she they them their "
    "his her our my your me him us you what which who whom whose".split()
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens, length >= 2."""
    return re.findall(r"[a-zA-Z0-9]{2,}", text.lower())


def _is_noun_like(word: str) -> bool:
    """POS-lite heuristic: prefer capitalized or length>=4 tokens."""
    return len(word) >= 4 or (len(word) >= 2 and word[0].isupper())


def _trim_tag(name: str) -> str:
    """Normalise a tag name for storage.

    Plain tags are lowercased and capped at ~40 chars (legacy behaviour).
    ``course:`` tags keep their case and length so derived course titles
    stay readable and un-truncated (``course:Operating Systems`` is a course
    title, not a keyword).
    """
    name = name.strip()
    if name.startswith(settings.COURSE_TAG_PREFIX):
        # Cap at the KbTag.name column width (100) — course names beyond that
        # would overflow on strict DBs (e.g. Postgres).
        return name[:100]
    return name.lower()[:40]


def _create_or_reuse_tag(db: Session, user_id: int, name: str, kind: str = "inline") -> KbTag:
    """Match existing (user_id, name) or create a new KbTag row."""
    name = _trim_tag(name)
    if not name:
        raise ValueError("tag name is empty after trimming")
    tag = (
        db.query(KbTag)
        .filter(KbTag.user_id == user_id, KbTag.name == name)
        .first()
    )
    if tag is None:
        tag = KbTag(user_id=user_id, name=name, kind=kind)
        db.add(tag)
        db.flush()
    return tag


def _existing_document_tag(db: Session, user_id: int, document_id: int, tag_id: int) -> bool:
    """Return True when a document_tags row already exists."""
    return (
        db.query(KbDocumentTag)
        .filter(
            KbDocumentTag.user_id == user_id,
            KbDocumentTag.document_id == document_id,
            KbDocumentTag.tag_id == tag_id,
        )
        .first()
        is not None
    )


# ---------------------------------------------------------------------------
# Phrase 31 — seed inline tags
# ---------------------------------------------------------------------------

def seed_inline_tags(db: Session, doc: KbDocument) -> list[int]:
    """Extract inline ``#tag`` tokens and/or a ``tags:`` list from
    ``doc.frontmatter_json`` / ``doc.extracted_text``.

    Creates-or-reuses ``KbTag`` rows with ``kind="inline"`` and
    ``KbDocumentTag`` rows with ``provenance="rule"`` (idempotent).
    Inline/rule tags are never suggested for deletion. Returns tag ids.
    """
    user_id = doc.user_id
    tag_names: set[str] = set()

    # 1) Frontmatter ``tags:`` key (list of strings).
    # frontmatter_json is stored as a JSON string (or None) — decode first.
    fm = KbService.json_loads(doc.frontmatter_json) or {}
    if isinstance(fm, dict):
        raw_tags = fm.get("tags")
        if isinstance(raw_tags, list):
            for t in raw_tags:
                if isinstance(t, str) and t.strip():
                    tag_names.add(t.strip())
        elif isinstance(raw_tags, str) and raw_tags.strip():
            tag_names.add(raw_tags.strip())

    # 2) Inline ``#tag`` tokens in extracted_text. The ``course:`` alternative
    # is tried first so ``#course:Operating Systems`` parses as one tag (the
    # colon and inner spaces are preserved for derivation).
    text = doc.extracted_text or ""
    inline_re = re.compile(
        r"(?:^|\s)#("
        r"course:[A-Za-z0-9_][A-Za-z0-9_ .&'-]*"
        r"|[A-Za-z0-9_][A-Za-z0-9_/.\-]*"
        r")"
    )
    for m in inline_re.finditer(text):
        tag_names.add(m.group(1))

    tag_ids: list[int] = []
    for name in tag_names:
        tag = _create_or_reuse_tag(db, user_id, name, kind="inline")
        # Idempotent: skip if document_tags row already exists.
        if not _existing_document_tag(db, user_id, doc.id, tag.id):
            doc_tag = KbDocumentTag(
                user_id=user_id,
                document_id=doc.id,
                tag_id=tag.id,
                provenance="rule",
            )
            db.add(doc_tag)
        tag_ids.append(tag.id)

    # Flush so the rule rows are visible to later queries even in
    # autoflush=False sessions (tests use such sessions).
    db.flush()
    return tag_ids


# ---------------------------------------------------------------------------
# Phrase 34 — deterministic TF-IDF fallback
# ---------------------------------------------------------------------------

def tfidf_tag_candidates(db: Session, doc: KbDocument, top_n: int = 6) -> list[str]:
    """Deterministic TF-IDF fallback over the doc's chunk texts vs the
    user's corpus. Returns lowercase, trimmed candidate tag strings.

    No LLM is called. Uses a stopword list and a POS-lite heuristic
    (prefers capitalized or length>=4 words).

    The user corpus comes from ``corpus.get_user_corpus`` (cached, two
    batched queries) rather than one chunk query per document — the reindex
    pipeline calls this per document, so the old N+1 pattern made a large
    reindex quadratic.
    """
    from app.services.kb.corpus import get_user_corpus

    corpus = get_user_corpus(db, doc.user_id)
    doc_texts = corpus.doc_texts.get(doc.id)
    if not doc_texts:
        return []

    # Per-document list of per-chunk token lists, computed once per corpus.
    chunk_toks = corpus.chunk_tokens("tagger", _tokenize)
    doc_token_lists = chunk_toks.get(doc.id, [])

    # Document frequency across the user corpus (number of *documents*
    # containing each token).  We approximate "document" = each chunk
    # list entry in the corpus.  A pure function of the corpus — compute
    # once and reuse for every document in the reindex.
    def _build_df() -> Counter:
        df: Counter = Counter()
        for toks in chunk_toks.values():
            for chunk_tokens in toks:
                for tok in set(chunk_tokens):
                    df[tok] += 1
        return df

    df = corpus.cached("tagger_df", _build_df)  # type: ignore[arg-type]
    total_docs = sum(len(toks) for toks in chunk_toks.values()) or 1

    # TF-IDF for the target document.
    scores: dict[str, float] = {}
    for tokens in doc_token_lists:
        tf = Counter(tokens)
        for tok, count in tf.items():
            if tok in STOPWORDS or len(tok) < 2:
                continue
            idf = 1.0 + (total_docs / (1 + df.get(tok, 0)))
            scores[tok] = scores.get(tok, 0.0) + count * idf

    # POS-lite filter: prefer capitalized or length>=4.
    candidates = [w for w in scores if _is_noun_like(w)]
    # Sort by score descending, then alphabetically for determinism.
    candidates.sort(key=lambda w: (-scores[w], w))

    # Build tag strings from the top candidates, capping at ~40 chars.
    result = []
    for w in candidates[:top_n]:
        tag = _trim_tag(w)
        if tag and tag not in result:
            result.append(tag)
    return result


# ---------------------------------------------------------------------------
# Phrase 33 — propose tags
# ---------------------------------------------------------------------------

def propose_tags(db: Session, doc: KbDocument) -> list:
    """Return a list of ``KbTagSuggestion`` dicts for *doc*.

    Rule tags (provenance ``"rule"``, confidence 1.0) come first.
    Then, if AI is available and the embedding budget allows, an LLM
    is asked for 3-7 concise topical tags (provenance ``"ai"``,
    confidence 0.8).  When AI is disabled/unreachable/parse-fails the
    deterministic TF-IDF fallback is used instead (provenance ``"ai"``,
    confidence 0.5).  Nothing is committed as authoritative — only
    ``provenance="rule"`` rows exist until the user applies.
    """
    user_id = doc.user_id
    suggestions: list[dict] = []
    seen_tag_ids: set[int] = set()

    # 1) Rule tags first (provenance="rule", confidence=1.0).
    rule_tags = (
        db.query(KbTag)
        .join(KbDocumentTag, KbTag.id == KbDocumentTag.tag_id)
        .filter(
            KbDocumentTag.document_id == doc.id,
            KbDocumentTag.user_id == user_id,
            KbDocumentTag.provenance == "rule",
        )
        .all()
    )
    for tag in rule_tags:
        suggestions.append(
            {
                "tag_id": tag.id,
                "name": tag.name,
                "provenance": "rule",
                "confidence": 1.0,
            }
        )
        seen_tag_ids.add(tag.id)

    # 2) AI or fallback proposal.
    ai_suggested_names: list[str] = []
    used_ai = False

    if ai_available():
        budget = embedding_budget(db, user_id)
        if budget["remaining"] > 0:
            # Gather the first few chunks, capped by the remaining budget.
            max_tokens = min(budget["remaining"] * 4, 4000)  # rough token cap
            chunks = (
                db.query(KbChunk)
                .filter(KbChunk.document_id == doc.id, KbChunk.user_id == user_id)
                .order_by(KbChunk.seq.asc())
                .all()
            )
            # Build a token-bounded text from the first chunks.
            collected: list[str] = []
            total_tokens = 0
            for chunk in chunks:
                tokens = KbService.token_estimate(chunk.content)
                if total_tokens + tokens > max_tokens and collected:
                    break
                collected.append(chunk.content)
                total_tokens += tokens
            prompt_text = "\n\n".join(collected) if collected else (doc.extracted_text or "")[:2000]

            prompt = (
                f"Given the following document text, propose 3 to 7 concise "
                f"topical tags (single words or short phrases, lowercase, "
                f"no more than 40 characters each). Return ONLY a JSON array "
                f"of strings. Do not include any explanation or markdown fences.\n\n"
                f"{prompt_text}"
            )
            result = generate_json(prompt, max_tokens=512, temperature=0.3)
            if isinstance(result, list):
                ai_suggested_names = [str(item).strip() for item in result if isinstance(item, str) and item.strip()]
                used_ai = True
            else:
                logger.warning("AI tag proposal did not return a list for doc %s", doc.id)

    if not used_ai:
        # Deterministic fallback (phrase 34).
        ai_suggested_names = tfidf_tag_candidates(db, doc, top_n=6)

    # Create-or-reuse tags for AI suggestions and add to output.
    for name in ai_suggested_names:
        tag = _create_or_reuse_tag(db, user_id, name, kind="auto")
        if tag.id not in seen_tag_ids:
            suggestions.append(
                {
                    "tag_id": tag.id,
                    "name": tag.name,
                    "provenance": "ai",
                    "confidence": 0.8 if used_ai else 0.5,
                }
            )
            seen_tag_ids.add(tag.id)

    return suggestions


# ---------------------------------------------------------------------------
# Phrase 33b — persisted suggestions (no LLM on GET)
# ---------------------------------------------------------------------------


def persisted_suggestions(db: Session, doc: KbDocument) -> list[dict]:
    """Rule + persisted-AI + deterministic suggestions — **never calls the LLM**.

    This is the read path for ``GET /api/kb/documents/{id}/tags`` (and every
    tag-editor response), so opening a document costs nothing:

    1. Rule tags (provenance ``"rule"``, confidence 1.0) — inline/frontmatter
       tags seeded at ingest.
    2. Persisted AI rows (provenance ``"ai"``) — written at ingest by
       ``auto_tag_document`` or on the explicit ``POST .../tags/propose``
       action. Reused as-is; the LLM is never re-invoked to re-derive them.
    3. When no AI rows have been persisted yet, the deterministic TF-IDF
       fallback stands in (confidence 0.5) so the panel is never empty.

    Nothing here is committed as authoritative — only ``provenance="rule"``
    rows exist until the user applies. Mirrors ``propose_tags``'s shape so the
    UI treats both identically.
    """
    user_id = doc.user_id
    suggestions: list[dict] = []
    seen_tag_ids: set[int] = set()

    # 1) Rule tags first (persisted at ingest — free to read).
    rule_tags = (
        db.query(KbTag)
        .join(KbDocumentTag, KbTag.id == KbDocumentTag.tag_id)
        .filter(
            KbDocumentTag.document_id == doc.id,
            KbDocumentTag.user_id == user_id,
            KbDocumentTag.provenance == "rule",
        )
        .order_by(KbTag.name)
        .all()
    )
    for tag in rule_tags:
        suggestions.append(
            {"tag_id": tag.id, "name": tag.name, "provenance": "rule", "confidence": 1.0}
        )
        seen_tag_ids.add(tag.id)

    # 2) Persisted AI suggestions (ingest pipeline / explicit propose action).
    ai_tags = (
        db.query(KbTag)
        .join(KbDocumentTag, KbTag.id == KbDocumentTag.tag_id)
        .filter(
            KbDocumentTag.document_id == doc.id,
            KbDocumentTag.user_id == user_id,
            KbDocumentTag.provenance == "ai",
        )
        .order_by(KbTag.name)
        .all()
    )
    for tag in ai_tags:
        if tag.id not in seen_tag_ids:
            suggestions.append(
                {"tag_id": tag.id, "name": tag.name, "provenance": "ai", "confidence": 0.8}
            )
            seen_tag_ids.add(tag.id)

    # 3) Deterministic stand-in when nothing AI-derived has been persisted yet.
    if not ai_tags:
        for name in tfidf_tag_candidates(db, doc, top_n=6):
            tag = _create_or_reuse_tag(db, doc.user_id, name, kind="auto")
            if tag.id not in seen_tag_ids:
                suggestions.append(
                    {
                        "tag_id": tag.id,
                        "name": tag.name,
                        "provenance": "ai",
                        "confidence": 0.5,
                    }
                )
                seen_tag_ids.add(tag.id)

    return suggestions


def persist_ai_suggestions(db: Session, doc: KbDocument) -> int:
    """Run ``propose_tags`` (the only LLM path) and persist its AI rows.

    Called by the explicit ``POST /api/kb/documents/{id}/tags/propose``
    action — the sole place a user-triggered refresh can spend a model call.
    Persisting the result as ``provenance="ai"`` document_tags rows means
    later GETs surface them via ``persisted_suggestions`` without re-calling
    the LLM. Returns the number of new rows persisted.
    """
    suggestions = propose_tags(db, doc)
    user_id = doc.user_id
    saved = 0
    for sug in suggestions:
        if sug["provenance"] == "ai" and not _existing_document_tag(
            db, user_id, doc.id, sug["tag_id"]
        ):
            db.add(
                KbDocumentTag(
                    user_id=user_id,
                    document_id=doc.id,
                    tag_id=sug["tag_id"],
                    provenance="ai",
                )
            )
            saved += 1
    db.flush()
    return saved


# ---------------------------------------------------------------------------
# Phrase 37 — apply / reject
# ---------------------------------------------------------------------------

def apply_tags(db: Session, doc: KbDocument, tag_ids: list[int]) -> int:
    """Promote suggested tags to ``KbDocumentTag`` rows with
    ``provenance="manual"`` (idempotent). Returns the count applied.
    """
    user_id = doc.user_id
    applied = 0
    for tag_id in tag_ids:
        if _existing_document_tag(db, user_id, doc.id, tag_id):
            # Already has a row — update provenance to manual if it was ai.
            existing = (
                db.query(KbDocumentTag)
                .filter(
                    KbDocumentTag.user_id == user_id,
                    KbDocumentTag.document_id == doc.id,
                    KbDocumentTag.tag_id == tag_id,
                )
                .first()
            )
            if existing and existing.provenance != "manual":
                existing.provenance = "manual"
                db.add(existing)
            applied += 1
        else:
            doc_tag = KbDocumentTag(
                user_id=user_id,
                document_id=doc.id,
                tag_id=tag_id,
                provenance="manual",
            )
            db.add(doc_tag)
            applied += 1
    db.flush()
    return applied


def create_document_tag(
    db: Session, doc: KbDocument, name: str, kind: str = "auto"
) -> tuple[KbTag, int]:
    """Create-or-reuse a tag by *name* and attach it to *doc* as manual.

    ``course:*`` tags keep their case/length (see ``_trim_tag``) so derived
    course titles stay readable. Returns ``(tag, applied)`` — ``applied`` is
    the number of associations created/promoted (idempotent).
    """
    tag = _create_or_reuse_tag(db, doc.user_id, name, kind=kind)
    applied = apply_tags(db, doc, [tag.id])
    db.flush()
    return tag, applied


def reject_tags(db: Session, doc: KbDocument, tag_ids: list[int]) -> int:
    """Remove ``KbDocumentTag`` rows for *tag_ids* ONLY when their
    provenance is ``"ai"`` or ``"manual"``.  Rule tags are never removed.
    Returns the count removed.
    """
    user_id = doc.user_id
    removed = 0
    for tag_id in tag_ids:
        row = (
            db.query(KbDocumentTag)
            .filter(
                KbDocumentTag.user_id == user_id,
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == tag_id,
                KbDocumentTag.provenance.in_(["ai", "manual"]),
            )
            .first()
        )
        if row is not None:
            db.delete(row)
            removed += 1
    db.flush()
    return removed


# ---------------------------------------------------------------------------
# Phrase 40 — ingest-stage entry point
# ---------------------------------------------------------------------------

def auto_tag_document(db: Session, doc: KbDocument) -> None:
    """Ingest-stage entry point for auto-tagging (phrase 40).

    Seeds inline/rule tags, proposes AI or fallback tags, persists
    suggestions, clears ``doc.tags_dirty``, and commits.  The
    coordinator wires this into the ingest pipeline after the
    embedding hook.
    """
    seed_inline_tags(db, doc)
    suggestions = propose_tags(db, doc)
    # Persist AI-suggested rows as provenance="ai" so the GET endpoint
    # can surface them without re-calling the LLM on every request.
    user_id = doc.user_id
    for sug in suggestions:
        if sug["provenance"] == "ai" and not _existing_document_tag(
            db, user_id, doc.id, sug["tag_id"]
        ):
            doc_tag = KbDocumentTag(
                user_id=user_id,
                document_id=doc.id,
                tag_id=sug["tag_id"],
                provenance="ai",
            )
            db.add(doc_tag)
    doc.tags_dirty = False
    db.add(doc)
    db.commit()