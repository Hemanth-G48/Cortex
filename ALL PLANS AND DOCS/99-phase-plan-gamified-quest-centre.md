# Gamified Quest Centre — 99-Phase Integration Plan (Student OS)

**Goal:** Add every feature from the `gamified quest centre.odt` spec to the existing Student Life OS app, integrating the new Quest-Centre dashboard alongside the current RPG/Quest/Mission/Reward system without breaking the 162 passing backend tests, the strict TS build, or the existing Student OS / RPG / Vault / Life Planner themes.

**Baseline (verified 2026-08-01):** Backend 162 tests pass; frontend `tsc -b` + `npm run build` clean. Existing RPG module already has: `Quest`+`QuestTask` models/router, `Mission`+`MissionTask` models/router, `Reward` model/router (claim + XP check), `Character` model/router (XP + level-up), `LifeArea` model/router, `daily_quests` auto-seed router, RPG theme (`rpg-theme.css`, orange/green), `QuestCenter`/`MissionCenter`/`RewardCenter`/`WeeklyCalendar` components, `RPGDashboard` page, and a unified `data-theme` token system.

---

## PART A — GAP ANALYSIS (spec vs. current codebase)

| Spec Feature | Spec Requirement | Status | Where |
|---|---|---|---|
| Sidebar Status-Window | Character card: wizard avatar, greeting, level, Total XP, XP-left, "Today's Task" checklist | ❌ **Missing as widget** | — |
| Progress Bars (macro) | Year / Month / Week / Day stacked bars | ⚠️ **Partial** (3 bars, no Day) | `components/widgets/ProgressBars.tsx` |
| Quick-Action list | "Add New Quest / Mission / Life Area / Reward" | ⚠️ **Partial** (RPG quick-action grid, no create-modal links) | `RPGDashboard.tsx` |
| Priority-Window | High / Medium / Low folder cards + Est. duration + task link | ❌ **Missing** | — |
| Row 1 — Pomodoro | 25:00 timer, Short/Long break toggles, Start, settings gear, progress ring | ⚠️ **Exists as page** (`/pomodoro` + `ProgressRing`) | `pages/Pomodoro.tsx` |
| Row 1 — Life-Areas grid | 4 cards, pixel-art backdrop, "Complete in X days", status badge | ⚠️ **Partial** (no target_days/status on model; no pixel-art backdrops) | `LifeArea` model, `LifeAreasGrid.tsx` |
| Row 2 — Quest-Center | Tabs Today/In Progress/Overdue/Inbox; cards with category/priority/status + Done | ✅ **Done** | `QuestCenter.tsx`, `QuestCard.tsx` |
| Row 3 — Mission-Center | Tabs All/In Progress/Not Started/Completed; larger cards | ✅ **Done** | `MissionCenter.tsx`, `MissionCard.tsx` |
| Row 4 — Reward-Center | Tabs Rewards/Claimed; XP cost, "Not available" red, Claim | ⚠️ **Partial** (no unlock-glow animation, no "Not available" red state) | `RewardCenter.tsx`, `RewardCard.tsx` |
| Row 5 — Quests Calendar | Weekly timeline, tasks plotted on dates, Week/Month tabs, "Open in Calendar" | ⚠️ **Partial** (week view exists; no Month tab, no open-link) | `WeeklyCalendar.tsx` |
| User/profile: `avatar_class`, `current_streak` | spec data model | ❌ **Missing** | `models/user.py` |
| LifeArea: `target_days`, `status` | spec data model ("Complete in X days", "In Progress") | ❌ **Missing** | `models/life_area.py` |
| Mission: `linked_quests` | spec data model (mission → quests) | ❌ **Missing** | `models/mission.py` |
| Progress_Tracking (Day/Week/Month/Year %) | spec data model | ⚠️ **Client-computed**, no backend endpoint | — |
| Done-button green flash | UX improvement | ❌ **Missing** | `QuestCard.tsx`/`MissionCard.tsx` |
| Reward unlock glow/pulse | UX improvement | ❌ **Missing** | `RewardCard.tsx` |
| Calendar daily/weekly view toggle | UX improvement | ❌ **Missing** | `WeeklyCalendar.tsx` |
| Pomodoro progress ring | UX improvement | ✅ **Done** (reuse) | `components/pomodoro/ProgressRing.tsx` |
| Empty-state pixel-art placeholders | UX improvement | ❌ **Missing** | create-form empty states |
| Gold accent theme (`#fbbf24`) | spec palette | ⚠️ **Partial** (RPG theme is orange/green; add `quest-centre` gold block) | `styles/theme.css` |

**Bottom line:** ~99 focused phases remain. Backend foundation (user/life-area/mission field gaps + priority/status/calendar aggregation endpoints) → seed → API client → quest-centre theme → sidebar widgets → main rows → gamification polish → integration → verification.

---

## PART B — THE PHASES

### GROUP 1 — Backend Foundation: Models, Schemas, Migrations (Phases 1–8)

#### Phase 1 — Add `avatar_class` + `current_streak` to User
- `models/user.py`: `avatar_class = Column(String(50), default="Wizard")`, `current_streak = Column(Integer, default=0)`
- `schemas/user.py`: add to `UserBase`/`UserUpdate`/`UserResponse`
- **Verify:** `from app.models import *` exposes both fields; schema compiles

#### Phase 2 — Add `target_days` + `status` to LifeArea
- `models/life_area.py`: `target_days = Column(Integer, nullable=True)`, `status = Column(String(50), default="In progress")`
- `schemas/life_area.py`: add to Base/Create/Update/Response
- `database.py` `COLUMN_MIGRATIONS["life_areas"]`: add both as `VARCHAR`/`INTEGER`
- **Verify:** existing areas untouched; new columns present

#### Phase 3 — Add `linked_quests` to Mission
- `models/mission.py`: `linked_quests = Column(String(500), nullable=True)` (comma-separated quest ids, or JSON via `Text`)
- `schemas/mission.py`: add to `MissionBase`/`MissionUpdate`/`MissionResponse`
- `database.py` `COLUMN_MIGRATIONS["missions"]`: add column
- **Verify:** mission stores + returns linked quests

#### Phase 4 — Register new fields in barrel imports
- `models/__init__.py` + `schemas/__init__.py`: ensure `User`, `LifeArea`, `Mission` already exported (add if missing)
- **Verify:** `from app.models import *` and `from app.schemas import *` work

#### Phase 5 — Priority aggregation query helper
- `app/services/` or inline: helper `group_by_priority(db)` → `{High: [...], Medium: [...], Low: [...]}` from `Quest` + `Task` with `time_estimate`
- **Verify:** unit-testable helper returns 3 buckets

#### Phase 6 — Status-window aggregation helper
- Helper `status_window_data(db)` → `{character: {...}, xp_to_next, today_tasks: [...]}` (completed quests today, due today)
- **Verify:** returns correct XP-left math `1000 - (xp % 1000)`

#### Phase 7 — Progress-Tracking computation endpoint helper
- Helper `progress_report(db)` → `{year, month, week, day}` percentages (calendar-based like `ProgressBars.tsx`)
- **Verify:** percentages 0–100 correct for current date

#### Phase 8 — Calendar by-date quest aggregation helper
- Helper `quests_by_date(db)` → list of `{date, quests:[...]}` from `Quest.due_date`
- **Verify:** groups quests correctly; null-due excluded

### GROUP 2 — Backend Routers (Phases 9–20)

#### Phase 9 — `routers/quest_centre.py` scaffold
- New router `prefix="/api"`, `tags=["quest-centre"]`; import all helpers
- **Verify:** router imports cleanly

#### Phase 10 — `GET /api/quest-centre/status-window`
- Returns `{character, xp_to_next, today_tasks}` from Phase 6 helper
- **Verify:** returns 200 with seeded character data

#### Phase 11 — `GET /api/quest-centre/progress`
- Returns `{year, month, week, day}` from Phase 7 helper
- **Verify:** returns 200; values match calendar

#### Phase 12 — `GET /api/quest-centre/priority-window`
- Returns `{high, medium, low}` buckets (Phase 5 helper) — each item with `title`, `time_estimate`, `id`, `kind` (`quest`|`task`)
- **Verify:** 3 buckets populated from seed

#### Phase 13 — `GET /api/quest-centre/quick-actions`
- Returns available create targets + URLs (frontend can hardcode; endpoint optional but spec-consistent)
- **Verify:** returns 200

#### Phase 14 — `GET /api/quest-centre/life-areas`
- Returns life areas incl. `target_days`, `status`, computed "Complete in X days"
- **Verify:** seeded areas include new fields

#### Phase 15 — `GET /api/quest-centre/calendar`
- Returns `quests_by_date` (Phase 8) merged with `ScheduleEvent`s for week/month
- **Verify:** quests plotted on correct dates

#### Phase 16 — Register `quest_centre` router
- `main.py`: `app.include_router(quest_centre.router)`
- **Verify:** app starts cleanly; all 6 new endpoints accessible

#### Phase 17 — User streak + avatar endpoint
- Extend `/api/users/me` or new `GET /api/users/{id}/gamification` → `{avatar_class, current_streak, total_xp, current_level}`
- **Verify:** returns updated user fields

#### Phase 18 — Streak increment on quest completion
- `routers/quests.py` `complete_quest`: on completion, increment `user.current_streak`; reset if gap >1 day
- **Verify:** completing a quest bumps streak; tests stay green

#### Phase 19 — LifeArea status flip on completion
- `routers/life_areas.py`: `POST /life-areas/{id}/complete` sets `status="Completed"`, keeps progress at 100
- **Verify:** endpoint flips status; no dupes

#### Phase 20 — Bonus: mission linked-quest resolution
- `routers/missions.py`: `GET /missions/{id}/linked` returns linked quest objects from `linked_quests`
- **Verify:** returns parsed quests

### GROUP 3 — Seed Data (Phase 21–24)

#### Phase 21 — Seed user gamification fields
- `app/seed/__init__.py`: set `avatar_class="Wizard"`, `current_streak` (e.g. 3) on seeded user (append-only)
- **Verify:** fresh DB has fields; no duplicate on re-run

#### Phase 22 — Seed life-area target_days/status
- `seed_life_areas`: add `target_days` (e.g. 30) + `status="In progress"` for 4 areas (Work, Fitness, Self Development, Health)
- **Verify:** fresh DB shows 4 areas with fields

#### Phase 23 — Seed mission linked_quests
- `seed_missions`: attach existing quest ids to missions (`linked_quests`)
- **Verify:** missions reference seeded quests

#### Phase 24 — Seed idempotency re-check
- Confirm all new seeds are append-only/guarded by existence checks
- **Verify:** re-running seed produces zero duplicates

### GROUP 4 — Frontend API Client & Types (Phases 25–30)

#### Phase 25 — Types: gamification + quest-centre
- `types/index.ts` or `services/api.ts`: `GamificationProfile`, `StatusWindow`, `ProgressReport`, `PriorityBucket`, `CalendarQuest`, `LifeArea` (add `target_days`,`status`), `Mission` (add `linked_quests`), `User` (add `avatar_class`,`current_streak`)
- **Verify:** strict `tsc -b` passes

#### Phase 26 — api.ts: questCentre group
- `services/api.ts`: `questCentre = { statusWindow, progress, priorityWindow, quickActions, lifeAreas, calendar }`
- **Verify:** typed methods compile

#### Phase 27 — api.ts: gamification + life-area complete
- Add `users.gamification(userId)`, `lifeAreas.complete(id)`, `missions.linked(id)`
- **Verify:** typed methods compile

#### Phase 28 — Types export through index
- Ensure `frontend/src/services/api.ts` exports all new types (components import from one place)
- **Verify:** no dangling imports

#### Phase 29 — Data hook `useQuestCentreData`
- `hooks/useQuestCentreData.ts`: fetches status-window + progress + priority-window + calendar in parallel, exposes `{loading, errors, refresh, data}`
- **Verify:** single hook feeds dashboard

#### Phase 30 — Manual QA of API client
- Point app at dev server; confirm each new endpoint returns shaped data in browser console
- **Verify:** shapes match TypeScript types

### GROUP 5 — Quest-Centre Theme (Phases 31–38)

#### Phase 31 — Gold token block
- `styles/theme.css`: `[data-theme="quest-centre"]` overriding `--qc-*` tokens (bg `#121212`, card `#1e1e1e`, accent gold `#fbbf24`, success `#22c55e`, progress `#3b82f6`, locked `#ef4444`)
- **Verify:** tokens resolve under `data-theme="quest-centre"`

#### Phase 32 — Theme switcher entry
- `components/shared/ThemeSwitcher.tsx`: add "Quest Centre" option
- **Verify:** dropdown lists 5 themes

#### Phase 33 — Apply quest-centre theme to dashboard
- `pages/QuestCentreDashboard.tsx` wrapper sets `data-theme="quest-centre"` on mount
- **Verify:** page renders under gold palette

#### Phase 34 — Scoped component classes
- Create `quest-centre.css` (or reuse theme.css) for `.qc-*` scoped classes; no hardcoded colors in components
- **Verify:** styles apply; RPG theme untouched

#### Phase 35 — Pixel-art font + accents
- Reuse `Press Start 2P` import already in `rpg-theme.css` for headers on quest-centre
- **Verify:** pixel headers render

#### Phase 36 — Card radius/shadow tokens
- Match spec: radius 8px, shadow `0 4px 6px rgba(0,0,0,0.4)`, border `1px solid #282a2d`
- **Verify:** cards match spec dimensions

#### Phase 37 — Responsive tokens
- Quest-centre grid collapses on tablet/mobile (4-col → 2-col → 1-col)
- **Verify:** layout adapts at breakpoints

#### Phase 38 — Theme regression
- Confirm Student OS/RPG/Vault/Life Planner themes still render correctly under their `data-theme`
- **Verify:** no theme collision; all pages unchanged

### GROUP 6 — Sidebar Widgets: Status-Window (Phases 39–45)

#### Phase 39 — StatusWindowWidget component
- `components/questcentre/StatusWindowWidget.tsx`: wizard avatar (emoji/`avatar_class`), greeting, level badge, Total XP, "XP left to next level", today-task checklist
- **Verify:** renders seeded character data

#### Phase 40 — XP-left progress bar
- In widget: `xp % 1000` fill + `1000 - xp%1000` remaining label
- **Verify:** numbers correct vs. character

#### Phase 41 — Today's Task checklist
- Checkbox list from `statusWindow.today_tasks`; toggling calls complete endpoint
- **Verify:** checks persist + XP reflects

#### Phase 42 — ProgressBars: add Day bar + quest-centre variant
- `components/questcentre/ProgressBarsQC.tsx`: Year/Month/Week/Day from `/quest-centre/progress`
- **Verify:** 4 bars render; Day matches calendar

#### Phase 43 — QuickActionsQC component
- `components/questcentre/QuickActionsQC.tsx`: "Add New Quest/Mission/Life Area/Reward" buttons opening existing create modals
- **Verify:** each button navigates/opens correct modal

#### Phase 44 — PriorityWindow component
- `components/questcentre/PriorityWindow.tsx`: High/Medium/Low folder cards, each with Est. duration + task link
- **Verify:** 3 cards populate from `/priority-window`

#### Phase 45 — Sidebar assembly for quest-centre
- Compose StatusWindow + ProgressBars + QuickActions + PriorityWindow into the quest-centre sidebar
- **Verify:** sidebar matches spec ordering

### GROUP 7 — Main Row 1: Pomodoro & Life-Areas (Phases 46–55)

#### Phase 46 — PomodoroWidget (compact)
- `components/questcentre/PomodoroWidget.tsx`: 25:00 timer, Short/Long break toggles, Start button, settings gear → reuse `usePomodoro` + `ProgressRing`
- **Verify:** timer starts/pauses; ring shrinks

#### Phase 47 — Pomodoro progress ring
- Wrap timer value in existing `ProgressRing`; ring fill = elapsed/25:00
- **Verify:** visual countdown works

#### Phase 48 — Pomodoro settings modal
- Reuse `SettingsModal` (durations) inside widget
- **Verify:** duration changes persist

#### Phase 49 — LifeAreasGridQC
- `components/questcentre/LifeAreasGridQC.tsx`: 4 cards (Work, Fitness, Self Development, Health) with pixel-art backdrop, title, "Complete in X days", status badge
- **Verify:** 4 cards render from `/life-areas`

#### Phase 50 — "Complete in X days" computed
- Card subtitle = `target_days - days_since_creation` (or configurable); show "Complete in: N days"
- **Verify:** label correct

#### Phase 51 — Pixel-art backdrop
- `background-image` from `image_url` or CSS gradient + pixel overlay; emoji fallback
- **Verify:** backdrops render without breaking layout

#### Phase 52 — Status badge
- `status` chip: green "In Progress" / grey "Completed"
- **Verify:** badge reflects seeded status

#### Phase 53 — Mark-complete action on life-area card
- "Complete" button → `lifeAreas.complete(id)` → flips status + green flash
- **Verify:** status updates + persists

#### Phase 54 — Row 1 layout container
- `2-col split` (left timer, right grid) at top of dashboard
- **Verify:** matches spec Row 1

#### Phase 55 — Row 1 empty states
- Pixel-art placeholder when no life areas (glowing plus icon)
- **Verify:** inviting empty state renders

### GROUP 8 — Quest / Mission / Reward Center Polish (Phases 56–67)

#### Phase 56 — Done-button green flash (quests)
- `QuestCard.tsx`: on Complete click, brief bright-green flash/animation before state update
- **Verify:** tactile feedback visible

#### Phase 57 — Done-button green flash (missions)
- `MissionCard.tsx`: same flash behavior
- **Verify:** feedback visible

#### Phase 58 — QuestCard spec tags audit
- Ensure category / priority / status tags + "Done" button all present (already largely done) — verify only
- **Verify:** card matches spec chips

#### Phase 59 — MissionCard spec tags audit
- Category + priority + "Done" for missions; add `linked_quests` chip
- **Verify:** chips render

#### Phase 60 — RewardCard "Not available" state
- `RewardCard.tsx`: when XP insufficient or claimed, red "Not available" text + faded button
- **Verify:** red locked state shows

#### Phase 61 — Reward unlock glow
- When XP ≥ cost and not claimed: gold glow/pulse animation on "Claim Reward"
- **Verify:** unlock animation triggers

#### Phase 62 — Reward claim feedback
- On claim: success green flash + toast; deduct XP shown
- **Verify:** claim persists + XP deducted

#### Phase 63 — QuestCentre filter tab counts
- `QuestCenter` reuse: tabs Today/In Progress/Overdue/Inbox with live counts
- **Verify:** counts match data

#### Phase 64 — MissionCentre tabs
- All / In Progress / Not Started / Completed tabs already exist — wire to quest-centre data hook
- **Verify:** tabs filter correctly

#### Phase 65 — RewardCentre tabs
- Rewards / Claimed tabs already exist — ensure "Claimed" shows claimed_date + used XP
- **Verify:** claimed list accurate

#### Phase 66 — Empty-state pixel-art for centers
- Add glowing-plus / parchment placeholders when a center is empty
- **Verify:** empty centers invite creation

#### Phase 67 — Row 2–4 layout containers
- Quest / Mission / Reward centers rendered as three horizontal rows
- **Verify:** rows match spec order

### GROUP 9 — Quests Calendar (Phases 68–75)

#### Phase 68 — Weekly view (existing)
- Reuse `WeeklyCalendar.tsx` in quest-centre; verify quests plotted on dates
- **Verify:** week timeline renders

#### Phase 69 — Month view toggle
- Add `MonthGrid` view: month grid, quest dots on days with due quests
- **Verify:** month grid renders + dots correct

#### Phase 70 — Week/Month tab bar
- "Week" / "Month" tabs switch between the two views
- **Verify:** toggle works without reload

#### Phase 71 — "Open in Calendar" link
- Button opens `/schedule` (or `/calendar`) full page
- **Verify:** navigation works

#### Phase 72 — Quest plotting on week rows
- Ensure `quests_by_date` merges with schedule events in the week rows
- **Verify:** quests + events coexist per day

#### Phase 73 — Daily view resolution (UX)
- Allow clicking a date to expand daily detail (text resize toggle)
- **Verify:** readability improved

#### Phase 74 — Calendar responsive
- Collapses columns on tablet; scrollable row on mobile
- **Verify:** adapts at breakpoints

#### Phase 75 — Calendar empty state
- Pixel-art "no quests scheduled" placeholder
- **Verify:** empty state renders

### GROUP 10 — Gamification Polish (Phases 76–86)

#### Phase 76 — Level-up toast
- On level change (from any complete/claim), fire RPG-styled toast "Level Up!" with gold icon
- **Verify:** level-up triggers toast

#### Phase 77 — XP gained toasts
- "Quest Complete! +XP" / "Mission Complete! +XP" toasts wired on completions
- **Verify:** every completion gives feedback

#### Phase 78 — Reward unlocked toast
- When XP crosses a reward threshold, "Reward Unlocked!" toast
- **Verify:** threshold crossing detected

#### Phase 79 — Streak display in Status-Window
- Show `current_streak` flame badge (🔥 N) in the status widget
- **Verify:** streak renders from user

#### Phase 80 — Rewards loop incentive
- Progress toward next affordable reward shown near reward center
- **Verify:** "X XP to unlock" hint appears

#### Phase 81 — Pixel-art micro-interactions
- Hover glow on quick-add buttons (≤200ms transitions)
- **Verify:** hover polish present

#### Phase 82 — Reduced-motion support
- `prefers-reduced-motion` disables flash/pulse animations
- **Verify:** a11y motion preference honored

#### Phase 83 — 44px touch targets
- Matrix/toggle/claim buttons ≥44px hit area
- **Verify:** touch targets pass

#### Phase 84 — aria-labels on interactive widgets
- Timer, priority cards, calendar tabs, quick actions labeled
- **Verify:** keyboard-only usage works

#### Phase 85 — Focus-visible styles
- Visible focus rings on all new interactive elements
- **Verify:** tab through page shows focus

#### Phase 86 — Color-contrast audit
- Gold on dark + status colors meet contrast (text-muted `#9ca3af` on `#1e1e1e`)
- **Verify:** contrast passes

### GROUP 11 — Integration (Phases 87–92)

#### Phase 87 — QuestCentreDashboard page assembly
- `pages/QuestCentreDashboard.tsx`: sidebar (G6) + Row 1 (G7) + Rows 2–4 (G8) + Calendar (G9); one data hook
- **Verify:** full page renders all sections

#### Phase 88 — Route + nav registration
- `App.tsx`: `/quest-centre` route; sidebar/nav link added
- **Verify:** route renders; nav active state

#### Phase 89 — Link from RPG dashboard
- Add "Quest Centre" button/link on `RPGDashboard`
- **Verify:** cross-navigation works

#### Phase 90 — Toasts on all quest-centre mutations
- `useToast()` on complete/claim/create/update
- **Verify:** every mutation gives feedback

#### Phase 91 — Edit pencils + pre-filled modals
- Quest/Mission/Reward/Life-Area edits open pre-filled forms
- **Verify:** edits persist

#### Phase 92 — Responsive + a11y final pass on dashboard
- 4-col → 1-col collapse; reduced-motion; focus rings
- **Verify:** mobile + keyboard usable

### GROUP 12 — Verification, Docs & Acceptance (Phases 93–99)

#### Phase 93 — Backend tests: quest_centre endpoints
- `tests/test_quest_centre.py`: status-window, progress, priority-window, life-areas, calendar, gamification
- **Verify:** new tests pass; full suite (162 + new) green

#### Phase 94 — Backend tests: streak + life-area complete + linked
- Tests for streak increment, life-area status flip, mission linked resolution
- **Verify:** behavior covered

#### Phase 95 — Frontend typecheck + build
- `tsc -b` strict + `npm run build` + `vitest run`
- **Verify:** build clean; no new errors

#### Phase 96 — Frontend component tests
- StatusWindow, PriorityWindow, PomodoroWidget, Calendar toggle render tests
- **Verify:** vitest green

#### Phase 97 — Full-stack smoke test (fresh DB)
- Fresh SQLite → uvicorn → all new endpoints return correct data; `/quest-centre` renders
- **Verify:** end-to-end from clean start

#### Phase 98 — Regression on existing features
- Student OS / RPG / Vault / Life Planner pages + 162 tests unaffected
- **Verify:** zero broken features

#### Phase 99 — Docs + acceptance gate
- Update `frontend/README.md` (route, endpoints, components, theme); mark plan complete
- **Verify:** all gates pass; every quest-centre spec feature present

---

## PART C — FEATURE PRESERVATION

| Existing Feature | Preserved By |
|---|---|
| Student OS dashboard + 19 pages | Phases 92, 98 |
| RPG dashboard + quests/missions/rewards | Phases 56–67, 98 (reuse) |
| Vault + Life Planner dashboards | Phases 38, 98 |
| 162 backend tests | Phases 93–94, 98 |
| RPG/Vault/Life-planner/pixel CSS | Phases 34, 38 (scoped) |
| Toast system, responsive CSS, a11y | Phases 77–86 (reused) |
| Seed idempotency (append-only) | Phase 24 |

## PART D — DEPENDENCY ORDER

```
Group 1 (Models) → Group 2 (Routers) → Group 3 (Seeds) → Group 4 (API client)
        ↓
Group 5 (Theme) → Groups 6–9 (Widgets & Rows) → Group 10 (Gamification)
        ↓
Group 11 (Integration) → Group 12 (Verification & Docs)
```

## PART E — RISK WARNINGS

1. **New columns on existing tables** must go in `COLUMN_MIGRATIONS` (`database.py`) — SQLite `create_all` cannot ALTER. New helper functions and the router are additive.
2. **Theme collision:** `.qc-*` classes must stay scoped; the `data-theme="quest-centre"` block overrides only custom-property tokens. Never hardcode colors in components.
3. **Seed idempotency:** all new seeds append-only with existence guards; restarts must not duplicate.
4. **RPG theme untouched:** the existing orange/green `rpg-theme.css` stays as-is; the gold palette is a *new* `quest-centre` theme, not a repaint of RPG.

## STATUS: COMPLETE — all 99 phases implemented and verified (2026-08-02)

Final verification state (G12):
- Backend: `pytest` 180/180 pass (incl. 18 new `tests/test_quest_centre.py` cases)
- Frontend: `npx tsc -b` clean, `npm run build` clean, `vitest` 20/20 pass
- Full-stack smoke test on a fresh DB (port 8765): all quest-centre GET endpoints
  return correct seeded data; life-area complete → Completed/100%/0 days; quest
  complete → streak 1 then 2 same-day; mission PUT persists.
- Docs: `frontend/README.md` gained the "Quest Centre (Gamified Quest Centre)"
  section + theme-table row (5 themes).
