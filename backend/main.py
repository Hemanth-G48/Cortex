import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base, migrate_schema
from app.routers import (
    assignments, profile, courses, notes, tasks,
    habits, pomodoro, fitness, journal, quests, projects, life_areas,
    characters, rewards, missions, schedule_events,
    daily_quests, weekly_reset, vault,
    daily_logs, events, life_planner, eisenhower,
    quest_centre, habit_tracker,
    fitness_hub, ai, grades, flashcards, study_plans, analytics,
    auth_google, classroom, gmail, calendar,
    uploads, curriculum, materials, summaries, quizzes,
    mood, sleep,
    books, braindumps, daily_schedule, notifications,
    enrollment,
    kb_sources, kb_documents, kb_papers, kb_jobs,
    kb_stats, kb_metadata, kb_tags, kb_concepts,
    kb_graph, kb_related, kb_duplicates, kb_reindex,
    kb_search, kb_health,
    global_search,
    kb_content, kb_daily_notes, kb_citations, kb_edges, kb_mindmap, kb_quality,
    kb_subjects,
    kb_study, kb_labs, kb_attendance,
    kb_tutor, kb_practice, kb_skills,
    kb_automation, kb_categorize, kb_links,
    kb_personal,
    kb_auto_subjects,
    kb_book_gaps,
    kb_agents, kb_memory, kb_context, kb_research,
    kb_recommendations, kb_reflections, kb_forecast, kb_observability,
    kb_today, kb_triage, kb_backup, kb_weekly_review,
    kb_learning_plans,
    kb_health_audit, kb_focus,
    kb_folders,
    leaderboard,
)
from app.seed import seed_database
from app.seed.student_planar import seed_student_planar


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    # Second Brain (Phase 3, Idea 21): create the FTS5 index + sync triggers
    # idempotently at startup. No-op when KB_FTS_ENABLED=false.
    from app.services.kb import fts

    fts.ensure_fts_schema(engine)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
        # STUDENT-PLANAR demo data (reading shelf, demo teacher/student, daily
        # schedule day, brain dump, assignment taxonomy) — live app only, so
        # test isolation is preserved (tests call seed_database directly).
        seed_student_planar(db)
        # Second Brain (Phase 1): resume jobs interrupted by a restart (Idea 10,
        # phrase 95). Idempotent — safe on every boot; skipped under pytest so
        # tests never touch the app's SQLite file.
        if "pytest" not in sys.modules:
            from app.services.kb import jobs

            jobs.resume_interrupted_jobs()
    finally:
        db.close()
    # Second Brain folder watcher (Idea 3, phrase 29) — never in tests.
    kb_watcher = None
    if settings.KB_WATCH_ENABLED and "pytest" not in sys.modules:
        from app.services.kb import watcher as kb_watcher_module

        kb_watcher_module.start_watcher()
        kb_watcher = kb_watcher_module
    # Warm the local embedding model so the first search/reindex after boot
    # isn't stalled by a lazy load (fastembed/ONNX, ~seconds). Never in tests.
    if "pytest" not in sys.modules:
        try:
            from app.services import embeddings

            if embeddings.fastembed_available():
                embeddings._get_fastembed()
        except Exception:  # noqa: BLE001 — warm-up is best-effort
            pass
    yield
    if kb_watcher is not None:
        kb_watcher.stop_watcher()


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# CORS: allow_origins must be explicit when allow_credentials=True — a
# wildcard origin is rejected by browsers for credentialed requests (Fetch spec).
# The Vite dev proxy serves /api same-origin, so this only matters for direct
# cross-origin access from the dev server (default 5173).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assignments.router)
app.include_router(profile.router)
app.include_router(courses.router)
app.include_router(notes.router)
app.include_router(tasks.router)
app.include_router(habits.router)
app.include_router(pomodoro.router)
app.include_router(fitness.router)
app.include_router(journal.router)
app.include_router(quests.router)
app.include_router(projects.router)
app.include_router(life_areas.router)
app.include_router(characters.router)
app.include_router(rewards.router)
app.include_router(missions.router)
app.include_router(schedule_events.router)
app.include_router(daily_quests.router)
app.include_router(weekly_reset.router)
app.include_router(vault.router)
app.include_router(daily_logs.router)
app.include_router(events.router)
app.include_router(life_planner.router)
app.include_router(eisenhower.router)
app.include_router(quest_centre.router)
app.include_router(habit_tracker.router)
app.include_router(fitness_hub.router)
app.include_router(ai.router)
app.include_router(grades.router)
app.include_router(flashcards.router)
app.include_router(study_plans.router)
app.include_router(analytics.router)
app.include_router(auth_google.router)
app.include_router(classroom.router)
app.include_router(gmail.router)
app.include_router(calendar.router)
app.include_router(uploads.router)
app.include_router(curriculum.router)
app.include_router(materials.router)
app.include_router(summaries.router)
app.include_router(quizzes.router)
app.include_router(mood.router)
app.include_router(sleep.router)
app.include_router(books.router)
app.include_router(braindumps.router)
app.include_router(daily_schedule.router)
app.include_router(notifications.router)
app.include_router(enrollment.router)

# Test-only auth shim: signup/login/me/logout for the legacy test suite.
# Never mounted in production — the application is single-user and tokenless.
if "pytest" in sys.modules:
    from app.routers import auth_test

    app.include_router(auth_test.router)
app.include_router(kb_sources.router)
app.include_router(kb_documents.router)
app.include_router(kb_papers.router)
app.include_router(kb_jobs.router)
app.include_router(kb_stats.router)
app.include_router(kb_metadata.router)
app.include_router(kb_tags.router)
app.include_router(kb_concepts.router)
app.include_router(kb_graph.router)
app.include_router(kb_related.router)
app.include_router(kb_duplicates.router)
app.include_router(kb_reindex.router)
app.include_router(kb_search.router)
app.include_router(kb_health.router)
app.include_router(global_search.router)
app.include_router(kb_content.router)
app.include_router(kb_daily_notes.router)
app.include_router(kb_citations.router)
app.include_router(kb_edges.router)
app.include_router(kb_mindmap.router)
app.include_router(kb_quality.router)
app.include_router(kb_subjects.router)
app.include_router(kb_study.router)
app.include_router(kb_labs.router)
app.include_router(kb_attendance.router)
app.include_router(kb_tutor.router)
app.include_router(kb_practice.router)
app.include_router(kb_skills.router)
app.include_router(kb_automation.router)
app.include_router(kb_categorize.router)
app.include_router(kb_links.router)
app.include_router(kb_personal.router)
app.include_router(kb_auto_subjects.router)
app.include_router(kb_book_gaps.router)
app.include_router(kb_agents.router)
app.include_router(kb_memory.router)
app.include_router(kb_context.router)
app.include_router(kb_research.router)
app.include_router(kb_recommendations.router)
app.include_router(kb_reflections.router)
app.include_router(kb_forecast.router)
app.include_router(kb_observability.router)
app.include_router(kb_today.router)
app.include_router(kb_triage.router)
app.include_router(kb_backup.router)
app.include_router(kb_weekly_review.router)
app.include_router(kb_learning_plans.router)
app.include_router(kb_health_audit.router)
app.include_router(kb_focus.router)
app.include_router(kb_folders.router)
app.include_router(leaderboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}
