"""Idea 97 — intelligent recommendation engine.

Cross-domain candidate generation (phrase 62) over the Phase 8 Idea 75
recommender: study next, revisit notes, read papers, take practice sets. Each
candidate is ranked by ``urgency × weakness × readiness`` (phrase 63) using
``KB_RECOMMENDATION_WEIGHTS`` and carries an explainable reason (phrase 64).
Accept/skip feedback is logged into ``ai_logs`` (feature=``recommend``) so
Idea 100 can tune the weights (phrase 66). Deterministic — no LLM calls.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbEdge, Topic, UserMemory
from app.services.kb import KbService
from app.services.kb import ai_log as ai_log_service
from app.services.kb import next_action as next_action_service
from app.services.kb import revision as revision_service
from app.services.kb.mastery import mastery_by_topic

# Domain labels (phrase 62).
DOMAINS = ("study", "revisit", "read", "practice")


def candidates(db: Session, user_id: int, *, limit: int = 8) -> list[dict]:
    """Ranked cross-domain candidates with explainable reasons (phrases 62–64)."""
    weights = settings.kb_recommendation_weights
    pool = (
        _study_candidates(db, user_id)
        + _revisit_candidates(db, user_id)
        + _read_candidates(db, user_id)
        + _practice_candidates(db, user_id)
    )
    for c in pool:
        c["score"] = round(
            weights.get("urgency", 0.4) * c["urgency"]
            + weights.get("weakness", 0.3) * c["weakness"]
            + weights.get("readiness", 0.3) * c["readiness"],
            4,
        )
    pool.sort(key=lambda c: (-c["score"], c["id"]))
    return pool[:limit]


def _base(domain: str, target_id: int, title: str) -> dict:
    return {
        "id": f"{domain}:{target_id}",
        "domain": domain,
        "target": target_id,
        "title": title,
        "reason": "",
        "urgency": 0.0,
        "weakness": 0.5,
        "readiness": 0.5,
    }


# --------------------------------------------------------------------------- #
# Candidate sources (phrase 62)
# --------------------------------------------------------------------------- #


def _study_candidates(db: Session, user_id: int) -> list[dict]:
    """Study-next topics from the Phase 8 recommender (Idea 75)."""
    out: list[dict] = []
    for rec in next_action_service.recommend(db, user_id, limit=5):
        c = _base("study", rec["topic_id"], rec["topic_name"])
        c["weakness"] = 1.0 - rec["reasons"].get("weakness", 0.5)
        c["urgency"] = max(
            rec["reasons"].get("due_reviews", 0.0),
            rec["reasons"].get("exam_proximity", 0.0),
            rec["reasons"].get("concept_gaps", 0.0),
        )
        c["readiness"] = 1.0 if rec.get("ready") else 0.3
        c["reason"] = _study_reason(rec)
        out.append(c)
    return out


def _study_reason(rec: dict) -> str:
    reasons = rec.get("reasons") or {}
    bits = []
    if reasons.get("due_reviews", 0) > 0:
        bits.append("has due reviews")
    if reasons.get("concept_gaps", 0) > 0:
        bits.append("has knowledge gaps")
    if reasons.get("exam_proximity", 0) > 0:
        bits.append("exam is near")
    if reasons.get("weakness", 0) > 0.5:
        bits.append("mastery is low")
    return "because " + (" and ".join(bits) or "it's the highest-scoring topic")


def _revisit_candidates(db: Session, user_id: int) -> list[dict]:
    """Revisit notes: concepts the user has met but not anchored (strength>0)."""
    from app.models import KbConcept

    rows = (
        db.query(UserMemory, KbConcept, KbDocument)
        .join(KbConcept, KbConcept.id == UserMemory.concept_id)
        .join(
            KbEdge,
            (KbEdge.target_concept_id == UserMemory.concept_id)
            & (KbEdge.relation == "MENTIONS")
            & (KbEdge.user_id == user_id),
        )
        .join(KbDocument, KbDocument.id == KbEdge.source_document_id)
        .filter(
            UserMemory.user_id == user_id,
            KbDocument.user_id == user_id,
            UserMemory.strength > 0,
            UserMemory.strength < settings.kb_memory_anchor_min,
        )
        .order_by(UserMemory.strength.asc())
        .all()
    )
    # Dedupe by document — one concept may be mentioned by several notes.
    seen_docs: set[int] = set()
    out: list[dict] = []
    for mem, concept, doc in rows:
        if doc.id in seen_docs:
            continue
        seen_docs.add(doc.id)
        c = _base("revisit", doc.id, doc.title or f"doc {doc.id}")
        c["weakness"] = 1.0 - (mem.strength or 0.0)
        c["urgency"] = 1.0 - (mem.strength or 0.0)
        c["readiness"] = 1.0  # user has met the concept
        c["reason"] = f"because you've seen '{concept.canonical_name}' but haven't anchored it yet"
        out.append(c)
        if len(out) >= 4:
            break
    return out


def _read_candidates(db: Session, user_id: int) -> list[dict]:
    """Read: paper-type documents without a cached summary (fresh material)."""
    from app.models import KbSummary

    summarized = {
        s.document_id
        for s in db.query(KbSummary).filter(KbSummary.user_id == user_id).all()
    }
    docs = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.status != "deleted",
        )
        .order_by(KbDocument.updated_at.desc())
        .limit(20)
        .all()
    )
    out: list[dict] = []
    for doc in docs:
        if doc.id in summarized:
            continue
        c = _base("read", doc.id, doc.title or f"doc {doc.id}")
        c["weakness"] = 0.5
        c["urgency"] = 0.6
        c["readiness"] = 1.0
        c["reason"] = "because it's a new note you haven't summarized yet"
        out.append(c)
    return out[:3]


def _practice_candidates(db: Session, user_id: int) -> list[dict]:
    """Practice: weak topics with approved/pending practice questions."""
    from app.models import PracticeQuestion

    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.status.in_(("pending", "confirmed")))
        .all()
    )
    mastery = mastery_by_topic(db, user_id, [t.id for t in topics])
    due = {d["topic_id"] for d in revision_service.due_reviews(db, user_id, on=date.today())}
    out: list[dict] = []
    for topic in topics:
        m = mastery.get(topic.id, {})
        if m.get("classification") not in ("weak", "unknown"):
            continue
        has_questions = (
            db.query(PracticeQuestion)
            .filter(
                PracticeQuestion.user_id == user_id,
                PracticeQuestion.topic_id == topic.id,
                PracticeQuestion.status == "approved",
            )
            .count()
            > 0
        )
        if not has_questions:
            continue
        c = _base("practice", topic.id, topic.name)
        c["weakness"] = 1.0 - m.get("score", 0.0)
        c["urgency"] = 0.8 if topic.id in due else 0.4
        c["readiness"] = 0.9
        c["reason"] = "because this weak topic has a ready practice set"
        out.append(c)
    return out[:3]


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #


def list_recommendations(db: Session, user_id: int, *, limit: int = 8) -> dict:
    items = candidates(db, user_id, limit=limit)
    return {"items": items, "total": len(items), "weights": settings.kb_recommendation_weights}


def record_feedback(db: Session, user_id: int, item_id: str, action: str) -> dict:
    """Log accept/skip feedback (phrase 66) — feeds Idea 100 tuning."""
    action = (action or "skip").lower()
    if action not in ("accept", "skip"):
        raise ValueError("action must be accept|skip")
    feedback = 1 if action == "accept" else -1
    ai_log_service.log_event(
        db, user_id,
        feature="recommend",
        request=item_id,
        response=action,
        feedback=feedback,
    )
    return {"ok": True, "item_id": item_id, "action": action}


__all__ = ["candidates", "list_recommendations", "record_feedback"]
