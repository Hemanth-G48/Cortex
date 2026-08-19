"""Roadmap → Study Schedule service.

Turns a generated personalised roadmap (``LearningPlan`` + ``LearningTask``
rows) into a day-by-day study plan honouring HOW the learner wants to study.
The user picks one of these modes when they create the plan:

* ``daily_hours``     — pack tasks into days up to N focused hours/day.
* ``modules_per_day`` — pack up to N tasks/modules per day (times still shown).
* ``time_slots``      — pack tasks into fixed daily time slots
                        (e.g. ``07:00-08:00, 20:00-21:00``).
* ``hybrid``          — both an hours budget AND a per-day module cap.
* ``ai_instruction``  — the learner describes their routine in free text
                        (\"1 hour daily at 7am, 2 hours on weekends…\") and the
                        AI assigns tasks to days. Deterministic fallback when
                        AI is unavailable.

Rules that keep it honest and instant:

* **Scheduling is an EXPLICIT user action** — building it calls the AI only
  in ``ai_instruction`` mode. Reading a stored schedule is read-only and
  NEVER calls the LLM (page loads stay instant).
* **Only real roadmap tasks are scheduled** (by ``task_id``) — nothing is
  invented, and completed tasks are skipped (they show up in the stats).
* A ``fingerprint`` of ``(task id, done)`` is stored so the UI can cheaply
  flag the schedule as **stale** when progress changed — without
  regenerating. Regeneration is always manual.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models import LearningPlan, LearningTask
from app.services.ai_client import ai_available, generate_json
from app.services.kb import utcnow

logger = logging.getLogger(__name__)

MODES = ("daily_hours", "modules_per_day", "time_slots", "hybrid", "ai_instruction")

DEFAULT_DAILY_HOURS = 1.0
DEFAULT_MODULES_PER_DAY = 5
# Safety cap: never cram more than this many tasks into a single day (a day
# with 200 tiny review items is not a plan).
MAX_TASKS_PER_DAY = 12
MINUTES_CAP = 12 * 60  # absolute upper bound for one day's budget

# Fallback minutes when the task has no usable est_time, by resource type.
_DEFAULT_MINUTES = {
    "lab": 60,
    "challenge": 45,
    "module": 40,
    "project": 60,
    "course": 30,
    "reading": 30,
}
_FALLBACK_MINUTES = 30


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def parse_est_minutes(est_time: str | None, resource_type: str | None = None) -> int:
    """Parse a task's ``est_time`` string (\"1h\", \"90m\", \"1.5h\", \"2h 30m\")
    into minutes. Falls back to a type-based default when unparseable."""
    text = (est_time or "").strip().lower()
    if text:
        total = 0.0
        for amount, unit in re.findall(r"([\d.]+)\s*(h|hr|hrs|hours|m|min|mins|minutes)", text):
            value = float(amount)
            if unit.startswith("h"):
                total += value * 60
            else:
                total += value
        if total > 0:
            return max(5, int(round(total)))
    return _default_minutes(resource_type)


def _default_minutes(resource_type: str | None) -> int:
    key = (resource_type or "").lower()
    return _DEFAULT_MINUTES.get(key, _FALLBACK_MINUTES)


def _parse_slot(slot: str) -> int | None:
    """Parse \"07:00-08:00\" → minutes of focused time (60). None when invalid."""
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*$", slot or "")
    if not m:
        return None
    start = int(m.group(1)) * 60 + int(m.group(2))
    end = int(m.group(3)) * 60 + int(m.group(4))
    return max(10, end - start) if end > start else None


def _parse_slots(raw: list[str] | None) -> list[str]:
    out: list[str] = []
    for slot in raw or []:
        if _parse_slot(slot) is not None:
            out.append(slot.strip())
        if len(out) >= 6:
            break
    return out


# ---------------------------------------------------------------------------
# Task loading + fingerprinting
# ---------------------------------------------------------------------------


def _ordered_tasks(db: Session, plan: LearningPlan) -> list[LearningTask]:
    return (
        db.query(LearningTask)
        .filter(LearningTask.plan_id == plan.id)
        .order_by(LearningTask.phase.asc(), LearningTask.sort_order.asc(), LearningTask.id.asc())
        .all()
    )


def _fingerprint(tasks: list[LearningTask]) -> str:
    """Hash of (id, done) so any progress change makes the schedule stale."""
    body = "|".join(f"{t.id}:{int(bool(t.done))}" for t in tasks)
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:12]


def _task_minutes(task: LearningTask) -> int:
    return parse_est_minutes(task.est_time, task.resource_type)


# ---------------------------------------------------------------------------
# Deterministic bucketing
# ---------------------------------------------------------------------------


def _day_task_dict(task: LearningTask) -> dict:
    return {
        "task_id": task.id,
        "phase": task.phase,
        "phase_title": task.phase_title,
        "title": task.title,
        "est_time": task.est_time or "",
        "minutes": _task_minutes(task),
        "resource_title": task.resource_title,
        "resource_url": task.resource_url,
        "resource_type": task.resource_type,
        "done": bool(task.done),
    }


def _bucket(
    tasks: list[LearningTask],
    *,
    budget_minutes: int | None = None,
    max_per_day: int | None = None,
) -> list[list[LearningTask]]:
    """Pack ordered tasks into day buckets honouring the constraints."""
    days: list[list[LearningTask]] = []
    current: list[LearningTask] = []
    current_minutes = 0

    def flush() -> None:
        nonlocal current, current_minutes
        if current:
            days.append(current)
        current = []
        current_minutes = 0

    for task in tasks:
        minutes = _task_minutes(task)
        if current:
            over_time = budget_minutes is not None and current_minutes + minutes > budget_minutes
            over_count = max_per_day is not None and len(current) >= max_per_day
            if over_time or over_count:
                flush()
        current.append(task)
        current_minutes += minutes
    flush()
    return days


def _buckets_for_mode(tasks: list[LearningTask], mode: str, params: dict) -> list[list[LearningTask]]:
    if mode == "modules_per_day":
        return _bucket(tasks, max_per_day=params["modules_per_day"])
    if mode == "hybrid":
        return _bucket(
            tasks,
            budget_minutes=params["budget_minutes"],
            max_per_day=params["modules_per_day"],
        )
    # daily_hours + time_slots both pack by time budget.
    return _bucket(tasks, budget_minutes=params["budget_minutes"], max_per_day=MAX_TASKS_PER_DAY)


def _days_payload(buckets: list[list[LearningTask]], slots: list[str]) -> list[dict]:
    start = date.today()
    out: list[dict] = []
    for index, tasks in enumerate(buckets, start=1):
        d = start + timedelta(days=index - 1)
        day_tasks = [_day_task_dict(t) for t in tasks]
        total = sum(t["minutes"] for t in day_tasks)
        out.append(
            {
                "day": index,
                "date": d.isoformat(),
                "label": d.strftime("%a, %b %-d"),
                "total_minutes": total,
                "slots": slots,
                "tasks": day_tasks,
            }
        )
    return out


# ---------------------------------------------------------------------------
# AI instruction mode
# ---------------------------------------------------------------------------


def _ai_days_payload(db: Session, plan: LearningPlan, tasks: list[LearningTask], instruction: str) -> list[dict]:
    """Ask the AI to assign task ids to days from the learner's routine.

    Strict validation: the AI may only reference existing task ids, each task
    is scheduled exactly once, and phase order is preserved (a later-phase
    task never lands on an earlier day than an earlier-phase one). Any
    violation degrades gracefully to the deterministic fallback.
    """
    lines = [
        f"[{t.id}] P{t.phase} {t.phase_title or ''} — {t.title} ({t.est_time or '~30m'})"
        for t in tasks
    ]
    prompt = f"""You are a study-schedule builder. Assign the learner's roadmap tasks to days
based on their stated study routine. Only re-arrange the given tasks — never invent tasks.

LEARNER'S ROUTINE: {instruction}

ROADMAP TASKS (id, phase, title, est time):
{chr(10).join(lines)}

Return ONLY JSON: {{"days": [{{"day": 1, "note": "optional", "task_ids": [1, 2]}}]}}

RULES:
- task_ids must reference ids from the list above.
- Every task must appear in exactly one day.
- Keep phase order: no task may be scheduled on an earlier day than a task from a lower phase.
- Respect the routine's time/module constraints as best you can.
"""
    raw = generate_json(prompt, max_tokens=3000, temperature=0.3)
    days_spec = raw.get("days") if isinstance(raw, dict) else None
    if not isinstance(days_spec, list) or not days_spec:
        raise ValueError("AI schedule did not return usable days")

    allowed = {t.id for t in tasks}
    seen: set[int] = set()
    buckets: list[list[LearningTask]] = []
    bucket_notes: list[str] = []  # index-aligned with ``buckets``
    by_id = {t.id: t for t in tasks}
    for spec in days_spec:
        if not isinstance(spec, dict):
            continue
        ids = spec.get("task_ids")
        if not isinstance(ids, list):
            continue
        bucket: list[LearningTask] = []
        for rid in ids:
            tid = int(rid) if isinstance(rid, int) or (isinstance(rid, str) and rid.isdigit()) else None
            if tid is None or tid not in allowed or tid in seen:
                continue
            seen.add(tid)
            bucket.append(by_id[tid])
        if bucket:
            buckets.append(bucket)
            bucket_notes.append(str(spec.get("note") or "").strip()[:200])

    # Any task the AI dropped lands at the end (never silently lost).
    remaining = [t for t in tasks if t.id not in seen]
    if remaining:
        buckets.append(remaining)
        bucket_notes.append("")

    # Phase-order guard: flatten, sort by phase, then re-chunk preserving the
    # day sizes the AI chose (a later-phase task never lands on an earlier day
    # than an earlier-phase one). Notes ride along on the same day indices.
    flat: list[LearningTask] = []
    for bucket in buckets:
        flat.extend(bucket)
    flat.sort(key=lambda t: (t.phase, t.sort_order, t.id))
    sizes = [len(b) for b in buckets]
    re_chunked: list[list[LearningTask]] = []
    cursor = 0
    for size in sizes:
        re_chunked.append(flat[cursor : cursor + size])
        cursor += size
    buckets = [b for b in re_chunked if b]
    days = _days_payload(buckets, [])
    for day, note in zip(days, bucket_notes):
        if note:
            day["note"] = note
    return days


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_schedule(
    db: Session,
    plan: LearningPlan,
    *,
    mode: str = "daily_hours",
    daily_hours: float | None = None,
    modules_per_day: int | None = None,
    time_slots: list[str] | None = None,
    instruction: str | None = None,
) -> dict:
    """Build (and store) the day-by-day study schedule for a roadmap.

    Explicit user action — never runs automatically. Returns the schedule
    dict; raises ``ValueError`` when the plan has no roadmap tasks.
    """
    if mode not in MODES:
        mode = "daily_hours"

    tasks = _ordered_tasks(db, plan)
    if not tasks:
        # No roadmap at all — a discovered-only plan cannot be scheduled.
        raise ValueError("Build the roadmap first — there are no tasks to schedule yet")
    todo = [t for t in tasks if not t.done]
    if not todo:
        # Nothing left to schedule — still store a valid (empty) schedule so
        # the UI shows the finished state instead of an error.
        schedule = {
            "plan_id": plan.id,
            "goal": plan.goal,
            "mode": mode,
            "params": _params_for(mode, daily_hours, modules_per_day, time_slots, instruction),
            "generated_at": utcnow().isoformat(),
            "engine": "deterministic",
            "fingerprint": _fingerprint(tasks),
            "stale": False,
            "note": "All roadmap tasks are already complete — nothing to schedule.",
            "stats": {
                "days": 0,
                "total_minutes": 0,
                "total_hours": 0,
                "tasks_scheduled": 0,
                "done_tasks": len([t for t in tasks if t.done]),
                "remaining_tasks": 0,
                "estimated_end_date": None,
            },
            "days": [],
        }
        plan.schedule_json = json.dumps(schedule)
        db.flush()
        return schedule

    engine = "deterministic"
    slots: list[str] = []
    params = _params_for(mode, daily_hours, modules_per_day, time_slots, instruction)

    if mode == "ai_instruction" and instruction and ai_available():
        try:
            days = _ai_days_payload(db, plan, todo, instruction)
            engine = "ai"
        except Exception as exc:  # noqa: BLE001 — AI failure → deterministic fallback
            logger.info("AI schedule fallback (deterministic) — %s", exc)
            days = None
        if days:
            schedule = _assemble(db, plan, mode, params, engine, days)
            plan.schedule_json = json.dumps(schedule)
            db.flush()
            return schedule

    # Deterministic bucketing for every mode.
    if mode == "time_slots":
        slots = _parse_slots(time_slots)
        if not slots:
            raise ValueError("Enter at least one valid time slot (e.g. 07:00-08:00)")
        params["time_slots"] = slots
        params["budget_minutes"] = min(MINUTES_CAP, sum(_parse_slot(s) or 0 for s in slots))
    buckets = _buckets_for_mode(todo, mode, params)
    days = _days_payload(buckets, slots)
    schedule = _assemble(db, plan, mode, params, engine, days)
    plan.schedule_json = json.dumps(schedule)
    db.flush()
    return schedule


def _params_for(
    mode: str,
    daily_hours: float | None,
    modules_per_day: int | None,
    time_slots: list[str] | None,
    instruction: str | None,
) -> dict:
    hours = float(daily_hours or DEFAULT_DAILY_HOURS)
    hours = max(0.25, min(12.0, hours))
    modules = int(modules_per_day or DEFAULT_MODULES_PER_DAY)
    modules = max(1, min(30, modules))
    return {
        "daily_hours": round(hours, 2),
        "modules_per_day": modules,
        "budget_minutes": min(MINUTES_CAP, int(round(hours * 60))),
        "time_slots": _parse_slots(time_slots),
        "instruction": (instruction or "").strip()[:2000] or None,
    }


def _assemble(
    db: Session,
    plan: LearningPlan,
    mode: str,
    params: dict,
    engine: str,
    days: list[dict],
) -> dict:
    total_minutes = sum(d["total_minutes"] for d in days)
    tasks_scheduled = sum(len(d["tasks"]) for d in days)
    tasks = _ordered_tasks(db, plan)
    done = sum(1 for t in tasks if t.done)
    return {
        "plan_id": plan.id,
        "goal": plan.goal,
        "mode": mode,
        "params": params,
        "generated_at": utcnow().isoformat(),
        "engine": engine,
        "fingerprint": _fingerprint(tasks),
        "stale": False,
        "note": None,
        "stats": {
            "days": len(days),
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 1),
            "tasks_scheduled": tasks_scheduled,
            "done_tasks": done,
            # Only incomplete tasks are bucketed, so every scheduled task is
            # still to do at build time (done tasks are skipped, not counted).
            "remaining_tasks": tasks_scheduled,
            "estimated_end_date": days[-1]["date"] if days else None,
        },
        "days": days,
    }


def schedule_dict(db: Session, plan: LearningPlan) -> dict | None:
    """Read-only: the stored schedule with live done/stale state.

    Never calls the LLM and never mutates rows — safe on every page load.
    ``done`` flags are re-rolled from the current task rows and ``stale`` is
    recomputed from the fingerprint, so progress made since generation is
    reflected without regenerating.
    """
    if not plan.schedule_json:
        return None
    try:
        schedule = json.loads(plan.schedule_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(schedule, dict):
        return None

    tasks = _ordered_tasks(db, plan)
    done_by_id = {t.id: bool(t.done) for t in tasks}
    for day in schedule.get("days") or []:
        for st in day.get("tasks") or []:
            tid = st.get("task_id")
            st["done"] = bool(done_by_id.get(tid, st.get("done", False)))

    stats = schedule.get("stats") or {}
    days = schedule.get("days") or []
    tasks_scheduled = sum(len(d.get("tasks") or []) for d in days)
    done = sum(1 for t in tasks if t.done)
    # Remaining = scheduled tasks still undone (done tasks from other sources
    # are never subtracted — they were never part of the schedule).
    remaining = sum(1 for d in days for st in d.get("tasks") or [] if not st.get("done"))
    stats["tasks_scheduled"] = tasks_scheduled
    stats["done_tasks"] = done
    stats["remaining_tasks"] = remaining
    schedule["stats"] = stats
    schedule["stale"] = schedule.get("fingerprint") != _fingerprint(tasks)
    return schedule


def clear_schedule(plan: LearningPlan) -> None:
    """Drop the stored schedule (explicit user action)."""
    plan.schedule_json = None
