"""Idea 92 — long-term memory system.

The episodic journal (``episodic_memory``) records what *happened* in the
learner's history beyond the Phase 8 ``user_memory`` concept table. This module:

- **appends** episodes from ``learning_events`` (Phase 6) automatically
  (phrase 13);
- **consolidates** old episodes into durable facts weekly, budget-capped
  (phrase 14), folding strength bumps + new concept entries back into
  ``user_memory`` (phrase 15);
- **injects** a compact durable-facts block into tutor/agent prompts
  (phrase 16) — token-aware and small.

Consolidation is idempotent: a ``consolidated`` episode records the covered
episode ids, so re-running folds each episode exactly once. Deterministic
fallbacks (AI disabled) fold via topic→concept memory bumps only.
``user_memory`` and ``learning_events`` schemas are never modified here
(phrase 20 — Idea 99 depends on them).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import EpisodicMemory, KbConcept, LearningEvent, Topic
from app.services import ai_client
from app.services.kb import KbService, utcnow
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.memory import bump

logger = logging.getLogger(__name__)

# Deterministic summary templates per event type (phrase 13).
_SUMMARY_TMPL = {
    "study": "Studied {topic} ({value} minutes)",
    "session": "Focused session on {topic} ({value} minutes)",
    "quiz": "Quizzed on {topic} — accuracy {value:.0%}",
    "revision": "Revised {topic} (grade {value:.0%})",
    "lab": "Completed lab for {topic}",
    "outcome": "Checked off an outcome on {topic}",
    "doubt": "Asked for help on {topic}",
}


# --------------------------------------------------------------------------- #
# Episode appends (phrase 13)
# --------------------------------------------------------------------------- #


def _covered_ids(db: Session, user_id: int) -> set[int]:
    """Episode ids already folded by previous consolidation runs (idempotency)."""
    covered: set[int] = set()
    for row in (
        db.query(EpisodicMemory)
        .filter(EpisodicMemory.user_id == user_id, EpisodicMemory.event_type == "consolidated")
        .all()
    ):
        refs = KbService.json_loads(row.refs) or {}
        covered.update(int(i) for i in (refs.get("episode_ids") or []))
    return covered


def append_episodes(db: Session, user_id: int, *, limit: int = 100) -> int:
    """Append episodes for learning events not yet journaled. Returns created.

    Deterministic summaries; ``refs`` carries the learning-event ids.
    """
    event_ids = {
        int(eid)
        for eid in _event_refs(db, user_id)
    }
    existing_events = {
        int(eid)
        for row in db.query(EpisodicMemory).filter(EpisodicMemory.user_id == user_id).all()
        for eid in (KbService.json_loads(row.refs) or {}).get("learning_event_ids") or []
    }
    rows = (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == user_id)
        .order_by(LearningEvent.created_at.asc(), LearningEvent.id.asc())
        .limit(limit)
        .all()
    )
    created = 0
    for event in rows:
        if event.id in existing_events:
            continue
        summary = _episode_summary(db, user_id, event)
        refs = {"learning_event_ids": [event.id]}
        if event.topic_id:
            refs["topic_id"] = event.topic_id
        db.add(
            EpisodicMemory(
                user_id=user_id,
                event_type=event.event_type,
                summary=summary,
                refs=KbService.json_dumps(refs),
            )
        )
        existing_events.add(event.id)
        created += 1
    if created:
        db.flush()
    return created


def _event_refs(db: Session, user_id: int) -> set[int]:
    out: set[int] = set()
    for row in db.query(EpisodicMemory).filter(EpisodicMemory.user_id == user_id).all():
        refs = KbService.json_loads(row.refs) or {}
        out.update(refs.get("learning_event_ids") or [])
    return out


def _episode_summary(db: Session, user_id: int, event: LearningEvent) -> str:
    topic_name = None
    if event.topic_id:
        topic = db.query(Topic).filter(Topic.id == event.topic_id, Topic.user_id == user_id).first()
        topic_name = topic.name if topic else None
    tmpl = _SUMMARY_TMPL.get(event.event_type)
    if tmpl and topic_name:
        return tmpl.format(topic=topic_name, value=float(event.value or 0.0))
    if topic_name:
        return f"Activity on {topic_name}"
    return f"{event.event_type} event"


# --------------------------------------------------------------------------- #
# Consolidation (phrase 14)
# --------------------------------------------------------------------------- #


def _unconsolidated(db: Session, user_id: int, *, days: int | None = None) -> list[EpisodicMemory]:
    days = settings.kb_memory_consolidation_days if days is None else max(0, int(days))
    cutoff = utcnow() - timedelta(days=days)
    covered = _covered_ids(db, user_id)
    return [
        row
        for row in db.query(EpisodicMemory)
        .filter(
            EpisodicMemory.user_id == user_id,
            EpisodicMemory.event_type != "consolidated",
            EpisodicMemory.created_at <= cutoff,
        )
        .all()
        if row.id not in covered
    ]


def consolidate(db: Session, user_id: int, *, days: int | None = None) -> dict:
    """Fold episodes older than ``days`` into durable user_memory facts.

    Budget-capped LLM pass extracts ``[{concept, strength_delta}]``; the
    deterministic fallback folds topic-attached concepts with a fixed bump.
    Idempotent — covered episode ids are recorded on a ``consolidated`` row.
    """
    episodes = _unconsolidated(db, user_id, days=days)
    if not episodes:
        return {"episodes": 0, "facts": 0, "folded": 0, "skipped": True, "reason": "nothing to consolidate"}

    episode_ids = [e.id for e in episodes]
    facts: list[dict] = []
    ai_used = False
    if ai_client.ai_available() and budget_allows(db, user_id):
        parsed = ai_client.generate_json(_consolidation_prompt(episodes), max_tokens=800)
        facts = _normalise_facts(parsed)
        if facts:
            ai_used = True
            record_generation(db, user_id, "summary")

    if not facts:
        facts = _fallback_facts(db, user_id, episodes)

    folded = _fold_facts(db, user_id, facts)
    # Mark this batch consolidated (idempotency marker).
    db.add(
        EpisodicMemory(
            user_id=user_id,
            event_type="consolidated",
            summary=f"Consolidated {len(episodes)} episodes into {len(facts)} durable fact(s).",
            refs=KbService.json_dumps({"episode_ids": episode_ids, "facts": folded}),
        )
    )
    db.flush()
    return {
        "episodes": len(episodes),
        "facts": len(facts),
        "folded": folded,
        "ai_used": ai_used,
    }


def _consolidation_prompt(episodes: list[EpisodicMemory]) -> str:
    lines = "\n".join(f"- [{e.event_type}] {e.summary}" for e in episodes[:40])
    return (
        "Turn these learning-history episodes into durable facts the learner now "
        "knows. Return ONLY JSON: {\"facts\": [{\"concept\": \"...\", "
        "\"strength_delta\": 0.1, \"note\": \"...\"}]}. Max 8 facts.\n"
        f"EPISODES:\n{lines}"
    )


def _normalise_facts(parsed: object) -> list[dict]:
    if not isinstance(parsed, dict):
        return []
    facts = parsed.get("facts")
    if not isinstance(facts, list):
        return []
    out: list[dict] = []
    for f in facts:
        if not isinstance(f, dict):
            continue
        concept = str(f.get("concept") or "").strip()
        if not concept or len(concept) > 200:
            continue
        try:
            delta = max(0.0, min(0.5, float(f.get("strength_delta") or 0.05)))
        except (ValueError, TypeError):
            delta = 0.05
        out.append({"concept": concept, "strength_delta": round(delta, 4)})
    return out[:8]


def _fallback_facts(db: Session, user_id: int, episodes: list[EpisodicMemory]) -> list[dict]:
    """Deterministic consolidation: bump concepts attached to episode topics.

    Uses the same topic→concept memory mapping as the rest of Phase 8 — no
    new concepts are invented, so the fallback never hallucinates.
    """
    topic_ids = {
        int(tid)
        for e in episodes
        for tid in [(KbService.json_loads(e.refs) or {}).get("topic_id")]
        if tid
    }
    out: list[dict] = []
    if topic_ids:
        from app.services.kb.memory import bump_from_topic

        for tid in topic_ids:
            bumped = bump_from_topic(db, user_id, tid, delta=0.05, source="revision")
            for cid in bumped:
                concept = db.query(KbConcept).filter(KbConcept.id == cid).first()
                if concept is not None:
                    out.append({"concept": concept.canonical_name, "strength_delta": 0.05})
    return out


def _fold_facts(db: Session, user_id: int, facts: list[dict]) -> int:
    """Fold durable facts into user_memory (phrase 15): upsert concepts + bump."""
    folded = 0
    for fact in facts:
        concept = _get_or_create_concept(db, user_id, fact["concept"])
        if concept is None:
            continue
        bumped = bump(db, user_id, [concept.id], delta=fact["strength_delta"], source="revision")
        if bumped:
            folded += 1
    db.flush()
    return folded


def _get_or_create_concept(db: Session, user_id: int, name: str) -> KbConcept | None:
    name = name.strip()
    if not name:
        return None
    row = (
        db.query(KbConcept)
        .filter(KbConcept.user_id == user_id, KbConcept.canonical_name == name)
        .first()
    )
    if row is not None:
        return row
    row = KbConcept(user_id=user_id, canonical_name=name)
    db.add(row)
    db.flush()
    return row


# --------------------------------------------------------------------------- #
# Prompt injection (phrase 16)
# --------------------------------------------------------------------------- #


def durable_facts(db: Session, user_id: int, limit: int = 8) -> list[dict]:
    """The durable memory snapshot for prompt injection (compact)."""
    from app.services.kb.memory import get_memory

    return [
        {"concept": r["concept"], "strength": r["strength"]}
        for r in get_memory(db, user_id, limit=limit)
        if r["strength"] > 0
    ]


def durable_facts_block(db: Session, user_id: int, max_chars: int = 600) -> str:
    """Token-aware compact block; empty when there are no durable facts."""
    facts = durable_facts(db, user_id, limit=8)
    if not facts:
        return ""
    lines = [
        f"- {f['concept']} (strength {f['strength']:.2f})"
        for f in facts
    ]
    text = "Durable facts you know (grounded, from your learning history):\n" + "\n".join(lines)
    return text[:max_chars]


# --------------------------------------------------------------------------- #
# Job entry (phrase 14 — runs on kb_jobs via the automation runner)
# --------------------------------------------------------------------------- #


def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Automation-style entry: append new episodes, then consolidate weekly."""
    if not KbService.bool_setting("KB_MEMORY_CONSOLIDATION_ENABLED", False):
        return {"skipped": True, "reason": "KB_MEMORY_CONSOLIDATION_ENABLED is off"}
    appended = append_episodes(db, user_id)
    consolidated = consolidate(db, user_id)
    return {"appended": appended, **consolidated}


__all__ = [
    "append_episodes",
    "consolidate",
    "durable_facts",
    "durable_facts_block",
    "run",
]
