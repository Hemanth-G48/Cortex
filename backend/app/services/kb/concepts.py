"""Concept extraction & canonicalization services (Phase 2, Idea 15, phrases 43-47).

Provides:
- canonicalize: normalize a raw concept name to a canonical form.
- tfidf_concepts: deterministic TF-IDF fallback when AI is unavailable.
- extract_concepts: LLM extraction with AI+budget guard; falls back to TF-IDF.
- create_or_reuse: upsert a concept per (user_id, canonical_name) with alias merge.
- link_mentions: build MENTIONS edges from concept occurrences in document text.
- extract_for_document: orchestrate the full concept pipeline for one document.
"""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any

from sqlalchemy.orm import Session

from app.models import KbChunk, KbConcept, KbEdge, KbDocument
from app.models.kb.concept import KbConcept
from app.services.ai_client import ai_available, generate_json
from app.services.embeddings import budget_allows
from app.services.kb import KbService, utcnow

logger = logging.getLogger(__name__)

# Minimal English stopword set for TF-IDF filtering.
_STOPWORDS = frozenset(
    "a an the is are was were be been being have has had do does did "
    "will would shall should may might can could must need dare "
    "i me my we us our you your he him his she her it its they them their "
    "this that these those what which who whom whose where when how why "
    "and or but not nor so yet both either neither for from to in on at by "
    "with about between into through during before after above below of as "
    "if then else than too also very much more most just only even still "
    "already each every all some any no many few several other another".split()
)

# Regex for extracting noun-phrase-like candidates: words >= 5 chars,
# not a stopword, starting with a letter (avoids pure numbers/punctuation).
_CANDIDATE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{4,}")


def canonicalize(name: str) -> str:
    """Normalize a raw concept name to its canonical form (phrase 45).

    Steps: lowercase, trim, strip trailing punctuation, naive singularization
    (drop trailing 's' when len>3 and not double-s), collapse whitespace.
    Returns "" for empty or whitespace-only input.
    """
    if not name or not name.strip():
        return ""
    s = name.strip().lower()
    # Strip trailing punctuation (but keep internal hyphens/apostrophes).
    s = s.rstrip(".,;:!?\"'()[]{}<>")
    # Naive singularization: drop trailing 's' when len>3 and not already
    # double-s (e.g. "classes" → "classe" is wrong, so skip double-s).
    if len(s) > 3 and s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    # Collapse whitespace.
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens."""
    return re.findall(r"[A-Za-z][A-Za-z0-9_]*", text.lower())


def _idf_scores(doc_tokens: list[list[str]]) -> dict[str, float]:
    """Compute IDF scores across a corpus of token lists."""
    n_docs = len(doc_tokens)
    if n_docs == 0:
        return {}
    doc_freq: Counter = Counter()
    for tokens in doc_tokens:
        unique = set(tokens)
        for t in unique:
            doc_freq[t] += 1
    return {term: math.log((n_docs + 1) / (freq + 1)) + 1
            for term, freq in doc_freq.items()}


def tfidf_concepts(db: Session, doc: KbDocument, top_n: int = 8) -> list[str]:
    """Deterministic TF-IDF noun-phrase extraction (phrase 44).

    Builds a per-user corpus from the target document's chunks plus all other
    documents belonging to the same user, scores candidate tokens by TF-IDF,
    and returns the top-N canonicalized names.

    The corpus is loaded once per user via ``corpus.get_user_corpus`` (two
    batched queries, cached + signature-invalidated) instead of issuing one
    chunk query per document on every call — the reindex pipeline calls this
    once per document, so the old N+1 pattern made a large reindex quadratic.
    """
    from app.services.kb.corpus import get_user_corpus

    corpus = get_user_corpus(db, doc.user_id)
    flat = corpus.flat_tokens("concepts", _tokenize)
    target_tokens = flat.get(doc.id, [])
    if not target_tokens:
        return []

    # IDF is a pure function of the (immutable) corpus — compute once.
    idf = corpus.cached(  # type: ignore[return-value]
        "concepts_idf",
        lambda: _idf_scores(list(flat.values())),
    )
    tf = Counter(target_tokens)
    total = max(1, sum(tf.values()))

    # Score candidates: TF-IDF, filtered by length and stopword heuristics.
    candidates: list[tuple[float, str]] = []
    seen: set[str] = set()
    for token, count in tf.most_common():
        if token in seen:
            continue
        if len(token) < 5 or token in _STOPWORDS:
            continue
        score = (count / total) * idf.get(token, 1.0)
        candidates.append((score, token))
        seen.add(token)

    candidates.sort(key=lambda x: (-x[0], x[1]))
    return [canonicalize(t) for _, t in candidates[:top_n] if canonicalize(t)]


def extract_concepts(db: Session, doc: KbDocument) -> list[KbConcept]:
    """Extract concepts for a document (phrase 43).

    If AI is available and the daily budget allows, call the LLM with a
    compact chunk summary requesting [{concept, definition, aliases}].
    Otherwise (or on any failure) fall back to the deterministic TF-IDF
    path. Never raises.
    """
    # Try AI path first.
    if ai_available() and budget_allows(db, doc.user_id):
        try:
            chunks = (
                db.query(KbChunk)
                .filter(KbChunk.document_id == doc.id)
                .order_by(KbChunk.seq)
                .limit(20)
                .all()
            )
            summary = " ".join(c.content[:300] for c in chunks)
            if not summary.strip():
                summary = (doc.extracted_text or "")[:2000]

            prompt = (
                f"Extract up to 8 key concepts from the following document "
                f"chunk summary. For each concept return a JSON object with "
                f"\"concept\" (canonical name), \"definition\" (1-2 sentence "
                f"explanation), and \"aliases\" (list of alternate spellings). "
                f"Return a JSON array.\n\nSummary:\n{summary}"
            )
            result = generate_json(prompt, max_tokens=1500, temperature=0.3)
            if isinstance(result, list):
                concepts: list[KbConcept] = []
                for item in result[:8]:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("concept") or item.get("name") or "").strip()
                    if not name:
                        continue
                    canonical = canonicalize(name)
                    if not canonical:
                        continue
                    definition = item.get("definition") or None
                    aliases_raw = item.get("aliases") or []
                    aliases = (
                        [str(a).strip() for a in aliases_raw if str(a).strip()]
                        if isinstance(aliases_raw, list)
                        else []
                    )
                    concepts.append(KbConcept(
                        user_id=doc.user_id,
                        canonical_name=canonical,
                        definition=definition,
                        aliases=KbService.json_dumps(aliases) if aliases else None,
                    ))
                if concepts:
                    return concepts
        except Exception as exc:  # noqa: BLE001
            logger.warning("Concept LLM extraction failed, falling back: %s", exc)

    # Deterministic fallback.
    names = tfidf_concepts(db, doc)
    return [KbConcept(user_id=doc.user_id, canonical_name=n) for n in names]


def create_or_reuse(
    db: Session,
    user_id: int,
    name: str,
    definition: str | None = None,
    aliases: list[str] | None = None,
) -> KbConcept:
    """Find existing concept or create one (phrase 47).

    Match is by (user_id, canonical_name). On hit: merge new aliases into
    the existing row's alias list (dedup), update definition only if empty.
    Commits the change.
    """
    canonical = canonicalize(name)
    if not canonical:
        raise ValueError("canonical name is empty")

    existing = (
        db.query(KbConcept)
        .filter(KbConcept.user_id == user_id, KbConcept.canonical_name == canonical)
        .first()
    )
    if existing:
        # Merge aliases.
        existing_aliases: list[str] = (
            KbService.json_loads(existing.aliases) or []
            if isinstance(existing.aliases, str)
            else list(existing.aliases or [])
        )
        new_aliases = [a for a in (aliases or []) if a and a not in existing_aliases]
        if new_aliases:
            existing_aliases.extend(new_aliases)
            existing.aliases = KbService.json_dumps(existing_aliases)
        # Update definition only if currently empty.
        if definition and not existing.definition:
            existing.definition = definition
        existing.updated_at = utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    concept = KbConcept(
        user_id=user_id,
        canonical_name=canonical,
        definition=definition or None,
        aliases=KbService.json_dumps(aliases) if aliases else None,
    )
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def link_mentions(db: Session, doc: KbDocument, concepts: list[KbConcept]) -> int:
    """Build MENTIONS edges for each concept found in the document text (phrase 46).

    For each concept, count occurrences of any alias or the canonical name in
    the document's extracted_text. Weight = count / total_words, clamped to
    [0.05, 1.0]. Provenance is "ai" when the concept came from LLM extraction,
    "rule" when it appears as an inline tag or in frontmatter. Deduplicates by
    (source_document_id, target_concept_id, relation). Returns edges written.
    """
    if not doc.extracted_text:
        return 0

    text = doc.extracted_text
    total_words = max(1, len(re.findall(r"\b\w+\b", text)))
    edges_written = 0

    # Determine provenance: "ai" by default; "rule" if the name appears as
    # an inline tag (# concept) or in frontmatter.
    frontmatter = KbService.json_loads(doc.frontmatter_json) or {}
    frontmatter_text = " ".join(str(v) for v in frontmatter.values() if v)

    for concept in concepts:
        # Defensive: a MENTIONS edge needs a persisted concept id. Unpersisted
        # objects (id=None) would otherwise insert NULL target ids and violate
        # the kb_edges schema. Callers should pass create_or_reuse() results.
        if concept.id is None:
            logger.warning(
                "Skipping MENTIONS edge for unpersisted concept %r",
                concept.canonical_name,
            )
            continue
        aliases: list[str] = (
            KbService.json_loads(concept.aliases) or []
            if isinstance(concept.aliases, str)
            else list(concept.aliases or [])
        )
        # Search terms: canonical name + all aliases.
        search_terms = [concept.canonical_name] + [a for a in aliases if a != concept.canonical_name]

        count = 0
        for term in search_terms:
            # Count whole-word, case-insensitive occurrences.
            count += len(re.findall(rf"\b{re.escape(term)}\b", text, re.IGNORECASE))

        if count == 0:
            continue

        weight = min(1.0, max(0.05, count / total_words))

        # Determine provenance.
        provenance = "ai"
        # Check if the canonical name appears as an inline tag (# name) or in frontmatter.
        if re.search(rf"\b#\s*{re.escape(concept.canonical_name)}\b", text, re.IGNORECASE):
            provenance = "rule"
        if concept.canonical_name.lower() in frontmatter_text.lower():
            provenance = "rule"

        # Dedupe: check for existing MENTIONS edge.
        existing = (
            db.query(KbEdge)
            .filter(
                KbEdge.source_document_id == doc.id,
                KbEdge.target_concept_id == concept.id,
                KbEdge.relation == "MENTIONS",
            )
            .first()
        )
        if existing:
            # Update weight if higher.
            if weight > (existing.weight or 0):
                existing.weight = weight
                existing.provenance = provenance
                db.add(existing)
            continue

        edge = KbEdge(
            user_id=doc.user_id,
            source_document_id=doc.id,
            target_type="concept",
            target_concept_id=concept.id,
            relation="MENTIONS",
            weight=weight,
            provenance=provenance,
        )
        db.add(edge)
        edges_written += 1

    if edges_written:
        db.commit()
    return edges_written


def extract_for_document(db: Session, doc: KbDocument) -> int:
    """Orchestrate concept extraction for a single document (entry point).

    Extracts concepts, creates/reuses them, links MENTIONS edges, clears
    the document's graph_dirty flag, and commits. Returns the number of
    concepts processed.
    """
    concepts = extract_concepts(db, doc)
    # Persist each concept so the returned rows carry real ids, then link
    # mentions against those persisted rows (unpersisted objects have id=None
    # and would produce NULL kb_edges targets).
    persisted: list[KbConcept] = []
    for concept in concepts:
        persisted.append(
            create_or_reuse(db, doc.user_id, concept.canonical_name,
                            definition=concept.definition,
                            aliases=KbService.json_loads(concept.aliases) or [])
        )
    link_mentions(db, doc, persisted)
    doc.graph_dirty = False
    db.add(doc)
    db.commit()
    return len(concepts)
