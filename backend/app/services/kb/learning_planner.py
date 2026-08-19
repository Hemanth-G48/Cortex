"""Learning Path Planner service — a personal learning-path architect.

Two strict layers, in this order (SOURCE FIRST → AI SECOND):

**Layer 1 — SOURCE DATA** (``app.services.kb.source_crawler``): the real
structure of the external platform, persisted as ``LearningPath`` /
``LearningResource`` rows. The external website is the source of truth; every
row carries an honest ``crawl_status`` (``discovered | crawled |
extraction_failed | http_error | not_found | auth_required``) and the exact
URLs discovered on the site. **Never modified by AI reasoning.**

**Layer 2 — PERSONALIZED PLAN**: the AI (or the deterministic fallback)
interprets, organises and prioritises *only* the Layer-1 data — it maps
resources to topics, buckets them by the learner's known/unknown knowledge,
orders them into the 5-phase roadmap and emits actionable tasks. Every task
references a real Layer-1 resource; the AI is forbidden from inventing
resources, titles or URLs.

Learning tasks are materialised as ``LearningTask`` rows (with ``resource_id``
/ ``path_id`` back-references) so progress survives reloads and can be rolled
up per learning path.
"""

from __future__ import annotations

import json
import logging
import re

from sqlalchemy.orm import Session

from app.models import (
    KbDocument,
    KbDocumentTag,
    KbTag,
    LearningDependency,
    LearningPath,
    LearningPathResource,
    LearningPlan,
    LearningResource,
    LearningTask,
)
from app.models.kb.learning_path import (
    CRAWL_CRAWLED,
    DEP_SOURCE_AI,
    RESOURCE_TYPE_LAB,
)
from urllib.parse import urlparse
from app.services.ai_client import ai_available, generate_json
from app.services.kb import source_crawler, utcnow

logger = logging.getLogger(__name__)

PHASES = [
    (1, "Phase 1 — Foundations"),
    (2, "Phase 2 — Core Concepts"),
    (3, "Phase 3 — Advanced Topics"),
    (4, "Phase 4 — Practical Labs & Application"),
    (5, "Phase 5 — Completion & Mastery"),
]

MAX_TOPICS = 120
# Upper bound on materialised task rows per plan (SQLite + UI sanity).
MAX_TASKS = 400
MAX_GENERIC_RESOURCES = 20

# Deterministic phase hints (only used when AI is off).
_FOUNDATION_KEYWORDS = ("foundation", "basics", "intro", "fundamental", "prerequisite", "overview", "http", "network")
_CORE_KEYWORDS = ("core", "essential", "authentication", "access control", "injection", "xss", "csrf", "sql", "module")
_ADVANCED_KEYWORDS = ("advanced", "deserialization", "race", "pollution", "cache", "ssrf", "xxe", "exploit")
_PRACTICAL_KEYWORDS = ("lab", "practice", "exercise", "ctf", "challenge", "burp", "workshop")


# ---------------------------------------------------------------------------
# Layer-1 helpers — read the persisted source hierarchy
# ---------------------------------------------------------------------------

def _flatten_sources(db: Session, plan: LearningPlan) -> list[dict]:
    """Flatten the persisted Layer-1 hierarchy into one resource list.

    Each entry carries ``resource_id`` / ``path_id`` so Layer-2 tasks can
    reference the real rows. Resources are ordered by path then position.
    """
    paths = (
        db.query(LearningPath)
        .filter(LearningPath.plan_id == plan.id)
        .order_by(LearningPath.id.asc())
        .all()
    )
    out: list[dict] = []
    for path in paths:
        links = (
            db.query(LearningPathResource)
            .filter(LearningPathResource.path_id == path.id)
            .order_by(LearningPathResource.sort_order.asc())
            .all()
        )
        for link in links:
            res = db.get(LearningResource, link.resource_id)
            if res is None:
                continue
            out.append(
                {
                    "resource_id": res.id,
                    "path_id": path.id,
                    "path_title": path.title,
                    "path_difficulty": path.difficulty,
                    "title": res.title,
                    "url": res.url,
                    "resource_type": res.resource_type,
                    "difficulty": res.difficulty,
                    "section": link.section or res.section,
                    "crawl_status": res.crawl_status,
                }
            )
    return out


def _generic_resources_from_submission(
    db: Session,
    user_id: int,
    plan: LearningPlan,
    resources: list[dict],
    crawled: dict[str, dict],
) -> None:
    """Layer-1 fallback for generic sites: one resource row per submitted URL.

    When discovery finds no learning-path index, the submitted URLs are still
    real sources — persist them as resources under a synthetic path named after
    the platform, with the honest crawl status of the URL fetch.
    """
    for r in resources[:MAX_GENERIC_RESOURCES]:
        url = (r.get("url") or "").strip()
        label = (r.get("label") or "").strip() or url or "Resource"
        host = urlparse(url).netloc if url else ""
        path = LearningPath(
            user_id=user_id,
            plan_id=plan.id,
            platform=host or "Submitted resource",
            title=(label[:300]),
            source_url=(url[:600] or ""),
            crawl_status="discovered",
        )
        db.add(path)
        db.flush()
        rec = crawled.get(url) or {}
        status = rec.get("crawl_status") or "discovered"
        res = LearningResource(
            user_id=user_id,
            plan_id=plan.id,
            title=label[:300],
            url=(url[:600] or None),
            resource_type="course",
            crawl_status=status,
            requested_url=rec.get("requested_url"),
            final_url=rec.get("final_url"),
            status_code=rec.get("status_code"),
            error=rec.get("error"),
            url_key=source_crawler._url_key(url) if url else None,
        )
        db.add(res)
        db.flush()
        db.add(LearningPathResource(path_id=path.id, resource_id=res.id, sort_order=0))
    db.flush()


# ---------------------------------------------------------------------------
# Layer-2 — personalised plan from real sources
# ---------------------------------------------------------------------------

def _source_block(sources: list[dict]) -> str:
    """Render the Layer-1 source list for the AI prompt (ids are referenceable)."""
    lines: list[str] = []
    current_path = None
    for i, s in enumerate(sources, start=1):
        if s["path_id"] != current_path:
            current_path = s["path_id"]
            lines.append(f"\nPATH {current_path}: {s['path_title']} ({s['path_difficulty'] or 'difficulty n/a'})")
        status = s["crawl_status"]
        url_part = f" URL: {s['url']}" if s["url"] else " (URL not exposed publicly)"
        lines.append(
            f"[res {i}] {s['title']} — type: {s['resource_type']}, difficulty: {s['difficulty'] or 'n/a'}, "
            f"crawl: {status}{url_part}"
        )
    return "\n".join(lines)


def _build_ai_prompt(
    goal: str,
    description: str | None,
    sources: list[dict],
    known: list[str],
    unknown: list[str],
    kb_evidence: dict[str, str],
) -> str:
    """One-shot prompt → structured Layer-2 plan JSON.

    The source list is authoritative. The AI organises EXISTING resources into
    topics/phases — it must never invent a resource, title or URL.
    """
    kb_lines = ", ".join(f"{k} ({v})" for k, v in sorted(kb_evidence.items())) or "none"
    return f"""You are a personal learning-path architect. A crawler already extracted the REAL
learning platform structure below (Layer 1 — from the actual website). Your job is ONLY to
organise, personalise and prioritise these existing resources into an actionable roadmap.
NEVER invent resources, titles, topics or URLs that are not in the source list.

LEARNING GOAL: {goal}
{('GOAL DESCRIPTION: ' + description) if description else ''}

LEARNER ALREADY KNOWS: {', '.join(known) or 'nothing declared'}
LEARNER DOESN'T KNOW: {', '.join(unknown) or 'nothing declared'}
SECOND BRAIN EVIDENCE (concept → strength): {kb_lines}

SOURCE STRUCTURE (the only resources that exist — reference them by [res N] id):
{_source_block(sources)}

Return ONLY JSON with this exact shape:
{{
  "overview": "2-3 sentence summary of the roadmap",
  "topics": [
    {{"name": "SSRF", "status": "known|partial|unknown|advanced_unknown",
      "resource_ids": [1, 4], "difficulty": "beginner|intermediate|advanced", "est_time": "2h"}}
  ],
  "dependencies": [
    {{"from": "What is SSRF?", "to": "Circumventing SSRF defenses", "source": "ai"}}
  ],
  "phases": [
    {{"phase": 1, "title": "Foundations", "tasks": [
      {{"title": "Work through: What is SSRF?", "resource_id": 1, "topics": ["SSRF"],
        "description": "why", "difficulty": "beginner", "est_time": "1h"}}
    ]}}
  ]
}}

RULES:
- "resource_id" and "resource_ids" MUST reference ids from the source list ([res N]).
- phase numbers MUST be 1-5 (1 Foundations, 2 Core Concepts, 3 Advanced Topics, 4 Practical Labs, 5 Completion).
- Do not invent new resource names — task titles must reference the real source resources.
- Mark resources matching the learner's knowledge as "known" (review-only).
- "dependencies": only use "source": "platform" when the website itself explicitly states a
  prerequisite. Everything you infer is "source": "ai" (a recommended prerequisite, never official).
- Leave "url" fields out entirely — they come from the source list.
"""


def _phase_hint(label: str, resource_type: str | None, difficulty: str | None) -> int:
    """Deterministic guess of which phase a resource belongs to."""
    if resource_type == RESOURCE_TYPE_LAB:
        return 4
    diff = (difficulty or "").lower()
    if "apprentice" in diff:
        return 1
    if "expert" in diff:
        return 3
    text = _topic_key(label)
    if any(k in text for k in _PRACTICAL_KEYWORDS):
        return 4
    if any(k in text for k in _FOUNDATION_KEYWORDS):
        return 1
    if any(k in text for k in _ADVANCED_KEYWORDS):
        return 3
    if any(k in text for k in _CORE_KEYWORDS):
        return 2
    if "practitioner" in diff:
        return 3
    return 2  # default to core


def _deterministic_plan(
    goal: str,
    description: str | None,
    sources: list[dict],
    known: list[str],
    unknown: list[str],
) -> dict:
    """Keyword-driven Layer-2 plan when AI is unavailable.

    Every task references a real Layer-1 resource (by id); nothing is
    invented. Known-matching resources are labelled review-only.
    """
    known_keys = {_topic_key(k) for k in known}
    unknown_keys = {_topic_key(u) for u in unknown}

    # Order sources by path then position, assign phases.
    phased: dict[int, list[dict]] = {p: [] for p, _ in PHASES}
    topic_rows: list[dict] = []
    seen_topics: set[str] = set()
    for s in sources:
        phase_no = _phase_hint(s["title"], s["resource_type"], s["difficulty"])
        key = _topic_key(s["title"])
        is_known = key in known_keys
        status = "known" if is_known or key in known_keys else "unknown"
        if key in unknown_keys:
            status = "unknown"
        prefix = "Review (known): " if is_known else "Complete: "
        phased[phase_no].append(
            {
                "title": f"{prefix}{s['title']}",
                "resource_id": s["resource_id"],
                "topics": [s["title"][:80]],
                "description": f"Part of learning path: {s['path_title']}.",
                "difficulty": "beginner" if phase_no <= 2 else "intermediate",
                "est_time": "",
            }
        )
        if key and key not in seen_topics:
            seen_topics.add(key)
            topic_rows.append(
                {
                    "name": s["title"],
                    "status": status,
                    "resources": [{"resource_id": s["resource_id"], "title": s["title"]}],
                    "difficulty": "beginner" if phase_no <= 2 else "intermediate",
                    "est_time": "",
                }
            )
            if len(topic_rows) >= MAX_TOPICS:
                break

    phases = []
    for phase_no, phase_title in PHASES:
        phases.append({"phase": phase_no, "title": phase_title, "tasks": phased.get(phase_no, [])})

    # Dependencies: within each path, consecutive resources (AI-inferred).
    deps: list[dict] = []
    by_path: dict[int, list[dict]] = {}
    for s in sources:
        by_path.setdefault(s["path_id"], []).append(s)
    for path_id, res_list in by_path.items():
        for a, b in zip(res_list, res_list[1:]):
            deps.append(
                {
                    "from": a["title"],
                    "to": b["title"],
                    "source": DEP_SOURCE_AI,
                    "from_url": a.get("url"),
                    "to_url": b.get("url"),
                    "note": "Recommended prerequisite (AI-inferred)",
                }
            )
            if len(deps) >= 60:
                break
        if len(deps) >= 60:
            break

    return {
        "overview": (
            f"A structured roadmap to reach: {goal}."
            + (f" {description}" if description else "")
            + f" Built from {len(sources)} resources discovered on the source platform"
            " (deterministic — no AI)."
        ),
        "topics": topic_rows,
        "dependencies": deps,
        "phases": phases,
    }


# ---------------------------------------------------------------------------
# Knowledge adaptation — manual + Second Brain evidence
# ---------------------------------------------------------------------------

def _topic_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _manual_knowledge(known: list[str], unknown: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k in known:
        key = _topic_key(k)
        if key:
            out[key] = "known"
    for u in unknown:
        key = _topic_key(u)
        if key:
            out[key] = "unknown"
    return out


def _kb_evidence_for_goal(db: Session, user_id: int, goal_key: str | None) -> dict[str, str]:
    """Concept → strength from the gap engine (Second Brain evidence)."""
    if not goal_key:
        return {}
    try:
        from app.services.kb import gap_engine

        if not gap_engine.goal_exists(goal_key):
            return {}
        concepts = gap_engine.concepts_for_goal(goal_key) or []
        names = [c.get("name") for c in concepts if isinstance(c, dict) and c.get("name")]
        if not names:
            return {}
        tags = {
            t.name.lower()
            for t in db.query(KbTag)
            .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
            .join(KbDocument, KbDocument.id == KbDocumentTag.document_id)
            .filter(KbDocument.user_id == user_id)
            .all()
        }
        out: dict[str, str] = {}
        for name in names[:60]:
            key = _topic_key(name)
            if not key:
                continue
            out[key] = "strong" if key in tags else "none"
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("kb evidence lookup failed: %s", exc)
        return {}


def _postprocess_topics(topics: list[dict], known_keys: set[str], unknown_keys: set[str]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for t in topics or []:
        name = (t.get("name") or "").strip()
        key = _topic_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        status = t.get("status") or "unknown"
        if key in unknown_keys:
            status = "unknown"
        elif key in known_keys:
            status = "known"
        row = dict(t)
        row["name"] = name
        row["status"] = status
        out.append(row)
        if len(out) >= MAX_TOPICS:
            break
    return out


# ---------------------------------------------------------------------------
# Task + dependency materialisation
# ---------------------------------------------------------------------------

def _materialise_tasks(db: Session, plan: LearningPlan, payload: dict, sources: list[dict]) -> bool:
    """Create LearningTask rows from the Layer-2 payload.

    Every task's ``resource_id``/``path_id`` references the real Layer-1 rows,
    and ``source_crawled`` is only True when the underlying resource was
    actually crawled (honest — never from an AI-generated label).
    Returns True when tasks were truncated at ``MAX_TASKS`` so the UI can say
    so instead of silently omitting.
    """
    by_id = {s["resource_id"]: s for s in sources}
    created = 0
    truncated = False
    for phase in payload.get("phases") or []:
        for sort_order, task in enumerate(phase.get("tasks") or []):
            if created >= MAX_TASKS:
                truncated = True
                break
            rid = task.get("resource_id")
            src = by_id.get(rid) if isinstance(rid, int) else None
            db.add(
                LearningTask(
                    plan_id=plan.id,
                    user_id=plan.user_id,
                    phase=phase["phase"],
                    phase_title=phase["title"],
                    sort_order=sort_order,
                    title=(task.get("title") or "")[:300],
                    description=task.get("description"),
                    resource_title=(src or {}).get("title"),
                    resource_url=(src or {}).get("url"),
                    resource_type=(src or {}).get("resource_type"),
                    difficulty=task.get("difficulty"),
                    est_time=task.get("est_time"),
                    topics_json=json.dumps(task.get("topics") or []),
                    skills_json=json.dumps([]),
                    prerequisites_json=json.dumps([]),
                    resource_id=rid if isinstance(rid, int) else None,
                    path_id=(src or {}).get("path_id"),
                    source_crawled=bool(src and src.get("crawl_status") == CRAWL_CRAWLED),
                    done=False,
                )
            )
            created += 1
        if truncated:
            break
    return truncated


def _materialise_deps(db: Session, plan: LearningPlan, payload: dict) -> None:
    for sort_order, d in enumerate(payload.get("dependencies") or []):
        db.add(
            LearningDependency(
                user_id=plan.user_id,
                plan_id=plan.id,
                from_label=(d.get("from") or "")[:300],
                to_label=(d.get("to") or "")[:300],
                from_url=(d.get("from_url") or "")[:600] or None,
                to_url=(d.get("to_url") or "")[:600] or None,
                source=d.get("source") or DEP_SOURCE_AI,
                note=(d.get("note") or "")[:300] or None,
                sort_order=sort_order,
            )
        )
    db.flush()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _run_layer1(
    db: Session,
    user_id: int,
    plan: LearningPlan,
    resources: list[dict],
) -> tuple[list[dict], dict]:
    """Discover + persist Layer-1 (paths + resources) for the submitted URLs.

    URLs that turn out to be learning-path indexes are crawled for their real
    paths; every other submitted URL is persisted as a generic resource with
    its honest crawl status (nothing is silently omitted). Returns
    ``(sources, report)``; ``report`` is saved into ``source_json``.
    """
    urls = [(r.get("url") or "").strip() for r in resources if (r.get("url") or "").strip()]
    report: dict = {
        "platform": None,
        "source_url": None,
        "paths_discovered": 0,
        "paths_crawled": 0,
        "paths_failed": 0,
        "resources_extracted": 0,
        "resources_with_url": 0,
        "resources_verified": 0,
        "resources_failed": 0,
        "statuses": {},
        "processed_urls": [],
    }
    if urls:
        report = source_crawler.run_discovery(db, user_id, plan, urls)
    # Generic fallback for submitted URLs that discovery did NOT turn into a
    # path index (runs even when another URL did yield paths — nothing dropped).
    processed = set(report.get("processed_urls") or [])
    remaining = [
        r
        for r in resources
        if not processed.intersection({(r.get("url") or "").strip()})
    ]
    if remaining:
        crawled: dict[str, dict] = {}
        for u in urls:
            if u not in processed:
                crawled[u] = source_crawler.fetch_verified(u)
                if crawled[u]["crawl_status"] == CRAWL_CRAWLED:
                    report["resources_verified"] += 1
                    report["statuses"]["crawled"] = report["statuses"].get("crawled", 0) + 1
        _generic_resources_from_submission(db, user_id, plan, remaining, crawled)
        report["resources_extracted"] += min(len(remaining), 20)
        report["resources_with_url"] += sum(
            1 for r in remaining if (r.get("url") or "").strip()
        )
    sources = _flatten_sources(db, plan)
    plan.source_json = json.dumps(report)
    db.flush()
    return sources, report


def _build_layer2(
    db: Session,
    plan: LearningPlan,
    sources: list[dict],
    known: list[str],
    unknown: list[str],
    kb_evidence: dict[str, str],
) -> tuple[dict, str]:
    """Generate the personalised plan (Layer 2) from Layer-1 sources."""
    payload: dict | None = None
    engine = "deterministic"
    if ai_available() and sources:
        prompt = _build_ai_prompt(plan.goal, plan.description, sources, known, unknown, kb_evidence)
        raw = generate_json(prompt, max_tokens=6000, temperature=0.4)
        if isinstance(raw, dict) and raw.get("phases"):
            manual = _manual_knowledge(known, unknown)
            known_keys = {k for k, v in manual.items() if v == "known"}
            unknown_keys = {k for k, v in manual.items() if v == "unknown"}
            raw["topics"] = _postprocess_topics(raw.get("topics"), known_keys, unknown_keys)
            raw["dependencies"] = raw.get("dependencies") or []
            payload = raw
            engine = "ai"
        else:
            logger.warning("AI plan parse failed — falling back to deterministic")
    if payload is None:
        payload = _deterministic_plan(plan.goal, plan.description, sources, known, unknown)

    # Sanity: phases always 1..5 in order.
    phase_by_no = {p["phase"]: p for p in (payload.get("phases") or [])}
    ordered_phases: list[dict] = []
    for phase_no, default_title in PHASES:
        p = phase_by_no.get(phase_no)
        if p is None:
            continue
        ordered_phases.append(
            {"phase": phase_no, "title": (p.get("title") or default_title), "tasks": p.get("tasks") or []}
        )
    payload["phases"] = ordered_phases
    # Topics each resource belongs to — the frontend renders resource topics
    # and prerequisites unconditionally, so these keys must ALWAYS be present
    # (a missing field used to crash the Learning Planner page into a blank
    # screen). Handles both topic shapes: AI ``resource_ids`` and the
    # deterministic ``resources: [{resource_id, ...}]``.
    topic_by_res: dict[int, list[str]] = {}
    for t in payload.get("topics") or []:
        name = (t.get("name") or "").strip()
        if not name:
            continue
        ids = t.get("resource_ids")
        if not isinstance(ids, list):
            ids = [
                r.get("resource_id")
                for r in (t.get("resources") or [])
                if isinstance(r, dict) and r.get("resource_id")
            ]
        for rid in ids:
            if isinstance(rid, int):
                topic_by_res.setdefault(rid, []).append(name)

    payload["resources"] = [
        {
            "id": s["resource_id"],
            "title": s["title"],
            "path": s["path_title"],
            "url": s["url"],
            "type": s["resource_type"],
            "difficulty": s["difficulty"],
            "section": s["section"],
            "crawl_status": s["crawl_status"],
            "topics": topic_by_res.get(s["resource_id"], []),
            "prerequisites": [],
        }
        for s in sources
    ]
    return payload, engine


def _persist_layer2(
    db: Session,
    plan: LearningPlan,
    payload: dict,
    engine: str,
    sources: list[dict],
) -> None:
    """Save Layer-2 payload + materialise tasks and dependencies."""
    truncated = _materialise_tasks(db, plan, payload, sources)
    payload["truncated"] = truncated
    plan.plan_json = json.dumps(payload)
    plan.engine = engine
    plan.status = "generated"
    plan.generated_at = utcnow()
    _materialise_deps(db, plan, payload)
    db.flush()


def discover_plan(
    db: Session,
    user_id: int,
    goal: str,
    resources: list[dict],
    known: list[str],
    unknown: list[str],
    *,
    description: str | None = None,
    goal_key: str | None = None,
) -> LearningPlan:
    """Create a plan and run ONLY Layer-1 discovery (no roadmap yet).

    The plan's status is ``discovered``; call :func:`generate_from_discovery`
    to build the personalised roadmap on top of the discovered structure.
    """
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("Goal is required")
    if not resources:
        raise ValueError("At least one resource is required")
    plan = LearningPlan(
        user_id=user_id,
        goal=goal[:300],
        goal_key=(goal_key or "")[:60] or None,
        description=description,
        resources_json=json.dumps([{"label": r.get("label"), "url": r.get("url")} for r in resources]),
        knowledge_json=json.dumps({"known": known, "unknown": unknown}),
        status="discovered",
    )
    db.add(plan)
    db.flush()
    # Persist the plan row before the long crawl so the write lock is never
    # held across network I/O (watcher scans can otherwise hit
    # "database is locked").
    db.commit()
    _run_layer1(db, user_id, plan, resources)
    db.flush()
    return plan


def generate_from_discovery(
    db: Session,
    user_id: int,
    plan: LearningPlan,
    known: list[str] | None = None,
    unknown: list[str] | None = None,
) -> LearningPlan:
    """Layer 2 on top of the persisted Layer-1 structure (explicit action).

    When the caller passes empty known/unknown lists, the knowledge the user
    declared when the plan was created (``knowledge_json``) is used — so
    building the roadmap later never silently drops it.
    """
    stored = {}
    if plan.knowledge_json:
        try:
            stored = json.loads(plan.knowledge_json) or {}
        except Exception:  # noqa: BLE001
            stored = {}
    known = known if known else (stored.get("known") or [])
    unknown = unknown if unknown else (stored.get("unknown") or [])
    sources = _flatten_sources(db, plan)
    kb_evidence = _kb_evidence_for_goal(db, user_id, plan.goal_key)
    payload, engine = _build_layer2(db, plan, sources, known, unknown, kb_evidence)
    _persist_layer2(db, plan, payload, engine, sources)
    return plan


def generate_plan(
    db: Session,
    user_id: int,
    goal: str,
    resources: list[dict],
    known: list[str],
    unknown: list[str],
    *,
    description: str | None = None,
    goal_key: str | None = None,
) -> LearningPlan:
    """One-shot: Layer-1 discovery + Layer-2 personalised roadmap."""
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("Goal is required")
    if not resources:
        raise ValueError("At least one resource is required")
    plan = LearningPlan(
        user_id=user_id,
        goal=goal[:300],
        goal_key=(goal_key or "")[:60] or None,
        description=description,
        resources_json=json.dumps([{"label": r.get("label"), "url": r.get("url")} for r in resources]),
        knowledge_json=json.dumps({"known": known, "unknown": unknown}),
        status="draft",
    )
    db.add(plan)
    db.flush()
    sources, _report = _run_layer1(db, user_id, plan, resources)
    kb_evidence = _kb_evidence_for_goal(db, user_id, plan.goal_key)
    payload, engine = _build_layer2(db, plan, sources, known, unknown, kb_evidence)
    _persist_layer2(db, plan, payload, engine, sources)
    return plan


# ---------------------------------------------------------------------------
# Plan re-sync — refresh Layer 1 without touching the roadmap
# ---------------------------------------------------------------------------

def resync_plan(
    db: Session,
    user_id: int,
    plan: LearningPlan,
    *,
    cookies: dict | None = None,
) -> dict:
    """Re-crawl the plan's stored source URL(s) and refresh Layer 1 in place.

    Plan Re-sync (explicit user action — never automatic):

    - Re-discovers learning paths from the same submitted source URL(s).
    - Upserts paths by (plan, source_url): new paths are created and crawled,
      existing ones are refreshed (metadata + re-crawled resources).
    - Flags paths the fresh index no longer lists as ``removed`` (honest — the
      row is kept so task references survive, but its crawl status says so).
    - Leaves the personalised roadmap (tasks / dependencies / plan_json)
      untouched: only Layer-1 source data is refreshed.
    - Rewrites ``source_json`` with the updated crawl report.

    Returns the resync report: ``{resynced_at, urls_checked, paths_added,
    paths_refreshed, paths_removed, paths_failed, resources_extracted,
    errors, plan}``.
    """
    from app.models.kb.learning_path import CRAWL_REMOVED
    from app.services.kb import source_crawler

    report: dict = {
        "resynced_at": utcnow().isoformat(),
        "urls_checked": 0,
        "paths_added": [],
        "paths_refreshed": 0,
        "paths_removed": [],
        "paths_failed": 0,
        "resources_extracted": 0,
        "errors": [],
    }

    submitted = _json_list(plan.resources_json) or []
    urls = [
        (r.get("url") or "").strip()
        for r in submitted
        if isinstance(r, dict) and (r.get("url") or "").strip()
    ]
    if not urls:
        raise ValueError("This plan has no stored source URLs to re-crawl")

    seen_urls: set[str] = set()
    for url in urls[:3]:
        report["urls_checked"] += 1
        discovery = source_crawler.discover_learning_paths(url, cookies=cookies)
        if not discovery:
            report["errors"].append(f"Could not re-crawl {url}")
            report["paths_failed"] += 1
            continue
        platform = discovery["platform"]
        fresh_urls: set[str] = set()
        for card in discovery["paths"]:
            path, created = source_crawler.upsert_path_crawl(
                db, user_id, plan, card, platform, cookies=cookies
            )
            src_url = path.source_url or ""
            fresh_urls.add(src_url)
            seen_urls.add(src_url)
            if created:
                report["paths_added"].append(
                    {"id": path.id, "title": path.title, "source_url": src_url}
                )
            else:
                report["paths_refreshed"] += 1
            report["resources_extracted"] += path.resource_count or 0
        # Flag paths that were on the index before but are gone now.
        existing_paths = (
            db.query(LearningPath)
            .filter(LearningPath.plan_id == plan.id, LearningPath.platform == platform)
            .all()
        )
        for p in existing_paths:
            if p.source_url and p.source_url not in fresh_urls:
                if p.crawl_status != CRAWL_REMOVED:
                    p.crawl_status = CRAWL_REMOVED
                    p.error = "No longer listed on the source index (re-synced)"
                    report["paths_removed"].append(
                        {"id": p.id, "title": p.title, "source_url": p.source_url}
                    )

    # Refresh the stored Layer-1 report snapshot.
    if seen_urls:
        payload = source_crawler.build_source_payload(db, plan)
        old_report = {}
        if plan.source_json:
            try:
                old_report = json.loads(plan.source_json)
            except Exception:  # noqa: BLE001
                old_report = {}
        merged = dict(old_report)
        merged["platform"] = payload["report"].get("platform")
        merged["source_url"] = payload["report"].get("source_url")
        merged["paths_discovered"] = len(payload["paths"])
        merged["paths_crawled"] = sum(
            1 for p in payload["paths"] if p["crawl_status"] == CRAWL_CRAWLED
        )
        merged["paths_failed"] = sum(
            1 for p in payload["paths"] if p["crawl_status"] not in (CRAWL_CRAWLED, CRAWL_REMOVED)
        )
        merged["resources_extracted"] = sum(
            len(p.get("resources") or []) for p in payload["paths"]
        )
        plan.source_json = json.dumps(merged)
    db.flush()
    return report


# ---------------------------------------------------------------------------
# Read side — plan payloads
# ---------------------------------------------------------------------------

def _json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:  # noqa: BLE001
        return []


def task_dict(t: LearningTask) -> dict:
    return {
        "id": t.id,
        "phase": t.phase,
        "phase_title": t.phase_title,
        "sort_order": t.sort_order,
        "title": t.title,
        "description": t.description,
        "resource_title": t.resource_title,
        "resource_url": t.resource_url,
        "resource_type": t.resource_type,
        "difficulty": t.difficulty,
        "est_time": t.est_time,
        "topics": _json_list(t.topics_json),
        "skills": _json_list(t.skills_json),
        "prerequisites": _json_list(t.prerequisites_json),
        "resource_id": t.resource_id,
        "path_id": t.path_id,
        "source_crawled": t.source_crawled,
        "done": t.done,
    }


def plan_dict(db: Session, plan: LearningPlan) -> dict:
    """Full plan payload: stored Layer-1 source + Layer-2 plan + live progress."""
    payload = {}
    if plan.plan_json:
        try:
            payload = json.loads(plan.plan_json)
        except Exception:  # noqa: BLE001
            payload = {}
    tasks = (
        db.query(LearningTask)
        .filter(LearningTask.plan_id == plan.id)
        .order_by(LearningTask.phase.asc(), LearningTask.sort_order.asc())
        .all()
    )
    task_rows = [task_dict(t) for t in tasks]
    done = sum(1 for t in tasks if t.done)
    total = len(tasks)

    # Layer-1 source payload + per-path progress from live task states.
    source = source_crawler.build_source_payload(db, plan)
    path_progress: list[dict] = []
    for p in source["paths"]:
        ptasks = [t for t in tasks if t.path_id == p["id"]]
        pdone = sum(1 for t in ptasks if t.done)
        ptotal = len(ptasks)
        path_progress.append(
            {
                "path_id": p["id"],
                "title": p["title"],
                "done_tasks": pdone,
                "total_tasks": ptotal,
                "progress_percent": round((pdone / ptotal) * 100) if ptotal else 0,
            }
        )

    deps_rows = (
        db.query(LearningDependency)
        .filter(LearningDependency.plan_id == plan.id)
        .order_by(LearningDependency.sort_order.asc())
        .all()
    )
    dependencies = (
        [
            {
                "from": d.from_label,
                "to": d.to_label,
                "source": d.source,
                "note": d.note,
                "from_url": d.from_url,
                "to_url": d.to_url,
            }
            for d in deps_rows
        ]
        if deps_rows
        else (payload.get("dependencies") or [])
    )

    # Normalise stored payloads on read: plans generated before resources
    # always carried `topics`/`prerequisites` must still hand the UI complete
    # resource dicts (the roadmap render reads both fields unconditionally).
    resources = [
        {
            **r,
            "topics": r.get("topics") if isinstance(r.get("topics"), list) else [],
            "prerequisites": r.get("prerequisites") if isinstance(r.get("prerequisites"), list) else [],
        }
        for r in (payload.get("resources") or [])
        if isinstance(r, dict)
    ]

    return {
        "id": plan.id,
        "goal": plan.goal,
        "goal_key": plan.goal_key,
        "description": plan.description,
        "status": plan.status,
        "engine": plan.engine,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        "resources": resources,
        "topics": payload.get("topics") or [],
        "dependencies": dependencies,
        "overview": payload.get("overview") or "",
        "phases": payload.get("phases") or [],
        "tasks": task_rows,
        "source": source,
        "path_progress": path_progress,
        "stats": {
            "total_tasks": total,
            "done_tasks": done,
            "progress_percent": round((done / total) * 100) if total else 0,
            "truncated": bool(payload.get("truncated")),
        },
        "next_task": next((t for t in task_rows if not t["done"]), None),
    }


def plan_summary(plan: LearningPlan) -> dict:
    report = {}
    if plan.source_json:
        try:
            report = json.loads(plan.source_json)
        except Exception:  # noqa: BLE001
            report = {}
    return {
        "id": plan.id,
        "goal": plan.goal,
        "goal_key": plan.goal_key,
        "status": plan.status,
        "engine": plan.engine,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        "source": {
            "platform": report.get("platform"),
            "paths_discovered": report.get("paths_discovered", 0),
            "paths_crawled": report.get("paths_crawled", 0),
            "paths_failed": report.get("paths_failed", 0),
            "resources_extracted": report.get("resources_extracted", 0),
            "resources_verified": report.get("resources_verified", 0),
            "resources_failed": report.get("resources_failed", 0),
        },
    }


def toggle_task(db: Session, user_id: int, task_id: int, done: bool) -> LearningTask | None:
    task = db.query(LearningTask).filter(
        LearningTask.id == task_id, LearningTask.user_id == user_id
    ).first()
    if task is None:
        return None
    task.done = bool(done)
    db.flush()
    return task
