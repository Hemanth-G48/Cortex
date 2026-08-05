import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base, migrate_schema
from app.routers import (
    assignments, auth, courses, notes, tasks,
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
    teacher, enrollment,
)
from app.seed import seed_database
from app.seed.student_planar import seed_student_planar


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
        # STUDENT-PLANAR demo data (reading shelf, demo teacher/student, daily
        # schedule day, brain dump, assignment taxonomy) — live app only, so
        # test isolation is preserved (tests call seed_database directly).
        seed_student_planar(db)
    finally:
        db.close()
    yield


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
app.include_router(auth.router)
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
app.include_router(teacher.router)
app.include_router(enrollment.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}
