"""Phase 8 concept-level knowledge-gap engine (Idea 72).

Extends the Phase 3 *topic*-level gap logic down to the *concept* atom. For each
concept the user has met, a gap score combines:
- memory strength / exposure (Idea 79 ``user_memory``) — never-met concepts are gaps,
- quiz/practice error counts on topics that match the concept (Phase 6 events),
- retrieval misses — ``kb_search_events`` where the user searched a concept but
  got nothing back (Phase 3 Idea 29).

Each gap carries evidence (errors, misses, strength) so the UI can say *why*,
plus the documents that mention the concept as suggested capture sources
(phrase 15). Feeds Idea 75 (recommend) and Idea 77 (missing-note suggestions).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KbConcept, KbDocument, KbEdge, KbSearchEvent, LearningEvent, Topic, UserMemory
from app.services.kb import KbService

# Weights for the composite formula (phrase 14). Sum = 1.0.
W_MEMORY = 0.5
W_ERRORS = 0.25
W_MISSES = 0.25
# Cap contributions so a single buggy search can't dominate the ranking.
MAX_ERROR_EVIDENCE = 3
MAX_MISS_EVIDENCE = 3
# A quiz attempt is an "error" below this accuracy (mirrors WEAK_MAX).
ERROR_ACC = 0.5


def _topic_concept_index(db: Session, user_id: int) -> dict[int, list[int]]:
    """topic_id -> [concept_ids] whose canonical name/alias equals the topic name.

    Built with a name → concept lookup instead of the old O(topics × concepts)
    double loop (which re-parsed every concept's alias JSON per topic and made
    the whole-user gap scan quadratic on real vaults).
    """
    topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    if not topics:
        return {}
    concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()

    # name (lower) → concept ids. JSON parsed once per concept, not per pair.
    lookup: dict[str, list[int]] = {}
    for c in concepts:
        cands = [c.canonical_name or ""] + (KbService.json_loads(c.aliases) or [])
        for n in cands:
            s = str(n).strip().lower()
            if s:
                lookup.setdefault(s, []).append(c.id)

    index: dict[int, list[int]] = {}
    for t in topics:
        tname = (t.name or "").strip().lower()
        if tname and tname in lookup:
            index[t.id] = lookup[tname]
    return index


def _error_counts(db: Session, user_id: int, topic_index: dict[int, list[int]]) -> dict[int, int]:
    """concept_id -> number of sub-pass quiz attempts (phrase 12)."""
    events = (
        db.query(LearningEvent)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.event_type == "quiz",
            LearningEvent.value < ERROR_ACC,
        )
        .all()
    )
    counts: dict[int, int] = {}
    for e in events:
        for cid in topic_index.get(e.topic_id or 0, []):
            counts[cid] = counts.get(cid, 0) + 1
    return counts


def _retrieval_misses(db: Session, user_id: int, concepts: list[KbConcept]) -> dict[int, int]:
    """concept_id -> number of searches that returned nothing (phrase 13).

    A miss is a search whose result list came back empty — the user looked for
    a concept and the vault had nothing to show. The query is matched against
    the concept's canonical name and aliases as a case-insensitive substring.
    Candidate strings are precomputed once so repeated scans don't re-parse
    every concept's alias JSON per search event.
    """
    events = (
        db.query(KbSearchEvent)
        .filter(KbSearchEvent.user_id == user_id)
        .order_by(KbSearchEvent.created_at.desc())
        .limit(500)
        .all()
    )
    if not events:
        return {}
    candidates: list[tuple[int, list[str]]] = []
    for c in concepts:
        cand = [c.canonical_name or ""] + (KbService.json_loads(c.aliases) or [])
        lowered = [str(n).strip().lower() for n in cand if str(n).strip()]
        if lowered:
            candidates.append((c.id, lowered))
    misses: dict[int, int] = {}
    for e in events:
        results = KbService.json_loads(e.result_ids) or []
        if results:
            continue  # had results — not a miss, regardless of click
        q = (e.query or "").strip().lower()
        if not q:
            continue
        for cid, cand in candidates:
            if any(q in n for n in cand):
                misses[cid] = misses.get(cid, 0) + 1
    return misses


def _mention_sources(db: Session, user_id: int, concept_id: int, limit: int = 3) -> list[dict]:
    """Documents that MENTIONS this concept — suggested capture sources."""
    return _mention_sources_batch(db, user_id, [concept_id], limit=limit).get(concept_id, [])


def _mention_sources_batch(
    db: Session, user_id: int, concept_ids: list[int], limit: int = 3
) -> dict[int, list[dict]]:
    """Mention-source documents for many concepts in ONE query.

    The old implementation ran one ``kb_edges`` scan per concept; with tens of
    thousands of edges that made the whole-user gap scan quadratic. Batched by
    ``target_concept_id IN (...)`` (indexed since the ``kb_edges`` schema fix),
    ordered by edge weight, capped per concept.
    """
    if not concept_ids:
        return {}
    rows = (
        db.query(
            KbEdge.target_concept_id,
            KbDocument.id,
            KbDocument.title,
            KbDocument.path_rel,
        )
        .join(KbDocument, KbEdge.source_document_id == KbDocument.id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.target_concept_id.in_(concept_ids),
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
        )
        .order_by(KbEdge.weight.desc())
        .all()
    )
    out: dict[int, list[dict]] = {}
    for concept_id, doc_id, title, path_rel in rows:
        lst = out.setdefault(concept_id, [])
        if len(lst) < limit:
            lst.append(
                {"document_id": doc_id, "title": title or path_rel or f"doc {doc_id}"}
            )
    return out


def concept_gaps(
    db: Session,
    user_id: int,
    *,
    limit: int = 20,
    concept_ids: set[int] | None = None,
) -> list[dict]:
    """Ranked per-concept gaps with evidence (phrase 16).

    ``concept_ids`` optionally restricts the candidate set (used by the
    course-level gap analysis to score only the concepts a subject's
    documents mention); ``None`` scores every concept (global view).
    """
    concepts_q = db.query(KbConcept).filter(KbConcept.user_id == user_id)
    if concept_ids is not None:
        if not concept_ids:
            return []
        concepts_q = concepts_q.filter(KbConcept.id.in_(concept_ids))
    concepts = concepts_q.all()
    if not concepts:
        return []
    concept_ids = [c.id for c in concepts]

    mem_rows = (
        db.query(UserMemory)
        .filter(UserMemory.user_id == user_id, UserMemory.concept_id.in_(concept_ids))
        .all()
    )
    mem = {m.concept_id: m for m in mem_rows}

    topic_index = _topic_concept_index(db, user_id)
    errors = _error_counts(db, user_id, topic_index)
    misses = _retrieval_misses(db, user_id, concepts)

    scored: list[dict] = []
    for c in concepts:
        m = mem.get(c.id)
        strength = m.strength if m else 0.0
        exposure = m.exposure_count if m else 0
        e = min(errors.get(c.id, 0), MAX_ERROR_EVIDENCE)
        s = min(misses.get(c.id, 0), MAX_MISS_EVIDENCE)
        never_met = 1.0 if m is None else 0.0
        score = (
            (1.0 - strength) * W_MEMORY
            + (e / MAX_ERROR_EVIDENCE) * W_ERRORS
            + (s / MAX_MISS_EVIDENCE) * W_MISSES
            + never_met * 0.05  # slight boost for untouched concepts
        )
        if score <= 0:
            continue
        scored.append(
            {
                "concept_id": c.id,
                "concept": c.canonical_name,
                "definition": c.definition,
                "score": round(score, 4),
                "evidence": {
                    "strength": round(strength, 4),
                    "exposure_count": exposure,
                    "quiz_errors": errors.get(c.id, 0),
                    "retrieval_misses": misses.get(c.id, 0),
                },
                "sources": [],  # filled in one batched query below
            }
        )

    scored.sort(key=lambda g: g["score"], reverse=True)
    scored = scored[:limit]
    # One query for all capture sources (was one kb_edges scan per concept).
    sources = _mention_sources_batch(
        db, user_id, [g["concept_id"] for g in scored]
    )
    for g in scored:
        g["sources"] = sources.get(g["concept_id"], [])
    return scored
