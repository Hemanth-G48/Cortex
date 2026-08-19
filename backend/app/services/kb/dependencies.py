"""Phase 5 topic dependency DAG (Idea 46, phrases 51–60).

``kb_edges`` requires a document source, so topic→topic prerequisites use the
dedicated ``topic_dependencies`` table. The DAG is seeded by an LLM pass
(budget-capped, ``ai`` provenance) with a syllabus-order fallback (``rule``),
is cycle-checked on every insert (phrase 55), manually editable, and exposes a
Kahn topological order for the roadmap engine (phrase 60).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Topic, TopicDependency
from app.services import ai_client, ai_fallback
from app.services.kb.budget import budget_allows, record_generation
from app.services.prompts import topic_deps_prompt


class DependencyCycleError(ValueError):
    """Raised when an edge would create a cycle (phrase 55)."""


def seed_dependencies(db: Session, user_id: int, subject_id: int, units: list[dict]) -> int:
    """Seed the topic DAG from parsed units (phrase 52).

    Returns the number of edges created. LLM pass first (budget-capped),
    syllabus-order fallback otherwise. Idempotent per (user, prereq, postreq).
    """
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == subject_id)
        .all()
    )
    name_to_topic = {t.normalized_name: t for t in topics}
    # also allow matching on the raw display name
    for t in topics:
        name_to_topic.setdefault(t.name.lower(), t)

    def _resolve(name: str) -> Topic | None:
        return name_to_topic.get(str(name).strip().lower())

    pairs: list[tuple[str, str]] = []

    if ai_client.ai_available() and budget_allows(db, user_id):
        parsed = ai_client.generate_json(topic_deps_prompt(units), max_tokens=2000)
        if isinstance(parsed, dict) and isinstance(parsed.get("dependencies"), list):
            for dep in parsed["dependencies"]:
                if not isinstance(dep, dict):
                    continue
                a = _resolve(dep.get("topic_a") or "")
                for b in dep.get("depends_on") or []:
                    prereq = _resolve(b)
                    if a is not None and prereq is not None and a.id != prereq.id:
                        pairs.append((a.id, prereq.id))
            record_generation(db, user_id, "dependencies")
    if not pairs:
        for dep in ai_fallback.demo_topic_deps(units):
            a = _resolve(dep.get("topic_a") or "")
            prereq = _resolve((dep.get("depends_on") or [None])[0] or "")
            if a is not None and prereq is not None and a.id != prereq.id:
                pairs.append((a.id, prereq.id))

    created = 0
    for postreq_id, prereq_id in pairs:
        existing = (
            db.query(TopicDependency)
            .filter(
                TopicDependency.user_id == user_id,
                TopicDependency.prereq_topic_id == prereq_id,
                TopicDependency.postreq_topic_id == postreq_id,
            )
            .first()
        )
        if existing:
            continue
        try:
            add_dependency(
                db, user_id, subject_id, prereq_id, postreq_id,
                provenance="ai",
            )
            created += 1
        except DependencyCycleError:
            continue
    db.flush()
    return created


def add_dependency(
    db: Session, user_id: int, subject_id: int,
    prereq_topic_id: int, postreq_topic_id: int,
    *,
    provenance: str = "manual",
    weight: float = 1.0,
) -> TopicDependency:
    """Insert a ``prereq → postreq`` edge, rejecting self/cycles (phrase 55)."""
    if prereq_topic_id == postreq_topic_id:
        raise DependencyCycleError("A topic cannot depend on itself")
    for tid in (prereq_topic_id, postreq_topic_id):
        topic = db.get(Topic, tid)
        if topic is None or topic.user_id != user_id or topic.subject_id != subject_id:
            raise ValueError("Topic not found or not in this subject")

    existing = (
        db.query(TopicDependency)
        .filter(
            TopicDependency.user_id == user_id,
            TopicDependency.prereq_topic_id == prereq_topic_id,
            TopicDependency.postreq_topic_id == postreq_topic_id,
        )
        .first()
    )
    if existing:
        return existing

    # A cycle exists iff there is already a path postreq → prereq.
    if _reachable(db, user_id, subject_id, postreq_topic_id, prereq_topic_id):
        raise DependencyCycleError("This dependency would create a cycle")

    dep = TopicDependency(
        user_id=user_id,
        subject_id=subject_id,
        prereq_topic_id=prereq_topic_id,
        postreq_topic_id=postreq_topic_id,
        weight=weight,
        provenance=provenance,
    )
    db.add(dep)
    db.flush()
    return dep


def remove_dependency(db: Session, user_id: int, dep_id: int) -> None:
    dep = db.get(TopicDependency, dep_id)
    if dep is None or dep.user_id != user_id:
        raise ValueError("Dependency not found")
    db.delete(dep)
    db.flush()


def list_dependencies(db: Session, user_id: int, subject_id: int) -> list[TopicDependency]:
    return (
        db.query(TopicDependency)
        .filter(TopicDependency.user_id == user_id, TopicDependency.subject_id == subject_id)
        .order_by(TopicDependency.id.asc())
        .all()
    )


def _reachable(
    db: Session, user_id: int, subject_id: int, start_topic_id: int, goal_topic_id: int
) -> bool:
    """DFS — is ``goal`` reachable from ``start`` following prereq→postreq?"""
    edges: dict[int, list[int]] = {}
    for dep in list_dependencies(db, user_id, subject_id):
        edges.setdefault(dep.prereq_topic_id, []).append(dep.postreq_topic_id)
    stack = [start_topic_id]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if node == goal_topic_id:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(edges.get(node, []))
    return False


def topological_order(db: Session, user_id: int, subject_id: int, topic_ids: list[int]) -> list[int]:
    """Kahn's algorithm over the subject DAG restricted to ``topic_ids``
    (phrase 60). Topics with no edges keep their input order. Raises
    ``DependencyCycleError`` if the stored graph has a cycle."""
    topic_set = set(topic_ids)
    prereqs: dict[int, set[int]] = {t: set() for t in topic_ids}
    postreqs: dict[int, list[int]] = {t: [] for t in topic_ids}
    for dep in list_dependencies(db, user_id, subject_id):
        p, q = dep.prereq_topic_id, dep.postreq_topic_id
        if p in topic_set and q in topic_set and p != q:
            prereqs[q].add(p)
            postreqs[p].append(q)
    ready = [t for t in topic_ids if not prereqs[t]]
    order: list[int] = []
    remaining = set(topic_ids)
    while ready:
        node = ready.pop(0)
        order.append(node)
        remaining.discard(node)
        for nxt in postreqs[node]:
            if nxt not in remaining:
                continue
            prereqs[nxt].discard(node)
            if not prereqs[nxt]:
                ready.append(nxt)
    if remaining:
        raise DependencyCycleError("The topic graph contains a cycle")
    return order


def graph_payload(db: Session, user_id: int, subject_id: int) -> dict:
    """``{topics: [...], edges: [...]}`` for the UI + roadmap engine."""
    topics = (
        db.query(Topic)
        .filter(Topic.user_id == user_id, Topic.subject_id == subject_id)
        .all()
    )
    deps = list_dependencies(db, user_id, subject_id)
    return {
        "subject_id": subject_id,
        "topics": [
            {
                "id": t.id,
                "name": t.name,
                "normalized_name": t.normalized_name,
                "status": t.status,
                "unit_id": t.unit_id,
            }
            for t in topics
        ],
        "edges": [
            {
                "id": d.id,
                "prereq_topic_id": d.prereq_topic_id,
                "postreq_topic_id": d.postreq_topic_id,
                "weight": d.weight,
                "provenance": d.provenance,
            }
            for d in deps
        ],
    }
