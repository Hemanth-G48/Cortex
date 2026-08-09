from app.routers import assignments, auth, courses, notes, tasks
from app.routers import habits, pomodoro, fitness, journal, quests, projects, life_areas
from app.routers import characters, rewards, missions, schedule_events
from app.routers import daily_quests, weekly_reset
from app.routers import quest_centre
from app.routers import ai
from app.routers import grades
from app.routers import flashcards
from app.routers import study_plans
from app.routers import analytics
from app.routers import auth_google, classroom, gmail, calendar
from app.routers import uploads
from app.routers import curriculum, materials, summaries, quizzes
from app.routers import mood, sleep
from app.routers import books, braindumps, daily_schedule, notifications
from app.routers import teacher
from app.routers import kb_sources, kb_documents, kb_papers, kb_jobs
# Phase 2 (Embeddings, Indexing & Knowledge Graph)
from app.routers import (
    kb_stats,
    kb_metadata,
    kb_tags,
    kb_concepts,
    kb_graph,
    kb_related,
    kb_duplicates,
    kb_reindex,
)
# Phase 3 (Search & Retrieval)
from app.routers import kb_search, kb_health
from app.routers import search as global_search
# Phase 4 (Note Intelligence & Content Generation)
from app.routers import (
    kb_content,
    kb_daily_notes,
    kb_citations,
    kb_edges,
    kb_mindmap,
    kb_quality,
)
# Phase 5 (Subject Management Core, Ideas 41–50)
from app.routers import kb_subjects
# Phase 6 (Study Planning & Execution, Ideas 51–60)
from app.routers import kb_study, kb_labs, kb_attendance
# Phase 9 (Automation, Ideas 81–90)
from app.routers import kb_automation, kb_categorize, kb_links
# Phase 8 (Personalization & Learning Memory, Ideas 71–80)
from app.routers import kb_personal

__all__ = [
    "assignments", "auth", "characters", "courses", "notes", "tasks",
    "habits", "pomodoro", "fitness", "journal", "quests", "projects", "life_areas",
    "rewards", "missions", "schedule_events",
    "daily_quests", "weekly_reset", "quest_centre", "ai", "grades", "flashcards", "study_plans", "analytics",
    "auth_google", "classroom", "gmail", "calendar", "uploads",
    "curriculum", "materials", "summaries", "quizzes",
    "mood", "sleep",
    "books", "braindumps", "daily_schedule", "notifications", "teacher",
    "kb_sources", "kb_documents", "kb_papers", "kb_jobs",
    "kb_stats", "kb_metadata", "kb_tags", "kb_concepts",
    "kb_graph", "kb_related", "kb_duplicates", "kb_reindex",
    "kb_search",
    "kb_health",
    "global_search",
    "kb_content",
    "kb_daily_notes",
    "kb_citations",
    "kb_edges",
    "kb_mindmap",
    "kb_quality",
    "kb_subjects",
    "kb_study",
    "kb_labs",
    "kb_attendance",
    "kb_automation",
    "kb_categorize",
    "kb_links",
    "kb_personal",
]
