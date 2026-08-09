"""Phase 5 topic service (Ideas 44, 48, 49, 50).

Topics are extracted from a confirmed profile's parsed syllabus, synonym-folded
into canonical names (via ``kb_concepts``), Bloom-tagged, scored for difficulty,
given time estimates, and carry checkable learning outcomes that link to the
existing ``goals`` table on completion.
"""

from __future__ import annotations

import re
from datetime import date

from sqlalchemy.orm import Session

from app.models import Goal, KbConcept, SubjectProfile, Topic
from app.services import ai_client, ai_fallback
from app.services.kb import KbService, utcnow
from app.services.kb.budget import budget_allows, record_generation
from app.services.prompts import outcomes_expand_prompt, topic_difficulty_prompt

PENDING, CONFIRMED, MERGED, REJECTED = "pending", "confirmed", "merged", "rejected"

BLOOM_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Create", ("create", "design", "build", "develop", "synthesize", "construct", "compose")),
    ("Evaluate", ("evaluate", "critique", "justify", "assess", "defend", "judge", "rank")),
    ("Analyze", ("analyze", "compare", "contrast", "differentiate", "examine", "classify", "deconstruct")),
    ("Apply", ("apply", "solve", "use", "calculate", "demonstrate", "implement", "run")),
    ("Understand", ("explain", "describe", "summarize", "interpret", "discuss", "outline", "paraphrase")),
    ("Remember", ("list", "recall", "identify", "define", "name", "label", "state", "memorize")),
]

# Reading-rate base for time estimation (chars/minute for first pass).
_BASE_CHARS_PER_MIN = 180
_DIFF_FACTOR = {"E": 1.0, "M": 1.5, "H": 2.0}


def normalize_name(db: Session, user_id: int, name: str) -> str:
    """Canonical topic name: lowercase/trim, folded through ``kb_concepts``
    canonical names + aliases (Idea 44, phrase 34)."""
    folded = re.sub(r"\s+", " ", (name or "").strip().lower())
    if not folded:
        return folded
    concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
    for c in concepts:
        if (c.canonical_name or "").lower() == folded:
            return folded
        aliases = KbService.json_loads(c.aliases) or []
        for alias in aliases:
            if str(alias).strip().lower() == folded:
                return c.canonical_name.lower()
    return folded


def bloom_for(name: str, outcomes: list[str] | None = None) -> str:
    """Rule-based Bloom level from topic + outcome verbs (phrase 37)."""
    haystack = f"{name} {' '.join(outcomes or [])}".lower()
    for level, keywords in BLOOM_KEYWORDS:
        if any(k in haystack for k in keywords):
            return level
    return "Understand"


def estimate_times(chars: int, difficulty: str, multiplier: float = 1.0) -> tuple[int, int, int]:
    """Pure time-estimate formula (Idea 49, phrase 82).

    ``(first_pass_mins, review_mins, mastery_mins)`` — volume × difficulty
    factor, scaled by the user's pacing multiplier.
    """
    chars = max(0, chars or 0)
    factor = _DIFF_FACTOR.get(difficulty, 1.0)
    first = max(15, round((chars / _BASE_CHARS_PER_MIN) * factor))
    review = max(5, round(first * 0.4))
    mastery = max(5, round(first * 0.6))
    mult = max(0.1, multiplier if multiplier else 1.0)
    return (
        max(5, round(first * mult)),
        max(5, round(review * mult)),
        max(5, round(mastery * mult)),
    )


def estimate_difficulty(
    db: Session, user_id: int, name: str, description: str | None, outcomes: list[str],
    *,
    chars: int = 0,
) -> tuple[str, float]:
    """Weighted E/M/H + confidence (Idea 48, phrase 76).

    Votes: LLM rubric (budget-capped) → fallback keyword heuristic; concept
    overlap upward bias; content density upward bias. Returns (difficulty,
    confidence).
    """
    votes: list[tuple[str, float]] = []

    rubric = None
    if ai_client.ai_available() and budget_allows(db, user_id):
        rubric = ai_client.generate_json(
            topic_difficulty_prompt(name, description, outcomes), max_tokens=120
        )
        if isinstance(rubric, dict) and rubric.get("difficulty") in ("E", "M", "H"):
            votes.append(
                (
                    rubric["difficulty"],
                    float(rubric.get("confidence") or 0.7),
                )
            )
            record_generation(db, user_id, "difficulty")
    # Fall back whenever no valid vote landed (unreachable provider, non-dict,
    # or an invalid rubric value) — votes must never stay empty.
    if not votes:
        fb = ai_fallback.demo_difficulty(name, description, outcomes)
        votes.append((fb["difficulty"], float(fb["confidence"])))

    # Concept overlap: canonical name matches a known concept → slight up (73).
    concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
    overlap = 0.0
    folded = normalize_name(db, user_id, name)
    for c in concepts:
        if (c.canonical_name or "").lower() == folded:
            overlap = 0.5
            break
    if overlap:
        # bump the current vote one notch when it's not already Hard
        current = votes[0]
        bumped = {"E": "M", "M": "H"}.get(current[0], current[0])
        votes.append((bumped, overlap))

    # Density: lots of content → higher first-pass difficulty (74).
    if chars > 4000:
        current = votes[0]
        bumped = {"E": "M", "M": "H"}.get(current[0], current[0])
        votes.append((bumped, 0.4))

    # Weighted vote: E=0, M=1, H=2.
    order = {"E": 0, "M": 1, "H": 2}
    total_weight = sum(v[1] for v in votes) or 1.0
    score = sum(order[v[0]] * v[1] for v in votes) / total_weight
    difficulty = "E" if score < 0.75 else "H" if score > 1.4 else "M"
    confidence = min(1.0, max(v[1] for v in votes))
    return difficulty, round(confidence, 2)


def extract_topics(db: Session, user_id: int, profile: SubjectProfile) -> list[Topic]:
    """Create pending Topic rows from the confirmed profile's parsed units
    (Idea 44, phrase 33). Dedupes by normalized name within the subject."""
    if profile.curriculum_subject_id is None:
        raise ValueError("Profile is not confirmed")
    parsed = KbService.json_loads(profile.parsed_json) or {}
    subject_id = profile.curriculum_subject_id
    created: list[Topic] = []
    for unit in parsed.get("units", []):
        for t in unit.get("topics", []):
            name = (t.get("name") or "").strip()
            if not name:
                continue
            normalized = normalize_name(db, user_id, name)
            existing = (
                db.query(Topic)
                .filter(
                    Topic.user_id == user_id,
                    Topic.subject_id == subject_id,
                    Topic.normalized_name == normalized,
                )
                .first()
            )
            if existing:
                continue
            topic = Topic(
                user_id=user_id,
                subject_id=subject_id,
                unit_id=None,  # set by unit matching (Idea 45)
                name=name,
                normalized_name=normalized,
                bloom_level=bloom_for(name, t.get("outcomes")),
                outcomes=KbService.json_dumps(
                    [{"text": o, "status": "pending", "completed_at": None} for o in t.get("outcomes", [])]
                ),
                status=PENDING,
            )
            db.add(topic)
            created.append(topic)
    db.flush()
    return created


def set_topic_estimates(db: Session, user_id: int, topic: Topic, *, chars: int = 0) -> None:
    """Recompute difficulty + time estimates on a topic (phrases 76, 85)."""
    difficulty, confidence = estimate_difficulty(
        db, user_id, topic.name, None,
        [o.get("text", "") for o in (KbService.json_loads(topic.outcomes) or [])],
        chars=chars or 2000,
    )
    topic.difficulty = difficulty
    topic.difficulty_confidence = confidence
    first, review, mastery = estimate_times(chars or 2000, difficulty)
    topic.first_pass_mins, topic.review_mins, topic.mastery_mins = first, review, mastery
    db.flush()


# ---------------------------------------------------------------------------
# Review lifecycle (Idea 44, phrase 36)
# ---------------------------------------------------------------------------


def confirm_topic(db: Session, user_id: int, topic: Topic) -> Topic:
    if topic.user_id != user_id:
        raise ValueError("Not your topic")
    if topic.status == MERGED:
        raise ValueError("Merged topics cannot be confirmed")
    topic.status = CONFIRMED
    db.flush()
    return topic


def reject_topic(db: Session, user_id: int, topic: Topic) -> Topic:
    topic.status = REJECTED
    db.flush()
    return topic


def merge_topic(db: Session, user_id: int, topic: Topic, into: Topic) -> Topic:
    """Merge ``topic`` into ``into`` (phrase 36): re-point dependencies and
    merge outcomes, then mark ``topic`` merged."""
    if topic.id == into.id or topic.subject_id != into.subject_id:
        raise ValueError("Cannot merge into itself or across subjects")
    from app.models import TopicDependency

    deps = (
        db.query(TopicDependency)
        .filter(
            TopicDependency.user_id == user_id,
            (TopicDependency.prereq_topic_id == topic.id)
            | (TopicDependency.postreq_topic_id == topic.id),
        )
        .all()
    )
    for d in deps:
        if d.prereq_topic_id == topic.id:
            d.prereq_topic_id = into.id
        if d.postreq_topic_id == topic.id:
            d.postreq_topic_id = into.id
    mine = KbService.json_loads(topic.outcomes) or []
    theirs = KbService.json_loads(into.outcomes) or []
    merged = list(theirs)
    existing = {o.get("text") for o in merged}
    for o in mine:
        if o.get("text") not in existing:
            merged.append(o)
            existing.add(o.get("text"))
    into.outcomes = KbService.json_dumps(merged)
    topic.status = MERGED
    db.flush()
    return topic


# ---------------------------------------------------------------------------
# Learning outcomes (Idea 50, phrases 91–99)
# ---------------------------------------------------------------------------


def get_outcomes(topic: Topic) -> list[dict]:
    return KbService.json_loads(topic.outcomes) or []


def add_outcome(db: Session, topic: Topic, text: str) -> Topic:
    outcomes = get_outcomes(topic)
    outcomes.append({"text": text.strip(), "status": "pending", "completed_at": None})
    topic.outcomes = KbService.json_dumps(outcomes)
    db.flush()
    return topic


def expand_outcomes(db: Session, user_id: int, topic: Topic) -> Topic:
    """LLM expansion of raw outcome phrases (phrase 93), fallback (phrase 94)."""
    current = get_outcomes(topic)
    raw = [o["text"] for o in current]
    expanded = None
    if ai_client.ai_available() and budget_allows(db, user_id):
        parsed = ai_client.generate_json(outcomes_expand_prompt(topic.name, raw), max_tokens=600)
        if isinstance(parsed, dict) and isinstance(parsed.get("outcomes"), list):
            expanded = [str(o).strip() for o in parsed["outcomes"] if str(o).strip()]
            record_generation(db, user_id, "outcomes")
    if expanded is None:
        expanded = ai_fallback.demo_outcome_expand(topic.name, raw)
    seen = {o["text"] for o in current}
    for text in expanded:
        if text not in seen:
            current.append({"text": text, "status": "pending", "completed_at": None})
            seen.add(text)
    topic.outcomes = KbService.json_dumps(current)
    db.flush()
    return topic


def complete_outcome(db: Session, user_id: int, topic: Topic, index: int) -> Topic:
    """Mark an outcome done; link a Goal row (phrase 96)."""
    outcomes = get_outcomes(topic)
    if index < 0 or index >= len(outcomes):
        raise IndexError("Outcome index out of range")
    outcome = outcomes[index]
    today = date.today()
    if outcome["status"] == "done":
        outcome["status"] = "pending"
        outcome["completed_at"] = None
    else:
        outcome["status"] = "done"
        outcome["completed_at"] = today.isoformat()
        _link_goal(db, user_id, topic, outcome["text"], today)
    topic.outcomes = KbService.json_dumps(outcomes)
    db.flush()
    return topic


def _link_goal(db: Session, user_id: int, topic: Topic, outcome_text: str, today: date) -> None:
    """Upsert a Goal row for a completed outcome (Idea 50, phrase 96).

    The existing ``goals`` table is not user-scoped (matches the current goals
    router), so the row is keyed by title + year only.
    """
    quarter = f"Q{(today.month - 1) // 3 + 1}"
    title = f"{topic.name}: {outcome_text[:90]}"
    existing = (
        db.query(Goal)
        .filter(Goal.title == title, Goal.year == today.year)
        .first()
    )
    if existing:
        existing.is_completed = True
        existing.progress_percentage = 100.0
        return
    db.add(
        Goal(
            title=title,
            quarter=quarter,
            progress_percentage=100.0,
            year=today.year,
            target_date=today,
            is_completed=True,
        )
    )
