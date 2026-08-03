# Fitness Hub — 99-Phase Integration Plan (Student OS)

**Goal:** Add every feature from the `fitness hub.odt` spec to the existing Student Life OS app — a fixed-sidebar gamified fitness dashboard with a minimal header, six sidebar modules (Quick-Action, Navigation, Weight Goal, PR-Tracker, Membership, Diet-Plan), and five main rows (Weekly-Split, Habit-Tracking heatmaps, Muscle-Group 3D grid, Expenses, Exercises) — while preserving the 158 passing backend tests, the strict TS build, and the existing Student OS / RPG / Vault / Quest-Centre / Life-Planner themes.

**Baseline (verified 2026-08-02):** Backend 158 tests defined; frontend `tsc -b` + `npm run build` clean. Existing fitness module is minimal: `Workout` + `FitnessGoal` models/router/schemas, a basic `Fitness.tsx` page (stat tiles + goal cards + workout table), and `#0f1012`-theme-agnostic styling. Strongly reusable assets: `Habit` model with `habit_logs` + `/habits/{id}/heatmap` + vault `HeatmapGrid`/`HabitHeatmapCard` (7×7 grid), `WeekGrid`/`WeeklyCalendarRow`, `COLUMN_MIGRATIONS` in `database.py`, the `data-theme` token system, RPG primitives (`RpgTabs`, `RpgCard`, `RpgBadge`, `RpgButton`), Quest-Centre widgets, and `utils/placeholders.ts`.

---

## PART A — GAP ANALYSIS (spec vs. current codebase)

| Spec Feature | Spec Requirement | Status | Where |
|---|---|---|---|
| Header (top full-width) | App title "Fitness-Hub" ~28px, minimalist | ⚠️ **Partial** (`Header` bar exists; title smaller) | `components/layout/Header.tsx`, `pages/Fitness.tsx` |
| Sidebar — Quick-Action | 7 links: Add Exercise / Expense / Muscle Group / Habit / Habit Grid Design / Weight Goal / Membership | ❌ **Missing** | — |
| Sidebar — Navigation | 11 links: Membership, Muscle Groups, Exercises, Workout Plan, Habit Grid Design, Weight Goals, PR Tracker, Resources, Archive, Physique Check In, Backend | ❌ **Missing** | `NavLinks.tsx` has generic nav only |
| Sidebar — Weight Goal | current weight, initial, target, progress bar | ❌ **Missing** (User has no weight fields) | `models/user.py` |
| Sidebar — PR-Tracker | Current/target bench press, overhead press | ❌ **Missing** (no `PersonalRecord` model) | — |
| Sidebar — Membership | Gym info, status "Active", next payment date | ❌ **Missing** (no membership fields) | `models/user.py` |
| Sidebar — Diet-Plan | List: Diet, Bulking, Cutting, Maintenance phases | ❌ **Missing** (no `DietPlan` model) | — |
| Row 1 — Weekly-Split | Week 1 / Week 2 / Customization tabs; Mon–Sat cards (PUSH/PULL/LEG) with exercise lists | ❌ **Missing** (no `WorkoutSplit` model; `Workout` is a log only) | `models/fitness.py` |
| Row 2 — Habit-Tracking | 4 heatmap cards (Workout, 3000 Kcal, 4L water, Supplements); 7×7 grid, goal, days-completed, %, mark-complete | ⚠️ **Partial** (heatmap UI + `/heatmap` endpoint exist; spec-specific 4 habits not seeded) | `vault/HeatmapGrid.tsx`, `HabitHeatmapCard.tsx`, `routers/habits.py` |
| Row 3 — Muscle-Group | 12 3D anatomical cards, Upper/Lower tag, exercise count | ❌ **Missing** (no `MuscleGroup`/`Exercise` models) | — |
| Row 4 — Expenses | Cards: Protein & Creatine, Multivitamin, Liver Salt, Equipments; date, cost, tag | ❌ **Missing** (no `Expense` model) | — |
| Row 5 — Exercises | By-Muscle-group / All tabs; nested Muscle → Exercise → Set lists | ❌ **Missing** (no `Exercise` model, no set breakdown) | — |
| User: `current_weight`/`initial_weight`/`target_weight` | spec data model (Weight Goal) | ❌ **Missing** | `models/user.py` |
| User: `membership_status`/`next_payment_date` | spec data model (Membership) | ❌ **Missing** | `models/user.py` |
| Habit: `goal` text + `heatmap_data` JSON | spec data model | ⚠️ **Partial** (`HabitLog`+`/heatmap` endpoint; no `goal` column) | `models/habit.py` |
| `Exercise` model (muscle_group_id, sets, reps, weight) | spec data model | ❌ **Missing** | — |
| `MuscleGroup` model (name, body_part, image_3d_url) | spec data model | ❌ **Missing** | — |
| `WorkoutSplit` model (day_of_week, split_name, exercise_list) | spec data model | ❌ **Missing** | — |
| `Expense` model (title, cost, date, category) | spec data model | ❌ **Missing** | — |
| `PersonalRecord` model (exercise_name, current, target) | spec data model | ❌ **Missing** | — |
| `DietPlan` model (title, is_active) | spec data model | ❌ **Missing** | — |
| Expense donut/pie chart | UI/UX improvement (spending % breakdown) | ❌ **Missing** | — |
| Interactive muscle groups (click → expand exercises) | UI/UX improvement | ❌ **Missing** | — |
| "Log Today's Workout" / Start Workout button | UI/UX improvement | ❌ **Missing** | `pages/Fitness.tsx` |
| 2×2 / 3-column exercise grid | UI/UX improvement (vs vertical stack) | ❌ **Missing** | — |
| Unified empty state with translucent icon | UI/UX improvement | ❌ **Missing** (plain text empties) | `components/shared/EmptyState.tsx` |
| Fitness-hub theme (`#0f1012`, blue/green/yellow/red) | spec palette | ⚠️ **Partial** (add `data-theme="fitness-hub"` block) | `styles/theme.css`, new `fitness-hub.css` |

**Bottom line:** ~99 focused phases remain. Backend (user weight/membership fields + 6 new models + schema/migrations + routers + aggregation) → seed → API client → fitness-hub theme → layout/header → sidebar widgets → Row 1 weekly split → Row 2 heatmaps → Row 3 muscle grid → Row 4 expenses → Row 5 exercises → gamification polish → integration → verification.

---

## PART B — THE PHASES

### GROUP 1 — Backend Foundation: User Weight/Membership + Habit Fields, Schemas, Migrations (Phases 1–8)

#### Phase 1 — Add `current_weight`/`initial_weight`/`target_weight` to User
- `models/user.py`: `current_weight = Column(Float, nullable=True)`, `initial_weight = Column(Float, nullable=True)`, `target_weight = Column(Float, nullable=True)`
- `schemas/user.py`: add to `UserBase`/`UserUpdate`/`UserResponse`
- `database.py` `COLUMN_MIGRATIONS["users"]`: add the three `FLOAT` columns
- **Verify:** `from app.models import *` exposes fields; schema compiles

#### Phase 2 — Add `membership_status` + `next_payment_date` to User
- `models/user.py`: `membership_status = Column(String(50), default="Active")`, `next_payment_date = Column(Date, nullable=True)`
- `schemas/user.py`: add to Base/Update/Response
- `database.py`: `("membership_status", "VARCHAR(50) DEFAULT 'Active'")`, `("next_payment_date", "DATE")`
- **Verify:** fields present after migration; existing users default to Active

#### Phase 3 — Add `goal` + `heatmap_data` to Habit
- `models/habit.py`: `goal = Column(String(300), nullable=True)`, `heatmap_data = Column(Text, nullable=True)` (JSON array)
- `schemas/habit.py`: add to `HabitBase`/`HabitResponse`
- `database.py` `COLUMN_MIGRATIONS["habits"]`: `("goal", "VARCHAR(300)")`, `("heatmap_data", "TEXT")`
- **Verify:** habit schema compiles; existing habits tolerate null goal

#### Phase 4 — Register new user/habit fields in barrel imports
- `models/__init__.py` + `schemas/__init__.py`: confirm `User`, `Habit` exported (already; add if missing)
- **Verify:** `from app.models import *` / `from app.schemas import *` work

#### Phase 5 — Weight-goal progress helper
- `app/services/fitness_hub.py` (new) or inline: helper `weight_progress(user)` → `{initial, current, target, percent}`; percent `(current-initial)/(target-initial)*100` clamped 0–100
- **Verify:** unit-testable; correct 0–100 math

#### Phase 6 — PR progress helper
- Helper `pr_summary(db, user)` → list of `{exercise_name, current_weight, target_weight, percent}` from `PersonalRecord`
- **Verify:** returns correct per-lift progress

#### Phase 7 — Heatmap JSON serialization helper
- Helper `habit_heatmap_json(habit)` → parses `heatmap_data` or derives from `HabitLog`s (dates → completed)
- **Verify:** 7×7 grid shape (last 49 days) serialized correctly

#### Phase 8 — Migration safety check
- `database.py` `migrate_schema()`: run against current `productivity.db`
- **Verify:** no exception; `PRAGMA table_info(users/habits)` shows new columns

### GROUP 2 — Backend: Six New Fitness Models (Phases 9–16)

#### Phase 9 — `Exercise` model
- New `models/exercise.py` (or extend `models/fitness.py`): `Exercise(id, name, muscle_group_id FK, sets int, reps int, weight float, user_id FK)`
- **Verify:** imports cleanly

#### Phase 10 — `MuscleGroup` model
- `MuscleGroup(id, name, body_part VARCHAR(20) Upper/Lower, image_3d_url String(500), sort_order, user_id FK)`
- **Verify:** imports cleanly

#### Phase 11 — `WorkoutSplit` model
- `WorkoutSplit(id, day_of_week int 0–6, split_name VARCHAR(20) PUSH/PULL/LEG/…, exercise_list Text JSON, week_number int, user_id FK)`
- **Verify:** imports cleanly; day_of_week unique per week

#### Phase 12 — `Expense` model
- `Expense(id, title, cost Float, date Date, category VARCHAR(50) Supplement/Equipment/Gym, user_id FK)`
- **Verify:** imports cleanly

#### Phase 13 — `PersonalRecord` model
- `PersonalRecord(id, exercise_name String(200), current_weight Float, target_weight Float, unit String(20) default "kg", user_id FK)`
- **Verify:** imports cleanly

#### Phase 14 — `DietPlan` model
- `DietPlan(id, title String(100), is_active Boolean default False, sort_order, user_id FK)`
- **Verify:** imports cleanly

#### Phase 15 — Barrel registration
- `models/__init__.py`: export `Exercise, MuscleGroup, WorkoutSplit, Expense, PersonalRecord, DietPlan`
- **Verify:** all six importable via `from app.models import *`

#### Phase 16 — Model smoke check
- `python -c "from app.models import Exercise, MuscleGroup, WorkoutSplit, Expense, PersonalRecord, DietPlan"`
- **Verify:** no import errors; relationships resolve

### GROUP 3 — Backend: Schemas + Migrations for New Models (Phases 17–24)

#### Phase 17 — `schemas/fitness.py` Exercise schemas
- `ExerciseBase` (name, muscle_group_id, sets, reps, weight), `ExerciseCreate` (+user_id), `ExerciseResponse`
- **Verify:** schema compiles

#### Phase 18 — MuscleGroup + WorkoutSplit schemas
- `MuscleGroupBase/Create/Response`; `WorkoutSplitBase` (day_of_week, split_name, exercise_list, week_number), `Create`/`Response`
- **Verify:** both compile

#### Phase 19 — Expense + PersonalRecord schemas
- `ExpenseBase` (title, cost, date, category), `Create`/`Response`; `PersonalRecordBase` (exercise_name, current_weight, target_weight, unit), `Create`/`Response`
- **Verify:** both compile

#### Phase 20 — DietPlan schemas
- `DietPlanBase` (title, is_active, sort_order), `Create`/`Response`
- **Verify:** compiles

#### Phase 21 — `COLUMN_MIGRATIONS` entries for new tables
- `database.py`: add `exercises`, `muscle_groups`, `workout_splits`, `expenses`, `personal_records`, `diet_plans` entries (create-only; tables are new)
- **Verify:** migration runs; new tables created in `productivity.db`

#### Phase 22 — Schema barrel registration
- `schemas/__init__.py`: export all new schemas
- **Verify:** `from app.schemas import *` works

#### Phase 23 — Pydantic/FK type check
- Confirm `muscle_group_id` FK types align between `Exercise` and `MuscleGroup`
- **Verify:** no circular import; types consistent

#### Phase 24 — Migration + seed smoke test
- Run app startup; confirm tables exist; existing 158 tests still green
- **Verify:** clean boot

### GROUP 4 — Backend Routers (Phases 25–34)

#### Phase 25 — `routers/fitness.py` extend — exercise CRUD
- `GET/POST /exercises`, `PUT/DELETE /exercises/{id}`; filter by `muscle_group_id`
- **Verify:** returns 200; nested sets/reps/weight present

#### Phase 26 — Muscle-group CRUD
- `GET/POST /muscle-groups`, `PUT/DELETE /muscle-groups/{id}`
- **Verify:** 12 seeded groups listable

#### Phase 27 — `GET /muscle-groups/{id}/exercises`
- Nested list of exercises for a muscle group (Row 5 data source)
- **Verify:** returns 200 with exercise array

#### Phase 28 — Workout-split CRUD
- `GET/POST /workout-splits`, `PUT/DELETE /workout-splits/{id}`; `GET /workout-splits?week_number=1|2`
- **Verify:** week filter works; Mon–Sat rows present

#### Phase 29 — Expense CRUD + category breakdown
- `GET/POST /expenses`, `DELETE /expenses/{id}`; `GET /expenses/summary` → `{total, by_category: {Supplement, Equipment, Gym}}`
- **Verify:** summary math correct for seed

#### Phase 30 — Personal-record CRUD
- `GET/POST /personal-records`, `PUT/DELETE /personal-records/{id}`
- **Verify:** 200; progress computed on read

#### Phase 31 — Diet-plan CRUD
- `GET/POST /diet-plans`, `PUT/DELETE /diet-plans/{id}`; `GET /diet-plans/active`
- **Verify:** active plan returned

#### Phase 32 — Weight-goal endpoint
- `GET/PUT /users/{id}/weight-goal` → read/update `initial/current/target_weight`
- **Verify:** 200; progress bar payload matches Phase 5 helper

#### Phase 33 — Membership endpoint
- `GET /users/{id}/membership` → `{membership_status, next_payment_date, days_to_payment}`
- **Verify:** days-to-payment computed

#### Phase 34 — Register routers + app boot
- `main.py`: ensure `fitness.router` (and new routers if separated) included; app starts cleanly
- **Verify:** all new endpoints return 200 via `start.sh`-style smoke

### GROUP 5 — Backend: Aggregation Service + Seed (Phases 35–42)

#### Phase 35 — `services/fitness_hub.py` scaffold
- `get_fitness_hub_summary(db, user)` → `{weight_goal, pr_tracker, membership, diet_plans, expenses_summary}`
- **Verify:** returns single aggregated payload

#### Phase 36 — Weekly split aggregation
- Helper `weekly_split(db, week)` → ordered Mon–Sat `{day, split_name, exercises:[...]}`
- **Verify:** correct day ordering (Mon=0)

#### Phase 37 — Habit heatmap aggregation for the 4 spec habits
- Helper `spec_habits_heatmap(db)` → the 4 habits (Workout, 3000 Kcal, 4L water, Supplements) with `{goal, days_completed, percent, heatmap_7x7}`
- **Verify:** 7×7 grid + percent correct

#### Phase 38 — Muscle-group + exercise count aggregation
- Helper `muscle_group_overview(db)` → 12 groups with `{name, body_part, image_3d_url, exercise_count}`
- **Verify:** counts match seeded exercises

#### Phase 39 — `GET /fitness-hub/summary` endpoint
- New `routers/fitness_hub.py` (prefix `/api`, tags `["fitness-hub"]`); composes Phase 35 helpers
- **Verify:** returns 200 with full payload

#### Phase 40 — Register `fitness_hub` router
- `main.py`: `app.include_router(fitness_hub.router)`
- **Verify:** app boots; endpoint accessible

#### Phase 41 — Seed muscle groups (12)
- `seed/__init__.py`: `seed_muscle_groups` — Calves, Shoulders, Chest, Abs, Back, Lower Back, Triceps, Glutes, Hamstring, Quads, Biceps, Forearms (Upper/Lower + `image_3d_url` placeholder)
- **Verify:** 12 groups; idempotent

#### Phase 42 — Seed exercises + weekly split + expenses + PRs + diet plans
- Exercises with sets/reps/weight per muscle group; Mon–Sat PUSH/PULL/LEG splits; 4 spec expenses; bench/overhead PRs; 4 diet phases
- **Verify:** all lists populated; second seed run adds nothing

### GROUP 6 — Frontend API Client + Types (Phases 43–49)

#### Phase 43 — Extend `User` type in `api.ts`
- Add `current_weight`, `initial_weight`, `target_weight`, `membership_status`, `next_payment_date`
- **Verify:** `tsc -b` clean

#### Phase 44 — Extend `Habit` type
- Add `goal: string | null`, `heatmap_data: string | null`
- **Verify:** `tsc -b` clean

#### Phase 45 — New fitness-hub types
- `Exercise`, `MuscleGroup`, `WorkoutSplit`, `Expense`, `PersonalRecord`, `DietPlan`, `WeightGoal`, `Membership`, `FitnessHubSummary`, `ExpenseSummary`
- **Verify:** strict TS passes

#### Phase 46 — `endpoints.fitnessHub` block
- `summary()`, `exercises()`, `muscleGroups()`, `workoutSplits(week)`, `expenses()`+`summary()`, `personalRecords()`, `dietPlans()`, `weightGoal(id)`, `membership(id)`
- **Verify:** each maps to Phase 25–40 routes

#### Phase 47 — Exercise/expense/muscle create helpers
- POST bodies for the Quick-Action add links
- **Verify:** TS signatures align

#### Phase 48 — Habit heatmap goal helper
- `endpoints.habits.goal(habitId)` read/write the new `goal` field
- **Verify:** types align

#### Phase 49 — API client smoke check
- `npm run tsc`; ensure no unused imports
- **Verify:** build clean

### GROUP 7 — Theme & Styling (Phases 50–56)

#### Phase 50 — `data-theme="fitness-hub"` token block
- `styles/theme.css`: `--bg-primary:#0f1012`, `--bg-card:#1c1e21`, `--text-primary:#f8f9fa`, `--border:#282a2d`, `--blue:#3b82f6`, `--green:#22c55e`, `--yellow:#eab308`, `--red:#ef4444`, `--success:#10b981`, `--radius:10px`, `--card-shadow:0 4px 6px rgba(0,0,0,.5)`
- **Verify:** theme-switcher lists the new option; tokens resolve

#### Phase 51 — `styles/fitness-hub.css` scaffold
- Scoped `.fh-*` file (all colors from tokens)
- **Verify:** CSS loads via `main.tsx`

#### Phase 52 — Sidebar module styles
- `.fh-status-card`, `.fh-widget`, `.fh-weight-bar`, `.fh-nav-link` with `#1c1e21` bg, `#282a2d` border, 10px radius
- **Verify:** spec radius/shadow/spacing applied

#### Phase 53 — Row card styles
- `.fh-row`, `.fh-day-card`, `.fh-expense-card`, `.fh-muscle-card`, `.fh-exercise-card` hover `scale(1.02)`
- **Verify:** hover effects present

#### Phase 54 — Heatmap + muscle 3D styles
- `.fh-heat-cell` intensity colors (blue/green/yellow/orange), `.fh-muscle-svg` neon highlight
- **Verify:** 7×7 grid + neon accents render

#### Phase 55 — Expense donut + empty-state styles
- `.fh-donut` (conic-gradient), `.fh-empty` translucent icon
- **Verify:** donut renders; empty states show icon

#### Phase 56 — Animation keyframes
- `@keyframes fh-pop` (mark-complete), `fh-pulse` (active diet plan), `fh-glow` (hover)
- **Verify:** keyframes wired to card classes

### GROUP 8 — Layout & Header (Phases 57–63)

#### Phase 57 — `FitnessHubDashboard` page shell
- New `pages/FitnessHubDashboard.tsx` with `.fh-layout` grid (300px sidebar + main 5-row stack)
- **Verify:** routes render with new grid

#### Phase 58 — Register route + nav link
- `App.tsx`: `<Route path="/fitness-hub" ...>`; `NavLinks.tsx`/`Sidebar.tsx`: add "Fitness Hub" entry
- **Verify:** nav navigates to the page

#### Phase 59 — Header (28px title)
- Reuse/extend `Header` with larger "Fitness-Hub" title (spec ~28px)
- **Verify:** title renders full-width top bar

#### Phase 60 — Row containers (5 rows)
- `.fh-row` wrappers + section headers for Weekly-Split, Habit-Tracking, Muscle-Group, Expenses, Exercises
- **Verify:** 5 distinct vertical bands

#### Phase 61 — Responsive behavior
- Media queries collapse sidebar → top; rows stack below 1024px
- **Verify:** desktop-first + narrow fallback

#### Phase 62 — Loading/empty states
- Skeleton shimmer per row while fetching; unified translucent-icon empty states
- **Verify:** skeleton + icon empties render

#### Phase 63 — Page composition
- Compose Header + Sidebar + 5 rows in one scrollable stack; 24px section padding, 16–20px card padding, 16–24px gaps
- **Verify:** layout matches spec hierarchy

### GROUP 9 — Sidebar Widgets (Phases 64–72)

#### Phase 64 — `FhQuickActions`
- New widget: 7 links (Add Exercise, Add New Expense, Add Muscle Group, Add New Habit, Habit Grid Design, Add New Weight Goal, Add New Membership) each with + icon → relevant create modal/route
- **Verify:** links wired

#### Phase 65 — `FhNavigation`
- New widget: 11 nav links (Membership, Muscle Groups, Exercises, Workout Plan, Habit Grid Design, Weight Goals, PR Tracker, Resources, Archive, Physique Check In, Backend)
- **Verify:** each navigates (routes or anchors)

#### Phase 66 — `FhWeightGoal`
- Weight Goal card: initial → current → target + progress bar (0% default)
- **Verify:** reads `/users/{id}/weight-goal`; bar math correct

#### Phase 67 — `FhPRTracker`
- PR list: "Current Bench Press: 60kg", "Target: 100kg" + progress
- **Verify:** renders `/personal-records` with percent

#### Phase 68 — `FhMembership`
- Gym info, "Active" badge, "Next Payment is in X days"
- **Verify:** reads membership endpoint; days computed

#### Phase 69 — `FhDietPlan`
- Diet phase list with active highlight (Diet / Bulking / Cutting / Maintenance)
- **Verify:** active plan highlighted

#### Phase 70 — Sidebar assembly + data hook
- `hooks/useFitnessHubData.ts`: parallel fetch of weight, PRs, membership, diet plans, expenses
- **Verify:** single mount loads all sidebar modules

#### Phase 71 — Quick-Action create modals
- Reuse/extend a generic modal for Exercise / Expense / Muscle Group / Weight Goal / Membership creation
- **Verify:** POST hits correct endpoints; UI refreshes

#### Phase 72 — Sidebar navigation + active states
- Active-link underline/highlight for `FhNavigation` based on current route
- **Verify:** active state tracks route

### GROUP 10 — Row 1: Weekly Split (Phases 73–79)

#### Phase 73 — `FhWeeklySplitTabs`
- Tabs: Week 1 / Week 2 / Customization (reuse `RpgTabs` pattern)
- **Verify:** switching fetches `week_number=1|2`

#### Phase 74 — `FhWeeklySplitDays`
- Horizontal scrollable row of Mon–Sat day cards (PUSH / PULL / LEG)
- **Verify:** 6 day cards render from `/workout-splits`

#### Phase 75 — Day-card exercise list
- Each card: split header + bulleted exercise list (from `exercise_list` JSON)
- **Verify:** exercises listed per day

#### Phase 76 — Customization tab
- Edit active week: reorder/add days; persist via PUT
- **Verify:** changes persist after reload

#### Phase 77 — "Log Today's Workout" button
- Large CTA at top of Row 1 → opens workout log modal (type, duration, calories)
- **Verify:** POST `/workouts`; list refreshes

#### Phase 78 — Workout log modal
- Form fields + validation; success toast
- **Verify:** toast on save; row updates

#### Phase 79 — Weekly-split completion state
- "In Progress" badge on days logged today; done-checkmark
- **Verify:** day card reflects logged workout

### GROUP 11 — Row 2: Habit-Tracking Heatmaps (Phases 80–86)

#### Phase 80 — `FhHabitHeatmaps`
- 4-column grid of heatmap cards (Workout, 3000 Kcal Diet, Drink 4L water, Take all supplements)
- **Verify:** 4 seeded spec habits render

#### Phase 81 — 7×7 heatmap reuse
- Reuse `HeatmapGrid` (`columns=7`) for each habit from `/habits/{id}/heatmap`
- **Verify:** grid fills with intensity colors

#### Phase 82 — Goal indicator + days completed + %
- Card header: goal text, "X days completed", completion %
- **Verify:** numbers match `/habits/{id}/heatmap`

#### Phase 83 — Mark-as-completed button
- "Mark as completed" → `logToday` → green `fh-pop` + streak bump
- **Verify:** cell fills; streak increments

#### Phase 84 — Habit goal editing
- Small edit affordance on `goal` field → PUT `habits/{id}`
- **Verify:** goal persists

#### Phase 85 — Weak-spot highlighting
- Highlight weekend columns with low fill (spec: spot weak spots)
- **Verify:** visual emphasis on gaps

#### Phase 86 — Heatmap empty state
- Translucent icon + "No data yet" when no logs
- **Verify:** renders

### GROUP 12 — Row 3: Muscle-Group 3D Grid (Phases 87–91)

#### Phase 87 — `FhMuscleGroupGrid`
- 2-row horizontal grid of 12 muscle cards
- **Verify:** 12 seeded groups render

#### Phase 88 — `FhMuscleGroupCard`
- 3D mannequin SVG with neon-highlighted muscle region; title; Upper/Lower badge; "Total Exercises: X"
- **Verify:** card visual + count correct

#### Phase 89 — Muscle SVG component
- `components/fitnesshub/MuscleDiagram.tsx`: inline SVG front/back mannequin, highlight by muscle key, fallback to colored placeholder
- **Verify:** highlights render; graceful fallback

#### Phase 90 — Interactive expand
- Click muscle card → expands exercise list for that group (Phase 27 endpoint)
- **Verify:** click toggles nested exercises

#### Phase 91 — Muscle hover glow
- `.fh-muscle-card:hover` neon glow matching body part
- **Verify:** hover effect present

### GROUP 13 — Row 4: Expenses + Row 5: Exercises (Phases 92–97)

#### Phase 92 — `FhExpenseCards`
- Horizontal row of expense cards (title, cost, date, Supplement/Equipment tag)
- **Verify:** 4 spec expenses render

#### Phase 93 — Expense donut chart
- `.fh-donut` conic-gradient breakdown: Supplements vs Equipment vs Gym (% of spend)
- **Verify:** donut segments match `/expenses/summary`

#### Phase 94 — `FhExerciseTabs`
- Tabs: "By Muscle group" / "All Exercises"
- **Verify:** tab switches data source

#### Phase 95 — `FhExerciseNestedLists`
- 2×2 / 3-column grid of muscle cards; each lists exercises with sets ("Set 1: 1kg", "Set 2: 1kg")
- **Verify:** nested Muscle → Exercise → Set renders in grid

#### Phase 96 — Expense/empty-state polish
- Translucent icon empty state for no expenses
- **Verify:** renders

#### Phase 97 — "Log Today's Workout" + exercise grid final pass
- Polish CTA + 3-column exercise layout; confirm no vertical-stack fallback
- **Verify:** spec-consistent layout

### GROUP 14 — Integration & Verification (Phases 98–99)

#### Phase 98 — Backend test suite
- Add/extend `test_fitness.py` + `test_habits.py` for: weight-goal, membership, exercise/muscle/expense/PR/diet CRUD, weekly split aggregation, expense summary, habit goal field
- **Verify:** full suite green (target ≥ 165+ tests)

#### Phase 99 — Frontend build + theme integration + final checklist
- `tsc -b` strict + `npm run build`; theme-switcher lists `fitness-hub`; cross-links from quest-centre/vault to fitness-hub work; manual walkthrough (header → sidebar widgets → 5 rows → heatmaps → muscle grid → expenses donut → exercise lists → empty states)
- **Verify:** build clean; no `test.skip`, no stubs, no TODO placeholders; all 99 phases accounted for
