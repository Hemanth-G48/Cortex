# 🎓 Student Life OS — Frontend

React 19 + TypeScript + Vite frontend for the Student Life OS productivity application.

## Setup

```bash
npm install
npm run dev
```

The dev server runs at `http://localhost:5173` and proxies `/api` requests to the backend at `http://localhost:8000`.

## Build

```bash
npm run build     # production build → dist/ (runs tsc -b + vite build)
npx tsc -b        # type-check only
npx vitest run    # unit tests (utils + App smoke)
```

## Project Structure

```
src/
├── components/      # Reusable UI components
│   ├── calendar/    # AcademicCalendar
│   ├── courses/     # CourseCard, CourseCardsRow
│   ├── layout/      # Sidebar, Header, NavLinks
│   ├── lifeplanner/ # DailyLogWidget, MiniCalendar, LifeNavigationGrid, RadarChartWidget, QuickTaskManager, LifeAreasGoals, EisenhowerMatrixWidget
│   ├── pomodoro/    # ProgressRing, SettingsModal
│   ├── resources/   # ResourceCard, AcademicResourcesGrid
│   ├── rpg/         # RpgLayout, QuestCard, MissionCard, RewardCard, …
│   ├── shared/      # Skeleton, EmptyState, ErrorBoundary, Toast (ToastProvider), ThemeSwitcher
│   ├── taskmanager/ # TaskList, MiniTodoList, RemindersList
│   ├── timetable/   # TimetableGrid
│   ├── vault/       # Vault components (see "Vault integration" below)
│   ├── visualization/ # StudentRadarChart
│   └── widgets/     # DigitalClock, ProgressBars, QuickActions, GoalTracker
├── hooks/           # usePomodoro, useFadeIn, ToastContext/useToast
├── pages/           # Route pages (19 original + 7 vault)
├── services/        # Typed API client
├── styles/          # theme.css (dark + vault tokens), pixel-art.css
├── themes/          # rpg-theme.css (retro pixel-art RPG theme)
└── utils/           # formatters, placeholders, vaultFilters, vaultDates, deadline, vaultGrid
```

## Vault integration (Productivity Vault)

The vault adds a data-dense dark dashboard (`#0d0d0d` / `#181818`, per-habit accents
blue/green/orange/red) on top of the existing app. Nothing existing was removed.

### Routes

| Route | Page | Purpose |
|---|---|---|
| `/vault` | VaultDashboard | 4-row dashboard: streak cards, heatmap carousel, tasks w/ tabs, projects + weekly calendar |
| `/vault-database` | VaultDatabase | Live table row counts |
| `/habits/:habitId/report` | HabitReport | Per-habit stats + 30-day streak line graph |
| `/habit-report` | HabitReport | Habit picker for the report |
| `/habits/archive` | ArchiveHabits | Archived habit management |
| `/archive-habits` | ArchiveHabits | Same page (nav alias) |
| `/goals-setting` | GoalsSetting | Goal CRUD incl. habit goals + complete toggle |
| `/habit-logs` | HabitLogs | Full per-habit log history (edit/delete) |
| `/grid-design` | GridDesign | Dashboard grid columns 1/2/3/4 (persisted) |

### Backend endpoints consumed

- `GET /api/vault/summary` — overdue_tasks, completed_today, habits, week streaks
- `GET /api/vault/tasks?tab=today|unrelated|this_week|inbox|completed`
- `GET /api/vault/calendar` — current-week per-day tasks/schedule/deadlines
- `GET /api/vault/database` — users/habits/tasks/projects/goals/logs counts
- `GET /api/habits/{id}/heatmap`, `/stats`, `/logs`, `POST /archive|/unarchive`
- `GET /api/projects/{id}/summary` — total/incomplete tasks, days-to-go
- `POST /api/goals/{id}/complete`, `GET /api/goals?habit_id=`

### Vault components (`src/components/vault/`)

`EditIcon`, `HabitHeatmapCard`, `HabitStatistics`, `HabitStreakCard`,
`HeatmapCarousel`, `HeatmapGrid` (gradient intensity 0–5), `PerformanceWidget`
(streak SVG line chart), `ProjectCard`, `ProjectDetail`, `ProjectModal`,
`QuickActionLink`, `TaskCard`, `TaskCreateModal`, `VaultHeader`, `VaultTabs`
(keyboard-navigable), `WeekGrid`, `WeekProgressStrip`, `WeeklyCalendarRow`.

### Client utilities

- `utils/vaultFilters.ts` — today/unrelated/thisWeek/inbox/completed filters (tested)
- `utils/deadline.ts` — days-to-go + "7 Days to go"/"Completed"/"Overdue" labels (tested)
- `utils/vaultDates.ts` — last N days + log map helpers
- `utils/vaultGrid.ts` — `--vault-cols` localStorage persistence

### Themes

- `styles/theme.css` — base dark theme + `--vault-*` tokens (appended, nothing removed)
- `themes/rpg-theme.css` — scoped under `.theme-rpg`, used by RPG pages (RPGDashboard, Character, Rewards, Missions, Quests)
- `styles/pixel-art.css` — pixel-art utility classes (`.pixel-text`, `.pixel-border-*`, …)

All three are imported from `src/index.css`.

### Vault UX improvements

1. Completed tasks/projects show strikethrough + green button
2. Heatmap slide navigation (scroll-snap carousel with arrows)
3. Heatmap gradient intensity by log count
4. Edit-pencil icons on task/project cards
5. Streak line-graph in the Performance widget

## Life Planner (Life OS)

The Life Planner adds a balanced-life dashboard on `/life-planner`, driven by
`[data-theme='life-planner']` tokens (`#121212` / `#1e1e1e`, magenta `#e8496d`).

### Route

| Route | Page | Purpose |
|---|---|---|
| `/life-planner` | LifePlannerDashboard | Life nav grid + radar, quick task manager, life areas & goals, Eisenhower matrix, daily log + mini calendar sidebar |

### Backend endpoints consumed

- `GET /api/life-planner/summary` — streaks, today's log, due tasks, active habits/goals, life-area progress
- `GET /api/daily-logs`, `POST /api/daily-logs` (upserts per day), `PUT|DELETE /api/daily-logs/{id}`, `GET /api/daily-logs/stats`
- `GET /api/events`, `POST /api/events`, `PUT|DELETE /api/events/{id}`, `GET /api/events/today`
- `GET /api/quick-tasks` — reminders + tasks + today's events sorted by time
- `GET /api/eisenhower/matrix`, `POST /api/eisenhower/tasks/{id}/complete`
- `GET /api/life-areas/{id}/goals`

Tasks carry `priority_quadrant` (Urgent/Important · Important/Not Urgent · Urgent/Not
Important · Not Important/Not Urgent) and ScheduleEvents carry `event_type` + `location`.

### Life Planner components (`src/components/lifeplanner/`)

`DailyLogWidget` (date, week, focused time, streaks, year/month/week bars, Log In
Today), `MiniCalendar` (month nav + today highlight), `LifeNavigationGrid` (2×3
cards), `RadarChartWidget` (5-axis life dimensions), `QuickTaskManager` (Reminders /
Mini To-Do / Today's Events), `LifeAreasGoals` (Areas/Quarterly tabs + circular
progress rings + Mark as achieved), `EisenhowerMatrixWidget` (4 tinted quadrants).

## Quest Centre (Gamified Quest Centre)

The Gamified Quest Centre adds a gold-themed productivity hub on `/quest-centre`,
driven by `[data-theme='quest-centre']` tokens (`#121212` / `#1e1e1e`, gold
`#fbbf24`). It layers a quest-based gamification loop over the existing RPG
module — status window, progress bars, priority folders, pomodoro, life-area
cards, quest/mission/reward centers and a week/month quest calendar.

### Route

| Route | Page | Purpose |
|---|---|---|
| `/quest-centre` | QuestCentreDashboard | Sidebar (status-window + progress + quick actions + priority), Row 1 (pomodoro + life areas), Rows 2–4 (quest/mission/reward centers), quests calendar |

### Backend endpoints consumed

- `GET /api/quest-centre/status-window` — character card, XP-to-next, today-task checklist
- `GET /api/quest-centre/progress` — year / month / week / day progress bars
- `GET /api/quest-centre/priority-window` — High / Medium / Low buckets of open quests + tasks
- `GET /api/quest-centre/quick-actions` — create-target list (quest/mission/life-area/reward)
- `GET /api/quest-centre/life-areas` — areas incl. `target_days`, `status`, `complete_in_days`
- `GET /api/quest-centre/calendar` — quests grouped by due date + weekly schedule events
- `GET /api/quest-centre/gamification?user_id=` — `avatar_class`, `current_streak`, `total_xp`, `current_level`
- `POST /api/life-areas/{id}/complete` — flips status to Completed (progress 100%)
- `GET /api/missions/{id}/linked` — resolves a mission's `linked_quests` CSV to quest rows
- Quest completion (`POST /api/quests/{id}/complete`) also updates the user streak (same-day increment, else reset to 1)

### Quest Centre components (`src/components/questcentre/`)

`StatusWindowWidget` (avatar card + XP bar + streak flame + today checklist),
`ProgressBarsQC`, `QuickActionsQC`, `PriorityWindow` (folder cards with
time estimates + links), `PomodoroWidget` (compact Focus/Short/Long/Stop),
`LifeAreasGridQC` (pixel-art cards with complete/edit actions). The dashboard
reuses the RPG `QuestCenter` / `MissionCenter` / `RewardCenter` and
`WeeklyCalendar` (week ↔ month toggle). All quest/mission/reward/life-area
cards have ✎ Edit pencils that open pre-filled forms, and every mutation fires
a toast. The dashboard fires a "Level Up!" toast when a refresh shows a higher
character level.

### Quest Centre styles

- `styles/quest-centre.css` — scoped `.qc-*` classes (sidebar/main grid, cards,
  XP bar, priority folders, life-area cards, calendar month grid, buttons), with
  `prefers-reduced-motion` support and 1024/768/480 responsive breakpoints
- `[data-theme='quest-centre']` block in `styles/theme.css` — gold token overrides

## Unified Theme System

The app ships eight themes, switched with the emoji switcher in the sidebar
(persisted to `localStorage` under `student-os-theme`):

| Theme | `data-theme` | Accent | Notes |
|---|---|---|---|
| Student OS | *(none)* | `#e8496d` pink | default `:root` tokens |
| RPG | `rpg` | `#ff9800` orange | pixel-art scoped classes still active |
| Vault | `vault` | `#3b82f6` blue | `#0d0d0d` background |
| Life Planner | `life-planner` | `#e8496d` magenta | `#121212` background |
| Quest Centre | `quest-centre` | `#fbbf24` gold | `#121212` background |
| Habit Tracker | `habit-tracker` | `#ffd700` gold | `#0c0c0c` background |
| Fitness Hub | `fitness-hub` | `#3b82f6` blue | `#0f1012` background |
| Cyberpunk | `cyberpunk` | `#00e5ff` cyan | Orbitron/Space Grotesk fonts (`themes/cyberpunk-theme.css`) |

Each `[data-theme='…']` block in `styles/theme.css` overrides only its unique
tokens; shared tokens live at `:root`. The Life Planner page additionally wraps
itself in `data-theme="life-planner"` so it always renders with its own palette.
The Cyberpunk theme's token set and font stacks live in
`themes/cyberpunk-theme.css` (imported from `src/index.css`) — Orbitron for
display headings, Space Grotesk for body text, neon cyan/magenta accents and a
subtle scanline page backdrop.
The switcher lives in `src/components/shared/ThemeSwitcher.tsx`.

## Single-user architecture & ported features (STUDENT-PLANAR)

The application is **single-user and local-only**: there is exactly one owner
(the seeded first user), no login/signup, no passwords, no roles, and no
application-level authorization. The app opens directly into the dashboard.

- Profile is served by `GET/PUT /api/profile` (see `context/ProfileContext.tsx`
  and `hooks/useProfile.ts`) — no tokens, no `Authorization` headers.
- The legacy auth router (`/api/auth/signup|login|me|logout`) and the teacher
  dashboard/broadcast surface have been **removed** from the production app;
  they survive only as a pytest-only shim so the legacy test suite's signup
  helpers keep working (`backend/app/routers/auth_test.py`).
- Google OAuth is kept as an **external integration** (read-only
  Classroom/Gmail/Calendar) — it is not application auth.

Ported STUDENT-PLANAR features that remain fully functional: the reading
tracker, the brain-dump autosave widget, date-specific daily schedule blocks,
assignment type/status/attachments, in-app notifications, and file uploads.

### Reading tracker (`/reading`)

- `GET|POST /api/books`, `PUT|DELETE /api/books/{id}` (category: reading/finished/want)
- `POST /api/books/upload`, `GET /api/books/insights` (total/completion %/per-author)
- `?category=` filter + `?page=&page_size=` pagination
- PDF reader modal + insights tab in the UI

### Brain dump

- `GET|PUT /api/braindumps` — single row per user; `BrainDumpWidget` on the
  Dashboard and Pomodoro auto-saves with a 1s debounce + "Synced" indicator

### Daily schedule (`/schedule` daily view)

- `GET /api/dailyschedule?date=`, `POST`, `PUT|DELETE /{id}`, `POST /{id}/toggle`, `GET /stats?date=`
- Blocks carry category (School/Study Time/Break), energy (High/Medium/Low),
  location and done; server-side overlap validation

### Assignments (enhanced)

- Columns: `type` (Homework/Quiz/Project/Test/Other), `type_color`, `time_estimate`, `file_url`
- `POST /api/assignments/{id}/status`, `POST /api/assignments/{id}/complete`, `POST /api/assignments/{id}/attachment`
- `GET /api/assignments?type=&status=&course_id=`, `GET /api/assignments/analytics`
- UI: Current / By Course / By Type / Completed tabs + status workflow + attachment upload

### Notifications

- `GET /api/notifications`, `GET /unread-count`, `POST /{id}/read`, `POST /mark-all-read`, `DELETE /{id}`, `DELETE` (clear all)
- `NotificationsBell` in the header with unread badge + deep-link navigation

### Uploads

- `POST /api/uploads` (multipart) + static serving from `UPLOAD_DIR`
- Extension allowlist + 10 MB cap + magic-byte sniffing (MIME spoofs rejected)
- `MAX_UPLOAD_MB`, `UPLOAD_DIR`, `APP_SECRET`, `TEACHER_SECRET_KEY` env vars (see `.env.example`)

### Demo data

Seeded on startup: the single owner profile (first `users` row) plus a demo
reading shelf, brain dump, daily-schedule day and assignment types.

## Toasts

All vault and life-planner mutations (create/edit/complete/archive/delete/log-in)
fire success/error toasts. The `ToastProvider` wraps the app in `main.tsx`; use
`useToast()` from `src/hooks/useToast.ts`.

## AI Layer (Shiori-v1 parity)

Every AI feature is server-backed (`backend/app/services/ai_client.py`, an
OpenAI-compatible client) and **always works offline**: when the provider is
unreachable or `AI_ENABLED=false`, the backend returns deterministic fallback
content (`services/ai_fallback.py`) so the UI never breaks.

### Routes

| Route | Page | Purpose |
|---|---|---|
| `/quiz` | Quiz | AI-generated multiple-choice quiz from pasted notes (setup → quiz → results, history in localStorage) |
| `/flashcards` | Flashcards | Deck grid, flip study mode, written-answer AI grading, AI card generation from notes |
| `/study-plans` | StudyPlans | Week-by-week AI study plan generator + saved plans + PDF export |
| `/import` | SyllabusImport | Paste a syllabus → AI-extracted assignments, one-click import |
| `/grades` | Grades | Grade/GPA tracker: credit-weighted GPA, per-course calculations, weighted categories, "needed on final" predictor, trend chart |
| `/analytics` | Analytics | Focus hours, completion rate, GPA, XP, study heatmap + weekly focus bars |
| `/settings` | Settings | Profile, AI model override, Google sync, JSON data export |

### AI endpoints (`/api/ai/*`)

`GET /health`, `GET /models`, `POST /complete`, `POST /quiz`, `POST /flashcards`,
`POST /study-plan`, `POST /syllabus`, `POST /grade-answer`, `POST /chat`.
The chat endpoint is context-aware — it reads your assignments, exams, grades,
plans and XP from the DB to answer study questions.

### AI chat + keyboard shortcuts

- **Ctrl+K** toggles the collapsible **Shiori Assistant** panel (bottom-right).
- **g** + letter navigates (`ga` assignments, `gg` grades, `gp` study plans, …).
- **Ctrl+Shift+A** opens the floating **Quick Capture** assignment form.
- **?** shows the shortcut help modal (`ShortcutModal`).

### Notes editor

`/notes` is now a split-pane editor: list + search + pin on the left, rich
markdown-ish editor (headings, bold, italics, code, lists) with live preview on
the right. Notes carry `pinned` + `updated_at` (pin toggle via `PUT /notes/{id}/pin`).

### Exports & sounds

- `utils/icalExport.ts` — export pending assignments to `.ics` (Assignments page)
- `utils/pdfExport.ts` — jsPDF dark-themed exports (Assignments PDF + Study Plan PDF)
- `utils/sounds.ts` — WebAudio dings wired into the Pomodoro timer

## Google Sync (read-only)

Optional read-only Google integration (`Settings → Google Sync`), server-side in
FastAPI with the token stored in the local DB. Configure via
`GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI`.

| Endpoint | Purpose |
|---|---|
| `GET /api/auth/google` / `/status` / `POST /disconnect` | OAuth connect/status/disconnect |
| `GET /api/classroom/courses` | Classroom courses → merged into local Course table |
| `GET /api/classroom/assignments` | Classroom coursework → merged into local Assignment table |
| `GET /api/gmail/unread`, `/messages` | Unread count + study-related messages |
| `GET /api/calendar/events` | Next-30-day events → merged into local Event table |

All merges are **idempotent** (matched by `google_id`, manual edits preserved).
When Google is not configured/connected the endpoints return deterministic mock
data so the UI is fully demonstrable offline.

## Curriculum & SyllabusAI (SyllabusAI parity)

Port of the SyllabusAI curriculum knowledge platform: a five-level catalog
(Institution → Program → Subject → Unit → Material) with file uploads, text
extraction, AI summaries and AI quizzes. Uses distinct `curriculum_*` tables and
`/api/curriculum` etc. namespaces so nothing collides with the personal `Course`
model or the in-flight `/api/ai` router.

### Routes

| Route | Page | Purpose |
|---|---|---|
| `/browse` | Browse | Public 3-level browse: Institution → Program → Subjects by semester |
| `/subjects/:id` | Subject | Unit cards + multi-unit summary selection |
| `/units/:id` | Unit | Material library, upload, Generate Quiz / Generate Summary |
| `/admin` | Admin | Curator page (owner-only surface): approve institutions, create catalog |
| `/complete-profile` | CompleteProfile | Pick institution + program (enrollment) |

### Backend endpoints consumed

| Endpoint | Purpose |
|---|---|
| `GET /api/curriculum/institutions` (+ `/admin/all`) | Active institutions / all (admin) |
| `GET /api/curriculum/institutions/{id}/programs`, `POST` | Program listing/create under institution |
| `GET /api/curriculum/programs/{id}/subjects`, `POST` | Subject listing/create under program |
| `GET /api/curriculum/subjects/{id}/units`, `POST` | Unit listing/create under subject |
| `GET /api/curriculum/units/{id}/materials` | Paginated, searchable material list |
| `POST /api/curriculum/units/{id}/materials` | Multipart upload (pdf/docx/txt/md, ≤10 MB) |
| `GET /api/materials/{id}`, `/download` | Detail (view count) + download (download count) |
| `POST /api/quizzes` / `POST /api/quizzes/{id}/attempt` | Generate quiz / submit answers (scored, indexed) |
| `GET /api/quizzes/history`, `/analytics` | Last-50 attempts + per-unit stats |
| `POST /api/summaries` | Single/multi-unit AI summary (cached by sorted unit ids) |
| `GET /api/enrollment/summary`, `PUT /api/profile/enrollment` | Enrolled program progress + save enrollment |
| `PATCH /api/curriculum/institutions/{id}/status` | Admin approve/deactivate |

### Gamification & guards (SyllabusAI G13)

- Passing a quiz (≥70%) awards **+25 XP** once per quiz (`xp_awarded` in the
  attempt response; banner shown on the results screen).
- First material upload to a unit awards **+15 XP**; duplicates earn nothing.
- Non-cached AI summary generations are capped at `SUMMARY_DAILY_LIMIT` (default
  10/day, 429 beyond). Cached lookups and the deterministic demo fallback are
  exempt.

### Components & theme

- `src/components/curriculum/` — InstitutionCard, ProgramCard, SubjectCard,
  SemesterGroup, MaterialList/Row/Search, MaterialUpload (drag-drop + optional
  course linking), InstitutionTable, StatusBadge, all create forms.
- `src/components/quiz/Quiz.tsx` — full quiz flow (navigation, radiogroup with
  arrow keys, results with explanations + XP banner).
- `src/themes/curriculum-theme.css` — opt-in scholarly indigo/navy theme
  (`data-theme="curriculum"`), responsive + reduced-motion rules.
