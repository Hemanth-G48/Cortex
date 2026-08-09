"""Phase 6 assignment intelligence (Idea 54).

``plan_assignment`` breaks an assignment into subtasks (LLM, budget-capped;
equal-split fallback), creates a Task per subtask spaced backwards from the
deadline, links the assignment to covered topics by name overlap, and fetches
hint chunks from the vault via Phase 3 search.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Assignment, Reminder, Task, Topic
from app.services import ai_client
from app.services.kb import KbService
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.search import KbSearcher
from app.services.prompts import assignment_plan_prompt

FALLBACK_SUBTASK_COUNT = 3


def _llm_subtasks(db: Session, user_id: int, assignment: Assignment) -> list[dict] | None:
    if not (ai_client.ai_available() and budget_allows(db, user_id)):
        return None
    raw = ai_client.generate_json(
        assignment_plan_prompt(assignment.title, assignment.description, assignment.due_date.isoformat()),
        max_tokens=900,
    )
    if not (isinstance(raw, dict) and isinstance(raw.get("subtasks"), list)):
        return None
    out: list[dict] = []
    for s in raw["subtasks"]:
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "").strip()
        if not title:
            continue
        try:
            hours = max(0.5, float(s.get("hours") or 1.0))
        except (TypeError, ValueError):
            hours = 1.0
        out.append({"title": title[:200], "hours": round(hours, 1)})
    if out:
        record_generation(db, user_id, "subtasks")
    return out or None


def _fallback_subtasks(assignment: Assignment) -> list[dict]:
    """Equal-split + volume-based hours (phrase 36)."""
    total_hours = max(1.0, (assignment.time_estimate or 180) / 60.0)
    count = FALLBACK_SUBTASK_COUNT
    per = round(total_hours / count, 1)
    return [
        {"title": f"{assignment.title} — step {i + 1}", "hours": per}
        for i in range(count)
    ]


def _due_dates(assignment: Assignment, subtasks: list[dict]) -> list:
    """Due dates spaced backwards from the deadline (phrase 32).

    The last subtask lands exactly on the deadline; earlier steps spread
    backwards over up to 5 days.
    """
    deadline = assignment.due_date
    n = len(subtasks)
    if n <= 1:
        return [deadline]
    out = []
    for i in range(n):
        frac = (n - 1 - i) / (n - 1)  # 0 → 1 across steps
        days_back = round(frac * 5)
        out.append(deadline - timedelta(days=days_back))
    return out


def _matched_topics(db: Session, user_id: int, assignment: Assignment) -> list[Topic]:
    """Topic overlap: normalized title/description tokens (phrase 34).

    Topics are matched by subject (generated topics carry ``subject_id`` even
    before unit matching assigns ``unit_id``, phrase 34).
    """
    if assignment.course_id is None:
        return []
    topics = (
        db.query(Topic)
        .filter(
            Topic.user_id == user_id,
            Topic.subject_id == assignment.course_id,
            Topic.status.in_(("pending", "confirmed")),
        )
        .all()
    )
    import re

    def _tokens(text: str) -> set[str]:
        return set(re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split())

    hay_tokens = _tokens(f"{assignment.title} {assignment.description or ''}")
    matched = []
    for t in topics:
        name_tokens = _tokens(t.name)
        if name_tokens and name_tokens & hay_tokens:
            matched.append(t)
    return matched


def _hint_chunks(db: Session, user_id: int, query: str, limit: int = 3) -> list[dict]:
    """Top relevant vault chunks as \"hints\" (phrase 35). Degrades to [].

    The search runs inside a savepoint: retrieval internals (query expansion
    budget meters, FTS self-heal DDL, etc.) may commit or roll back the
    connection, and must never wipe the caller's *pending* task inserts.
    """
    try:
        with db.begin_nested():
            searcher = KbSearcher(db, user_id)
            result = searcher.search(query, mode="hybrid", limit=limit)
        items = result.get("items", [])[:limit]
    except Exception:  # noqa: BLE001 — hints must never break planning
        return []
    return [
        {
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "title": item.get("title"),
            "snippet": item.get("snippet"),
            "score": item.get("score"),
        }
        for item in items
    ]


def plan_assignment(
    db: Session,
    user_id: int,
    assignment: Assignment,
    *,
    create_tasks: bool = True,
    create_reminders: bool = True,
) -> dict:
    """Full assignment intelligence pipeline (phrases 31–37)."""
    subtasks = _llm_subtasks(db, user_id, assignment) or _fallback_subtasks(assignment)
    dates = _due_dates(assignment, subtasks)
    topics = _matched_topics(db, user_id, assignment)

    # Fetch hints *before* creating tasks: the search path may run FTS DDL /
    # budget meter writes on the same connection, and SQLite DDL implicitly
    # commits the surrounding transaction — which would silently wipe the
    # caller's *pending* task inserts. Retrieval has no dependency on the new
    # tasks, so run it while the session is still clean.
    hint_query = assignment.title or assignment.description or ""
    hints = _hint_chunks(db, user_id, hint_query) if hint_query else []

    tasks_created: list[int] = []
    reminders_created: list[int] = []
    if create_tasks:
        for s, d in zip(subtasks, dates):
            existing = (
                db.query(Task)
                .filter(Task.user_id == user_id, Task.title == s["title"], Task.due_date == d)
                .first()
            )
            if existing is not None:
                tasks_created.append(existing.id)
                continue
            task = Task(
                user_id=user_id,
                title=s["title"],
                due_date=d,
                status="Not started",
                priority_tag="Medium",
            )
            db.add(task)
            db.flush()
            tasks_created.append(task.id)
            if create_reminders:
                reminder = Reminder(
                    title=f"Due: {s['title']}",
                    date=d,
                )
                db.add(reminder)
                db.flush()
                reminders_created.append(reminder.id)

    db.flush()
    return {
        "assignment_id": assignment.id,
        "subtasks": [
            {**s, "due_date": d.isoformat()}
            for s, d in zip(subtasks, dates)
        ],
        "tasks_created": tasks_created,
        "reminders_created": reminders_created,
        "topic_ids": [t.id for t in topics],
        "hints": hints,
    }
