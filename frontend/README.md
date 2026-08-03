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

The app ships five themes, switched with the emoji switcher in the sidebar
(persisted to `localStorage` under `student-os-theme`):

| Theme | `data-theme` | Accent | Notes |
|---|---|---|---|
| Student OS | *(none)* | `#e8496d` pink | default `:root` tokens |
| RPG | `rpg` | `#ff9800` orange | pixel-art scoped classes still active |
| Vault | `vault` | `#3b82f6` blue | `#0d0d0d` background |
| Life Planner | `life-planner` | `#e8496d` magenta | `#121212` background |
| Quest Centre | `quest-centre` | `#fbbf24` gold | `#121212` background |

Each `[data-theme='…']` block in `styles/theme.css` overrides only its unique
tokens; shared tokens live at `:root`. The Life Planner page additionally wraps
itself in `data-theme="life-planner"` so it always renders with its own palette.
The switcher lives in `src/components/shared/ThemeSwitcher.tsx`.

## Toasts

All vault and life-planner mutations (create/edit/complete/archive/delete/log-in)
fire success/error toasts. The `ToastProvider` wraps the app in `main.tsx`; use
`useToast()` from `src/hooks/useToast.ts`.
