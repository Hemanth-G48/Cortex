from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base, migrate_schema
from app.routers import (
    assignments, auth, courses, notes, tasks,
    habits, pomodoro, fitness, journal, quests, projects, life_areas,
    characters, rewards, missions, schedule_events,
    daily_quests, weekly_reset, vault,
    daily_logs, events, life_planner, eisenhower,
    quest_centre, habit_tracker,
    fitness_hub,
)
from app.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_schema()
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)

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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}
