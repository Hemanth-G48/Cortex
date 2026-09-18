# Architecture Analysis

## Frontend Architecture

### Component Hierarchy
```
App (BrowserRouter)
└── ProfileProvider (ProfileContext)
    └── AppShell
        ├── Sidebar (navigation, theme switcher)
        ├── main (Routes)
        │   ├── Dashboard (stat-grid + widgets)
        │   ├── Today (morning/evening review)
        │   ├── VaultDashboard (week grid + projects + tasks)
        │   ├── Courses → CourseDetail → Subject → SubjectWorkspace → Unit
        │   ├── Tasks, Habits, Journal, Fitness, Schedule
        │   ├── Quests, Missions, Rewards, Character (RPG layer)
        │   ├── Grades, Flashcards, Quiz, StudyPlans
        │   ├── KnowledgeBase, KnowledgeGraph, VaultSearch
        │   ├── Tutor, Practice, Mocks, Interview
        │   └── Settings, Analytics, Admin
        ├── AIChat (floating chat widget)
        ├── CommandPalette (Ctrl+K)
        ├── QuickCapture (Ctrl+Shift+A)
        ├── ShortcutModal (? key)
        └── InstallBanner (PWA install prompt)
```

### State Management Pattern
- **No global state library** — all state lives in component-level `useState`
- **ProfileContext** is the only shared context (user profile, theme)
- **Data fetching** is per-component via `useEffect` + `endpoints.*`
- **No request deduplication** — each page fetches independently
- **No caching layer** — stale data on back-navigation (components remount)
- **Error handling**: `.catch(() => {})` silently swallows most errors

### API Layer
```
frontend/src/services/api.ts (4500+ lines)
├── request() — generic fetch wrapper with error extraction
├── api object — get/post/put/patch/del methods
├── Type interfaces (100+ types)
└── endpoints object — organized by feature module
    ├── endpoints.courses, .tasks, .habits, .notes, .goals
    ├── endpoints.assignments, .exams, .grades, .flashcards
    ├── endpoints.vault (.summary, .tasks, .calendar, .database)
    ├── endpoints.kb (.sources, .documents, .search, .graph, .tutor)
    ├── endpoints.ai (.health, .chat, .complete, .insights)
    ├── endpoints.fitness, .fitnessHub, .journal, .pomodoro
    ├── endpoints.quests, .missions, .rewards, .characters
    └── endpoints.search (.global)
```

## Backend Architecture

### Router Organization (90+ routers)
```
backend/app/routers/
├── Core CRUD: assignments, courses, notes, tasks, habits, goals, etc.
├── RPG: characters, quests, missions, rewards, daily_quests
├── Vault: vault.py (summary/tasks/calendar/database)
├── Analytics: analytics.py (summary/weekly-focus/heatmap)
├── AI: ai.py (health/models/complete/quiz/chat/insights/providers)
├── KB System (50+ routers):
│   ├── kb_sources, kb_documents, kb_papers, kb_jobs
│   ├── kb_search, kb_graph, kb_related, kb_concepts
│   ├── kb_stats, kb_health, kb_quality, kb_tags
│   ├── kb_tutor, kb_practice, kb_skills
│   ├── kb_today, kb_triage, kb_backup, kb_weekly_review
│   ├── kb_learning_plans, kb_folders, kb_health_audit, kb_focus
│   └── ... many more
└── Google: auth_google, classroom, gmail, calendar
```

### Database Schema
```
40+ tables:
├── users, characters
├── courses, assignments, exams, notes, grades, course_weights
├── tasks, habits, habit_logs, goals
├── journal_entries, pomodoro_sessions
├── workouts, fitness_goals, exercises, muscle_groups, etc.
├── quests, quest_tasks, missions, mission_tasks, rewards
├── schedule_events, events, daily_logs
├── flashcard_decks, flashcards, flashcard_schedules
├── study_plans, sleep_logs, mood_logs
├── kb_* (50+ KB tables):
│   ├── kb_sources, kb_documents, kb_chunks, kb_embeddings
│   ├── kb_edges, kb_concepts, kb_tags, kb_summaries
│   ├── kb_revision_schedules, kb_learning_plans
│   └── ... etc.
└── Column migrations defined in database.py (ALTER TABLE statements)
```

### Second Brain Pipeline
```
KB Watcher (polling every 30s)
  → Scanner (find new/changed files)
    → Parser (markdown → structured content)
      → Chunker (1200 char chunks, 150 overlap)
        → Embedder (fastembed ONNX, 384-dim)
          → FTS5 index (keyword search)
          → Vector store (numpy/faiss/pgvector)
          → Knowledge graph (edges, concepts)
          → Concepts extraction
          → Auto-subject detection
          → Auto-course sync (from course:* tags)
```

### AI Provider System
```
Registry (app/data/ai_providers.json)
  ├── Multiple providers (Ollama, OpenAI, etc.)
  ├── Fallback chain (AI_MODELS_FALLBACK)
  ├── Per-feature budgets (summary_daily_limit, embeddings_daily_limit)
  ├── Cache layer (AI_CACHE, 600s TTL)
  └── Deterministic fallbacks when offline
```

## Identified Architectural Issues

1. **api.ts is 4500+ lines** — single file, no code splitting by feature
2. **No React Query/SWR** — every page re-fetches on mount, no dedup/caching
3. **Silent error swallowing** — `.catch(() => {})` throughout frontend
4. **Duplicate data models** — Task in DB has both traditional use AND project linking
5. **Column migration sprawl** — 30+ ALTER TABLE statements in database.py
6. **KB router explosion** — 50+ individual routers for KB features
7. **No request cancellation** — race conditions possible on fast navigation
