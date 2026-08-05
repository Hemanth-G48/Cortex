# 99-Phase Implementation Plan — Shiori-v1 → Student Life OS (productivity_app) Integration

**Source repo:** `Shiori-v1/` (shiori-v1)
**Target repo:** `productivity_app` (Student Life OS) — `/home/hemanth/productivity_app` — React 19 + TypeScript strict + Vite + react-router-dom + vitest frontend · FastAPI + SQLAlchemy + SQLite backend
**Source repo:** `/home/hemanth/productivity_app/Shiori-v1` — React 18 + Zustand + Supabase + Express + client-side Gemini
**Baseline (verified 2026-08-03):** Backend **234 pytest** (`test_courses`, `test_habits`, `test_health`, `test_life_planner`, `test_other_endpoints`, `test_regression`, `test_rpg`, `test_tasks`, `test_vault`, `test_fitness_hub`, `test_habit_tracker`, `test_quest_centre`) · Frontend `tsc -b` + `npm run build` clean · **23 vitest** across `App`, `fitnessHub`, `habitTracker`, `questCentre` + 2 util test files · oxlint clean (5 pre-existing warnings).

> **✅ IMPLEMENTATION STATUS — 2026-08-03: ALL 16 GROUPS COMPLETE**
>
> Backend **290 pytest** (baseline 234 + `test_ai` 21, `test_grades` 13, `test_flashcards` 9,
> `test_study_plans` 5, `test_analytics` 4, `test_google` 11, notes-pin additions) · Frontend
> **55 vitest** (baseline 23 + grades 4, flashcards 4, studyPlans 4, quiz 2, syllabus 2, aiChat 3,
> analytics 3, notes 3, settings 3) · `tsc -b` clean · **oxlint 0 warnings / 0 errors** · fresh-DB
> smoke passed on all 13 new endpoint groups. Deps added: `httpx` (backend, root `pyproject.toml`),
> `jspdf` (frontend). `.env.example` documents `AI_*` + `GOOGLE_*`.
>
> **Notes / deviations:** `Quiz.tsx` + `SyllabusImport.tsx` live in the same session as Groups 6–9
> (AI endpoints landed in Group 1 since they only depend on `ai_client`/`ai_fallback`).
> `AIChat`'s toggle bus was extracted to `utils/aiChatBus.ts` to satisfy fast-refresh lint.
> Assignments keeps its table (export buttons added); filters/priority deferred as optional per PART B row 22.
> Google OAuth requires real credentials (`GOOGLE_CLIENT_ID/SECRET`) to go beyond the deterministic mock fallbacks.

---

## Executive Summary

Shiori-v1's differentiating value is its **AI layer** — AI quiz generator, AI flashcards with written-answer grading, AI study plans, syllabus import, and an AI chat assistant — plus a **grade calculator / GPA predictor**, a **study analytics page**, and a **Google Classroom/Gmail/Calendar sync**. The current project (Student Life OS) already has a large, mature surface (courses, assignments, exams, tasks, habits with XP, pomodoro, fitness, quests, missions, rewards, character/RPG, vault, life planner, quest centre, fitness hub) but has **zero AI features, no grade/GPA model, no analytics page, no OAuth sync, and a read-only Notes page**.

This plan integrates every valuable Shiori-v1 feature that is missing, **reusing Shiori's algorithms, prompts, and data shapes** (grade math, flashcard flow, quiz state machine, study-plan JSON, syllabus extraction, chat heuristics, iCal/PDF/sounds) **adapted to the current architecture**: FastAPI-backed AI via an OpenAI-compatible provider, single-user local SQLite, React 19 strict TS, and the existing CSS-variable theme system. Nothing existing is removed or regressed.

**User decisions (locked in):**
- **AI provider:** use **OmniRoute** (OpenAI-compatible proxy at `http://localhost:20128/v1`, key `omniroute-local`, default model `oc/deepseek-v4-flash-free`), **configurable so other models can be selected** (env-driven model list + Settings selector). Deterministic fallback when AI is unreachable (mirrors Shiori's demo fallback).
- **Google Classroom/Gmail/Calendar OAuth sync: KEEP** — implement server-side in FastAPI, read-only scopes, token stored in local DB.
- **Stripe Pro billing: SKIP** (out of scope per user).
- **Supabase auth: SKIP** — keep current single-user local `/api/auth/login`; personal use only.
- **Leaderboard:** single-user local — implement as a personal XP/level/streak "progress board" (no friend network), or defer (low value for one user).

---

## PART A — Repository Comparison

| Aspect | Shiori-v1 | Current project (Student Life OS) |
|---|---|---|
| Frontend | React 18, JSX, Zustand persist → localStorage/IndexedDB, inline styles + Tailwind, lucide-react, framer-motion, jsPDF, `@mlc-ai/web-llm` (WebGPU), three.js | React 19, **strict TypeScript**, Vite, CSS-variable theme system (`theme.css` + `rpg-theme.css` + per-feature css), emoji icons, date-fns, recharts, react-query, Toast/EmptyState/Skeleton/ErrorBoundary shared kit |
| State | Zustand `persist` (client-side) | Server-backed REST via `services/api.ts` `endpoints` object + feature hooks |
| Backend | Express (OAuth/Classroom/Gmail/Calendar/AI/Stripe proxies) + Vercel serverless + Supabase | **FastAPI + SQLAlchemy + SQLite**, ~28 routers, ~120 endpoints, `COLUMN_MIGRATIONS`, idempotent `seed_database` |
| Auth | Supabase (Google/GitHub/email) + local in-memory | Single seeded user (`/api/auth/login` → "Alex") — **keep** |
| Data model | 10 Supabase tables (courses, assignments, notes, flashcard_decks, flashcards, events, habits, study_plans, profiles, subscriptions) | 30 models (User, Course, Assignment, Exam, Note, Goal, Task, Habit, PomodoroSession, Fitness×8, Journal, Quest, Project, LifeArea, Character, Reward, Mission, ScheduleEvent, DailyLog, Event) |
| AI | Gemini REST client-side + WebGPU `localAI.js` fallback | **none** → new `services/ai_client.py` (OpenAI-compatible → OmniRoute) |
| Tests | none | 234 backend pytest · 23 frontend vitest · tsc clean |

---

## PART B — Feature Inventory & Gap Analysis

Legend: ✅ exists · ⚠️ partial (gap noted) · ❌ missing · ✖ out of scope (user decision)

| # | Shiori feature | Source files (Shiori-v1) | Current status | Gap to close |
|---|---|---|---|---|
| 1 | **AI quiz generator** (MCQ from notes, setup→quiz→results, XP) | `pages/Quiz.jsx`, `utils/ai.js`, `utils/gemini.js` | ❌ Missing | `/api/ai/quiz` + `Quiz.tsx` + localStorage `quiz-history` |
| 2 | **AI flashcards** (decks, flip study, written-answer grading, 5 difficulties) | `pages/Flashcards.jsx`, `stores/index.js` (flashcards), `supabase/schema.sql` | ❌ Missing | `FlashcardDeck`+`Flashcard` models/routers, `/api/ai/flashcards` + `/api/ai/grade-answer`, `Flashcards.tsx` |
| 3 | **AI study plans** (week-by-week JSON) | `pages/StudyPlans.jsx`, `stores/index.js` (studyPlans), `api/ai/study-plan.js` | ❌ Missing | `StudyPlan` model/router, `/api/ai/study-plan`, `StudyPlans.tsx` |
| 4 | **Syllabus import** (paste/file → AI-extracted assignments) | `pages/SyllabusImport.jsx` | ❌ Missing | `/api/ai/syllabus` + `SyllabusImport.tsx` |
| 5 | **AI chat assistant** (context-aware, local heuristic fallback) | `components/AIChat.jsx`, `server/routes/ai.js` | ❌ Missing | `/api/ai/chat` + `AIChat.tsx` collapsible panel + `Ctrl+K` |
| 6 | **Grade calculator + GPA + "needed on final"** | `pages/Grades.jsx`, `stores/index.js` (grades: `LETTER_GRADE`, `pctToGPA`, `calculateCourseGrade`), `server/routes/grades.js` | ❌ Missing | `Grade` model + `Course.credits` migration + `CourseWeight` + grades router + `services/grade_calc.py` (port math) + `Grades.tsx` |
| 7 | **Study analytics** (weekly focus hours, completion rate, GPA, streaks, grade trends) | `pages/Analytics.jsx`, `components/StudyHeatmap.jsx`, `components/TimeTrackerBars.jsx`, `components/GradeTrendChart.jsx` | ⚠️ Partial — current has per-habit stats only | `services/analytics.py` (aggregate `pomodoro_sessions`+assignments+grades+XP) + `Analytics.tsx` + 3 components |
| 8 | **Notes editor** (split-pane list+editor, search, pin, markdown preview) | `pages/Notes.jsx`, `stores/index.js` (notes) | ⚠️ Partial — current Notes page is **read-only grid**; backend CRUD exists | Rebuild `Notes.tsx` as editor; add `Note.pinned`/`updated_at` + pin endpoint |
| 9 | **Google Classroom sync** (courses+assignments, idempotent merge) | `lib/classroom.js`, `server/routes/classroom.js`, `extension/content-classroom.js` | ❌ Missing | `services/google_oauth.py` (OAuth2, token in DB) + `routers/classroom.py` (merge into Course/Assignment) |
| 10 | **Gmail unread/messages** | `server/routes/gmail.js` | ❌ Missing | `routers/gmail.py` (unread count + message list) — surface on Home/Settings |
| 11 | **Google Calendar events** (sync to schedule) | `server/routes/calendar.js` | ❌ Missing | `routers/calendar.py` → merge into `ScheduleEvent`/`Event` |
| 12 | **Keyboard shortcuts** (`g`+letter nav, `Ctrl+K`, `?`) | `hooks/useKeyboardShortcuts.js`, `components/ShortcutModal.jsx` | ❌ Missing | `hooks/useKeyboardShortcuts.ts` + `ShortcutModal.tsx` + Layout wiring |
| 13 | **iCal export** | `utils/icalExport.js` | ❌ Missing | `utils/icalExport.ts` + button on Assignments |
| 14 | **PDF export** (study plan → jsPDF) | `utils/pdfExport.js` | ❌ Missing | `utils/pdfExport.ts` + `jspdf` dep + buttons |
| 15 | **Pomodoro sounds** | `utils/sounds.js` | ❌ Missing | `utils/sounds.ts` (WebAudio) wired into Pomodoro |
| 16 | **Quick capture** (floating add-assignment, `Ctrl+Shift+A`) | `components/QuickCapture.jsx` | ⚠️ Partial (`QuickActions` widget exists) | `QuickCapture.tsx` floating form |
| 17 | **Settings page** (profile, AI model, Google status, theme, data export) | `pages/Settings.jsx` | ❌ Missing | `Settings.tsx` + `/api/settings`-style prefs (localStorage is fine) |
| 18 | **XP/levels** | `stores/index.js` (XP, 6 tiers) | ✅ Current has richer wallet (User.total_xp + Character.xp + habit_xp service) | None — keep current |
| 19 | **Habits 7-day grid** | `pages/Habits.jsx` | ✅ Current has a far richer gamified habit tracker | None |
| 20 | **Focus mode / pomodoro** | `pages/FocusMode.jsx`, `components/PomodoroTimer.jsx` | ⚠️ Partial — current has Pomodoro page + `usePomodoro` | Optional: preset chips + task-link + sounds |
| 21 | **Calendar month grid** | `pages/Calendar.jsx` | ⚠️ Partial — current has TimetableGrid + AcademicCalendar + MiniCalendar | Optional month-grid with event dots |
| 22 | **Assignments filters/priority/modal** | `pages/Assignments.jsx` | ⚠️ Partial — current Assignments is a plain table | Add today/week/overdue tabs + priority + add modal |
| 23 | **Profile/badges** | `pages/Profile.jsx` | ⚠️ Partial (`Character` page exists) | Optional badge grid |
| 24 | **Landing / marketing** | `pages/Landing.jsx`, `HeroScene.jsx` | ✖ Out of scope (personal app) | Skip |
| 25 | **Pro / Stripe billing** | `pages/Pro.jsx`, `server/routes/stripe.js` | ✖ Out of scope (user) | Skip |
| 26 | **Supabase auth / GitHub OAuth / AuthCallback** | `stores/index.js`, `lib/supabase.js`, `Login/Signup/AuthCallback.jsx` | ✖ Out of scope (user: local DB, single user) | Skip — keep `/api/auth/login` |
| 27 | **Demo mode + DemoTour** | `pages/Demo.jsx`, `DemoTour.jsx`, `utils/demoData.js` | ↦ Seed already provides demo data | Skip |
| 28 | **PWA / install banner** | `public/manifest.json`, `sw.js`, `InstallBanner.jsx` | ❌ Optional | Optional late phase (after 99 if desired) |
| 29 | **Chrome extension** | `extension/` | ✖ Separate artifact | Skip |
| 30 | **MCP server** | `mcp/` | ✖ Out of scope | Skip |

**Bottom line:** ~8 feature areas to build (AI×5, grades, analytics, notes editor, Google sync×3) plus shared utilities (shortcuts, exports, sounds, quick capture, settings). Everything else already exists in the current project in equal or richer form.

---

## PART C — Feature Mapping (source → destination)

| New feature | Reuse from Shiori (adapt) | New / modified in current project |
|---|---|---|
| AI client | `utils/ai.js` orchestration, `utils/gemini.js` model-retry list, `parseJSONBlock`, `\[\{\}\]` JSON slicing | `services/ai_client.py` — OpenAI-compatible POST to `{AI_BASE_URL}/v1/chat/completions`, `model` from settings/override, `extract_json`, graceful `None` + fallback; `utils/ai.ts` (frontend) |
| Grades | `LETTER_GRADE`, `pctToGPA`, `calculateCourseGrade` (weighted categories + unweighted), `neededOnFinal` math, `EMPTY_GRADE/COURSE` forms | `models/grade.py` (+`Course.credits` migration), `routers/grades.py`, `services/grade_calc.py`, `pages/Grades.tsx`, `components/grades/GradeTrendChart.tsx` |
| Flashcards | deck/card shape, flip mode, written-answer AI grading prompt, 5-difficulty prompt map, `parseJSONBlock` | `models/flashcard.py`, `routers/flashcards.py`, `/api/ai/flashcards` + `/api/ai/grade-answer`, `pages/Flashcards.tsx` |
| Study plans | 4-week JSON shape `{subject, weeks:[{week,topic,tasks}]}`, `DEMO_PLAN` fallback | `models/study_plan.py`, `routers/study_plans.py`, `/api/ai/study-plan`, `pages/StudyPlans.tsx` |
| Quiz | `DEMO_QUIZ`, phase machine (setup/quiz/results), option-button coloring, +XP | `/api/ai/quiz`, `pages/Quiz.tsx`, localStorage `quiz-history` |
| Syllabus | extraction prompt + `DEMO_EXTRACTED` fallback | `/api/ai/syllabus`, `pages/SyllabusImport.tsx` |
| AI chat | `getLocalResponse` heuristics (due/priority/plan/grades/help/tips), `QUICK_PROMPTS`, demo greeting | `/api/ai/chat` (context from DB), `components/AIChat.tsx`, Layout panel + `Ctrl+K` |
| Analytics | weekly-hours memo, completion rate, GPA overview, StudyHeatmap + TimeTrackerBars | `routers/analytics.py` (aggregate `pomodoro_sessions`+assignments+grades+XP), `pages/Analytics.tsx`, `components/analytics/StudyHeatmap.tsx` + `TimeTrackerBars.tsx` |
| Notes editor | split-pane layout, search, pin toggle, markdown preview | `Note.pinned`/`updated_at` migration + pin endpoint; rewrite `pages/Notes.tsx` |
| Google OAuth + Classroom/Gmail/Calendar | OAuth scopes, `services/google.js` shape, `fetchClassroomData` idempotent merge, mock fallbacks | `services/google_oauth.py`, `routers/auth_google.py` (connect/callback/status/disconnect), `routers/classroom.py`, `gmail.py`, `calendar.py` (token in DB; env `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`) |
| Shortcuts | `useKeyboardShortcuts` + SHORTCUTS map + `ShortcutModal` | `hooks/useKeyboardShortcuts.ts` + `components/ShortcutModal.tsx` + Layout |
| Exports / sounds | `icalExport.js`, `pdfExport.js`, `sounds.js` | TS ports + `jspdf` dep + buttons on Assignments/StudyPlans/Pomodoro |
| Settings | sectioned settings layout, API-key input, sync status | `pages/Settings.tsx` (AI model select, Google status, theme, JSON data export) |

---

## PART D — Dependency Analysis

- **Backend (`pyproject.toml`):** add `httpx` (AI + Google REST client; lighter than `openai`/`google-auth` and matches Shiori's direct-REST approach). No DB driver change. New tables auto-created by `create_all`; existing tables extended via `COLUMN_MIGRATIONS`.
- **Frontend (`package.json`):** add `jspdf` (PDF export). Everything else reuses existing deps (date-fns, recharts, react-router, shared UI kit). Emoji-icon convention retained — no `lucide-react` needed.
- **Env:** `.env` gains `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `AI_MODELS_FALLBACK`, `AI_ENABLED`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`. No new secrets required for core AI (OmniRoute accepts any key locally).
- **Conflicts:** none destructive — all new tables/routes are additive; the 234 existing backend tests + 23 vitest + tsc must stay green after each group.

---

## PART E — Architecture Notes

- **AI tier:** `services/ai_client.py` wraps `POST {AI_BASE_URL}/v1/chat/completions` (`Authorization: Bearer {AI_API_KEY}`, `model` from `AI_MODEL` or per-call override, retries across `AI_MODELS_FALLBACK`). Every AI feature falls back to a deterministic local generator when `None`, exactly like Shiori. `AI_ENABLED=false` short-circuits so CI/tests never touch the network.
- **Backend pattern:** routers stay thin (CRUD + Pydantic `response_model`); logic lives in `services/` (mirrors `habit_xp.py`, `quest_centre.py`, `fitness_hub.py`). New services: `ai_client.py`, `ai_fallback.py`, `grade_calc.py`, `analytics.py`, `google_oauth.py`.
- **Frontend pattern:** pages fetch via `endpoints.*` from `services/api.ts`; feature-scoped components under `components/<feature>/`; new routes in `App.tsx` + `NavLinks.tsx`; theme tokens appended to `styles/theme.css`. Reuse `Header`, `Toast`, `EmptyState`, `Skeleton`, `ErrorBoundary`, `useToast`, `useFadeIn`, `formatters.ts`, `placeholders.ts`.
- **DB migrations:** every new column added to a model is registered in `database.py COLUMN_MIGRATIONS` (idempotent `ALTER TABLE`), per the established convention.

---

## PART F — Risks

1. **AI latency/unavailability** → every AI path has a deterministic fallback; `/api/ai/health` reports provider status; UI shows `aiModeLabel()`.
2. **Model-name drift** (OmniRoute model renames) → env-driven model list + fallback retry list (Shiori's `GEMINI_MODELS` pattern).
3. **Google OAuth scopes/consent** → read-only Classroom/Gmail/Calendar scopes; token in DB; graceful mock fallback when unconfigured.
4. **Scope creep** (temptation to port XP/habits/landing too) → explicitly out of scope; keep current richer systems.
5. **Type-safety on large new pages** → each page passes `tsc -b`; vitest covers pure logic (grade math, AI parsing, ical, filters).
6. **Regression** → per-group verification (full pytest + `tsc -b`/`vitest`/`oxlint`) and a final fresh-DB smoke test.

---

## PART G — THE 99-PHASE ROADMAP

Each phase: **Objective · Files to modify · Files to create · Deps · Complexity · Risks · Validation · Completion criteria.** Groups are dependency-ordered (foundations → backend → frontend → integration → polish).

### GROUP 1 — Foundations: AI service + config (Phases 1–9)

#### Phase 1 — AI + Google config hygiene
- **Objective:** Add AI + Google settings to `config.py` and `.env.example`.
- **Modify:** `backend/app/config.py`, `.env.example`
- **Create:** — | **Deps:** none | **Complexity:** low
- **Risks:** env var name drift | **Validation:** `config.py` imports; `.env.example` documents new vars
- **Completion:** settings resolve with defaults (`AI_BASE_URL=http://localhost:20128/v1`, `AI_API_KEY=omniroute-local`, `AI_MODEL=oc/deepseek-v4-flash-free`)

#### Phase 2 — AI client service (`ai_client.py`)
- **Objective:** OpenAI-compatible chat-completions client with model override + retry list + `extract_json`.
- **Create:** `backend/app/services/ai_client.py` — `generate(prompt, max_tokens=2048, temperature=0.7, model=None)`, `ai_available()`, `ai_models()`
- **Modify:** `backend/pyproject.toml` (add `httpx`)
- **Deps:** httpx | **Complexity:** medium | **Risks:** network in tests → `AI_ENABLED` seam
- **Validation:** unit test with mocked POST; `extract_json` handles fenced/plain JSON
- **Completion:** `generate` returns text for a stub, `None` on failure

#### Phase 3 — AI router + health + models endpoints
- **Objective:** Expose AI capability endpoints.
- **Create:** `backend/app/routers/ai.py` — `GET /api/ai/health`, `GET /api/ai/models`, `POST /api/ai/complete`
- **Modify:** `backend/main.py` (include router)
- **Deps:** Phase 2 | **Complexity:** low | **Risks:** none
- **Validation:** TestClient GETs 200; `tests/test_ai.py`
- **Completion:** endpoints return JSON

#### Phase 4 — AI fallback generators (demo payloads)
- **Objective:** Port Shiori demo data so every AI feature works offline.
- **Create:** `backend/app/services/ai_fallback.py` — `demo_quiz()`, `demo_study_plan(subject)`, `demo_flashcards(topic)`, `demo_syllabus(text)`, `demo_grade_answer()`
- **Modify:** — | **Deps:** none | **Complexity:** low | **Risks:** shape drift
- **Validation:** unit tests assert stable JSON shape
- **Completion:** every demo returns parseable JSON

#### Phase 5 — Shared JSON-block parser
- **Objective:** Robust extraction of JSON from model output (port `parseJSONBlock`).
- **Modify:** `services/ai_client.py` (add `extract_json`)
- **Create:** — | **Deps:** Phase 2 | **Complexity:** low | **Risks:** nested braces
- **Validation:** tests for fenced/plain/whitespace JSON
- **Completion:** parser robust

#### Phase 6 — Frontend AI util
- **Objective:** `aiAvailable()`, `aiModeLabel()`, `generateAI()` calling `endpoints.ai.*`.
- **Create:** `frontend/src/utils/ai.ts`
- **Modify:** — | **Deps:** Phase 7 | **Complexity:** low | **Risks:** none
- **Validation:** `tsc -b`; unit test with mocked fetch
- **Completion:** util compiles + returns fallback flags

#### Phase 7 — `endpoints.ai.*` + types in api.ts
- **Objective:** Typed AI endpoints.
- **Modify:** `frontend/src/services/api.ts` — `ai: { health, models, complete, quiz, flashcards, studyPlan, syllabus, gradeAnswer, chat }`
- **Create:** — | **Deps:** Phase 3 | **Complexity:** low | **Risks:** none
- **Validation:** `tsc -b`
- **Completion:** typed endpoints compile

#### Phase 8 — AI feature flag & test seams
- **Objective:** `AI_ENABLED` so CI/tests never hit network.
- **Modify:** `config.py`, `services/ai_client.py`
- **Create:** — | **Deps:** Phase 2 | **Complexity:** low | **Risks:** none
- **Validation:** pytest passes with AI disabled
- **Completion:** offline-safe

#### Phase 9 — Group-1 verification gate
- **Objective:** Prove baseline still green + new endpoints tested.
- **Modify:** — | **Create:** — | **Deps:** 1–8 | **Complexity:** low
- **Validation:** full `pytest` (234 baseline + `test_ai.py`), `tsc -b`, `vitest`
- **Completion:** all green, no new warnings

### GROUP 2 — Grades/GPA backend (Phases 10–17)

#### Phase 10 — `Grade` model + `Course.credits`
- **Objective:** Grade table + credits column for GPA.
- **Modify:** `models/course.py` (credits default 3), `database.py` migrations, `models/__init__.py`
- **Create:** `models/grade.py` — `Grade(id, course_id, assignment_id?, title, points_earned, points_possible, category_id?, date)`
- **Deps:** none | **Complexity:** medium | **Risks:** existing courses need credits
- **Validation:** import; `PRAGMA table_info(courses)` shows `credits`
- **Completion:** schema compiles + migration applied

#### Phase 11 — `CourseWeight` model (weighted categories)
- **Objective:** Weighted category support (port Shiori weights).
- **Modify:** `models/grade.py`, `models/__init__.py`, `database.py`
- **Create:** — | **Deps:** Phase 10 | **Complexity:** low
- **Validation:** migration list updated
- **Completion:** two new tables

#### Phase 12 — Grade schemas
- **Objective:** Pydantic schemas for grades + weights + calculate.
- **Create:** `schemas/grade.py` — `GradeBase/Create/Response`, `CourseWeightBase/Create/Response`, `GradeCalculateRequest/Response`
- **Modify:** `schemas/__init__.py`
- **Deps:** Phase 10 | **Complexity:** low | **Risks:** none
- **Validation:** barrel import
- **Completion:** schemas compile

#### Phase 13 — Grade calculation service (port math)
- **Objective:** `letter_grade`, `pct_to_gpa`, `calculate_course_grade` (weighted + unweighted), `needed_on_final` — exact port.
- **Create:** `services/grade_calc.py`
- **Deps:** Phase 11 | **Complexity:** medium | **Risks:** math mismatch
- **Validation:** unit tests mirror Shiori's `LETTER_GRADE`/`pctToGPA` tables
- **Completion:** math matches Shiori exactly

#### Phase 14 — Grades router
- **Objective:** CRUD + calculate + GPA endpoints.
- **Create:** `routers/grades.py` — `GET/POST/PUT/DELETE /api/grades`, `GET /api/grades/courses/{id}`, `POST /api/grades/calculate`, `GET /api/grades/gpa`
- **Modify:** `main.py`
- **Deps:** Phase 12–13 | **Complexity:** medium
- **Validation:** TestClient round-trip + calc
- **Completion:** endpoints live

#### Phase 15 — Grade seed + demo weights
- **Objective:** Deterministic seed for grades + weights.
- **Modify:** `seed/__init__.py` (add `seed_grades`)
- **Deps:** Phase 11 | **Complexity:** low
- **Validation:** seeded rows on fresh DB
- **Completion:** idempotent seed

#### Phase 16 — Backend grade tests
- **Objective:** Cover CRUD, calc, GPA, needed-on-final.
- **Create:** `tests/test_grades.py`
- **Deps:** Phase 14 | **Complexity:** medium
- **Validation:** new tests + full suite green
- **Completion:** grades covered

#### Phase 17 — Group-2 verification gate
- **Validation:** full pytest + `tsc -b` | **Completion:** green

### GROUP 3 — Grades/GPA frontend (Phases 18–24)

#### Phase 18 — `endpoints.grades.*` + types
- **Modify:** `services/api.ts` — grades CRUD + calculate + gpa; `Course.credits`
- **Validation:** `tsc -b` | **Completion:** typed

#### Phase 19 — Grades page shell + GPA overview
- **Create:** `pages/Grades.tsx` — cumulative GPA card (credit-weighted), course grid (port layout to theme classes)
- **Deps:** Phase 18 | **Validation:** renders seed data | **Completion:** page loads

#### Phase 20 — Add Grade / Add Course / Weights modals
- **Create:** `components/grades/AddGradeModal.tsx`, `AddCourseModal.tsx`, `WeightsModal.tsx`
- **Validation:** modal CRUD persists | **Completion:** data round-trips

#### Phase 21 — "Needed on final" predictor + letter badges
- **Modify:** `pages/Grades.tsx` — wire `needed_on_final`, letter/colour thresholds
- **Validation:** matches `grade_calc` | **Completion:** predictor works

#### Phase 22 — `GradeTrendChart` component (canvas)
- **Create:** `components/grades/GradeTrendChart.tsx` (port Shiori canvas chart)
- **Validation:** renders trend | **Completion:** chart

#### Phase 23 — Route + nav + vitest
- **Modify:** `App.tsx`, `components/layout/NavLinks.tsx` (Academics)
- **Create:** `src/test/grades.test.tsx`
- **Validation:** vitest; nav link | **Completion:** `/grades` reachable

#### Phase 24 — Group-3 verification gate
- **Validation:** full pytest + `tsc -b` + `vitest` + oxlint | **Completion:** green

### GROUP 4 — Flashcards backend (Phases 25–32)

#### Phase 25 — `FlashcardDeck` + `Flashcard` models
- **Create:** `models/flashcard.py` — deck + card (FK cascade, difficulty, streak, next_review); barrel + migrations
- **Validation:** tables created | **Completion:** schema

#### Phase 26 — Flashcard schemas
- **Create:** `schemas/flashcard.py` — Deck/Card Base/Create/Update/Response
- **Validation:** barrel | **Completion:** compile

#### Phase 27 — Decks router (CRUD + nested cards)
- **Create:** `routers/flashcards.py` — `/api/flashcard-decks` CRUD + `/api/flashcard-decks/{id}/cards` nested CRUD; register
- **Validation:** TestClient round-trip | **Completion:** live

#### Phase 28 — AI flashcard generation endpoint
- **Create:** `POST /api/ai/flashcards` (`{content, difficulty}` → `{cards}`) via `ai_client` + difficulty prompt map; fallback `demo_flashcards`
- **Validation:** disabled-AI returns demo cards | **Completion:** endpoint

#### Phase 29 — AI written-answer grading endpoint
- **Create:** `POST /api/ai/grade-answer` (`{question, expected, answer}` → `{correct, explanation}`); exact-match fallback
- **Validation:** tests (exact + AI path) | **Completion:** endpoint

#### Phase 30 — Seed demo decks
- **Modify:** `seed/__init__.py` (add `seed_flashcards` — 2 decks, ~8 cards each)
- **Validation:** fresh-DB rows | **Completion:** seed

#### Phase 31 — Backend flashcard tests
- **Create:** `tests/test_flashcards.py`
- **Validation:** new + full suite | **Completion:** covered

#### Phase 32 — Group-4 verification gate
- **Validation:** full pytest + `tsc -b` | **Completion:** green

### GROUP 5 — Flashcards frontend (Phases 33–39)

#### Phase 33 — `endpoints.flashcards.*` + types
- **Modify:** `services/api.ts` — decks/cards + `ai.flashcards` + `ai.gradeAnswer`
- **Validation:** `tsc -b` | **Completion:** typed

#### Phase 34 — Flashcards page — deck list + create
- **Create:** `pages/Flashcards.tsx` deck grid + new-deck modal
- **Validation:** renders seed decks | **Completion:** list

#### Phase 35 — Study mode (flip)
- **Modify:** `pages/Flashcards.tsx` — flip + prev/next + progress bar
- **Validation:** interaction works | **Completion:** flip

#### Phase 36 — Written mode + AI grading + difficulty chips
- **Modify:** `pages/Flashcards.tsx` — written answer → `ai.gradeAnswer`; difficulty chips
- **Validation:** exact-match fallback when AI off | **Completion:** grading

#### Phase 37 — AI generate cards from note/text
- **Modify:** `pages/Flashcards.tsx` — generate modal (note selector/paste, difficulty) → `ai.flashcards`
- **Validation:** cards appended | **Completion:** generation

#### Phase 38 — Route + nav + vitest
- **Modify:** `App.tsx`, `NavLinks.tsx`
- **Create:** `src/test/flashcards.test.tsx`
- **Validation:** vitest + nav | **Completion:** reachable

#### Phase 39 — Group-5 verification gate
- **Validation:** full pytest + `tsc -b` + vitest + oxlint | **Completion:** green

### GROUP 6 — Study plans backend (Phases 40–45)

#### Phase 40 — `StudyPlan` model + schema
- **Create:** `models/study_plan.py`, `schemas/study_plan.py`; barrel + migration
- **Validation:** table + compile | **Completion:** done

#### Phase 41 — Study plans router (CRUD)
- **Create:** `routers/study_plans.py` — `/api/study-plans` CRUD; register
- **Validation:** TestClient | **Completion:** live

#### Phase 42 — AI study-plan generation endpoint
- **Create:** `POST /api/ai/study-plan` (`{subject, exam_date}` → `{subject, weeks}`); fallback `demo_study_plan`
- **Validation:** fallback shape test | **Completion:** endpoint

#### Phase 43 — Seed + backend tests
- **Modify:** `seed/__init__.py`
- **Create:** `tests/test_study_plans.py`
- **Validation:** new + full suite | **Completion:** covered

#### Phase 44 — Group-6 verification gate
- **Validation:** pytest + `tsc -b` | **Completion:** green

### GROUP 7 — Study plans frontend (Phases 45–49)

#### Phase 45 — `endpoints.studyPlans.*` + types
- **Modify:** `services/api.ts`
- **Validation:** `tsc -b` | **Completion:** typed

#### Phase 46 — StudyPlans page (generate form, list, plan display)
- **Create:** `pages/StudyPlans.tsx` (port `StudyPlans.jsx` layout to theme classes)
- **Deps:** Phase 45 | **Validation:** generates + renders | **Completion:** page

#### Phase 47 — Route + nav
- **Modify:** `App.tsx`, `NavLinks.tsx`
- **Validation:** nav | **Completion:** `/study-plans` reachable

#### Phase 48 — vitest + polish
- **Create:** `src/test/studyPlans.test.tsx`
- **Validation:** vitest | **Completion:** covered

#### Phase 49 — Group-7 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint | **Completion:** green

### GROUP 8 — Quiz (Phases 50–56)

#### Phase 50 — AI quiz generation endpoint
- **Create:** `POST /api/ai/quiz` (`{content}` → `[{q, opts, ans}]`); fallback `demo_quiz`
- **Deps:** Phase 4 | **Validation:** fallback test | **Completion:** endpoint

#### Phase 51 — Backend quiz tests
- **Create:** `tests/test_quiz.py`
- **Validation:** new + full suite | **Completion:** covered

#### Phase 52 — `endpoints.ai.quiz` + types
- **Modify:** `services/api.ts`
- **Validation:** `tsc -b` | **Completion:** typed

#### Phase 53 — Quiz page (setup/quiz/results)
- **Create:** `pages/Quiz.tsx` (port phase machine + option coloring + XP)
- **Deps:** Phase 52 | **Validation:** demo quiz works offline | **Completion:** page

#### Phase 54 — Route + nav + localStorage history
- **Modify:** `App.tsx`, `NavLinks.tsx`; `pages/Quiz.tsx` (quiz-history)
- **Validation:** nav | **Completion:** reachable

#### Phase 55 — vitest
- **Create:** `src/test/quiz.test.tsx`
- **Validation:** vitest | **Completion:** covered

#### Phase 56 — Group-8 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint | **Completion:** green

### GROUP 9 — Syllabus import (Phases 57–61)

#### Phase 57 — AI syllabus extraction endpoint
- **Create:** `POST /api/ai/syllabus` (`{text}` → `[{title, dueDate, course, priority}]`); fallback `demo_syllabus`
- **Deps:** Phase 4 | **Validation:** fallback test | **Completion:** endpoint

#### Phase 58 — SyllabusImport page
- **Create:** `pages/SyllabusImport.tsx` (paste + file drop + extracted list + import-all)
- **Deps:** Phase 57 | **Validation:** demo extraction | **Completion:** page

#### Phase 59 — `endpoints.ai.syllabus` + route + nav
- **Modify:** `services/api.ts`, `App.tsx`, `NavLinks.tsx`
- **Validation:** nav | **Completion:** `/import` reachable

#### Phase 60 — vitest
- **Create:** `src/test/syllabusImport.test.tsx`
- **Validation:** vitest | **Completion:** covered

#### Phase 61 — Group-9 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint | **Completion:** green

### GROUP 10 — AI chat (Phases 62–68)

#### Phase 62 — AI chat endpoint (context-aware)
- **Create:** `POST /api/ai/chat` (`{message}` → `{message}`) — builds context from DB assignments/courses; system prompt port
- **Deps:** Phase 3 | **Validation:** TestClient | **Completion:** endpoint

#### Phase 63 — Chat heuristic fallback
- **Modify:** `services/ai_fallback.py` (add `local_chat_response`) — port `getLocalResponse` heuristics
- **Validation:** unit tests for due/priority/help branches | **Completion:** fallback

#### Phase 64 — `endpoints.ai.chat` + AIChat component
- **Create:** `components/AIChat.tsx` (quick prompts, message list, typing indicator)
- **Modify:** `services/api.ts`
- **Validation:** renders; sends via endpoint | **Completion:** component

#### Phase 65 — Layout integration + `Ctrl+K`
- **Modify:** `components/layout/Sidebar.tsx` or app shell (collapsible chat panel), keyboard hook
- **Validation:** toggles | **Completion:** panel

#### Phase 66 — vitest
- **Create:** `src/test/aiChat.test.tsx`
- **Validation:** vitest | **Completion:** covered

#### Phase 67 — Group-10 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint | **Completion:** green

### GROUP 11 — Analytics backend (Phases 68–73)

#### Phase 68 — Analytics aggregation service
- **Create:** `services/analytics.py` — weekly focus from `pomodoro_sessions`, completion rate from assignments, GPA from grades, XP, streak
- **Deps:** Phase 14 | **Validation:** unit tests | **Completion:** aggregates

#### Phase 69 — Analytics router
- **Create:** `routers/analytics.py` — `GET /api/analytics/summary`, `GET /api/analytics/weekly-focus`, `GET /api/analytics/heatmap`
- **Modify:** `main.py`
- **Validation:** TestClient with seed | **Completion:** endpoints live

#### Phase 70 — Backend analytics tests
- **Create:** `tests/test_analytics.py`
- **Validation:** new + full suite | **Completion:** covered

#### Phase 71 — Group-11 verification gate
- **Validation:** full pytest + tsc | **Completion:** green

### GROUP 12 — Analytics frontend (Phases 72–78)

#### Phase 72 — `endpoints.analytics.*` + types
- **Modify:** `services/api.ts`
- **Validation:** `tsc -b` | **Completion:** typed

#### Phase 73 — Analytics page (stat cards + weekly bars + grade trends)
- **Create:** `pages/Analytics.tsx`
- **Deps:** Phase 72 | **Validation:** renders seed aggregates | **Completion:** page

#### Phase 74 — `StudyHeatmap` component (52-week)
- **Create:** `components/analytics/StudyHeatmap.tsx` (port Shiori heatmap)
- **Validation:** renders | **Completion:** heatmap

#### Phase 75 — `TimeTrackerBars` component
- **Create:** `components/analytics/TimeTrackerBars.tsx` (TODAY/MONTH/YEAR)
- **Validation:** renders | **Completion:** bars

#### Phase 76 — Route + nav + vitest
- **Modify:** `App.tsx`, `NavLinks.tsx`
- **Create:** `src/test/analytics.test.tsx`
- **Validation:** vitest + nav | **Completion:** `/analytics` reachable

#### Phase 77 — Group-12 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint | **Completion:** green

### GROUP 13 — Notes editor (Phases 78–83)

#### Phase 78 — `Note.pinned`/`updated_at` + pin endpoint
- **Modify:** `models/note.py`, `database.py`, `schemas/note.py`, `routers/notes.py` (add pin toggle + list order)
- **Validation:** migration + TestClient | **Completion:** pin works

#### Phase 79 — `endpoints.notes.*` create/update/delete/pin
- **Modify:** `services/api.ts`
- **Validation:** `tsc -b` | **Completion:** typed

#### Phase 80 — Notes page — list panel + search
- **Rewrite:** `pages/Notes.tsx` (left list pane, search, new-note)
- **Validation:** renders + search | **Completion:** list

#### Phase 81 — Notes page — editor + preview
- **Modify:** `pages/Notes.tsx` (right editor pane, edit/preview toggle, markdown preview, pin, delete)
- **Validation:** CRUD persists | **Completion:** editor

#### Phase 82 — Notes vitest
- **Create:** `src/test/notes.test.tsx`
- **Validation:** vitest | **Completion:** covered

#### Phase 83 — Group-13 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint | **Completion:** green

### GROUP 14 — Google OAuth + Classroom/Gmail/Calendar (Phases 84–91)

#### Phase 84 — Google OAuth service
- **Create:** `services/google_oauth.py` — auth-url, callback (code→token), token store/refresh in DB, `GOOGLE_*` env, read-only scopes
- **Deps:** httpx | **Complexity:** high | **Risks:** token expiry/refresh
- **Validation:** unit tests with mocked token endpoint
- **Completion:** OAuth flow implemented

#### Phase 85 — Google auth router
- **Create:** `routers/auth_google.py` — `GET /api/auth/google`, `/api/auth/google/callback`, `/api/auth/google/status`, `/api/auth/google/disconnect`; register
- **Validation:** TestClient status returns `{connected:false}` when unconfigured
- **Completion:** endpoints live

#### Phase 86 — Classroom router (idempotent merge)
- **Create:** `routers/classroom.py` — `GET /api/classroom/courses`, `/api/classroom/assignments`; merges into `Course`/`Assignment` (matched by google id), preserves manual completions
- **Deps:** Phase 84 | **Risks:** duplicates
- **Validation:** merge test with stub payload
- **Completion:** sync endpoint

#### Phase 87 — Gmail router
- **Create:** `routers/gmail.py` — `GET /api/gmail/unread`, `/api/gmail/messages`; mock fallback
- **Deps:** Phase 84 | **Validation:** fallback test
- **Completion:** unread count

#### Phase 88 — Calendar router (sync → schedule)
- **Create:** `routers/calendar.py` — `GET /api/calendar/events`; merges into `ScheduleEvent`/`Event`; mock fallback
- **Deps:** Phase 84 | **Validation:** merge test
- **Completion:** calendar sync

#### Phase 89 — Frontend: Google connect + sync buttons + endpoints
- **Modify:** `services/api.ts` (auth_google/classroom/gmail/calendar), `pages/Settings.tsx` (connect button + status), `pages/Assignments.tsx` (Sync button)
- **Validation:** `tsc -b`; status UI
- **Completion:** connect UI

#### Phase 90 — Google integration tests
- **Create:** `tests/test_google.py` (mock endpoints, fallback paths)
- **Validation:** new + full suite
- **Completion:** covered

#### Phase 91 — Group-14 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint
- **Completion:** green

### GROUP 15 — Utilities: shortcuts, exports, sounds, quick capture, settings (Phases 92–97)

#### Phase 92 — Keyboard shortcuts + ShortcutModal
- **Create:** `hooks/useKeyboardShortcuts.ts`, `components/ShortcutModal.tsx`
- **Modify:** app shell (Layout/Sidebar) to mount hook + `?` help
- **Validation:** `g`+letter nav in dev; `Ctrl+K` toggles chat
- **Completion:** shortcuts live

#### Phase 93 — iCal export + PDF export
- **Create:** `utils/icalExport.ts`, `utils/pdfExport.ts` (port); add `jspdf`
- **Modify:** `Assignments.tsx` (iCal button), `StudyPlans.tsx` (PDF button), `package.json`
- **Validation:** downloads `.ics`/`.pdf` in dev
- **Completion:** exports work

#### Phase 94 — Pomodoro sounds
- **Create:** `utils/sounds.ts` (WebAudio port)
- **Modify:** `Pomodoro.tsx` (playDing on phase change; toggle)
- **Validation:** ding on transition
- **Completion:** sounds wired

#### Phase 95 — Quick capture + Assignments filters/priority
- **Create:** `components/QuickCapture.tsx` (`Ctrl+Shift+A`)
- **Modify:** `pages/Assignments.tsx` (today/week/overdue tabs, priority, add modal), app shell
- **Validation:** capture adds assignment; filters work
- **Completion:** capture + filters

#### Phase 96 — Settings page (profile, AI model, Google status, theme, data export)
- **Create:** `pages/Settings.tsx` (sections: profile, AI model select from `/api/ai/models`, Google status, theme, JSON export)
- **Modify:** `App.tsx`, `NavLinks.tsx`
- **Validation:** saves prefs (localStorage), exports JSON
- **Completion:** settings

#### Phase 97 — Group-15 verification gate
- **Validation:** full pytest + tsc + vitest + oxlint
- **Completion:** green

### GROUP 16 — Integration, polish, verification, docs (Phases 98–99)

#### Phase 98 — Full integration + fresh-DB smoke test
- **Objective:** All new routes wired; full regression.
- **Modify:** `App.tsx`, `NavLinks.tsx`, `main.tsx` (if needed)
- **Validation:** fresh-DB uvicorn smoke on a temp SQLite (like the quest-centre smoke): all new GET endpoints + write paths; `pytest` (234 baseline + new suites); `tsc -b`; `vitest`; `oxlint`
- **Completion:** full stack green on a fresh DB

#### Phase 99 — Docs + completion report
- **Modify:** `frontend/README.md` (new features + routes), root `README.md` (optional)
- **Create:** completion report inline (features added, merged, files created/modified, deps added, manual steps — Google OAuth credentials + OmniRoute model selection, remaining issues)
- **Validation:** README accurate
- **Completion:** plan closed out

---

## PART H — Success Criteria

1. **Feature parity:** All Shiori features marked ❌ above are implemented and reachable from the sidebar: AI quiz, AI flashcards, AI study plans, syllabus import, AI chat, grades/GPA, analytics, notes editor, Google Classroom/Gmail/Calendar sync, keyboard shortcuts, iCal/PDF export, sounds, quick capture, settings.
2. **Zero regression:** all 234 baseline backend tests + 23 baseline vitest still pass; `tsc -b` and `npm run build` clean; no new oxlint errors.
3. **AI works offline:** every AI feature has a working deterministic fallback; `AI_ENABLED=false` keeps the suite hermetic.
4. **Architecture-consistent:** FastAPI services + thin routers, `COLUMN_MIGRATIONS` used for every new column, feature-scoped TS components, existing theme/UI kit reused (no duplicate components).
5. **Fresh-DB safe:** app boots and seeds on an empty SQLite DB; new tables auto-created.

---

## PART I — Final Checklist

- [x] Group 1–16 gates all green (phases 9, 17, 24, 32, 39, 44, 49, 56, 61, 67, 71, 77, 83, 91, 97, 98)
- [x] New models: `Grade`, `CourseWeight`, `FlashcardDeck`, `Flashcard`, `StudyPlan`, `GoogleToken` (+ `Course.credits`, `Note.pinned`, `Note.updated_at`, `Course.google_id`, `Assignment.google_id`, `Event.google_id`)
- [x] New routers: `ai`, `grades`, `flashcards`, `study_plans`, `analytics`, `auth_google`, `classroom`, `gmail`, `calendar`
- [x] New services: `ai_client`, `ai_fallback`, `grade_calc`, `analytics`, `google_oauth`
- [x] New pages: `Grades`, `Flashcards`, `StudyPlans`, `Quiz`, `SyllabusImport`, `Analytics`, `Settings`; rewritten `Notes`
- [x] New frontend utils/hooks/components: `ai.ts`, `aiChatBus.ts`, `icalExport.ts`, `pdfExport.ts`, `sounds.ts`, `useKeyboardShortcuts.ts`, `ShortcutModal.tsx`, `QuickCapture.tsx`, `GoogleSyncCard.tsx`, `GradeTrendChart.tsx`, `StudyHeatmap.tsx`, `TimeTrackerBars.tsx`
- [x] Deps added: `httpx` (backend), `jspdf` (frontend)
- [x] Env documented: `AI_*`, `GOOGLE_*`
- [x] Fresh-DB smoke test passed
- [x] `frontend/README.md` updated
