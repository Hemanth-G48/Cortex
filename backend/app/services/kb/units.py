"""Phase 5 unit & lecture segmentation (Idea 45, phrases 41–50).

Matches parsed syllabus units against existing ``curriculum_units`` for a
confirmed subject — normalized string similarity first, embedding cosine as a
fallback when no name match clears the threshold. The user confirms the mapping
before any topic gets a ``unit_id``.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.models import CurriculumUnit, Topic
from app.services.kb import KbService

NAME_THRESHOLD = 0.55
EMBED_THRESHOLD = 0.7


def _normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (name or "").lower()).strip()


def _token_overlap(a: str, b: str) -> float:
    ta = set(_normalise(a).split())
    tb = set(_normalise(b).split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def name_similarity(a: str, b: str) -> float:
    """Blend of SequenceMatcher ratio + token overlap (phrase 42)."""
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, _normalise(a), _normalise(b)).ratio()
    return round(max(ratio, _token_overlap(a, b)), 3)


def match_candidates(
    db: Session,
    user_id: int,
    subject_id: int,
    parsed_units: list[dict],
    *,
    use_embeddings: bool = False,
) -> list[dict]:
    """Candidate matches for each parsed unit (phrase 44).

    ``[{title, description, candidate_unit_id, candidate_title, score,
    match_type}]`` — match_type is ``name`` or ``embedding``; unmatched parsed
    units get ``candidate_unit_id=None`` and are returned as \"create new\"
    suggestions (phrase 47).
    """
    existing = (
        db.query(CurriculumUnit)
        .filter(CurriculumUnit.subject_id == subject_id, CurriculumUnit.is_active.is_(True))
        .all()
    )
    results: list[dict] = []
    for unit in parsed_units or []:
        title = (unit.get("title") or "").strip()
        if not title:
            continue
        # Track the top candidate even below threshold so the embedding
        # fallback has a unit to compare against (phrase 43).
        best: tuple[float, CurriculumUnit | None] = (0.0, None)
        for cand in existing:
            score = name_similarity(title, cand.name)
            if score >= best[0]:
                best = (score, cand)
        entry: dict = {
            "title": title,
            "description": unit.get("description"),
            "candidate_unit_id": None,
            "candidate_title": None,
            "score": 0.0,
            "match_type": "none",
        }
        if best[1] is None:
            results.append(entry)
            continue
        if best[0] >= NAME_THRESHOLD:
            entry.update(
                {
                    "candidate_unit_id": best[1].id,
                    "candidate_title": best[1].name,
                    "score": best[0],
                    "match_type": "name",
                }
            )
        elif use_embeddings:
            score = _embedding_match(db, user_id, title, best[1])
            if score >= EMBED_THRESHOLD:
                entry.update(
                    {
                        "candidate_unit_id": best[1].id,
                        "candidate_title": best[1].name,
                        "score": round(score, 3),
                        "match_type": "embedding",
                    }
                )
        results.append(entry)
    return results


def _embedding_match(db: Session, user_id: int, title: str, candidate: CurriculumUnit) -> float:
    """Cosine similarity via the Phase 2 embeddings service (phrase 43).

    Never throws — returns 0 when embeddings are unavailable.
    """
    try:
        from app.services import embeddings

        vecs, _ = embeddings.backend_embed(
            [title, f"{candidate.name} {candidate.description or ''}"],
            budget_check=False,
        )
        if not vecs or len(vecs) < 2:
            return 0.0
        return _cosine(vecs[0], vecs[1])
    except Exception:  # noqa: BLE001 — matching must degrade gracefully
        return 0.0


def _cosine(a: list[float], b: list[float]) -> float:
    import math

    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return max(0.0, dot / (na * nb))


def confirm_mapping(
    db: Session,
    user_id: int,
    subject_id: int,
    mapping: dict[str, int],
    *,
    parsed_units: list[dict] | None = None,
) -> int:
    """Persist parsed-unit title → ``curriculum_unit.id`` and set ``Topic.unit_id``
    from the mapping (phrases 45–46). Returns how many topics were assigned."""
    linked: dict[int, int] = {}  # unit_number → curriculum_unit.id
    for i, unit in enumerate(parsed_units or [], start=1):
        unit_id = mapping.get(unit.get("title") or "")
        if unit_id:
            linked[i] = unit_id

    assigned = 0
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == subject_id)
        .all()
    )
    # topics know their unit by the syllabus order they were extracted from —
    # map them back via their position within the parsed units list.
    for i, unit in enumerate(parsed_units or [], start=1):
        unit_id = linked.get(i)
        if not unit_id:
            continue
        names = {(t.get("name") or "").lower() for t in unit.get("topics", [])}
        for t in topics:
            if t.name.lower() in names and t.unit_id is None:
                t.unit_id = unit_id
                assigned += 1
    db.flush()
    return assigned
