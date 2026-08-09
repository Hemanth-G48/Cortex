"""Phase 8 learning-preference profile (Idea 71).

One ``UserPreference`` row per user (unique ``user_id``). The profile drives
prompt rendering across the tutor and explanations: ``depth`` (overview vs
deep-dive), a 0–1 ``examples_vs_theory`` slider, verbosity ``style``, preferred
``session_length_mins``, and the explanation register
(plain | analogy | formal). Every write is validated/clamped — no arbitrary
strings. A behavioral nudge (phrase 8, phrase 25) adjusts a subset of fields
with ``provenance=inferred`` so the user can see what was inferred vs. chosen.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import UserPreference
from app.services.kb import utcnow

VALID_DEPTH = ("overview", "deep_dive")
VALID_STYLE = ("concise", "detailed")
VALID_EXPLANATION_STYLE = ("plain", "analogy", "formal")

# Maximum reasonable session length (minutes) — beyond this clamps.
MAX_SESSION_MINS = 480


def defaults() -> dict:
    return {
        "depth": "overview",
        "examples_vs_theory": 0.5,
        "style": "concise",
        "session_length_mins": 30,
        "explanation_style": "plain",
        "onboarding_completed": False,
    }


def _row_to_dict(row: UserPreference) -> dict:
    return {
        "depth": row.depth or "overview",
        "examples_vs_theory": round(row.examples_vs_theory if row.examples_vs_theory is not None else 0.5, 4),
        "style": row.style or "concise",
        "session_length_mins": row.session_length_mins or 30,
        "explanation_style": row.explanation_style or "plain",
        "onboarding_completed": bool(row.onboarding_completed),
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def get_preferences(db: Session, user_id: int) -> dict:
    """Current profile, or defaults when the user hasn't set one (phrase 3)."""
    row = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    return _row_to_dict(row) if row else defaults()


def _sanitize(data: dict) -> dict:
    """Validate + clamp inbound fields; unknown values fall back to defaults."""
    out = defaults()
    if data.get("depth") in VALID_DEPTH:
        out["depth"] = data["depth"]
    if data.get("style") in VALID_STYLE:
        out["style"] = data["style"]
    if data.get("explanation_style") in VALID_EXPLANATION_STYLE:
        out["explanation_style"] = data["explanation_style"]
    evt = data.get("examples_vs_theory")
    if evt is not None:
        out["examples_vs_theory"] = max(0.0, min(1.0, float(evt)))
    mins = data.get("session_length_mins")
    if mins is not None:
        out["session_length_mins"] = max(1, min(MAX_SESSION_MINS, int(mins)))
    ob = data.get("onboarding_completed")
    if ob is not None:
        out["onboarding_completed"] = bool(ob)
    return out


def upsert_preferences(db: Session, user_id: int, data: dict) -> dict:
    """Create or update the user's profile with validation (phrases 3–4).

    Partial payloads merge over the current profile (PATCH semantics) so a
    client can update one field without resetting the rest to defaults.
    """
    current = get_preferences(db, user_id)
    clean = _sanitize({**current, **data})
    row = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if row is None:
        row = UserPreference(user_id=user_id)
        db.add(row)
    row.depth = clean["depth"]
    row.examples_vs_theory = clean["examples_vs_theory"]
    row.style = clean["style"]
    row.session_length_mins = clean["session_length_mins"]
    row.explanation_style = clean["explanation_style"]
    row.onboarding_completed = clean["onboarding_completed"]
    row.updated_at = utcnow()
    db.flush()
    return _row_to_dict(row)


def preferences_prompt(profile: dict | None) -> str:
    """Render the profile into a prompt snippet (phrase 5).

    Empty when the profile is unset/onboarding-incomplete, so the tutor and
    explanations degrade to their default style rather than reading noise.
    """
    if not profile or not profile.get("onboarding_completed"):
        return ""
    lines = [
        "Learning profile (adapt your style to this student):",
        f"- depth: {profile.get('depth', 'overview')}",
        f"- verbosity: {profile.get('style', 'concise')}",
        f"- explanation style: {profile.get('explanation_style', 'plain')}",
        f"- examples vs theory: {profile.get('examples_vs_theory', 0.5):.2f} "
        "(higher = more worked examples)",
        f"- preferred session length: {profile.get('session_length_mins', 30)} minutes",
    ]
    return "\n".join(lines)


def infer_adjustment(
    db: Session,
    user_id: int,
    *,
    depth: str | None = None,
    examples_vs_theory: float | None = None,
    style: str | None = None,
    explanation_style: str | None = None,
    session_length_mins: int | None = None,
) -> dict:
    """Apply a single inferred preference signal (phrases 8, 25).

    Only explicitly-passed signals are applied (so callers decide what counts
    as evidence, e.g. "the user asked for simpler"). Returns
    ``{provenance: 'inferred', changed: {field: old->new}}``; no-op when every
    signal is None or already matches.
    """
    current = get_preferences(db, user_id)
    patch = _sanitize(
        {
            "depth": depth,
            "examples_vs_theory": examples_vs_theory,
            "style": style,
            "explanation_style": explanation_style,
            "session_length_mins": session_length_mins,
            "onboarding_completed": current["onboarding_completed"],
        }
    )
    changed = {}
    for field in ("depth", "examples_vs_theory", "style", "explanation_style", "session_length_mins"):
        if patch[field] != current[field]:
            changed[field] = {"from": current[field], "to": patch[field]}
    if changed:
        upsert_preferences(db, user_id, patch)
    return {"provenance": "inferred", "changed": changed}


def nudge_for_feedback(db: Session, user_id: int, feedback: str) -> dict:
    """Implicit preference adjustment from follow-up feedback (phrase 25).

    "simpler"/"too complex"/"confusing" → plain register + concise verbosity;
    "more examples"/"concrete" → nudge the examples-vs-theory slider up. Both
    write with ``provenance=inferred`` so the profile never silently diverges
    from what the user chose. No-op when no signal matches.
    """
    f = (feedback or "").lower()
    if any(k in f for k in ("simpler", "too complex", "simplify", "confusing")):
        return infer_adjustment(db, user_id, explanation_style="plain", style="concise")
    if any(k in f for k in ("example", "examples", "concrete")):
        return infer_adjustment(db, user_id, examples_vs_theory=0.8)
    return {"provenance": "inferred", "changed": {}}


def nudge_from_behavior(db: Session, user_id: int, *, min_sessions: int = 3) -> dict:
    """Infer session length from recent study events (phrase 8).

    Averages the last ``min_sessions`` ``session``/``study`` events (minutes)
    and nudges ``session_length_mins`` toward it (clamped to a sane 5–240
    range). No-op when there isn't enough evidence.
    """
    from app.models import LearningEvent

    events = (
        db.query(LearningEvent)
        .filter(
            LearningEvent.user_id == user_id,
            LearningEvent.event_type.in_(("session", "study")),
        )
        .order_by(LearningEvent.created_at.desc())
        .limit(min_sessions)
        .all()
    )
    if len(events) < min_sessions:
        return {"provenance": "inferred", "changed": {}}
    avg = sum(float(e.value or 0.0) for e in events) / len(events)
    target = max(5, min(240, round(avg)))
    return infer_adjustment(db, user_id, session_length_mins=target)
