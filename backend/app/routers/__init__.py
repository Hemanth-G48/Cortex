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

__all__ = [
    "assignments", "auth", "characters", "courses", "notes", "tasks",
    "habits", "pomodoro", "fitness", "journal", "quests", "projects", "life_areas",
    "rewards", "missions", "schedule_events",
    "daily_quests", "weekly_reset", "quest_centre", "ai", "grades", "flashcards", "study_plans", "analytics",
    "auth_google", "classroom", "gmail", "calendar", "uploads",
    "curriculum", "materials", "summaries", "quizzes",
    "mood", "sleep",
    "books", "braindumps", "daily_schedule", "notifications", "teacher",
]
