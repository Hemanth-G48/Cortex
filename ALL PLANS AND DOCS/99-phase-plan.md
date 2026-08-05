# Life OS — Life Planner Integration Plan (Revised) — ✅ COMPLETE (2026-07-31)

**Goal:** Finish merging the `life planner.odt` spec into the unified Student Life OS app, and unify the four theme systems (Student OS / RPG / Vault / Life Planner) behind one `data-theme` mechanism.

**Note:** The original "99-phase plan" (117 phases) was written before the Productivity Vault plan was completed. Phases covering vault features, habit archive/stats/heatmap, goal habit-fields, task `project_id`, toast system, responsive layout, accessibility, vault seed data, and regression tests are **already DONE**. This revision restates the true remaining gap (Life Planner + theme unification) as a lean, phase-by-phase plan.

---

## PART A — GAP ANALYSIS (verified against the current codebase on 2026-07-31)

| Feature | Spec | Status | Where |
|---|---|---|---|
| Task `project_id` | Vault | ✅ Done | `models/task.py`, schema, seed |
| Task `priority_quadrant` (Eisenhower) | Life Planner | ❌ **Missing** | — |
| ScheduleEvent `event_type` + `location` | Life Planner | ❌ **Missing** | — |
| DailyLog model (date, time_focused, status) | Life Planner | ❌ **Missing** | — |
| Event model (title, time, date, location, is_completed) | Life Planner | ❌ **Missing** | — |
| Habit `color_theme`, `is_archived` | Vault | ✅ Done | `models/habit.py` |
| Goal `habit_id`, `target_date`, `is_completed` | Vault | ✅ Done | `models/note.py` |
| Habit archive / unarchive / stats / heatmap endpoints | Vault | ✅ Done | `routers/habits.py` |
| Goal complete + `?habit_id=` filter | Vault | ✅ Done | `routers/notes.py` |
| Project summary endpoint | Vault | ✅ Done | `routers/projects.py` |
| Vault summary / tasks / calendar / database endpoints | Vault | ✅ Done | `routers/vault.py` |
| Vault dashboard + 7 vault pages | Vault | ✅ Done | `pages/Vault*.tsx`, `Habit*`, `GoalsSetting`, `GridDesign` |
| Toast system (ToastProvider + useToast) | All | ✅ Done | `main.tsx`, `hooks/ToastContext.ts` |
| Responsive breakpoints + keyboard-accessible tabs | All | ✅ Done | `styles/theme.css`, `VaultTabs.tsx` |
| Seed vault demo + fresh-DB gating | Vault | ✅ Done | `app/seed/__init__.py` |
| Backend regression suite (136 tests) | All | ✅ Done | `backend/tests/` |
| DailyLog router (CRUD + stats) | Life Planner | ❌ **Missing** | — |
| Event router (CRUD + today) | Life Planner | ❌ **Missing** | — |
| Life Planner summary aggregation endpoint | Life Planner | ❌ **Missing** | — |
| Eisenhower matrix endpoint + complete action | Life Planner | ❌ **Missing** | — |
| Quick-tasks endpoint (reminders + tasks + events) | Life Planner | ❌ **Missing** | — |
| Life-area goals endpoint | Life Planner | ❌ **Missing** | — |
| Life Planner dashboard page + components | Life Planner | ❌ **Missing** | — |
| Unified `data-theme` system + theme switcher | All | ❌ **Missing** (RPG/Vault themes are separate files) | — |
| Life Planner seed data (daily logs, events, quadrants) | Life Planner | ❌ **Missing** | — |

**Bottom line:** ~28 focused phases remain (backend foundation → routers → seeds → API client → theme unification → Life Planner UI → integration → verification).

---

## PART B — THE REMAINING PHASES

### GROUP 1 — Backend Foundation: Models, Schemas, Migrations (Phases 1–5)

#### Phase 1 — Add `priority_quadrant` to Task
- `models/task.py`: `priority_quadrant = Column(String(30), nullable=True)` (values: `Urgent/Important`, `Important/Not Urgent`, `Urgent/Not Important`, `Not Important/Not Urgent`)
- `schemas/task.py`: add to `TaskBase` + `TaskUpdate`
- `database.py` `COLUMN_MIGRATIONS["tasks"]`: add `("priority_quadrant", "VARCHAR(30)")`
- **Verify:** existing tasks untouched; new column present

#### Phase 2 — Add `event_type` + `location` to ScheduleEvent
- `models/schedule_event.py`: `event_type = Column(String(50), nullable=True)`, `location = Column(String(200), nullable=True)`
- `schemas/schedule_event.py`: add to Base/Create/Update/Response
- `database.py` `COLUMN_MIGRATIONS`: new `"schedule_events"` entry
- **Verify:** events store + return location/type

#### Phase 3 — Create DailyLog model + schemas
- `models/daily_log.py`: `DailyLog(id, user_id FK, date Date NOT NULL, time_focused Integer default 0, status String(50) default "active", created_at, updated_at)`
- `schemas/daily_log.py`: `DailyLogBase/Create/Update/Response`
- **Verify:** model + schemas compile

#### Phase 4 — Create Event model + schemas
- `models/event.py`: `Event(id, user_id FK, title String(200), time Time nullable, date Date NOT NULL, location String(200), is_completed Boolean default False, created_at)`
- `schemas/event.py`: `EventBase/Create/Update/Response`
- **Verify:** model + schemas compile

#### Phase 5 — Register models/schemas + migrations
- `models/__init__.py` + `schemas/__init__.py`: import + `__all__` for `DailyLog`, `Event` (and fix missing `Mission`/`MissionTask`/`ScheduleEvent` in `__all__`)
- New tables are created by `Base.metadata.create_all` at startup (no migration entry needed)
- **Verify:** `from app.models import *` and `from app.schemas import *` work

### GROUP 2 — Backend Routers (Phases 6–11)

#### Phase 6 — DailyLog router
- `routers/daily_logs.py`: `GET /daily-logs`, `POST /daily-logs`, `PUT /daily-logs/{id}`, `DELETE /daily-logs/{id}`, `GET /daily-logs/stats` (total focused time this month, days active)
- **Verify:** all 5 endpoints return 200

#### Phase 7 — Event router
- `routers/events.py`: `GET /events`, `POST /events`, `PUT /events/{id}`, `DELETE /events/{id}`, `GET /events/today`
- **Verify:** all 5 endpoints return 200

#### Phase 8 — Life Planner summary endpoint
- `routers/life_planner.py`: `GET /life-planner/summary` → `{current_streak, longest_streak, daily_log_today, time_focused_today, tasks_due_today, habits_active, goals_active, life_area_progress[]}`
- **Verify:** aggregation returns correct data from seed

#### Phase 9 — Eisenhower matrix endpoint
- `routers/eisenhower.py`: `GET /eisenhower/matrix` → 4 quadrant arrays from `priority_quadrant`; `POST /eisenhower/tasks/{id}/complete` → sets status + records completion quadrant action
- **Verify:** classification works; completion updates task

#### Phase 10 — Quick-tasks endpoint
- `routers/life_planner.py` (or `routers/quick_tasks.py`): `GET /quick-tasks` → reminders (incomplete) + tasks (not completed) + events (today) sorted by time
- **Verify:** unified list returns correct types + sorting

#### Phase 11 — Life-area goals + register routers
- `routers/life_areas.py`: `GET /life-areas/{area_id}/goals`
- `main.py`: register `daily_logs`, `events`, `life_planner`, `eisenhower`
- **Verify:** all new routes accessible; app starts cleanly

### GROUP 3 — Seed Data (Phase 12)

#### Phase 12 — Life Planner seed data
- `app/seed/__init__.py`: seed 7 DailyLog entries (varying `time_focused`), 5 Events (with locations), assign `priority_quadrant` to seeded tasks, `event_type`/`location` to schedule events; all append-only/idempotent
- **Verify:** fresh DB has all Life Planner entities; no duplicates on re-run

### GROUP 4 — Frontend API Client & Types (Phase 13)

#### Phase 13 — api.ts + types
- `services/api.ts`: add `dailyLogs`, `events`, `lifePlanner.summary`, `eisenhower.matrix/completeTask`, `tasks.byPriorityQuadrant`, `quickTasks`, `lifeAreaGoals`
- `types/index.ts`: `priority_quadrant`, `event_type`, `location`, `DailyLog`, `LifePlannerEvent`, matrix types
- **Verify:** TypeScript strict type-check passes

### GROUP 5 — Theme Unification (Phases 14–15)

#### Phase 14 — Unified `data-theme` token system
- `styles/theme.css`: shared tokens at `:root`; `[data-theme="student-os"]`, `[data-theme="rpg"]`, `[data-theme="vault"]`, `[data-theme="life-planner"]` blocks overriding only their unique tokens (vault `#0d0d0d`/`#3b82f6`, life-planner `#121212`/`#e8496d`, rpg orange/green)
- Keep `rpg-theme.css` + `pixel-art.css` imports (already wired); scoped classes stay untouched
- **Verify:** switching `data-theme` on `<html>` updates all themed tokens

#### Phase 15 — Theme switcher
- `components/shared/ThemeSwitcher.tsx`: dropdown with 4 themes, persists to `localStorage`, sets `document.documentElement.dataset.theme`
- Wire into `Header`/`Sidebar`; apply `data-theme="life-planner"` on the Life Planner page and `data-theme="vault"` already where used
- **Verify:** theme persists on reload; all pages render under their theme

### GROUP 6 — Life Planner Components (Phases 16–21)

#### Phase 16 — DailyLogWidget + MiniCalendar
- `DailyLogWidget.tsx`: date, week number, focused time, streak stats, "Log In Today" button, year/month/week progress bars
- `MiniCalendar.tsx`: month grid, nav arrows, today highlighted, `selectedDate` prop
- **Verify:** renders with seeded data; Log In Today calls API

#### Phase 17 — LifeNavigationGrid + RadarChartWidget
- `LifeNavigationGrid.tsx`: 2×3 cards (Wheel of Life, Goal Tracker, Eisenhower Matrix, Habit Tracker, Daily Journal, Reflection Diary) linking to pages
- `RadarChartWidget.tsx`: 5-axis radar (Finance, Physical Health, Work, Personal Life, Overall) in `#e8496d` (reuse `visualization/RadarChart.tsx` where possible)
- **Verify:** 6 cards navigate; radar renders data-driven

#### Phase 18 — QuickTaskManager (Reminders + Mini To-Do + Events)
- `RemindersList.tsx` / `MiniTodoList.tsx` / `EventsList.tsx`: three checklists fed by `/quick-tasks` + `/reminders` + `/events/today`; toggle + mark-done wired to API
- **Verify:** all 3 cards render side by side; toggles persist

#### Phase 19 — LifeAreasGoals (tabs + progress rings)
- 4-column card grid with "Areas" / "Quarterly" tabs; circular SVG progress ring per card; "Mark as achieved" → `POST /goals/{id}/complete` with green feedback
- **Verify:** tabs switch; progress renders; achieve works

#### Phase 20 — EisenhowerMatrixWidget
- 2×2 quadrants with tinted borders (red urgent / green important); "Do first / Schedule / Delegate / Delete" headers; task checkboxes + "Mark as done"
- **Verify:** all 4 quadrants render from `/eisenhower/matrix`; completion works

#### Phase 21 — LifePlannerDashboard assembly
- `pages/LifePlannerDashboard.tsx`: sidebar (DailyLog + Quick Actions + Mini Calendar) + 4-section main (Nav grid + radar, QuickTaskManager, LifeAreasGoals, EisenhowerMatrix); loads via one data hook
- **Verify:** full page renders all sections

### GROUP 7 — Integration (Phases 22–24)

#### Phase 22 — Routes + nav + sidebar
- `App.tsx`: `/life-planner` route; `NavLinks.tsx` + `Sidebar.tsx` additions; apply `data-theme="life-planner"` wrapper
- **Verify:** route renders; nav links active

#### Phase 23 — Toasts + edit pencils + mark-as-done
- `useToast()` on every Life Planner mutation; edit pencils open pre-filled modals; green button + strikethrough for completed items
- **Verify:** every mutation gives feedback and persists

#### Phase 24 — Responsive + a11y + hover polish
- Collapse 4-col goals grid on tablet; 44px touch targets on matrix/toggles; `prefers-reduced-motion`; aria-labels; hover glow on quick-adds (≤200ms transitions)
- **Verify:** layout adapts; keyboard-only usage works

### GROUP 8 — Verification, Docs & Acceptance (Phases 25–28)

#### Phase 25 — Backend regression + new-endpoint tests
- New `tests/test_life_planner.py`: daily-logs CRUD/stats, events CRUD/today, eisenhower matrix/complete, life-planner summary, quick-tasks, life-area goals; full suite stays green
- **Verify:** zero broken endpoints

#### Phase 26 — Frontend build + typecheck + regression
- `tsc -b` strict + `npm run build` + `vitest run`; every page (26 existing + 1 new) renders
- **Verify:** build passes cleanly

#### Phase 27 — Full-stack smoke test (fresh DB)
- Fresh SQLite DB → uvicorn → all core + new endpoints return correct data; frontend routes load
- **Verify:** end-to-end flow from clean start

#### Phase 28 — Docs + final acceptance gate
- Update `frontend/README.md` (routes, endpoints, components, themes); mark plan complete
- **Verify:** all gates pass; every Life Planner spec feature present

---

## PART C — FEATURE PRESERVATION

| Existing Feature | Preserved By |
|---|---|
| Student OS dashboard + 19 pages | Phases 26 (regression) |
| RPG dashboard + pages | Phases 26 (regression) |
| Vault dashboard + 7 vault pages | Phases 26 (regression) |
| 136 backend tests | Phases 25 |
| Vault/RPG/pixel CSS files | Phases 14 (imports kept) |
| Toast system, responsive CSS, a11y | Phases 23–24 (reused) |
| Seed idempotency (append-only) | Phase 12 |

## PART D — DEPENDENCY ORDER

```
Group 1 (Models) → Group 2 (Routers) → Group 3 (Seeds) → Group 4 (API client)
        ↓
Group 5 (Theme system) → Group 6 (Components) → Group 7 (Integration)
        ↓
Group 8 (Verification & Docs)
```

## PART E — RISK WARNINGS

1. **New columns on existing tables** must be added to `COLUMN_MIGRATIONS` in `database.py` (SQLite `create_all` cannot ALTER). New *tables* (daily_logs, events) are created automatically.
2. **Theme collision:** keep `.rpg-*`/`.pixel-*` classes scoped; the `data-theme` system must only override CSS custom-property *tokens*, never hardcode colors in components.
3. **Seed idempotency:** all Life Planner seeds must be append-only (check existing before insert) so restarts never duplicate data.
4. **`models/__init__.py` `__all__`** is currently incomplete (missing Mission/MissionTask/ScheduleEvent) — fix it while adding DailyLog/Event so barrel imports stay consistent.

## STATUS: ALL 28 PHASES COMPLETE ✅

- **Group 1 (Phases 1–5)** — `priority_quadrant` on Task, `event_type`/`location` on ScheduleEvent,
  `DailyLog` + `Event` models/schemas, barrel registration + column migrations ✅
- **Group 2 (Phases 6–11)** — `routers/daily_logs.py`, `routers/events.py`, `routers/life_planner.py`
  (summary + quick-tasks), `routers/eisenhower.py`, life-area goals endpoint, all registered in `main.py` ✅
- **Group 3 (Phase 12)** — `seed_life_planner_demo` (7 daily logs, 5 events with locations,
  task quadrants, event locations) — append-only/idempotent ✅
- **Group 4 (Phase 13)** — `api.ts` (dailyLogs/events/lifePlanner/eisenhower/quickTasks/reminders.update)
  + new TypeScript types ✅
- **Group 5 (Phases 14–15)** — `[data-theme]` blocks (vault/rpg/life-planner) + `ThemeSwitcher`
  (localStorage-persisted, lazy-initialized) wired into the sidebar ✅
- **Group 6 (Phases 16–21)** — DailyLogWidget, MiniCalendar, LifeNavigationGrid, RadarChartWidget,
  QuickTaskManager, LifeAreasGoals (progress rings + mark achieved), EisenhowerMatrixWidget,
  LifePlannerDashboard ✅
- **Group 7 (Phases 22–24)** — `/life-planner` route + nav group, toast feedback on every mutation,
  responsive breakpoints + focus styles ✅
- **Group 8 (Phases 25–28)** — `tests/test_life_planner.py` (26 tests), strict `tsc -b` + `npm run build`
  + `vitest` green, fresh-DB smoke test passed, `frontend/README.md` updated ✅

**Final counts:** 162 backend tests · 13 frontend tests · strict TS build clean · all new endpoints
verified against a fresh SQLite DB.

*Revised: 2026-07-31. Original plan was 117 phases; ~89 were complete via the Productivity Vault plan; the remaining 28 Life Planner phases are now done.*
