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
    """topic_id -> [concept_ids] whose canonical name/alias equals the topic name."""
    topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    if not topics:
        return {}
    concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
    index: dict[int, list[int]] = {t.id: [] for t in topics}
    for t in topics:
        tname = (t.name or "").strip().lower()
        if not tname:
            continue
        for c in concepts:
            cand = [c.canonical_name or ""] + (KbService.json_loads(c.aliases) or [])
            if any(str(n).strip().lower() == tname for n in cand if str(n).strip()):
                index[t.id].append(c.id)
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
    """
    events = (
        db.query(KbSearchEvent)
        .filter(KbSearchEvent.user_id == user_id)
        .order_by(KbSearchEvent.created_at.desc())
        .limit(500)
        .all()
    )
    misses: dict[int, int] = {}
    for e in events:
        results = KbService.json_loads(e.result_ids) or []
        if results:
            continue  # had results — not a miss, regardless of click
        q = (e.query or "").strip().lower()
        if not q:
            continue
        for c in concepts:
            cand = [c.canonical_name or ""] + (KbService.json_loads(c.aliases) or [])
            if any(q in str(n).strip().lower() for n in cand if str(n).strip()):
                misses[c.id] = misses.get(c.id, 0) + 1
    return misses


def _mention_sources(db: Session, user_id: int, concept_id: int, limit: int = 3) -> list[dict]:
    """Documents that MENTIONS this concept — suggested capture sources."""
    rows = (
        db.query(KbDocument)
        .join(KbEdge, KbEdge.source_document_id == KbDocument.id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.target_concept_id == concept_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
        )
        .limit(limit)
        .all()
    )
    return [
        {"document_id": d.id, "title": d.title or d.path_rel or f"doc {d.id}"}
        for d in rows
    ]


def concept_gaps(db: Session, user_id: int, *, limit: int = 20) -> list[dict]:
    """Ranked per-concept gaps with evidence (phrase 16)."""
    concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
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
                "sources": _mention_sources(db, user_id, c.id),
            }
        )

    scored.sort(key=lambda g: g["score"], reverse=True)
    return scored[:limit]
