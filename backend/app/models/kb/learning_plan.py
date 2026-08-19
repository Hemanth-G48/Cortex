"""Learning Path Planner models (workflow glue — personal learning-path architect).

``LearningPlan`` stores the goal, the submitted resources, the user's declared
known/unknown knowledge, and the full generated plan payload (goal mapping,
deduplicated resources, dependency graph, 5-phase roadmap). ``LearningTask``
rows give each roadmap task persistent progress (checkbox state).

The plan payload is versioned in ``plan_json`` (same save-and-reuse pattern as
``Roadmap``); tasks are real rows so progress survives reloads.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    goal = Column(String(300), nullable=False)
    # Optional link to the gap-engine goal catalog (e.g. "cybersecurity").
    goal_key = Column(String(60), nullable=True, index=True)
    description = Column(Text, nullable=True)
    # JSON: [{label, url, crawled(bool)}] — exactly what the user submitted.
    resources_json = Column(Text, nullable=True)
    # JSON: declared knowledge — {"known": [...], "unknown": [...]}.
    knowledge_json = Column(Text, nullable=True)
    # Full generated payload (goal overview, resources, topics, dependencies,
    # phases, next task, stats). Absent while status == "draft".
    plan_json = Column(Text, nullable=True)
    # Layer-1 snapshot: the real platform hierarchy discovered by the crawler
    # (platform, learning paths, resources, crawl report). Never modified by
    # AI reasoning — the source of truth for what exists on the site.
    source_json = Column(Text, nullable=True)
    # draft | generated | failed
    status = Column(String(20), default="draft", index=True)
    # Which engine produced the plan: "ai" (assisted) | "deterministic".
    engine = Column(String(20), default="deterministic")
    # Stored day-by-day study schedule (roadmap → schedule service). Absent
    # until the user explicitly builds one; reading it never calls the LLM.
    schedule_json = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    generated_at = Column(DateTime, nullable=True)


class LearningTask(Base):
    __tablename__ = "learning_tasks"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    phase = Column(Integer, default=1)
    phase_title = Column(String(120), nullable=True)
    sort_order = Column(Integer, default=0)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    # Resource metadata snapshot (denormalised from the plan payload).
    resource_title = Column(String(300), nullable=True)
    resource_url = Column(String(600), nullable=True)
    resource_type = Column(String(30), nullable=True)  # course | module | lab | challenge | project
    difficulty = Column(String(30), nullable=True)
    est_time = Column(String(60), nullable=True)
    # JSON arrays: topics, skills, prerequisites.
    topics_json = Column(Text, nullable=True)
    skills_json = Column(Text, nullable=True)
    prerequisites_json = Column(Text, nullable=True)
    # Whether this task's content was verified from a crawled page.
    source_crawled = Column(Boolean, default=False)
    # Reference back to the Layer-1 source entity this task points at
    # (nullable — legacy tasks and generic review tasks have none).
    resource_id = Column(Integer, ForeignKey("learning_resources.id"), nullable=True, index=True)
    path_id = Column(Integer, ForeignKey("learning_paths.id"), nullable=True, index=True)
    done = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
