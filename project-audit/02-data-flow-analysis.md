# Data Flow Analysis

## Critical Data Flows

### 1. Dashboard Data Flow
```
Dashboard.tsx
  useEffect → endpoints.courses.list() → GET /api/courses/
  useEffect → endpoints.tasks.list() → GET /api/tasks
  useEffect → endpoints.assignments.list() → GET /api/assignments
  useEffect → endpoints.exams.list() → GET /api/exams
  useEffect → endpoints.goals.list() → GET /api/goals
  ↓
  5 parallel API calls (no dedup, no loading state for individual items)
  ↓
  Derived stats: pendingTasks, completedAssignments, upcomingExams, avgProgress
  ↓
  stat-grid tiles (static numbers) + widget components
```

**Issues:**
- No loading state — tiles show 0 until data loads
- No error state — if any call fails, that section stays empty
- Courses show raw DB counts (current_assignment/total_assignments) — not from real activity
- Goal progress is simple average, not weighted

### 2. Vault Dashboard Data Flow
```
VaultDashboard.tsx
  load() → Promise.all([
    endpoints.vault.summary(),    // overdue tasks, habit stats
    endpoints.habits.list(),       // all habits
    endpoints.tasks.list(),        // all tasks
    endpoints.projects.list(),     // all projects
    endpoints.vault.calendar(),    // week calendar
  ])
  ↓
  Parallel: heatmap loading per habit, project summaries per project
  ↓
  Tab filtering (client-side) for Today/Unrelated/This Week/Inbox/Completed
```

**Issues:**
- N+1 queries for heatmaps (one per habit)
- N+1 queries for project summaries (one per project)
- Tab filtering runs client-side but also has server fallback — inconsistent

### 3. Second Brain → Course Content Flow
```
CourseDetail.tsx
  endpoints.courses.content(id) → GET /api/courses/:id/content
  ↓
  Backend: course_derivation.py
    → kb_documents WHERE course_id = ?
    → build topic tree from headings
    → folder hierarchy from kb_folders
    → concepts from kb_concepts
    → knowledge graph from kb_graph
  ↓
  CourseContentResponse {
    course, second_brain: { documents, topics, domains, concepts, graph },
    classroom: { linked, assignments }
  }
```

**Issues:**
- Single monolithic endpoint returns everything
- No progressive loading (topics/graph load together)
- Classroom assignments may not be synced

### 4. Knowledge Base Search Flow
```
VaultSearch.tsx
  query → endpoints.kb.search(q, domains)
  ↓
  Backend: kb/search.py
    → FTS5 keyword search (if enabled)
    → Vector similarity search (if enabled)
    → Hybrid RRF fusion (if mode=hybrid)
    → RAG pipeline (rewrite → retrieve → rerank → verify)
  ↓
  SearchResponse { results, total, mode, query }
```

**Issues:**
- No search-as-you-type debounce
- No search history / suggestions
- No loading skeleton during search
- Error state not shown to user

### 5. AI Chat Flow
```
AIChat.tsx (floating widget)
  message → endpoints.ai.chat({ message })
  ↓
  Backend: ai.py → ai_client.py
    → Provider registry lookup
    → System prompt + chat history
    → KB context injection (RAG if enabled)
    → LLM completion
    → Response
  ↓
  Chat bubble rendering
```

**Issues:**
- No streaming response
- No conversation persistence
- No rate limiting on frontend

### 6. Task CRUD Flow (Vault)
```
TaskCreateModal → endpoints.tasks.create(d)
  ↓
  Backend: tasks.py → INSERT INTO tasks
  ↓
  refreshTasks() → endpoints.tasks.list() → re-fetch all
  ↓
  Tab re-filtering
```

**Issues:**
- Full re-fetch after create (not optimistic update)
- No undo capability
- Task create doesn't validate required fields

### 7. Habit Log Flow
```
HabitTracker.tsx → handleLog(habitId) → endpoints.habits.logToday(habitId)
  ↓
  Backend: habit_tracker.py → INSERT INTO habit_logs
    → UPDATE habits SET current_streak = ...
  ↓
  load() → endpoints.habits.list() → re-fetch all
```

**Issues:**
- No optimistic UI update
- No check for duplicate logging (same day)
- No debouncing rapid clicks

### 8. Flashcard Review Flow
```
Flashcards.tsx → handleGrade(grade)
  → endpoints.flashcards.review(deckId, cardId, grade)
  ↓
  Backend: flashcard_srs.py
    → FSRS algorithm → new schedule
    → UPDATE flashcards SET ...
    → INSERT INTO flashcard_schedules
  ↓
  next card, refresh deck
```

**Issues:**
- Refreshes entire deck list after grading one card
- XP earned not persisted to user profile
- No review statistics aggregation

## Data Consistency Map

| Data | Source | Frontend Cache | Refresh Strategy |
|------|--------|---------------|-----------------|
| Courses | DB + KB derivation | Per-page mount | Manual refresh |
| Tasks | DB | Per-page mount | Full re-fetch |
| Habits | DB | Per-page mount | Full re-fetch |
| Notes (traditional) | DB | Per-page mount | Full re-fetch |
| KB Documents | SQLite FTS5 + vectors | Per-page mount | Source scan |
| Search results | KB search engine | None | Per query |
| User profile | DB | ProfileContext | On mount |
| Analytics | DB aggregation | Per-page mount | Full re-fetch |
| AI insights | AI provider + cache | Per mount | On demand |

## Missing Data Flows

1. **No real-time updates** — no WebSocket/SSE for live data
2. **No cross-page sync** — completing a task on Dashboard doesn't update Tasks page
3. **No background refresh** — stale data persists until page reload
4. **No optimistic updates** — all mutations wait for server response
5. **No offline support** — Service Worker registered but not functional
