# 100-Phase Plan: RPG Weekly Planner → Student OS Integration

**Goal:** Add all features from the RPG Weekly Planner `.odt` design spec into the Student OS app.
**Theme:** Retro Pixel Art / RPG Gamification — orange (`#ff9800`) / green (`#4caf50`) palette.
**Current state:** Quest model + basic Quests page exist. Everything else needs building.

---

## PHASE GROUP 1: Scaffold & Theme (Phases 1–8)

### Phase 1 — Create RPG theme CSS file
- Create `frontend/src/themes/rpg.css` with `#ff9800` orange accent, `#4caf50` green, `#121212` bg, `#1e1e1e` cards, pixel-art font stack
- Define CSS custom properties: `--rpg-bg-main`, `--rpg-bg-card`, `--rpg-accent-orange`, `--rpg-accent-green`, `--rpg-text-primary`, `--rpg-text-muted`, `--rpg-border`
- **Verify:** File exists with all tokens defined

### Phase 2 — Create pixel-art CSS utilities
- Create `frontend/src/styles/pixel-art.css` with pixelated border effects (`box-shadow` stacking technique), pixel-font import (e.g., "Press Start 2P" from Google Fonts), `image-rendering: pixelated` utility class
- **Verify:** Page with pixel-art class renders sharp-edged borders

### Phase 3 — Add RPG header banner component
- Create `frontend/src/components/rpg/RpgHeader.svelte` — pixel-art banner section with forest/trophy imagery (CSS-drawn or emoji-based), title "RPG Weekly Planner", subtitle/instruction note
- Style with orange accent
- **Verify:** Header renders at top of any page it's placed on

### Phase 4 — Create RPG layout wrapper
- Create `frontend/src/components/rpg/RpgLayout.svelte` — fixed left sidebar + scrollable 2-column masonry grid main area, 20–24px padding, 16px card gaps
- **Verify:** Layout renders sidebar + main grid correctly

### Phase 5 — Create reusable RPG card component
- Create `frontend/src/components/rpg/RpgCard.svelte` — dark card `#1e1e1e`, 8px border-radius, 1px `#2a2a2a` border, `0 4px 6px rgba(0,0,0,0.4)` shadow, 16–20px internal padding, slots for header/body/footer
- **Verify:** Card renders with correct styling and slot content

### Phase 6 — Create reusable RPG badge component
- Create `frontend/src/components/rpg/RpgBadge.svelte` — colored chip/tag for status, priority, category labels. Props: `color`, `size`, `variant` (filled/outline)
- **Verify:** Badge renders in different colors

### Phase 7 — Create RPG button component
- Create `frontend/src/components/rpg/RpgButton.svelte` — pixel-art styled buttons with variants: primary (orange), success (green), danger (red), ghost. Props: `variant`, `size`, `disabled`, `icon`
- **Verify:** All button variants render correctly

### Phase 8 — Create RPG tab component
- Create `frontend/src/components/rpg/RpgTabs.svelte` — minimal text-based toggle tabs with active state highlighted in white/orange underline. Props: `tabs` (array), `activeTab` (bindable)
- **Verify:** Tabs render and switch correctly

---

## PHASE GROUP 2: Backend Models (Phases 9–21)

### Phase 9 — Create Character model
- Create `backend/app/models/character.py` — SQLAlchemy model with fields: `id` (UUID PK), `user_id` (FK users), `name`, `class_name` (Wizard/Warrior/Rogue/etc.), `level` (int, default 1), `xp` (int, default 0), `strength`, `agility`, `intelligence`, `endurance` (int, default 5), `current_quests` (int, default 0), `created_at`, `updated_at`
- **Verify:** Model file exists with all fields

### Phase 10 — Create Reward model
- Create `backend/app/models/reward.py` — SQLAlchemy model with fields: `id` (UUID PK), `user_id` (FK users), `title`, `description`, `xp_cost` (int), `image_url` (optional), `category`, `is_available` (bool, default True), `claimed_date` (optional), `created_at`
- **Verify:** Model file exists with all fields

### Phase 11 — Create LifeArea model
- Create `backend/app/models/life_area.py` — SQLAlchemy model with fields: `id` (UUID PK), `user_id` (FK users), `title` (Work/Fitness/Self Development/Health), `description`, `image_url`, `progress_percent` (float, default 0), `sort_order` (int), `created_at`, `updated_at`
- **Verify:** Model file exists with all fields

### Phase 12 — Create Mission model
- Create `backend/app/models/mission.py` — SQLAlchemy model with fields: `id` (UUID PK), `user_id` (FK users), `title`, `description`, `mission_type`, `priority` (enum: High/Medium/Low), `status` (enum: Not started/In progress/Completed), `due_date`, `xp_reward` (int), `created_at`, `updated_at`
- **Verify:** Model file exists with all fields

### Phase 13 — Create MissionTask model
- Create `backend/app/models/mission_task.py` — SQLAlchemy model with fields: `id` (UUID PK), `mission_id` (FK missions), `title`, `completed` (bool, default False), `sort_order` (int), `created_at`
- **Verify:** Model file exists with all fields

### Phase 14 — Create ScheduleEvent model (Weekly Calendar)
- Create `backend/app/models/schedule_event.py` — SQLAlchemy model with fields: `id` (UUID PK), `user_id` (FK users), `title`, `day_of_week` (int, 0–6), `start_time`, `end_time`, `reference_type` (quest/mission/task), `reference_id` (UUID), `color`, `created_at`
- **Verify:** Model file exists with all fields

### Phase 15 — Add missing fields to existing Quest model
- Edit `backend/app/models/quest.py` — add fields: `category` (str, optional), `priority` (enum: High/Medium/Low), `time_estimate` (int, minutes, optional)
- **Verify:** Quest model now has category, priority, time_estimate columns

### Phase 16 — Update Quest schema with new fields
- Edit `backend/app/schemas/quest.py` — add `category`, `priority`, `time_estimate` to QuestBase, QuestCreate, QuestResponse
- **Verify:** Schemas compile and validate new fields

### Phase 17 — Create Character schemas
- Create `backend/app/schemas/character.py` — Pydantic models: `CharacterBase`, `CharacterCreate`, `CharacterUpdate`, `CharacterResponse` (with id, user_id, model_config=from_attributes)
- **Verify:** Schemas compile

### Phase 18 — Create Reward schemas
- Create `backend/app/schemas/reward.py` — Pydantic models: `RewardBase`, `RewardCreate`, `RewardUpdate`, `RewardResponse`
- **Verify:** Schemas compile

### Phase 19 — Create LifeArea schemas
- Create `backend/app/schemas/life_area.py` — Pydantic models: `LifeAreaBase`, `LifeAreaCreate`, `LifeAreaUpdate`, `LifeAreaResponse`
- **Verify:** Schemas compile

### Phase 20 — Create Mission schemas
- Create `backend/app/schemas/mission.py` — Pydantic models: `MissionBase`, `MissionCreate`, `MissionUpdate`, `MissionResponse`, `MissionTaskBase`, `MissionTaskCreate`, `MissionTaskResponse`
- **Verify:** Schemas compile

### Phase 21 — Create ScheduleEvent schemas
- Create `backend/app/schemas/schedule_event.py` — Pydantic models: `ScheduleEventBase`, `ScheduleEventCreate`, `ScheduleEventUpdate`, `ScheduleEventResponse`
- **Verify:** Schemas compile

---

## PHASE GROUP 3: Backend API Routers (Phases 22–33)

### Phase 22 — Register all new models in __init__.py
- Edit `backend/app/models/__init__.py` — import and export Character, Reward, LifeArea, Mission, MissionTask, ScheduleEvent
- **Verify:** All models appear in `__all__`

### Phase 23 — Register all new schemas in __init__.py
- Edit `backend/app/schemas/__init__.py` — import and export all new schema classes
- **Verify:** All schemas appear in `__all__`

### Phase 24 — Create Character router
- Create `backend/app/routers/characters.py` — endpoints: `GET /characters/{user_id}` (get profile), `PUT /characters/{user_id}` (update), `POST /characters/{user_id}/xp` (add XP, auto-level-up logic), `GET /characters/{user_id}/stats` (get stats breakdown)
- **Verify:** All 4 endpoints return 200 with test client

### Phase 25 — Create Reward router
- Create `backend/app/routers/rewards.py` — endpoints: `GET /rewards` (list all), `POST /rewards` (create), `PUT /rewards/{id}` (update), `DELETE /rewards/{id}` (delete), `POST /rewards/{id}/claim` (claim — deduct XP, set claimed_date), `GET /rewards/claimed` (list claimed)
- **Verify:** All 6 endpoints return 200

### Phase 26 — Create LifeArea router
- Create `backend/app/routers/life_areas.py` — endpoints: `GET /life-areas` (list), `POST /life-areas` (create), `PUT /life-areas/{id}` (update progress, etc.), `DELETE /life-areas/{id}`
- **Verify:** All 4 endpoints return 200

### Phase 27 — Create Mission router
- Create `backend/app/routers/missions.py` — endpoints: `GET /missions` (list, filterable by status), `POST /missions` (create), `PUT /missions/{id}` (update), `DELETE /missions/{id}`, `GET /missions/{id}/tasks` (list subtasks), `POST /missions/{id}/tasks` (add subtask), `PUT /mission-tasks/{id}` (update subtask), `DELETE /mission-tasks/{id}`
- **Verify:** All 8 endpoints return 200

### Phase 28 — Create ScheduleEvent router
- Create `backend/app/routers/schedule_events.py` — endpoints: `GET /schedule` (list, filterable by week/date range), `POST /schedule` (create), `PUT /schedule/{id}` (update), `DELETE /schedule/{id}`
- **Verify:** All 4 endpoints return 200

### Phase 29 — Update Quest router with new fields
- Edit `backend/app/routers/quests.py` — update CRUD to handle category, priority, time_estimate; add filter by priority/category query params to `GET /quests`
- **Verify:** Updated endpoints work with new fields

### Phase 30 — Register all new routers
- Edit `backend/app/routers/__init__.py` — import and export characters, rewards, life_areas, missions, schedule_events
- **Verify:** Router module imports cleanly

### Phase 31 — Wire routers into main.py
- Edit `backend/main.py` — `app.include_router()` for each new router under `/api` prefix
- **Verify:** `GET /api/characters/...` and other endpoints respond

### Phase 32 — Run database migration
- Run `alembic revision --autogenerate` and `alembic upgrade head` (or `Base.metadata.create_all`) to create new tables
- **Verify:** New tables exist in the SQLite database

---

## PHASE GROUP 4: Seed Data (Phases 33–37)

### Phase 33 — Create character seed data
- Edit `backend/app/seed/__init__.py` — add seed for 1 Character: Wizard class, level 3, 1250 XP, stats evenly distributed
- **Verify:** Character record exists after seed

### Phase 34 — Create reward seed data
- Edit `backend/app/seed/__init__.py` — add 4 rewards: "Take a walk" (50 XP), "Dinner outside" (200 XP), "Take a day off" (500 XP), "Buy a game" (1000 XP). All available initially.
- **Verify:** Rewards exist after seed

### Phase 35 — Create life area seed data
- Edit `backend/app/seed/__init__.py` — add 4 Life Areas: Work (45%), Fitness (30%), Self Development (60%), Health (70%)
- **Verify:** Life Areas exist after seed

### Phase 36 — Create mission seed data
- Edit `backend/app/seed/__init__.py` — add 2 Missions: "Notion Templates" (in progress, with 2 subtasks) and "Content Creation" (not started, with 3 subtasks)
- **Verify:** Missions + subtasks exist after seed

### Phase 37 — Create schedule seed data
- Edit `backend/app/seed/__init__.py` — add sample weekly schedule events (Mon–Fri, 3–4 events per day)
- **Verify:** Schedule events exist after seed

---

## PHASE GROUP 5: Frontend — Character Profile (Phases 38–43)

### Phase 38 — Create API endpoint helpers for Character
- Edit `frontend/src/services/api.ts` — add `endpoints.characters` with `get(userId)`, `update(userId, data)`, `addXp(userId, amount)`
- **Verify:** Helper functions compile and are exported

### Phase 39 — Create StatusProfile component
- Create `frontend/src/components/rpg/StatusProfile.svelte` — Wizard avatar (emoji or SVG), name, class, level badge, stat bars (STR/AGI/INT/END) with labels, current quests count
- Props: `character` object
- **Verify:** Component renders with all stats displayed

### Phase 40 — Create ProgressBars component (RPG version)
- Create `frontend/src/components/rpg/ProgressBars.svelte` — three stacked bars: Year/Month/Week completion percentages. White fill with percentage label. Orange glow on active bar.
- Props: `year`, `month`, `week` percentages
- **Verify:** All three bars render with correct fill widths

### Phase 41 — Create QuickActions component (RPG version)
- Create `frontend/src/components/rpg/QuickActions.svelte` — four pill-shaped buttons: `+ Add New Quest`, `+ Add New Mission`, `+ Add New Life Area`, `+ New Reward`. Each dispatches a click event with action type.
- **Verify:** All four buttons render and dispatch events

### Phase 42 — Create PriorityList component
- Create `frontend/src/components/rpg/PriorityList.svelte` — three folder-style cards: High Priority (red tint), Medium Priority (orange tint), Low Priority (green tint). Each shows title + estimated day range.
- Props: `high`, `medium`, `low` arrays of tasks with `title` and `days_remaining`
- **Verify:** Folder cards render with priority coloring

### Phase 43 — Assemble RPG Sidebar
- Create `frontend/src/components/rpg/RpgSidebar.svelte` — composes StatusProfile + ProgressBars + QuickActions + PriorityList vertically with 16px gaps
- **Verify:** Full sidebar renders in layout

---

## PHASE GROUP 6: Frontend — Pomodoro Timer (Phases 44–48)

### Phase 44 — Create API endpoint helpers for Pomodoro
- Ensure `endpoints.pomodoro` exists in `api.ts` with `list()`, `create()`, `update()`, `getStats()`
- **Verify:** Helper functions compile

### Phase 45 — Create PomodoroWidget component
- Create `frontend/src/components/rpg/PomodoroWidget.svelte` — dark card with central countdown display (MM:SS format), "Short Break" / "Long Break" tabs, timer circle-progress ring, Start/Pause button, settings gear icon, briefcase icon
- **Verify:** Timer displays 25:00, tabs switch between modes

### Phase 46 — Implement Pomodoro timer logic
- Add Svelte store or component-level timer logic: countdown, pause/reset, session tracking, auto-switch between focus/break cycles (25min focus → 5min short break → 25min focus → 15min long break)
- **Verify:** Timer counts down, switches breaks correctly

### Phase 47 — Add Pomodoro session persistence
- Wire Pomodoro component to backend: save completed sessions on timer end, fetch today's session count for stats display
- **Verify:** Sessions persist and reload across page visits

### Phase 48 — Add Pomodoro session stats
- Display today's total focus time, sessions completed, streak counter in the widget footer
- **Verify:** Stats update after each completed session

---

## PHASE GROUP 7: Frontend — Life Areas (Phases 49–52)

### Phase 49 — Create API endpoint helpers for Life Areas
- Add `endpoints.lifeAreas` to `api.ts` with `list()`, `create()`, `update()`, `remove()`
- **Verify:** Helpers compile

### Phase 50 — Create LifeAreaCard component
- Create `frontend/src/components/rpg/LifeAreaCard.svelte` — card with pixel-art backdrop (CSS gradient/emoji), title overlay, compact progress bar, "Complete by [Date]" label
- Props: `area` object (title, image, progress, dueDate)
- **Verify:** Card renders with all elements

### Phase 51 — Create LifeAreasGrid component
- Create `frontend/src/components/rpg/LifeAreasGrid.svelte` — horizontal 4-card row layout with scroll support. Fetches from API, renders LifeAreaCard for each.
- **Verify:** 4 cards display in a row

### Phase 52 — Add Life Area detail/edit modal
- Create `frontend/src/components/rpg/LifeAreaModal.svelte` — modal for editing progress %, title, image. Form fields bound to API update call.
- **Verify:** Modal opens, edits save to backend

---

## PHASE GROUP 8: Frontend — Quest Center Enhancement (Phases 53–61)

### Phase 53 — Update Quest type interfaces
- Edit `frontend/src/services/api.ts` — add `category`, `priority`, `time_estimate` to `Quest` interface
- **Verify:** TypeScript compiles without errors

### Phase 54 — Create QuestCard component
- Create `frontend/src/components/rpg/QuestCard.svelte` — enhanced task card with: status badge (color-coded), priority badge (High=red/Med=orange/Low=green), category tag, due date, time estimate, XP reward badge, description, "Done" button at bottom
- Props: `quest` object
- **Verify:** Card renders all fields

### Phase 55 — Create QuestCenter tabs
- Create `frontend/src/components/rpg/QuestCenter.svelte` — tabbed view with RpgTabs: "Today", "In Progress", "Overdue", "Inbox". Filters quest list based on active tab.
- **Verify:** Tabs switch and filter correctly

### Phase 56 — Create QuestCreateForm component
- Create `frontend/src/components/rpg/QuestCreateForm.svelte` — form with fields: title, description, category, priority (dropdown), time_estimate, due_date, xp_reward. Validates inputs.
- **Verify:** Form submits and creates quest via API

### Phase 57 — Implement quest complete action
- Add "Done" button handler — marks quest as completed, awards XP to character via API call, shows brief completion animation
- **Verify:** Quest completes, XP updates

### Phase 58 — Create empty state for each tab
- Add empty-state placeholder for each QuestCenter tab with distinct hover effect (glowing border) and "Add your first quest" prompt
- **Verify:** Empty state shows when no quests match filter

### Phase 59 — Wire QuestCenter to API
- Integrate QuestCenter with backend: fetch quests on mount with tab filter, create new quest via POST, complete quest via PUT
- **Verify:** Full CRUD cycle works from UI

### Phase 60 — Add quest search/filter bar
- Add search input above quest list that filters by title, plus dropdown filter for category/priority
- **Verify:** Search filters results in real-time

### Phase 61 — Add quest count badges on tabs
- Each tab shows count of matching quests (e.g., "In Progress (3)")
- **Verify:** Counts update when quests change

---

## PHASE GROUP 9: Frontend — Mission Center (Phases 62–69)

### Phase 62 — Create API endpoint helpers for Missions
- Add `endpoints.missions` to `api.ts` with `list()`, `create()`, `update()`, `remove()`, `listTasks()`, `createTask()`, `updateTask()`, `removeTask()`
- **Verify:** Helpers compile

### Phase 63 — Create MissionCard component
- Create `frontend/src/components/rpg/MissionCard.svelte` — card with: title, type badge, priority tag, due date, progress (subtasks completed/total), expandable subtask list, "Done" button. Color-coded border (orange/green per type).
- Props: `mission` object
- **Verify:** Card renders all fields

### Phase 64 — Create MissionCenter component
- Create `frontend/src/components/rpg/MissionCenter.svelte` — tabbed view: "All Missions", "In Progress", "Not Started Yet", "Completed". Fetches from API, filters by tab.
- **Verify:** Tabs filter missions correctly

### Phase 65 — Create MissionCreateForm component
- Create `frontend/src/components/rpg/MissionCreateForm.svelte` — form with fields: title, description, type, priority, due_date, xp_reward, subtasks (dynamic add/remove). Validates.
- **Verify:** Form creates mission with subtasks

### Phase 66 — Implement subtask management
- Subtask items: checkbox to mark complete, inline edit, delete button. Progress updates parent mission automatically.
- **Verify:** Checking subtasks updates mission progress

### Phase 67 — Implement mission complete action
- "Done" button on mission — marks completed, awards XP to character, shows completion state
- **Verify:** Mission completes, XP awarded

### Phase 68 — Add mission empty states
- Empty state per tab with glowing hover effect
- **Verify:** Empty states display correctly

### Phase 69 — Add mission search/filter
- Search by title, filter by type and priority
- **Verify:** Filtering works

---

## PHASE GROUP 10: Frontend — Reward Center (Phases 70–78)

### Phase 70 — Create API endpoint helpers for Rewards
- Add `endpoints.rewards` to `api.ts` with `list()`, `create()`, `update()`, `remove()`, `claim(id)`, `listClaimed()`
- **Verify:** Helpers compile

### Phase 71 — Create RewardCard component
- Create `frontend/src/components/rpg/RewardCard.svelte` — visually rich card with: pixel-art image banner (emoji/CSS), title, XP cost badge, availability status ("Available" green / "Not available" red), "Claim Reward" button (disabled when locked)
- Props: `reward` object
- **Verify:** Both available and locked states render

### Phase 72 — Create available reward badge logic
- Show green "Available" + enabled Claim button when character XP >= reward.xp_cost
- Show red "Not available" + disabled button when XP insufficient
- Show "Claimed" + claimed date when already claimed
- **Verify:** All three states display correctly

### Phase 73 — Create RewardCenter component
- Create `frontend/src/components/rpg/RewardCenter.svelte` — tabs: "Rewards" and "Claimed Rewards". Horizontal scrollable row of RewardCards.
- **Verify:** Tabs switch between available and claimed

### Phase 74 — Implement reward claim flow
- Click "Claim Reward" → confirmation dialog → POST to claim endpoint → deduct XP → show pixel-art confetti animation → move to claimed tab
- **Verify:** Claim deducts XP, shows animation, moves card

### Phase 75 — Create RewardCreateForm component
- Create `frontend/src/components/rpg/RewardCreateForm.svelte` — form with: title, description, xp_cost, category, image_url
- **Verify:** Form creates reward via API

### Phase 76 — Add reward empty states
- Empty state for no rewards ("Create your first reward!") and no claimed rewards ("Go earn some XP and claim rewards!")
- **Verify:** Empty states display

### Phase 77 — Add pixel-art confetti animation on claim
- Create CSS-only confetti burst animation triggered on successful claim
- **Verify:** Animation plays on claim

### Phase 78 — Add reward sorting/filtering
- Sort by XP cost (low to high / high to low), filter by category
- **Verify:** Sorting and filtering work

---

## PHASE GROUP 11: Frontend — Weekly Calendar (Phases 79–86)

### Phase 79 — Create API endpoint helpers for Schedule
- Add `endpoints.schedule` to `api.ts` with `list()`, `create()`, `update()`, `remove()`
- **Verify:** Helpers compile

### Phase 80 — Create WeeklyCalendar component (header + nav)
- Create `frontend/src/components/rpg/WeeklyCalendar.svelte` — horizontal weekly timeline showing Mon–Sun (or 18th–24th format). Navigation arrows to shift weeks, "Today" button to jump to current week. "Manage in Calendar" action button.
- **Verify:** Calendar shows correct 7-day range

### Phase 81 — Implement calendar day columns
- Each day column shows: day name/number header, list of event/task chips below. Event chips colored by type (quest=orange, mission=green, task=blue). Click chip to see details.
- **Verify:** Events display in correct day columns

### Phase 82 — Implement drag-to-create on calendar
- Click on a day column to open quick-add form: title, time, type selector. Saves to schedule API.
- **Verify:** Quick-add creates event on clicked day

### Phase 83 — Load quests/missions on calendar
- Automatically fetch quests and missions with due dates and plot them on the calendar. Show total count per day.
- **Verify:** Quests/missions appear on their due dates

### Phase 84 — Add calendar zoom toggle
- Toggle between "Day", "Week", "Month" views. Week view is default.
- **Verify:** Views switch correctly

### Phase 85 — Add calendar empty state
- Empty week message: "No quests scheduled this week. Add your first quest!"
- **Verify:** Empty state shows

### Phase 86 — Add calendar drag-to-reschedule (future)
- Allow dragging event chips between days to change due_date
- **Verify:** Dragged event updates its day

---

## PHASE GROUP 12: Dashboard Assembly (Phases 87–94)

### Phase 87 — Create RpgDashboard page
- Create `frontend/src/pages/RpgDashboard.svelte` — full-page layout using RpgLayout, RpgHeader, RpgSidebar, and all widgets in 2-column grid
- **Verify:** Page renders all components

### Phase 88 — Add Pomodoro + LifeAreas to first row
- Top row of main content: PomodoroWidget (left column, spans full width or 1.5 columns) + LifeAreasGrid (right column)
- **Verify:** Row renders correctly

### Phase 89 — Add QuestCenter + MissionCenter to second row
- Middle row: QuestCenter (left column) + MissionCenter (right column)
- **Verify:** Both render side by side

### Phase 90 — Add RewardCenter + WeeklyCalendar to third row
- Bottom row: RewardCenter (left/right) + WeeklyCalendar (full width below)
- **Verify:** RewardCenter and Calendar render

### Phase 91 — Add route for RPG Dashboard
- Edit `frontend/src/App.tsx` — add `/rpg` route → `<RpgDashboard>` component. Add nav link in NavLinks.
- **Verify:** `/rpg` route loads the dashboard

### Phase 92 — Wire RPG Dashboard to Character API
- On mount, fetch character profile from API and pass to StatusProfile + ProgressBars
- **Verify:** Character data loads on page load

### Phase 93 — Wire PriorityList to real data
- Fetch quests grouped by priority (High/Medium/Low) and display in PriorityList with count and nearest due date
- **Verify:** Priority list shows real quest data

### Phase 94 — Add loading skeletons for each widget
- Create `frontend/src/components/rpg/RpgSkeleton.svelte` — pulsing placeholder shapes matching each widget layout. Show while data loads.
- **Verify:** Skeletons display during API fetch

---

## PHASE GROUP 13: Theme Polish & Pixel Art (Phases 95–100)

### Phase 95 — Apply RPG theme globally
- Edit `frontend/src/app.css` — add RPG color scheme variables, apply pixel font as optional theme. Create `.theme-rpg` class on body to activate all RPG variables.
- **Verify:** Toggle `.theme-rpg` changes entire app styling

### Phase 96 — Add pixel-art hover/active effects
- Add CSS: `:hover` glow effect on cards (orange/gold box-shadow), button press effect (2px downward shift), tab active underline animation
- **Verify:** All interactive elements have pixel-art feedback

### Phase 97 — Add page transition animations
- Add fade-in + slight upward slide for each widget on page load, staggered by index. CSS `@keyframes` only, no JS animation library.
- **Verify:** Widgets animate in on page load

### Phase 98 — Create RPG-specific icons directory
- Create `frontend/src/icons/rpg/` with SVG icon components: sword, shield, potion, scroll, trophy, star, coin, lock, key, calendar, clock, wizard-hat. Use pixel-art style (sharp edges, limited colors).
- **Verify:** Icons render inline

### Phase 99 — Add toast notifications for RPG actions
- Extend existing Toast system: custom RPG-styled toasts for "Quest Complete!", "XP Gained!", "Reward Unlocked!", "Level Up!" with appropriate icon + color
- **Verify:** Toasts display on actions

### Phase 100 — Final integration test & bug fix
- Manually test full flow: create quest → complete quest → gain XP → character levels up → reward unlocks → claim reward
- Fix any UI glitches, data loading errors, or styling inconsistencies
- Run `npm run build` to verify production build succeeds
- **Verify:** Full gamification loop works end-to-end, build passes

---

## Summary

| Group | Phases | Area |
|---|---|---|
| 1 | 1–8 | Scaffold & Theme (8) |
| 2 | 9–21 | Backend Models (13) |
| 3 | 22–33 | Backend API Routers (12) |
| 4 | 33–37 | Seed Data (5) |
| 5 | 38–43 | Frontend — Character Profile (6) |
| 6 | 44–48 | Frontend — Pomodoro Timer (5) |
| 7 | 49–52 | Frontend — Life Areas (4) |
| 8 | 53–61 | Frontend — Quest Center Enhancement (9) |
| 9 | 62–69 | Frontend — Mission Center (8) |
| 10 | 70–78 | Frontend — Reward Center (9) |
| 11 | 79–86 | Frontend — Weekly Calendar (8) |
| 12 | 87–94 | Dashboard Assembly (8) |
| 13 | 95–100 | Theme Polish & Pixel Art (6) |

**Total: 100 phases — RPG Weekly Planner fully integrated into Student OS.**
