"""Router package — lazy imports (audit F2).

Routers are NOT imported eagerly at package load. Each heavy router (OAuth,
Google API clients, AI features) pulls in its own dependency tree, and
importing all of them here would make every ``from app.routers import X``
statement load the whole app.

Instead, modules are loaded on first attribute access via ``__getattr__``
(PEP 562), so ``app.routers.gmail`` only imports the Gmail router when
``gmail`` is actually touched. ``main.py`` imports the routers it mounts
directly from their submodules — this registry exists for the ``__all__``
contract and any code that does ``from app.routers import <name>``.
"""

from __future__ import annotations

# Single source of truth for router module names. Keep in sync with the
# ``app.include_router(<name>.router)`` calls in ``backend/main.py``.
_ROUTER_MODULES = [
    # Core productivity
    "assignments", "profile", "courses", "notes", "tasks",
    "habits", "pomodoro", "fitness", "journal", "quests", "projects",
    "life_areas", "characters", "rewards", "missions", "schedule_events",
    "daily_quests", "weekly_reset", "quest_centre", "habit_tracker",
    "fitness_hub", "ai", "grades", "flashcards", "study_plans", "analytics",
    # Auth + integrations
    "auth", "auth_google", "classroom", "gmail", "calendar", "uploads",
    # SyllabusAI
    "curriculum", "materials", "summaries", "quizzes",
    # Wellness
    "mood", "sleep",
    # Vault + planner
    "books", "braindumps", "daily_schedule", "notifications", "enrollment",
    "vault", "daily_logs", "events", "life_planner", "eisenhower",
    # Knowledge Base — Phase 1 (sources, documents, jobs)
    "kb_sources", "kb_documents", "kb_papers", "kb_jobs",
    # Phase 2 (Embeddings, Indexing & Knowledge Graph)
    "kb_stats", "kb_metadata", "kb_tags", "kb_concepts",
    "kb_graph", "kb_related", "kb_duplicates", "kb_reindex",
    # Phase 3 (Search & Retrieval)
    "kb_search", "kb_health", "search",
    # Phase 4 (Note Intelligence & Content Generation)
    "kb_content", "kb_daily_notes", "kb_citations", "kb_edges",
    "kb_mindmap", "kb_quality",
    # Phase 5 (Subject Management Core, Ideas 41–50)
    "kb_subjects",
    # Phase 6 (Study Planning & Execution, Ideas 51–60)
    "kb_study", "kb_labs", "kb_attendance",
    # Phase 7 (AI Tutor & Practice, Ideas 61–70)
    "kb_tutor", "kb_practice", "kb_skills",
    # Phase 8 (Personalization & Learning Memory, Ideas 71–80)
    "kb_personal", "kb_memory", "kb_context", "kb_research",
    "kb_recommendations", "kb_reflections", "kb_forecast", "kb_observability",
    "kb_agents",
    # Phase 9 (Automation, Ideas 81–90)
    "kb_automation", "kb_categorize", "kb_links",
    # Knowledge Capture XP (defect #79 fix)
    "kb_capture_xp",
    # Vault mastery read model (defects #40, #71, #76, #82, #96)
    "kb_mastery",
    # Auto subject detection for course derivation
    "kb_auto_subjects",
    # Book Knowledge Gap Analyzer (KB books)
    "kb_book_gaps",
    # Workflow glue: Today command center, new-note triage, vault backup,
    # weekly review ritual, learning path planner.
    "kb_today", "kb_triage", "kb_backup", "kb_weekly_review",
    "kb_learning_plans",
    # Vault health audit + focus sessions
    "kb_health_audit", "kb_focus",
    # Folder-hierarchy-as-source-of-truth: canonical domains + domain gaps
    "kb_folders",
    # Flat vault-domain list for non-study surfaces (defect #83)
    "kb_domains",
    # Gamified leaderboard
    "leaderboard",
]

__all__ = list(_ROUTER_MODULES) + ["global_search"]

# Import aliases: attribute name → actual module name (suffix of
# ``app.routers.<module>``). ``main.py`` imports the global search router as
# ``global_search``; keep any future aliases here.
_ALIASES = {
    "global_search": "search",
}


def __getattr__(name: str):
    """Import a router module on first access (PEP 562 lazy import).

    Raises ``AttributeError`` (not ``ImportError``) for unknown names so
    ``from app.routers import *`` and hasattr checks behave correctly.
    """
    if name in _ALIASES:
        module_name = _ALIASES[name]
    elif name in _ROUTER_MODULES:
        module_name = name
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    module = importlib.import_module(f"app.routers.{module_name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + _ROUTER_MODULES)
