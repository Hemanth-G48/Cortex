# Gamified Habit Tracker — 99-Phase Integration Plan (Student OS)

**Goal:** Add every feature from the `Gamified Habit Tracker .odt` spec to the existing Student Life OS app — a fixed-sidebar gamified habit dashboard with a cinematic 3D header, a Status-Window / Pomodoro / Rewards sidebar, Quick-Action + Life-Areas row, Daily Good-Bad Habit rows with filter tabs, and Completed-Good/Bad-Habit weekly calendars — while preserving the 158 passing backend tests, the strict TS build, and the existing Student OS / RPG / Vault / Quest-Centre / Life-Planner themes.

**Baseline (verified 2026-08-02):** Backend 158 tests defined (`test_courses`, `test_habits`, `test_health`, `test_life_planner`, `test_other_endpoints`, `test_regression`, `test_rpg`, `test_tasks`, `test_vault`); frontend `tsc -b` + `npm run build` clean. Existing Habit module already has: `Habit` + `HabitLog` models/router/schemas (streak + longest-streak tracking, stats + heatmap endpoints, archive/unarchive), a `User` model already carrying `avatar_class` + `current_streak`, a `Character` model with XP/level, a `LifeArea` model with `target_days`/`status`/`image_url`, a `Reward` model with `xp_cost`/`is_available`/`claimed_date`, a `PomodoroSession` model, the Quest-Centre dashboard (`quest_centre.py` service + router + 6 widgets + gold theme tokens), and reusable RPG components (`RewardCard`, `RewardCenter`, `WeeklyCalendar`, `RpgBadge`, `RpgButton`, `RpgTabs`).

---

## PART A — GAP ANALYSIS (spec vs. current codebase)

| Spec Feature | Spec Requirement | Status | Where |
|---|---|---|---|
| Header (top full-width) | Cinematic 3D pixel-art living-room banner + app title overlay | ❌ **Missing** | `components/layout/Header.tsx` is a plain text bar |
| Sidebar — Status-Window | Wizard avatar, greeting, total XP, XP-left, "Today's Stats", "Keep going! 💪" | ⚠️ **Partial** (Quest-Centre `StatusWindowWidget` exists, no habit "Today's Stats") | `questcentre/StatusWindowWidget.tsx` |
| Sidebar — Pomodoro Timer | 25:00 timer, Short/Long Break toggles, Start, settings gear | ⚠️ **Partial** (`PomodoroWidget` exists; model has no `mode` Focus/Break) | `questcentre/PomodoroWidget.tsx`, `models/pomodoro.py` |
| Sidebar — Rewards | XP-cost reward cards + "Claim Reward" button | ⚠️ **Partial** (`RewardCard`/`RewardCenter` exist; no compact sidebar widget, no glow) | `rpg/RewardCard.tsx`, `RewardCenter.tsx` |
| Row 1 — Quick-Action | "New Good Habit", "New Bad Habit", "Database" links | ⚠️ **Partial** (Quest-Centre `QuickActionsQC` covers quest/mission/reward) | `questcentre/QuickActionsQC.tsx` |
| Row 1 — Progress Bars | Year / Month / Week / Day stacked bars | ✅ **Done** (reuse `ProgressBarsQC`) | `questcentre/ProgressBarsQC.tsx` |
| Row 1 — Life-Areas | 4 cards (Health, Self Improvement, Work, Fitness) + "All Time XP" + status badge | ⚠️ **Partial** (`LifeAreasGridQC` exists; no `total_xp_earned` on model) | `questcentre/LifeAreasGridQC.tsx`, `models/life_area.py` |
| Row 2 — Daily-Good-Habits | Tabs (All / Did Today / Overview) + good habit cards (XP reward) | ⚠️ **Partial** (Habit model exists, no good/bad type, no `xp_reward`) | `models/habit.py`, `pages/HabitTracker.tsx` |
| Row 3 — Daily-Bad-Habits | Tabs + bad habit cards with "Shit I did it: -X XP" | ❌ **Missing** (no `habit_type`, no `xp_penalty`) | `models/habit.py` |
| Row 4 — Completed-Good-Habits | Weekly calendar timeline, habits plotted on dates | ⚠️ **Partial** (vault `WeeklyCalendarRow` exists, habit-agnostic) | `components/vault/WeeklyCalendarRow.tsx` |
| Row 5 — Completed-Bad-Habits | Weekly calendar timeline for bad habits | ❌ **Missing** | — |
| Habit: `habit_type` (Good/Bad) | spec data model | ❌ **Missing** | `models/habit.py` |
| Habit: `xp_reward` / `xp_penalty` | spec data model (Complete to earn / Shit I did it) | ❌ **Missing** | `models/habit.py` |
| Habit: `image_url` | spec data model (3D scene thumbnails) | ❌ **Missing** | `models/habit.py` |
| Habit: `days_streak` / `days_caught` | spec data model | ⚠️ **Partial** (`current_streak` exists; no `days_caught`) | `models/habit.py` |
| Habit_Log: `type`, `status`, `xp_change` | spec data model (Good/Bad, Completed/Shit, ±XP) | ❌ **Missing** | `models/habit.py` |
| Life_Area: `total_xp_earned` | spec data model ("All Time XP: 58") | ❌ **Missing** | `models/life_area.py` |
| Reward: `xp_cost`, `status`, `image_url` | spec data model | ✅ **Done** | `models/reward.py` |
| Pomodoro_Session: `mode` (Focus/Break) | spec data model | ❌ **Missing** | `models/pomodoro.py` |
| User/Profile: `avatar_class`, `current_streak`, `total_xp`, `level` | spec data model | ✅ **Done** | `models/user.py` |
| XP engine: good habit → +XP, bad habit → −XP | Gamification core ("Gold & Punishment") | ❌ **Missing** (log creation only bumps streak) | `routers/habits.py` |
| Completed calendar: color-coded dots | UI/UX improvement | ❌ **Missing** | `WeeklyCalendarRow.tsx` |
| Reward claim glow/pulse | UI/UX improvement | ❌ **Missing** | `rpg/RewardCard.tsx` |
| XP penalty red flash / fly-up | UI/UX improvement | ❌ **Missing** | — |
| Card hover scale + glow | UI/UX improvement | ❌ **Missing** | habit/life-area cards |
| Calendar drag-and-drop / uncompleted filter | UI/UX improvement | ❌ **Missing** | — |
| Habit-tracker theme (`#0c0c0c`, gold/green/red/blue) | spec palette | ⚠️ **Partial** (add `data-theme="habit-tracker"` block) | `styles/theme.css`, new `habit-tracker.css` |

**Bottom line:** ~99 focused phases remain. Backend (habit good/bad fields + XP engine + aggregation endpoints + seed) → API client → habit-tracker theme → layout/header → sidebar widgets → Row 1 → Row 2 → Row 3 → Row 4/5 calendars → gamification polish → integration → verification.

---

## PART B — THE PHASES

### GROUP 1 — Backend Foundation: Habit Good/Bad Fields, Schemas, Migrations (Phases 1–8)

#### Phase 1 — Add `habit_type` to Habit
- `models/habit.py`: `habit_type = Column(String(20), default="good")  # good / bad`
- `schemas/habit.py`: add to `HabitBase`/`HabitResponse`
- `database.py` `COLUMN_MIGRATIONS["habits"]`: append `("habit_type", "VARCHAR(20) DEFAULT 'good'")`
- **Verify:** `from app.models import *` exposes `habit_type`; schema compiles; existing habits get `good`

#### Phase 2 — Add `xp_reward` + `xp_penalty` to Habit
- `models/habit.py`: `xp_reward = Column(Integer, default=30)`, `xp_penalty = Column(Integer, default=20)`
- `schemas/habit.py`: add both to `HabitBase`/`HabitResponse`
- `database.py`: `("xp_reward", "INTEGER DEFAULT 30")`, `("xp_penalty", "INTEGER DEFAULT 20")`
- **Verify:** good habit stores reward; bad habit stores penalty; defaults non-null

#### Phase 3 — Add `image_url` + `days_caught` to Habit
- `models/habit.py`: `image_url = Column(String(500), nullable=True)`, `days_caught = Column(Integer, default=0)`
- `schemas/habit.py`: add to `HabitBase`/`HabitResponse`
- `database.py`: `("image_url", "VARCHAR(500)")`, `("days_caught", "INTEGER DEFAULT 0")`
- **Verify:** columns present after migration; schemas round-trip

#### Phase 4 — Extend HabitLog with `type`, `status`, `xp_change`
- `models/habit.py` `HabitLog`: `type = Column(String(10), default="good")`, `status = Column(String(20), default="Completed")`, `xp_change = Column(Integer, default=0)`
- `schemas/habit.py` `HabitLogBase`/`HabitLogCreate`/`HabitLogResponse`: add all three
- `database.py`: add `habit_logs` entry with the three columns
- **Verify:** `HabitLog` import + schema compile; new log rows carry type/status/xp_change

#### Phase 5 — Register Habit/HabitLog fields in barrel imports
- `models/__init__.py` + `schemas/__init__.py`: confirm `Habit` + `HabitLog` exported (add if missing)
- **Verify:** `from app.models import *` / `from app.schemas import *` work

#### Phase 6 — Add `mode` to PomodoroSession
- `models/pomodoro.py`: `mode = Column(String(10), default="Focus")  # Focus / Break`
- `schemas/pomodoro.py`: add to Base/Create/Response
- `database.py` `COLUMN_MIGRATIONS["pomodoro_sessions"]`: `("mode", "VARCHAR(10) DEFAULT 'Focus'")`
- **Verify:** pomodoro schema compiles; existing sessions default to `Focus`

#### Phase 7 — Add `total_xp_earned` to LifeArea
- `models/life_area.py`: `total_xp_earned = Column(Integer, default=0)`
- `schemas/life_area.py`: add to Base/Create/Update/Response
- `database.py` `COLUMN_MIGRATIONS["life_areas"]`: `("total_xp_earned", "INTEGER DEFAULT 0")`
- **Verify:** life-area schema compiles; default 0 on existing rows

#### Phase 8 — Column-migration safety check
- `database.py` `migrate_schema()`: run against current `productivity.db`
- **Verify:** no exception; `PRAGMA table_info(habits/habit_logs/pomodoro_sessions/life_areas)` shows new columns

### GROUP 2 — Backend: XP Engine Service (Phases 9–15)

#### Phase 9 — `services/habit_xp.py` scaffold
- New `backend/app/services/habit_xp.py` with `GOOD`/`BAD` constants + signature mirrors of `quest_centre.py`
- **Verify:** module imports cleanly

#### Phase 10 — Good-habit completion XP award
- Helper `award_good_habit(db, habit, user)` → adds `habit.xp_reward` to `user.total_xp` + `character.xp`; returns `xp_change`
- **Verify:** unit-testable; XP credited to user + character

#### Phase 11 — Bad-habit penalty
- Helper `penalize_bad_habit(db, habit, user)` → subtracts `habit.xp_penalty` from `user.total_xp`/`character.xp` (floor at 0); returns `xp_change`
- **Verify:** penalty applied; XP never negative

#### Phase 12 — Streak / days_caught increment
- Helper `bump_streak(habit)` → good: `current_streak += 1` (+ longest); bad: `days_caught += 1`
- **Verify:** good bumps streak, bad bumps days_caught

#### Phase 13 — `HabitLog` xp_change writer
- Helper `record_log(db, habit, user, date)` → creates `HabitLog(type, status, xp_change)` consistent with the spec
- **Verify:** log persists with correct ±XP; unit test passes

#### Phase 14 — Life-area XP attribution
- Helper `credit_life_area(db, area)` → increments `area.total_xp_earned` by the last XP change
- **Verify:** "All Time XP" reflects habit completion totals

#### Phase 15 — Gamification summary helper
- Helper `habit_gamification_summary(db)` → `{total_xp, level, current_streak, good_today, bad_today, xp_to_next}`
- **Verify:** returns correct XP-left math `1000 - (xp % 1000)`

### GROUP 3 — Backend Routers (Phases 16–24)

#### Phase 16 — Extend `POST /habit-logs` to award/penalize XP
- `routers/habits.py` `create_habit_log`: call Phase 10–13 helpers based on `habit.habit_type`; return log with `xp_change`
- **Verify:** good completion → `+xp_reward`; bad admit → `−xp_penalty`; tests stay green

#### Phase 17 — `GET /habits?type=good|bad` filter
- `routers/habits.py` `list_habits`: accept `type` query param → filter `habit_type`
- **Verify:** returns only good or only bad habits

#### Phase 18 — `GET /habits/good` + `GET /habits/bad` aliases
- Thin wrappers around Phase 17 (spec-consistent URL surface)
- **Verify:** both return 200 with seeded split

#### Phase 19 — `GET /habits/today` (Did Today aggregation)
- Returns habits with a `log_today: bool` + `xp_today` computed from today's logs
- **Verify:** correct `Did Today` flags after a logged completion

#### Phase 20 — `GET /habit-logs/calendar?type=good|bad&start=&end=`
- Groups `HabitLog` by date for the two completed-habit calendar rows
- **Verify:** plots habits on correct dates; honors type filter

#### Phase 21 — `GET /habit-tracker/status-window`
- Composes `status_window_data`-style payload + habit "Today's Stats" list (habits logged today)
- **Verify:** returns 200 with wizard + today's habit stats

#### Phase 22 — `GET /habit-tracker/summary`
- Returns `{good_count, bad_count, good_today, bad_today, total_xp, level, life_areas, rewards_available}`
- **Verify:** aggregate matches seeded data

#### Phase 23 — `routers/habit_tracker.py` scaffold + register
- New router `prefix="/api"`, `tags=["habit-tracker"]`; `main.py`: `app.include_router(habit_tracker.router)`
- **Verify:** app starts; both new endpoints accessible

#### Phase 24 — Reward claim XP-gating consistency
- `routers/rewards.py` claim: confirm it deducts user XP (align with habit XP so both share the same wallet)
- **Verify:** claiming a reward after good habits succeeds; insufficient XP rejects

### GROUP 4 — Seed Data (Phases 25–31)

#### Phase 25 — Seed good habits
- `seed/__init__.py`: add idempotent `seed_good_habits` — "Deep Work", "Workout", "Healthy Diet", "Reading", "Good Sleep" with `habit_type="good"`, `xp_reward=30`, `image_url` placeholders
- **Verify:** 5 good habits seeded; no duplicates on re-seed

#### Phase 26 — Seed bad habits
- Add `seed_bad_habits` — "Smoking", "Alcohol", "Fast Food", "High Screen Time", "Bad Sleep" with `habit_type="bad"`, `xp_penalty=20`
- **Verify:** 5 bad habits seeded

#### Phase 27 — Seed habit logs with type/status/xp_change
- Add logs for the past 7 days across good/bad habits (Completed / Shit I did it) so calendars render
- **Verify:** calendar endpoints return populated week

#### Phase 28 — Seed the 4 spec rewards
- Rewards: "Go for a walk", "Watch movie", "Eat outside", "Day off" with `xp_cost` (30/50/60/80) + thumbnails
- **Verify:** reward list returns the 4; some `claimed_date` set for the Claimed tab

#### Phase 29 — Seed pomodoro sessions with `mode`
- 3–5 sessions mixing `Focus`/`Break`
- **Verify:** `/pomodoro-sessions` returns modes

#### Phase 30 — Seed life-area `total_xp_earned`
- Set Health/Self-Improvement/Work/Fitness with plausible totals ("All Time XP")
- **Verify:** life-areas endpoint exposes totals

#### Phase 31 — Idempotency + seed smoke test
- Run `seed_database` twice; assert no duplicate rows; existing 158 tests still green
- **Verify:** idempotent append-only behavior

### GROUP 5 — Frontend API Client + Types (Phases 32–38)

#### Phase 32 — Extend `Habit` + `HabitLog` types in `api.ts`
- Add `habit_type`, `xp_reward`, `xp_penalty`, `image_url`, `days_caught` to `Habit`; `type`/`status`/`xp_change` to `HabitLog`
- **Verify:** `tsc -b` clean

#### Phase 33 — Add `PomodoroSession.mode` + `LifeArea.total_xp_earned` types
- Update both interfaces
- **Verify:** `tsc -b` clean

#### Phase 34 — Habit-tracker endpoint helpers
- `endpoints.habitTracker` block: `statusWindow()`, `summary()`, `habitsByType(type)`, `today()`, `calendar(type,start,end)`
- **Verify:** each maps to the Phase 16–23 routes

#### Phase 35 — Habit-action helpers
- `endpoints.habits.logHabit(habitId, date)` → reuse `logToday` but return `xp_change`
- **Verify:** TS signatures align with backend response

#### Phase 36 — Reward widget helper
- `endpoints.rewards` already present; add `available()` filter usage for sidebar
- **Verify:** types align

#### Phase 37 — New `GamifiedHabitTracker` page types
- `types/index.ts` or inline: `HabitTrackerStatusWindow`, `HabitTrackerSummary`, `HabitCalendarDay`
- **Verify:** strict TS passes

#### Phase 38 — API client smoke check
- `npm run tsc`; ensure no unused/incorrect imports from previous phases
- **Verify:** build clean

### GROUP 6 — Theme & Styling (Phases 39–46)

#### Phase 39 — `data-theme="habit-tracker"` token block
- `styles/theme.css`: add block mirroring spec palette: `--bg-primary:#0c0c0c`, `--bg-card:#181818`, `--accent-gold:#ffd700`, `--status-good:#4ade80`, `--status-bad:#f43f5e`, `--progress-blue:#3b82f6`, `--border:#262626`
- **Verify:** tokens resolve; theme-switcher shows the new option

#### Phase 40 — `styles/habit-tracker.css` scaffold
- New scoped file (`.ht-*` prefixes, all colors from tokens)
- **Verify:** CSS loads via `main.tsx` import

#### Phase 41 — Cinematic header styles
- `.ht-header`: 3D banner background (gradient + pixel-art placeholder via CSS), title overlay, 24px heading
- **Verify:** renders full-width banner above content

#### Phase 42 — Sidebar card styles
- `.ht-status-card`, `.ht-pomodoro-card`, `.ht-rewards-card` with `#181818` bg, `#262626` border, 8–12px radius, `0 4px 6px rgba(0,0,0,.6)` shadow
- **Verify:** spec spacing/radius/shadows applied

#### Phase 43 — Good/Bad habit card styles
- `.ht-good-card` (green border/glow), `.ht-bad-card` (red border/glow), hover `scale(1.02)`
- **Verify:** distinct green vs red treatment

#### Phase 44 — Calendar row styles + color-coded dots
- `.ht-calendar-row`, `.ht-cal-item`, `.ht-dot-good` (green), `.ht-dot-bad` (red)
- **Verify:** dots render next to items

#### Phase 45 — Progress-bar + life-area card styles
- Reuse `.qc-progress` patterns; add `.ht-life-area-card` with image backdrop + badge
- **Verify:** 4 life-area cards styled

#### Phase 46 — Animation keyframes
- `@keyframes ht-glow` (reward), `ht-flash-red` (penalty), `ht-fly-up` (−20 XP), `ht-pop` (done)
- **Verify:** keyframes referenced in card styles

### GROUP 7 — Layout & Header (Phases 47–53)

#### Phase 47 — `GamifiedHabitTracker` page shell
- New `pages/GamifiedHabitTracker.tsx` with `.ht-layout` grid (300px sidebar + main 5-row stack)
- **Verify:** routes render with the new grid

#### Phase 48 — Register route + nav link
- `App.tsx`: `<Route path="/habit-tracker" ...>`; `Sidebar.tsx`/`NavLinks.tsx`: add "Gamified Habit Tracker" entry
- **Verify:** nav navigates to the page

#### Phase 49 — `HtHeader` component
- `components/habittracker/HtHeader.tsx`: cinematic banner + app title overlay (reuses Phase 41 styles)
- **Verify:** renders full-width banner

#### Phase 50 — Layout composition
- Compose `<Sidebar/><MainContent/>` inside the page (5 rows in one scrollable stack)
- **Verify:** 24px section padding, 16–20px internal card padding, 16–24px grid gaps

#### Phase 51 — Row containers (5 rows)
- `.ht-row` wrappers with section headers for Quick-Action/Life-Areas, Good Habits, Bad Habits, Completed calendars
- **Verify:** 5 distinct horizontal rows render

#### Phase 52 — Responsive behavior
- Media queries collapse sidebar → top; rows stack below 1024px
- **Verify:** 1920×1080 desktop-first layout + graceful narrow fallback

#### Phase 53 — Empty/loading states
- `EmptyState` reuse + skeleton shimmer for each row while fetching
- **Verify:** skeleton shows before data; empty state when no habits

### GROUP 8 — Sidebar Widgets (Phases 54–61)

#### Phase 54 — `HtStatusWindow` (wizard + Today's Stats)
- New `components/habittracker/HtStatusWindow.tsx`: wizard avatar, greeting ("Good Morning Player"), total XP, XP-left, Today's Stats list (habit + XP today), "Keep going! 💪"
- **Verify:** renders from `/habit-tracker/status-window`

#### Phase 55 — Greeting logic
- Time-based greeting (Good Morning/Afternoon/Evening) + avatar glyph from `avatar_class`
- **Verify:** greeting switches by hour

#### Phase 56 — `HtPomodoro` widget (reuse)
- Wrap `questcentre/PomodoroWidget` (25:00, Short/Long Break, Start, gear) in sidebar card
- **Verify:** timer runs; sessions POST with `mode`

#### Phase 57 — Pomodoro mode toggle persistence
- Pass `mode` (Focus/Break) to session create; display last mode
- **Verify:** session record carries mode

#### Phase 58 — `HtRewards` sidebar widget
- New compact reward list (thumbnail, "XP Needed: X", "Claim Reward") using `RewardCard` primitives
- **Verify:** 4 rewards render with costs; claim hits `rewards.claim`

#### Phase 59 — Reward claim glow
- When `user.total_xp >= xp_cost`, `.ht-glow` gold pulse on Claim button
- **Verify:** affordable rewards glow; others don't

#### Phase 60 — Sidebar assembly
- Compose Status-Window + Pomodoro + Rewards in `.ht-sidebar`
- **Verify:** three stacked modules match spec order

#### Phase 61 — Sidebar data hook
- `hooks/useHabitTrackerData.ts`: parallel fetch of status-window + summary + rewards
- **Verify:** single mount fetches all sidebar data

### GROUP 9 — Row 1: Quick-Action + Progress + Life-Areas (Phases 62–68)

#### Phase 62 — `HtQuickActions`
- New widget: "New Good Habit", "New Bad Habit", "Database" links (+ icons)
- **Verify:** links open create modals / `/vault-database`

#### Phase 63 — Good/Bad habit create modals
- Reuse/extend a modal with `habit_type` selector; POST `/habits`
- **Verify:** creating a good habit persists `habit_type="good"`

#### Phase 64 — `HtProgressBars`
- Reuse `ProgressBarsQC` (Year/Month/Week/Day) from `/habit-tracker/summary`
- **Verify:** 4 stacked bars reflect progress values

#### Phase 65 — `HtLifeAreasGrid`
- 4 cards (Health, Self Improvement, Work, Fitness) with 3D thumbnail, title, "All Time XP: N", status badge
- **Verify:** reads `total_xp_earned` + `status` from API

#### Phase 66 — Row-1 layout composition
- Two-column split: Quick-Action+Progress left, Life-Areas right
- **Verify:** matches spec 2-column split

#### Phase 67 — Life-area hover glow
- `.ht-life-area-card:hover` scale 1.02 + gold/green glow
- **Verify:** hover effect present

#### Phase 68 — Quick-action empty states
- Pixel-art placeholder in create-form empty states
- **Verify:** styled placeholders (reuse `placeholders.ts`)

### GROUP 10 — Row 2: Daily-Good-Habits (Phases 69–76)

#### Phase 69 — `HtDailyGoodHabits`
- New component: horizontal row of good-habit cards + 3 filter tabs
- **Verify:** 5 seeded good habits render

#### Phase 70 — Good habit card
- `HtGoodHabitCard`: 3D thumbnail, title, "Complete to earn: X XP", "Today" placeholder, "Completed" badge
- **Verify:** card content matches spec copy

#### Phase 71 — Tab filter: All / Did Today / Overview
- `HtTabs` (reuse `RpgTabs` pattern); "Did Today" filters `log_today`
- **Verify:** switching tabs re-filters list

#### Phase 72 — Complete action + green flash
- "Complete" button → `logHabit` → success + green `ht-pop` flash + streak bump
- **Verify:** XP credited; card flashes green; `current_streak` increments

#### Phase 73 — Overview tab (aggregate stats)
- Shows this week's completions, total XP earned, streak summary per habit
- **Verify:** aggregates from `/habit-logs/calendar?type=good`

#### Phase 74 — "Today" placeholder per card
- Completed-today state shows ✓ vs pending "Today"
- **Verify:** toggles on completion

#### Phase 75 — Sorting by streak
- Sort good cards by `current_streak` desc (dopamine ordering)
- **Verify:** highest streak first

#### Phase 76 — Good-habit empty state
- Pixel-art placeholder when no good habits
- **Verify:** renders empty state

### GROUP 11 — Row 3: Daily-Bad-Habits (Phases 77–84)

#### Phase 77 — `HtDailyBadHabits`
- New component: horizontal row of bad-habit cards + 3 filter tabs (All / Did Today / Overview)
- **Verify:** 5 seeded bad habits render

#### Phase 78 — Bad habit card
- `HtBadHabitCard`: dark moody thumbnail, title, "Shit I did it: -X XP", Today placeholder, "Completed" status
- **Verify:** card copy matches spec

#### Phase 79 — Admit action + red flash + fly-up
- "Shit I did it" button → `logHabit` → `ht-flash-red` card + `-X XP` fly-up text
- **Verify:** penalty applied; animation plays; `days_caught` increments

#### Phase 80 — Bad-habit tabs
- All / Did Today / Overview filters (reuse Phase 71 tab logic)
- **Verify:** tabs re-filter

#### Phase 81 — Bad-habit overview
- Shows caught count, XP lost this week, worst offender
- **Verify:** aggregates `/habit-logs/calendar?type=bad`

#### Phase 82 — XP penalty floor
- Confirm user/character XP never drops below 0 (Phase 11 helper)
- **Verify:** floor enforced in UI + backend

#### Phase 83 — Bad-habit sorting
- Sort by `days_caught` desc (accountability)
- **Verify:** most-caught first

#### Phase 84 — Bad-habit empty state
- Pixel-art placeholder when none tracked
- **Verify:** renders

### GROUP 12 — Rows 4/5: Completed-Good/Bad-Habit Calendars (Phases 85–91)

#### Phase 85 — `HtCompletedGoodCalendar`
- New weekly calendar: 7 day columns, good-habit logs plotted on dates
- **Verify:** logs appear on correct days (Apr–May style)

#### Phase 86 — `HtCompletedBadCalendar`
- Same row for bad habits
- **Verify:** bad logs plotted; separate from good

#### Phase 87 — Calendar item + color-coded dots
- Each item: task title, ±XP, badge, green/gold dot (good) or red dot (bad)
- **Verify:** dots let users scan the week

#### Phase 88 — Week/Month toggle
- Week view default; Month toggle re-renders grid (reuse `WeeklyCalendarRow` month math)
- **Verify:** both views render

#### Phase 89 — "Open in Calendar" link
- External-arrow link per row → `/schedule` or `/vault` calendar
- **Verify:** link navigates

#### Phase 90 — Uncompleted-item filter
- Checkbox "Show only uncompleted" filters each day's items
- **Verify:** filter works

#### Phase 91 — Drag-and-drop calendar sort (enhancement)
- HTML5 drag reorder within day; persist order via `sort_order` if adopted
- **Verify:** reorder persists after reload

### GROUP 13 — Gamification Polish (Phases 92–96)

#### Phase 92 — Reward claim glow + pulse pass
- Polish `.ht-glow` timing; pulse when XP sufficient (spec UX improvement)
- **Verify:** animation smooth, stops when insufficient

#### Phase 93 — XP penalty red flash polish
- Fly-up text `-20 XP` positioned over bad card; fade-out
- **Verify:** animation reads clearly

#### Phase 94 — Card hover states across rows
- Uniform `scale(1.02)` + color-matched glow on life-area, good, bad, reward cards
- **Verify:** consistent interactivity

#### Phase 95 — Toast integration
- `useToast` on XP earned / XP lost / reward claimed
- **Verify:** toasts fire on each action

#### Phase 96 — Accessibility + focus states
- aria-labels on tabs/buttons, focus-visible rings, `prefers-reduced-motion` gating
- **Verify:** keyboard nav works; animations disabled on request

### GROUP 14 — Integration & Verification (Phases 97–99)

#### Phase 97 — Backend test suite
- Add/extend `test_habits.py` + `test_rpg.py` for: type filter, XP award/penalty, calendar endpoints, streak/days_caught, pomodoro mode, life-area totals
- **Verify:** full suite green (target ≥ 165+ tests)

#### Phase 98 — Frontend build + theme integration
- `tsc -b` strict + `npm run build`; theme-switcher lists `habit-tracker`; cross-links between quest-centre and habit-tracker work
- **Verify:** build clean; theme toggle applies `#0c0c0c`/gold palette

#### Phase 99 — Final verification checklist
- Manual walkthrough: header banner → sidebar (status/pomodoro/rewards) → Row 1 → Row 2 good habits → Row 3 bad habits → Row 4/5 calendars → reward glow → XP animations
- **Verify:** no `test.skip`, no stubs, no TODO placeholders; all 99 phases accounted for; end-to-end flows tested
