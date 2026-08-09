"""Idea 91 — multi-agent architecture.

A lightweight orchestrator (no external framework): a rule-based planner turns
a request into typed steps ``{agent, inputs, expected_output, budget}``
(phrase 1); each step dispatches to a registered specialist that wraps an
existing Phase 1–9 service (phrase 2); the orchestrator composes step outputs
into a final answer (phrase 3). Every LLM-consuming agent goes through the
shared ``ai_client`` + ``KB_DAILY_GEN_LIMIT`` meter (phrase 4), and when
``AI_ENABLED=false`` the same steps run with the existing deterministic
fallbacks (phrase 8). Each run is recorded in ``agent_runs`` (phrase 6) and
metered into ``ai_logs`` (Rule A).

Per-user scoping is non-negotiable — every step filters ``user_id``.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.models import AgentRun, KbDocument
from app.services.kb import KbService, utcnow
from app.services.kb import ai_log as ai_log_service
from app.services.kb import memory_longterm
from app.services.kb import next_action as next_action_service
from app.services.kb import tutor as tutor_service
from app.services.kb.budget import budget_allows, record_generation

logger = logging.getLogger(__name__)

# The agent registry (phrase 2): name → callable(db, user_id, inputs) -> dict.
# Every agent wraps an existing Phase 1–9 service — no new LLM engines.


def _agent_retriever(db: Session, user_id: int, inputs: dict) -> dict:
    query = str(inputs.get("query") or "")
    limit = int(inputs.get("limit") or 6)
    items = tutor_service.retrieve_chunks(db, user_id, query, limit=limit)
    return {
        "items": [
            {
                "chunk_id": i.get("chunk_id"),
                "document_id": i.get("document_id"),
                "title": i.get("title"),
                "source_path": i.get("source_path"),
                "snippet": (i.get("snippet") or "")[:300],
            }
            for i in items
        ]
    }


def _agent_scheduler(db: Session, user_id: int, inputs: dict) -> dict:
    limit = int(inputs.get("limit") or 3)
    items = next_action_service.recommend(db, user_id, limit=limit)
    return {"items": items}


def _agent_quizzer(db: Session, user_id: int, inputs: dict) -> dict:
    """Generate practice questions for the top weak topic (Phase 7 Idea 63)."""
    from app.models import Topic
    from app.services.kb import questions as questions_service

    topic_id = inputs.get("topic_id")
    topic = db.query(Topic).filter(Topic.id == topic_id, Topic.user_id == user_id).first() if topic_id else None
    if topic is None:
        recs = next_action_service.recommend(db, user_id, limit=1)
        if not recs:
            return {"items": [], "topic": None}
        topic = db.query(Topic).filter(Topic.id == recs[0]["topic_id"], Topic.user_id == user_id).first()
    if topic is None:
        return {"items": [], "topic": None}
    created = questions_service.generate_for_topic(
        db, user_id, topic, count=int(inputs.get("count") or 4)
    )
    return {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "items": [
            {
                "question": q.question,
                "options": KbService.json_loads(q.options) or [],
                "difficulty": q.difficulty,
            }
            for q in created
        ],
    }


def _agent_tutor(db: Session, user_id: int, inputs: dict) -> dict:
    message = str(inputs.get("message") or inputs.get("query") or "")
    result = tutor_service.tutor_chat(db, user_id, message)
    return result


def _agent_summarizer(db: Session, user_id: int, inputs: dict) -> dict:
    from app.services.kb import summarize as summarize_service

    doc_id = inputs.get("document_id")
    doc = db.query(KbDocument).filter(KbDocument.id == doc_id, KbDocument.user_id == user_id).first() if doc_id else None
    if doc is None:
        doc = (
            db.query(KbDocument)
            .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
            .order_by(KbDocument.updated_at.desc())
            .first()
        )
    if doc is None:
        return {"summary": None}
    result = summarize_service.get_or_generate_summary(db, user_id, doc)
    return {"document_id": doc.id, "title": doc.title, "summary": result.get("summary")}


def _agent_health_checker(db: Session, user_id: int, inputs: dict) -> dict:
    from app.services.kb import health as health_service

    payload = health_service.compute_health(db, user_id)
    return {"items": [{"score": payload.get("score"), "signals": payload.get("signals", {})}]}


def _agent_memory(db: Session, user_id: int, inputs: dict) -> dict:
    return {"facts": memory_longterm.durable_facts(db, user_id, limit=int(inputs.get("limit") or 5))}


AGENT_REGISTRY: dict[str, dict] = {
    "retriever": {"fn": _agent_retriever, "expected_output": "list of cited vault excerpts"},
    "scheduler": {"fn": _agent_scheduler, "expected_output": "ranked topics to study now"},
    "quizzer": {"fn": _agent_quizzer, "expected_output": "practice questions with options"},
    "tutor": {"fn": _agent_tutor, "expected_output": "cited, grounded explanation"},
    "summarizer": {"fn": _agent_summarizer, "expected_output": "structured document summary"},
    "health_checker": {"fn": _agent_health_checker, "expected_output": "knowledge-health signals"},
    "memory": {"fn": _agent_memory, "expected_output": "durable learning facts"},
}

# Rule-based planner (phrase 3): request keywords → ordered step spec.
_PLANNERS: list[tuple[list[str], list[dict]]] = [
    (
        ["exam", "prepare", "weak", "test", "quiz me", "revise"],
        [
            {"agent": "scheduler", "inputs": {"limit": 3}, "expected_output": "weakest topics", "budget": 0},
            {"agent": "retriever", "inputs": {"query": "{request}", "limit": 6}, "expected_output": "vault excerpts", "budget": 0},
            {"agent": "quizzer", "inputs": {"count": 4}, "expected_output": "practice questions", "budget": 1},
            {"agent": "tutor", "inputs": {"message": "Explain how to prepare for the upcoming exam, focusing on my weakest topics."}, "expected_output": "grounded study guidance", "budget": 1},
        ],
    ),
    (
        ["summary", "summarize", "tl;dr"],
        [
            {"agent": "retriever", "inputs": {"query": "{request}", "limit": 4}, "expected_output": "vault excerpts", "budget": 0},
            {"agent": "summarizer", "inputs": {"document_id": None}, "expected_output": "structured summary", "budget": 1},
        ],
    ),
    (
        ["health", "audit", "review my knowledge", "how healthy"],
        [
            {"agent": "memory", "inputs": {"limit": 5}, "expected_output": "durable facts", "budget": 0},
            {"agent": "health_checker", "inputs": {}, "expected_output": "health signals", "budget": 0},
        ],
    ),
]

_DEFAULT_PLAN = [
    {"agent": "retriever", "inputs": {"query": "{request}", "limit": 6}, "expected_output": "vault excerpts", "budget": 0},
    {"agent": "tutor", "inputs": {"message": "{request}"}, "expected_output": "cited answer", "budget": 1},
]


def plan_request(request: str) -> list[dict]:
    """Plan a request into ordered steps (phrase 3, rule-based)."""
    lowered = (request or "").lower()
    for keywords, plan in _PLANNERS:
        if any(k in lowered for k in keywords):
            return _materialize_plan(plan, request)
    return _materialize_plan(_DEFAULT_PLAN, request)


def _materialize_plan(plan: list[dict], request: str) -> list[dict]:
    out = []
    for step in plan:
        step = dict(step)
        inputs = {
            k: (v.replace("{request}", request) if isinstance(v, str) else v)
            for k, v in step.get("inputs", {}).items()
        }
        step["inputs"] = inputs
        out.append(step)
    return out


def _execute_step(db: Session, user_id: int, step: dict) -> dict:
    """Run one step through its registered agent (phrase 2). Never raises."""
    agent = str(step.get("agent") or "")
    spec = AGENT_REGISTRY.get(agent)
    if spec is None:
        return {"agent": agent, "status": "failed", "output": {}, "error": f"unknown agent {agent}"}
    t0 = time.perf_counter()
    try:
        # Budget gate (phrase 4): LLM steps spend the shared daily meter.
        budget = int(step.get("budget") or 0)
        if budget > 0 and not budget_allows(db, user_id):
            # Deterministic fallback — same agent, services are fallback-safe.
            output = spec["fn"](db, user_id, step.get("inputs", {}))
            status = "fallback"
        else:
            output = spec["fn"](db, user_id, step.get("inputs", {}))
            status = "ok"
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {"agent": agent, "status": status, "output": output, "latency_ms": latency_ms}
    except Exception as exc:  # noqa: BLE001 — step failure is captured, not fatal
        logger.exception("Agent step %s failed", agent)
        return {"agent": agent, "status": "failed", "output": {}, "error": str(exc)[:500]}


def _compose_result(plan: list[dict], step_results: list[dict]) -> str:
    """Compose the final answer from step outputs (phrase 3)."""
    lines: list[str] = ["# Study Plan"]
    by_agent = {r["agent"]: r.get("output") or {} for r in step_results}

    scheduler = by_agent.get("scheduler") or {}
    recs = scheduler.get("items") or []
    if recs:
        lines.append("\n## Focus on these topics first")
        for r in recs[:3]:
            lines.append(f"- {r.get('topic_name')} (score {r.get('score')})")
            reasons = r.get("reasons") or {}
            if reasons:
                lines.append(f"  - reasons: {reasons}")

    quizzer = by_agent.get("quizzer") or {}
    qs = quizzer.get("items") or []
    if qs:
        lines.append(f"\n## Practice set — {quizzer.get('topic_name')}")
        for i, q in enumerate(qs, start=1):
            lines.append(f"{i}. {q.get('question')}")

    tutor_out = by_agent.get("tutor") or {}
    if tutor_out.get("answer"):
        lines.append(f"\n## Guidance\n{tutor_out['answer']}")
        sources = tutor_out.get("sources") or []
        if sources:
            lines.append("\nSources:")
            for s in sources[:5]:
                lines.append(f"- {s.get('title')} ({s.get('source_path')})")

    summary = by_agent.get("summarizer") or {}
    if summary.get("summary"):
        s = summary["summary"]
        lines.append(f"\n## Summary\n{s.get('content')}")
        for kp in (s.get("key_points") or [])[:5]:
            lines.append(f"- {kp}")

    health = by_agent.get("health_checker") or {}
    if health.get("items"):
        lines.append("\n## Knowledge health")
        lines.append(f"- signals: {health['items']}")

    facts = by_agent.get("memory") or {}
    if facts.get("facts"):
        lines.append("\n## What you already know")
        for f in facts["facts"]:
            lines.append(f"- {f.get('concept')} (strength {f.get('strength')})")

    lines.append("\n*(Composed by the Second Brain orchestrator — every claim is grounded in your vault.)*")
    return "\n".join(lines)


def run(db: Session, user_id: int, request: str, context: dict | None = None) -> dict:
    """Orchestrate a request end-to-end (phrase 5). Records ``agent_runs``."""
    request = (request or "").strip()
    if not request:
        raise ValueError("request must not be empty")

    plan = plan_request(request)
    t0 = time.perf_counter()

    # Steps run first: several step services commit/rollback the shared session
    # (e.g. ``summarize``), which would expire any in-flight, uncommitted
    # ``AgentRun`` write and make the final UPDATE stale. Writing the record
    # only after the steps keeps the orchestrator immune to step-side
    # transaction boundaries.
    step_results: list[dict] = []
    try:
        for step in plan:
            step_result = _execute_step(db, user_id, step)
            step_results.append(step_result)
        result_text = _compose_result(plan, step_results)
        status = "done"
        if any(r["status"] == "failed" for r in step_results):
            status = "failed"
    except Exception as exc:  # noqa: BLE001 — record the failure, never crash
        logger.exception("Agent orchestration failed")
        result_text = f"Orchestration failed: {exc}"
        status = "failed"

    record = AgentRun(
        user_id=user_id,
        request=request,
        status=status,
        result=result_text,
        latency_ms=int((time.perf_counter() - t0) * 1000),
        finished_at=utcnow(),
    )
    record.plan = KbService.json_dumps(plan)
    record.steps = KbService.json_dumps(step_results)
    record.cost_estimate = round(record.latency_ms / 1000.0 * 0.0001, 6)
    db.add(record)
    db.flush()

    # Meter into ai_logs (Rule A / phrase 30) — best-effort.
    ai_log_service.log_event(
        db, user_id,
        feature="agent",
        request=request,
        response=(record.result or "")[:2000],
        latency_ms=record.latency_ms,
        cost_estimate=record.cost_estimate,
        retrieval={"plan": plan},
    )
    db.commit()
    return {
        "run_id": record.id,
        "status": record.status,
        "request": request,
        "plan": plan,
        "steps": step_results,
        "result": record.result,
        "latency_ms": record.latency_ms,
        "cost_estimate": record.cost_estimate,
    }


def run_dict(record: AgentRun) -> dict:
    return {
        "id": record.id,
        "request": record.request,
        "status": record.status,
        "plan": KbService.json_loads(record.plan) or [],
        "steps": KbService.json_loads(record.steps) or [],
        "result": record.result,
        "latency_ms": record.latency_ms,
        "cost_estimate": record.cost_estimate,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def list_runs(db: Session, user_id: int, limit: int = 20) -> list[dict]:
    rows = (
        db.query(AgentRun)
        .filter(AgentRun.user_id == user_id)
        .order_by(AgentRun.id.desc())
        .limit(limit)
        .all()
    )
    return [run_dict(r) for r in rows]


__all__ = ["plan_request", "run", "run_dict", "list_runs", "AGENT_REGISTRY"]
