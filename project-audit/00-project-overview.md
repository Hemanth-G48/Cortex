# Project Audit: Student Life OS — Full Overview

## Project Identity

**Student Life OS** is a comprehensive single-user web application that combines:
- Academic management (courses, assignments, exams, grades, study plans)
- Life productivity (tasks, habits, journal, fitness, goals)
- RPG gamification (characters, quests, missions, rewards, XP)
- Knowledge management (Second Brain vault integration, knowledge graph, flashcards)
- AI-powered features (tutor, quiz generation, insights, chat)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + TypeScript + Vite |
| Styling | Vanilla CSS (custom properties) |
| State | Local component state (useState/useCallback) |
| Routing | React Router v6 (BrowserRouter) |
| Backend | FastAPI (Python) |
| ORM | SQLAlchemy |
| Database | SQLite (student_os.db) |
| AI | OpenAI-compatible API (OmniRoute) |
| Embeddings | fastembed (local ONNX) |
| KB Engine | Custom Second Brain pipeline (scan → chunk → embed → index → search) |
| Testing | pytest (backend) + vitest (frontend) |

## Architecture Summary

```
React SPA (Vite dev server, port 5173)
  ├── /api/* proxy → FastAPI (port 8000)
  ├── 60+ lazy-loaded page routes
  ├── 15+ custom hooks
  ├── Single ProfileContext for user data
  └── Code-split chunks with error boundaries

FastAPI Backend
  ├── 90+ routers (assignments, courses, kb_*, vault, etc.)
  ├── SQLAlchemy models (40+ tables)
  ├── KB services (100+ modules in services/kb/)
  ├── AI provider registry (multi-model support)
  ├── Folder watcher (Second Brain polling)
  └── Seed data (demo on first boot)
```

## Feature Map

### Primary Modules
1. **Dashboard** — stat grid + widgets (radar chart, calendar, brain dump, AI insights)
2. **Today** — morning/evening review, session start, deadlines
3. **Courses** — KB-derived subjects, document explorer, domain folders, gap analysis
4. **Tasks** — CRUD, priority, project linking
5. **Habits** — good/bad habits, heatmap, streaks, gamified tracker
6. **Vault** — week grid, project cards, task tabs, performance widget
7. **Quests/Missions/Rewards** — RPG gamification layer
8. **Grades** — GPA calculator, grade predictor, trend charts
9. **Flashcards** — FSRS spaced repetition, AI generation, written mode
10. **Knowledge Base** — Second Brain source management, search, graph, tutor
11. **Schedule/Calendar** — timetable grid, events, academic calendar
12. **Analytics** — focus heatmap, weekly bars, grade trends
13. **Settings** — profile, AI providers, Google sync, backup/restore

### Second Brain Integration
- Vault sources (local folder scanning)
- Document indexing (chunking, embedding, FTS5)
- Knowledge graph (sigma.js visualization)
- Auto-subject detection from vault folders
- Course derivation from `course:*` tags
- Search (hybrid: keyword + semantic)
- AI tutor (RAG over vault chunks)

## Seed Data

The application seeds demo data on first boot via `backend/app/seed/__init__.py`:
- 1 user ("Alex", Level 5, Wizard)
- 5 courses, 12 assignments, 5 exams
- 8 tasks, 5 goals, 3 habits + logs
- 5 journal entries, 3 workouts, 2 fitness goals
- 2 quests with subtasks, 1 project with tasks
- 3 life areas, 4 rewards, 2 missions
- 12 schedule events, 5 reminders
- 7 days of habit logs, mood logs, sleep logs
- 2 flashcard decks, grades, study plans
- Fitness hub: 12 muscle groups, exercises, splits, expenses, PRs, diet plans

## Key Observations

1. **Massive codebase**: 60+ frontend pages, 90+ backend routers, 100+ KB service modules
2. **Seed data is realistic**: Generated on first boot, idempotent, append-only
3. **Second Brain is sophisticated**: Full pipeline from scanning to RAG
4. **Dual data model**: Traditional DB (tasks/habits/notes) + KB vault (documents/chunks/embeddings)
5. **Single-user app**: No authentication needed, tokenless by design
6. **Offline-first AI**: Every AI feature falls back to deterministic local generators

## Audit Scope

This audit covers:
- All frontend pages and components
- All backend routers and services
- Database schema and migrations
- Second Brain integration pipeline
- Seed data vs real data concerns
- Workflow completeness
- UI/UX consistency
- Data flow integrity
