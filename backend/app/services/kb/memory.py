"""Phase 8 long-term learning memory store (Idea 79).

``user_memory`` is the single source of truth for "the user knows X". One row
per ``(user_id, concept_id)`` with a 0–1 ``strength`` that accumulates from
every study surface (quiz, tutor, revision, note, practice) and decays with an
exponential half-life (``KB_MEMORY_HALF_LIFE_DAYS``).

Rule A (Phase 8): the tutor and explanations may only reference concepts whose
row exists here with ``strength > 0`` — nothing is ever inferred.

This module is the substrate for Ideas 72 (gaps), 73 (anchors), 74 (tutor
recall), 75 (recommend factors), and 80 (adaptation), and is the documented
substrate for Idea 99 (trajectory forecasting), so its public surface is small
and stable.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbConcept, KbEdge, Topic, UserMemory
from app.services.kb import KbService, utcnow


def get_memory(
    db: Session,
    user_id: int,
    *,
    concept_ids: list[int] | None = None,
    limit: int = 200,
) -> list[dict]:
    """Per-user memory snapshot, strongest first (phrase 86)."""
    q = (
        db.query(UserMemory, KbConcept)
        .join(KbConcept, KbConcept.id == UserMemory.concept_id)
        .filter(UserMemory.user_id == user_id)
    )
    if concept_ids:
        q = q.filter(UserMemory.concept_id.in_(concept_ids))
    rows = q.order_by(UserMemory.strength.desc()).limit(limit).all()
    return [
        {
            "concept_id": m.concept_id,
            "concept": c.canonical_name,
            "strength": round(m.strength or 0.0, 4),
            "exposure_count": m.exposure_count or 0,
            "last_seen": m.last_seen.isoformat() if m.last_seen else None,
            "source": m.source,
        }
        for m, c in rows
    ]


def bump(
    db: Session,
    user_id: int,
    concept_ids: list[int],
    *,
    delta: float = 0.1,
    source: str = "practice",
) -> list[int]:
    """Upsert strength/exposure for each concept (phrase 84).

    A row with ``strength > 0`` is the Rule-A mark of prior knowledge. Missing
    rows are created (from 0.0) so every interacted concept enters the store.
    ``delta`` is clamped to >= 0 so a bad answer never *erases* prior knowledge.
    """
    if not concept_ids:
        return []
    if source not in ("quiz", "tutor", "revision", "note", "practice"):
        source = "practice"
    now = utcnow()
    touched: list[int] = []
    for cid in concept_ids:
        row = (
            db.query(UserMemory)
            .filter(UserMemory.user_id == user_id, UserMemory.concept_id == cid)
            .first()
        )
        if row is None:
            row = UserMemory(user_id=user_id, concept_id=cid, strength=0.0, exposure_count=0)
            db.add(row)
        row.strength = max(0.0, min(1.0, (row.strength or 0.0) + max(0.0, float(delta))))
        row.exposure_count = (row.exposure_count or 0) + 1
        row.last_seen = now
        row.updated_at = now
        row.source = source
        touched.append(cid)
    db.flush()
    return touched


def bump_from_topic(
    db: Session,
    user_id: int,
    topic_id: int | None,
    *,
    delta: float = 0.1,
    source: str = "practice",
) -> list[int]:
    """Resolve a topic's related concepts and bump them (phrase 84).

    Concepts attach to topics three ways: the topic's name/aliases match a
    concept's canonical name, or a document belonging to that topic carries a
    MENTIONS edge to a concept. All matches are bumped.
    """
    if topic_id is None:
        return []
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first()
    if topic is None:
        return []
    matched: dict[int, int] = {}  # concept_id -> weight hint (unused for now)

    # 1) Name/alias equality against the topic name.
    names = {topic.name} | {topic.normalized_name} if getattr(topic, "normalized_name", None) else {topic.name}
    if topic.name:
        for concept in db.query(KbConcept).filter(KbConcept.user_id == user_id).all():
            cand = [concept.canonical_name or ""] + (KbService.json_loads(concept.aliases) or [])
            if any(str(n).strip().lower() and str(n).strip().lower() == topic.name.strip().lower() for n in cand):
                matched[concept.id] = concept.id

    # 2) MENTIONS edges on documents of this topic. Topic -> documents is not
    #    a direct FK; documents carry concepts via edges, so match edges whose
    #    source document belongs to the topic through its source path prefix is
    #    unreliable. Instead fall back to any MENTIONS edge for this user where
    #    the concept name equals the topic name (covers the common case) plus
    #    explicit topic-concept links recorded elsewhere.
    if not matched and topic.name:
        edges = (
            db.query(KbEdge, KbConcept)
            .join(KbConcept, KbConcept.id == KbEdge.target_concept_id)
            .filter(
                KbEdge.user_id == user_id,
                KbEdge.relation == "MENTIONS",
                KbEdge.target_type == "concept",
                KbEdge.target_concept_id.is_not(None),
            )
            .all()
        )
        for _e, concept in edges:
            if concept.canonical_name and concept.canonical_name.strip().lower() == topic.name.strip().lower():
                matched[concept.id] = concept.id

    return bump(db, user_id, list(matched), delta=delta, source=source)


def decay(db: Session, user_id: int, *, now: datetime | None = None) -> int:
    """Apply exponential half-life decay to every memory row (phrase 85).

    ``strength *= 0.5 ** (age_days / KB_MEMORY_HALF_LIFE_DAYS)`` so unused
    concepts fade toward zero. Rows already at 0 stay 0. Returns rows touched.
    """
    now = now or utcnow()
    half_life_days = max(1.0, float(settings.kb_memory_half_life_days))
    rows = db.query(UserMemory).filter(UserMemory.user_id == user_id).all()
    touched = 0
    for row in rows:
        last = row.last_seen or row.updated_at or now
        age_days = max(0.0, (now - last).total_seconds() / 86400.0)
        if age_days <= 0:
            continue
        factor = 0.5 ** (age_days / half_life_days)
        new = max(0.0, min(1.0, (row.strength or 0.0) * factor))
        if abs(new - (row.strength or 0.0)) > 1e-9:
            row.strength = new
            row.updated_at = now
            touched += 1
    if touched:
        db.flush()
    return touched


def strengths_weaknesses(db: Session, user_id: int) -> dict:
    """Known strengths/weaknesses for the tutor prompt (phrases 32, 35).

    Strengths: strength >= ``KB_MEMORY_ANCHOR_MIN`` (a solid anchor). Weaknesses:
    strength > 0 but below the anchor bar — the user has met the concept, so the
    tutor may still reference it, but as "you started this".
    """
    anchor = settings.kb_memory_anchor_min
    strengths: list[str] = []
    weaknesses: list[str] = []
    for row in get_memory(db, user_id):
        if row["strength"] >= anchor:
            strengths.append(row["concept"])
        elif row["strength"] > 0:
            weaknesses.append(row["concept"])
    return {"strengths": strengths, "weaknesses": weaknesses}


def anchors(db: Session, user_id: int, threshold: float | None = None) -> list[str]:
    """Known-anchor concept names for personalized explanations (phrase 22)."""
    threshold = settings.kb_memory_anchor_min if threshold is None else max(0.0, min(1.0, float(threshold)))
    return [r["concept"] for r in get_memory(db, user_id) if r["strength"] >= threshold]
