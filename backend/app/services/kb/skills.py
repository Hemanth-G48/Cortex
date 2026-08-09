"""Phase 7 skill mapping (Idea 70, phrases 91–99).

A versioned taxonomy (``app/data/skills.json``) is matched against a user's
topics/outcomes — LLM first (budget-capped), keyword fallback. Each user's
skill rows aggregate the mastery of contributing topics into a 1–5 level
(phrase 95); interview scores nudge the relevant skill (phrase 96).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Topic, UserSkill
from app.services import ai_client
from app.services.kb import KbService
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.mastery import mastery_by_topic

logger = logging.getLogger(__name__)

TAXONOMY_CACHE: dict | None = None


def load_taxonomy() -> dict:
    """Load + cache the versioned skill taxonomy (phrase 91)."""
    global TAXONOMY_CACHE
    if TAXONOMY_CACHE is not None:
        return TAXONOMY_CACHE
    path = Path(settings.KB_SKILLS_JSON)
    if not path.is_absolute():
        # services/kb/skills.py → backend/ (4 levels up) then app/data/…
        path = Path(__file__).resolve().parent.parent.parent.parent / settings.KB_SKILLS_JSON
    try:
        with open(path, encoding="utf-8") as fh:
            TAXONOMY_CACHE = json.load(fh)
    except (OSError, ValueError):
        TAXONOMY_CACHE = {"version": 0, "skills": []}
    return TAXONOMY_CACHE


def _skill_index() -> dict[str, dict]:
    """``{skill_id: {name, keywords}}``."""
    return {s["id"]: s for s in load_taxonomy().get("skills", [])}


def _keyword_match(text: str) -> list[str]:
    """Rule-based fallback: taxonomy keyword hits in topic name + outcomes."""
    text = (text or "").lower()
    hits: list[tuple[int, str]] = []
    for sid, skill in _skill_index().items():
        score = sum(1 for kw in skill.get("keywords", []) if kw.lower() in text)
        if score:
            hits.append((score, sid))
    hits.sort(reverse=True)
    return [sid for _, sid in hits[:3]]


def map_subject(db: Session, user_id: int, subject_id: int) -> list[UserSkill]:
    """Map a subject's topics → skills and upsert UserSkill rows (phrases 94–95)."""
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == subject_id)
        .all()
    )
    if not topics:
        return []

    topic_map: dict[str, Topic] = {}
    listing: list[str] = []
    for t in topics:
        topic_map.setdefault(t.normalized_name or t.name.lower(), t)
        listing.append(t.name)

    mapping: dict[str, str] = {}  # topic name → skill_id
    used_ai = False
    if ai_client.ai_available() and budget_allows(db, user_id):
        from app.services.prompts import skill_mapping_prompt

        parsed = ai_client.generate_json(skill_mapping_prompt(f"subject {subject_id}", listing), max_tokens=1200)
        if isinstance(parsed, dict) and isinstance(parsed.get("mappings"), list):
            for m in parsed["mappings"]:
                if isinstance(m, dict) and m.get("topic") and m.get("skill_id"):
                    mapping[str(m["topic"]).strip().lower()] = str(m["skill_id"])
            record_generation(db, user_id, "skills")
            used_ai = True

    if not mapping:
        for t in topics:
            blob = f"{t.name} {' '.join(o.get('text', '') for o in (KbService.json_loads(t.outcomes) or []))}"
            matches = _keyword_match(blob)
            if matches:
                mapping[t.normalized_name or t.name.lower()] = matches[0]

    # Aggregate mastery per skill from contributing topics.
    ids = [t.id for t in topics]
    mastery = mastery_by_topic(db, user_id, ids)
    by_skill: dict[str, list[dict]] = {}
    for t in topics:
        sid = mapping.get(t.normalized_name or t.name.lower())
        if not sid:
            continue
        by_skill.setdefault(sid, []).append(
            {"topic_id": t.id, "topic_name": t.name, "score": mastery[t.id]["score"]}
        )

    upserted: list[UserSkill] = []
    for sid, contrib in by_skill.items():
        avg = round(sum(c["score"] for c in contrib) / len(contrib), 4)
        row = (
            db.query(UserSkill)
            .filter(UserSkill.user_id == user_id, UserSkill.skill_id == sid)
            .first()
        )
        if row is None:
            row = UserSkill(user_id=user_id, skill_id=sid, mastery=avg, level=_level_for(avg))
            db.add(row)
        else:
            row.mastery = avg
            row.level = _level_for(avg)
        row.contributing_topics = KbService.json_dumps(contrib)
        upserted.append(row)
    db.flush()
    return upserted


def _level_for(mastery: float) -> int:
    """1–5 level from aggregated mastery (phrase 95)."""
    m = max(0.0, min(1.0, mastery))
    return max(1, min(5, int(m * 5 + 0.5)))  # round-half-up (not banker's)


def apply_interview_score(db: Session, user_id: int, skill_id: str, score: int) -> None:
    """Nudge the skill level from an interview session score (phrase 96)."""
    row = (
        db.query(UserSkill)
        .filter(UserSkill.user_id == user_id, UserSkill.skill_id == skill_id)
        .first()
    )
    if row is None:
        row = UserSkill(user_id=user_id, skill_id=skill_id, mastery=0.0)
        db.add(row)
    # Interview evidence shifts mastery a fifth of the way toward score/100.
    blended = row.mastery + (min(1.0, max(0.0, score / 100.0)) - row.mastery) * 0.2
    row.mastery = round(blended, 4)
    row.level = _level_for(row.mastery)
    db.flush()


def profile(db: Session, user_id: int) -> list[dict]:
    """The user's skill profile (phrase 97): skill, level, mastery, topics."""
    rows = (
        db.query(UserSkill)
        .filter(UserSkill.user_id == user_id)
        .order_by(UserSkill.level.desc(), UserSkill.mastery.desc())
        .all()
    )
    index = _skill_index()
    out = []
    for r in rows:
        out.append(
            {
                "skill_id": r.skill_id,
                "name": index.get(r.skill_id, {}).get("name", r.skill_id),
                "level": r.level,
                "mastery": r.mastery,
                "contributing_topics": KbService.json_loads(r.contributing_topics) or [],
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
        )
    return out


def export(db: Session, user_id: int, fmt: str = "markdown") -> str:
    """Portfolio export (phrase 98): markdown or JSON skills summary."""
    rows = profile(db, user_id)
    if fmt == "json":
        return json.dumps({"version": load_taxonomy().get("version"), "skills": rows}, indent=2)
    if not rows:
        return "# Skills\n\nNo skills mapped yet — import a syllabus to build your profile.\n"
    lines = ["# Skills Profile\n"]
    for r in rows:
        bars = "●" * r["level"] + "○" * (5 - r["level"])
        lines.append(f"## {r['name']} ({r['skill_id']})\n")
        lines.append(f"- Level: {r['level']} {bars}  \n- Mastery: {round(r['mastery'] * 100)}%\n")
        topics = ", ".join(t["topic_name"] for t in r["contributing_topics"])
        if topics:
            lines.append(f"- Contributing topics: {topics}\n")
        lines.append("")
    return "\n".join(lines)


__all__ = ["load_taxonomy", "map_subject", "profile", "export", "apply_interview_score", "_level_for"]
