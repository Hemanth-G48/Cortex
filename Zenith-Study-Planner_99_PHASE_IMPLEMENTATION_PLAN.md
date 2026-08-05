# 99-Phase Implementation Plan — Zenith-Study-Planner → Student Life OS

| | |
|---|---|
| **Source (Reference) Repository** | `Zenith-Study-Planner/` (AI-Powered Study Planner — feature spec) |
| **Target Repository** | `productivity_app/` — **Student Life OS** (FastAPI + SQLAlchemy/SQLite backend, React 19 + TypeScript + Vite frontend) |
| **Plan Status** | PLANNED — awaiting phase-by-phase execution |
| **Baseline (verified 2026-08-02)** | Backend pytest **200/200** green · Frontend `tsc -b` clean · `npm run build` clean · Vitest **25/25** · oxlint exit 0 (5 pre-existing warnings) |

---

# PART 0 — Executive Summary

`Zenith-Study-Planner` is an **AI-Powered Study Planner** reference. In its current checkout it is a **README-only feature spec** (no application source), describing eight high-level capabilities: a reinforcement-learning–driven scheduler, KNN friend recommendations, a chatbot with document Q&A (Gemini + FAISS), mood-driven session customization, smart content & break suggestions, sleep-tracker integration, gamification & social engagement (leaderboards, achievements, challenges), and progress visualization (interactive timeline, social feed).

The target — **Student Life OS** — is a mature, working, gamified productivity suite. It already covers *non-AI* study planning extremely well: courses, assignments, exams, tasks, projects, notes, journal, habits (with XP/penalties, heatmaps, streaks), pomodoro sessions, quests/missions/rewards/character, life areas, fitness hub, vault, life planner, and a calendar/timetable — all behind 28 registered FastAPI routers and 31 frontend routes.

**The gap is not productivity — it is intelligence + social + personalization.** The target has no AI layer, no chat/document Q&A, no mood tracking, no sleep tracking, no adaptive scheduler, no social graph (friends/leaderboards/contests/feed), and no study analytics. Every one of the eight reference capabilities is either **missing** or only **partially** covered by existing gamification.

This plan brings Student Life OS to feature parity with the reference (and beyond, by wiring the new intelligence features into the existing gamified engine) while **preserving its architecture, conventions, and all existing functionality**. Because the reference ships no code, there is nothing to copy verbatim; instead the plan **reuses the target's own established patterns** (router/model/schema/service layout, `migrate_schema()` column migrations, `seed_database()`, demo-fallback data, theme-based CSS, shared components, `services/api.ts` client, vitest/pytest gates) for every new module, and introduces a thin, provider-agnostic AI abstraction so the app stays runnable **without any external API keys**.

The roadmap is organized into **16 dependency-ordered groups (G1–G16)** covering exactly **99 independently implementable and verifiable phases**: foundations → mood → sleep → analytics → adaptive planner → chatbot/document Q&A → frontends → social → timeline/feed → achievements → settings → verification/docs.

---

# PART 1 — Repository Overview

## 1.1 Reference: Zenith-Study-Planner

| Aspect | Detail |
|---|---|
| **Type** | AI-Powered Study Planner (product concept / spec) |
| **Contents** | `README.md` only — no application source in this checkout |
| **Stack (per spec)** | React (Vite) + Tailwind + Framer Motion + Recharts · Flask REST API · FAISS vector search · Gemini AI · Firebase Realtime DB + Firestore |
| **Core idea** | Schedules that *learn* (PPO), study habits that *connect* (KNN friends), documents that *answer* (chatbot + FAISS), sessions that *adapt* (mood), and motivation that is *social* (leaderboards, contests, feed) |

### Reference feature spec (F1–F8)
| ID | Capability | Spec description |
|---|---|---|
| F1 | **RL-driven scheduler** | PPO optimization loop; adaptive daily/weekly plans; sleep-aware balancing of study vs. rest |
| F2 | **KNN friend recommendations** | Study-habit clustering; weekly friend goals; contest mode ranked by hours/subjects |
| F3 | **Chatbot with document Q&A** | Gemini chat; upload PDF/text/DOCX; FAISS indexing; targeted, context-aware answers |
| F4 | **Mood-driven customization** | Input `stressed / focused / relaxed`; session length, break type, resource difficulty adapt |
| F5 | **Smart content & break suggestions** | Study-history analytics → weak/strong subject recs; creative breaks (mini-games, mindfulness, stretches) |
| F6 | **Sleep tracker integration** | Historical sleep logs; optimal bedtime/wake-up recommendations; schedule rebalancing |
| F7 | **Gamification & social** | Leaderboards (hours/streaks/quiz); achievements & badges; local challenges |
| F8 | **Progress visualization** | Interactive timeline (sessions, tasks, milestones); social feed (friend streaks, contest highlights, shared achievements) |

## 1.2 Target: Student Life OS (productivity_app)

| Aspect | Detail |
|---|---|
| **Type** | Full-stack gamified student productivity OS (working, tested, shipped to `main`) |
| **Backend** | Python 3.11+ · **FastAPI** · SQLAlchemy 2 · **SQLite** · Pydantic v2 · pydantic-settings |
| **Frontend** | **React 19** · TypeScript strict · Vite · react-router-dom v7 · @tanstack/react-query · recharts · date-fns · oxlint · vitest |
| **Entry points** | `backend/main.py` (28 routers, lifespan `create_all` + `migrate_schema()` + `seed_database()`) · `frontend/src/App.tsx` (31 routes) |
| **Data** | SQLite (`student_os.db`) with idempotent `COLUMN_MIGRATIONS` ALTER-table registry |
| **Auth** | Minimal single-user `POST /api/auth/login` returning the first user (no password, no tokens) |
| **Theming** | `data-theme` CSS files: `rpg-theme.css`, `pixel-art.css`, `habit-tracker.css`, `fitness-hub.css`, `quest-centre.css` |

### Existing backend domains (28 routers)
`assignments` · `auth` · `characters` · `courses` · `daily_logs` · `daily_quests` · `eisenhower` · `events` · `fitness` · `fitness_hub` · `habits` · `habit_tracker` · `journal` · `life_areas` · `life_planner` · `missions` · `notes` · `pomodoro` · `projects` · `quest_centre` · `quests` · `rewards` · `schedule_events` · `tasks` · `vault` · `weekly_reset` (+ `auth`, `health`)

### Existing frontend routes (31)
`/` · `/courses` · `/tasks` · `/schedule` · `/assignments` · `/exams` · `/goals` · `/notes` · `/habits` · `/pomodoro` · `/fitness` · `/journal` · `/quests` · `/projects` · `/life-areas` · `/character` · `/rewards` · `/missions` · `/rpg-dashboard` · `/vault` · `/vault-database` · `/habits/:habitId/report` · `/habits/archive` · `/goals-setting` · `/habit-logs` · `/grid-design` · `/habit-report` · `/archive-habits` · `/life-planner` · `/quest-centre` · `/habit-tracker` · `/fitness-hub`

### Existing data models (from `app/models/__init__.py`)
User · Course · Assignment · Exam · Note · Goal · Task · Reminder · Schedule · Habit · HabitLog · PomodoroSession · Workout · FitnessGoal · Exercise · MuscleGroup · WorkoutSplit · Expense · PersonalRecord · DietPlan · JournalEntry · Quest · QuestTask · Project · ProjectTask · LifeArea · Character · Reward · Mission · MissionTask · ScheduleEvent · DailyLog · Event

---

# PART 2 — Architecture Comparison

| Dimension | Zenith-Study-Planner (spec) | Student Life OS (target) | Verdict / strategy |
|---|---|---|---|
| **API framework** | Flask | FastAPI (async-ready, Pydantic validation) | Keep **FastAPI** — superior, already standard |
| **Database** | Firebase RTDB + Firestore | SQLAlchemy + SQLite | Keep **SQLite + SQLAlchemy** — local-first, transactional; add relational tables for social/sleep/mood/AI |
| **Migrations** | — | `migrate_schema()` idempotent ALTER registry | **Reuse** this pattern for every new column |
| **Vector search** | FAISS | none | Add a **`vector_store.py` abstraction** — numpy-cosine default, optional FAISS swap |
| **LLM / AI** | Gemini API | none | Add a **provider-agnostic `ai_client.py`** with env-driven settings + deterministic demo fallback |
| **Frontend** | React Vite + Tailwind + Framer Motion + Recharts | React 19 + TS strict + Vite + react-query + recharts | Keep target stack; add new pages/components in the existing pattern |
| **State / data fetching** | (implied custom) | `services/api.ts` + @tanstack/react-query + hooks | **Reuse** `services/api.ts` + hooks + `types/index.ts` |
| **Theming** | Tailwind utilities | `data-theme` CSS custom-property themes | **Reuse** theme system; add a `study-os` theme if a new palette is wanted |
| **Auth** | (implied multi-user social) | single-user stub login | **Enhance minimally** to multi-user (password hash + scoped rows) — required for F2/F7/F8 |
| **Tests** | — | pytest 200 + vitest 25 | **Reuse** both gates per phase |

**Architectural rules for integration**
1. Preserve the target's `router → model → schema → service → seed` layout and `main.py` router registration.
2. Every new column goes through `COLUMN_MIGRATIONS`; every new table through `Base.metadata.create_all`.
3. No external service is required to run the app: all AI features ship a deterministic **demo fallback** (matching the project's demo-data convention).
4. All new frontend features use `services/api.ts`, `types/index.ts`, shared components (`Toast`, `Skeleton`, `EmptyState`, `ErrorBoundary`, `ThemeSwitcher`), and are gated by vitest + `tsc -b`.
5. **No duplicate logic**: reuse `habit_xp.py`, `quest_centre.py`, `fitness_hub.py`, pomodoro, and course/assignment services rather than re-implementing.

---

# PART 3 — Complete Feature Inventory & Comparison

Legend: ✅ Fully implemented · ◑ Partially implemented · ❌ Missing · 🎨 Better in target · ⏸ Not applicable

| # | Reference feature | Status | Where in target today | Gap |
|---|---|---|---|---|
| F1 | RL-driven scheduler | ❌ | `Schedule`/`TimetableGrid`/`ScheduleEvent` are static CRUD; `WeeklyCalendar` is display-only | No planner engine, no adaptation, no sleep/mood input |
| F2 | KNN friend recommendations | ❌ | Single-user app; no friends/relations | No social graph, no similarity engine, no contests |
| F3 | Chatbot + document Q&A | ❌ | `Notes`/`Vault` store text but no AI, no chat, no upload parsing | No chat, no document ingestion, no vector retrieval |
| F4 | Mood-driven customization | ❌ | `DailyLog`/`Journal` accept free-form text | No structured mood, no session-parameter mapping |
| F5 | Smart content & break suggestions | ❌ | Habit analytics + `FitnessHub` offer stats but no recs | No suggestion engine, no creative-break catalog |
| F6 | Sleep tracker | ❌ | none | No sleep model, no bedtime/wake recs |
| F7 | Gamification & social | ◑ | Quests, missions, rewards, XP, levels, streaks, badges (`RpgBadge`) are rich | No leaderboards, no achievements catalog/unlocks, no challenges |
| F8 | Progress visualization | ◑ | Heatmaps, weekly calendars, progress bars, radar chart, week grid | No interactive **timeline**, no **social feed** |

**Features the target already exceeds (not planned for back-port):** quest/mission/reward gamification engine, habit XP/penalties + heatmaps, fitness hub, life planner radar chart, Eisenhower matrix, vault database, daily quests/weekly reset. These are preserved untouched.

**Not-applicable features (excluded with justification):**
- **Full PPO reinforcement-learning training loop** — research-grade, high complexity, unverifiable without a training corpus, and unobservable value for a single-user planner. The plan ships a **deterministic adaptive scheduler** first and an **opt-in experimental PPO module (Phases 34)** kept off by default; full PPO remains explicitly out of scope to preserve maintainability. (F1)
- **Firebase Realtime DB / Firestore** — replaced by the target's SQLite persistence; the social features are modeled relationally instead. (all)
- **Gemini-specific coupling** — replaced by the provider-agnostic `ai_client.py`; `AI_MODEL` is env-configurable. (F3)

---

# PART 4 — Gap Analysis

## 4.1 Frontend gaps
| Area | Gap |
|---|---|
| Pages | No `/ai-chat`, `/study-planner`, `/sleep`, `/mood`, `/friends`, `/leaderboard`, `/contests`, `/achievements`, `/timeline` routes |
| Components | No chat UI, mood selector, sleep charts, recommendation cards, social feed, timeline widget |
| State | No hooks for mood/sleep/chat/social (pattern exists: `useQuestCentreData` etc.) |
| API layer | `services/api.ts` lacks chat/document/mood/sleep/social/planner functions; `types/index.ts` lacks the new domains |
| UX | No global "AI assistant" affordance; no notification for suggestions/contests |
| Accessibility/responsiveness | New features must match existing standards (keyboard submit, focus states, mobile grid) |

## 4.2 Backend gaps
| Area | Gap |
|---|---|
| AI | No `ai_client`, no chat endpoint, no document ingestion/text extraction, no vector store |
| Personalization | No `MoodLog`, `SleepLog`, study analytics, planner engine |
| Social | No `Friend`/`FriendRequest`/`Contest`/`Achievement`/`TimelineEvent` models or routers |
| Auth | Single-user stub; social features require scoped multi-user identity |
| Uploads | No `python-multipart` upload handling, no `UPLOAD_DIR` static serving |
| Validation | New Pydantic schemas must follow `app/schemas/*` conventions |

## 4.3 Productivity features gaps
Search/AI/notifications/settings/workflows:
- **AI**: entirely absent → Phases 1–7, 36–49.
- **Notifications**: no in-app notification system for suggestions, contests, or achievements → Phases 68–69, 85–89 (lightweight `Notifications` table + toast integration).
- **Settings**: no profile/AI/sleep defaults page → Phase 96.
- **Workflows/automation**: no planner generation → Phases 29–35; no achievement auto-unlock → Phases 91–94; no timeline auto-logging → Phase 85.

## 4.4 Infrastructure gaps
- **Security**: upload validation/size limits; AI prompt-injection hardening for document Q&A (Phases 6, 39); password hashing (Phase 5).
- **Logging**: no structured logging for AI/social actions (Phase 36 adds minimal logging).
- **Error handling**: AI provider failures must degrade to demo fallback (Phase 1).
- **Performance**: vector indexing must be incremental; N+1 avoided in leaderboard queries (Phases 38, 74).
- **Dev tooling**: `requirements.txt` grows with `httpx`, `pypdf`, `python-docx`, `python-multipart`, `passlib`/`bcrypt`, `numpy` (Part 7).
- **Deployment**: `.env.example` gains `AI_*`, `UPLOAD_DIR`, `APP_SECRET` (Phases 1–2).

---

# PART 5 — Feature Mapping (source → destination)

> The reference repo ships no code, so "Source" below names the spec capability + the analogous existing target module whose pattern is reused. Everything is **built on the target's own conventions** — nothing is imported verbatim.

| # | Reference feature | Reused pattern (target) | New target files (create) | Target files (modify) | Key deps | Refactor / config | Effort | Risk |
|---|---|---|---|---|---|---|---|---|
| F1 | RL/smart scheduler | `services/quest_centre.py`, `weekly_reset`, `Schedule`/`TimetableGrid` | `models/study_plan.py`, `models/study_session.py`, `services/planner/engine.py`, `services/planner/rl_ppo.py`, `routers/planner.py`, `routers/study.py` | `main.py`, `app/services/__init__.py`, `.env.example`, `schemas/*`, `services/api.ts`, `types/index.ts`, `App.tsx`, `Sidebar.tsx` | mood+sleep+analytics (G2–G4) | `AI_*` env; plan approval flow; PPO off by default | **High** | Medium (scope creep → heuristic-first) |
| F2 | KNN friend recs | `app/routers/*` CRUD + `vector_store.py` cosine | `models/friend.py`, `models/contest.py`, `services/social.py`, `routers/friends.py`, `routers/leaderboard.py`, `routers/contests.py` | `main.py`, `models/user.py` (+password_hash), `services/api.ts`, `types/index.ts`, `Sidebar.tsx` | multi-user auth (G1) | similarity vectors from study analytics | **High** | Medium (privacy) |
| F3 | Chatbot + doc Q&A | `services/ai_client.py` + `notes`/`vault` patterns | `models/document.py`, `models/chat_message.py`, `services/text_extractor.py`, `services/vector_store.py`, `routers/chat.py`, `routers/documents.py` | `main.py`, `config.py`, `.env.example`, `services/api.ts`, `types/index.ts`, `App.tsx`, `Sidebar.tsx` | AI client + uploads (G1) | `MAX_UPLOAD_MB`, prompt-injection guard | **High** | Medium (parsing edge cases) |
| F4 | Mood-driven sessions | `DailyLog`/`Journal` + `pomodoro` router | `models/mood_log.py`, `services/mood.py`, `routers/mood.py` | `main.py`, `schemas/*`, `Pomodoro.tsx`, `services/api.ts`, `types/index.ts` | AI client (G1) | intensity mapping table | **Low** | Low |
| F5 | Smart content & breaks | `habit_xp.py`, `FitnessHub` services | `models/suggestion.py`, `services/suggestions.py`, `routers/suggestions.py` | `main.py`, `Dashboard.tsx`, `Pomodoro.tsx`, `services/api.ts`, `types/index.ts` | study analytics (G4) | static creative-break catalog | **Medium** | Low |
| F6 | Sleep tracker | `fitness` health patterns | `models/sleep_log.py`, `services/sleep.py`, `routers/sleep.py` | `main.py`, `schemas/*`, `services/api.ts`, `types/index.ts`, `Sidebar.tsx` | — | healthy-range constants | **Low** | Low |
| F7 | Social gamification | `quest_centre.py` + `Character`/`total_xp` | `models/achievement.py`, `services/achievements.py`, `routers/achievements.py` | `main.py`, `RpgHeader.tsx`, `QuestCentreDashboard.tsx`, `services/api.ts`, `types/index.ts` | timeline events (G13) | rule-based unlock catalog in seed | **Medium** | Low |
| F8 | Timeline + feed | `vault` heatmaps, `WeeklyCalendar` | `models/timeline_event.py`, `services/timeline.py`, `routers/timeline.py`, `routers/feed.py` | `main.py`, `App.tsx`, `Sidebar.tsx`, `Dashboard.tsx` | social (G11–12) | event emitter from quest/session/contest | **Medium** | Low |

**Potential conflicts & mitigations:** new `/api/mood` etc. namespaces are collision-free; extending `User` with `password_hash`/`email` is additive and non-breaking for the existing login; react-router route additions don't touch existing routes; new CSS themes are additive `data-theme` blocks.

---

# PART 6 — Integration Strategy

1. **Layered rollout (G1→G16).** Infrastructure first (AI client, config, uploads, auth), then data domains (mood, sleep, analytics), then logic (planner), then AI surfaces (chat/doc-QA), then social, then visualization, then polish/docs.
2. **Every phase independently shippable.** Each phase lists exact `Modify`/`Create` files, a `Validation` step, and a `Completion` bar; verification gates close every group.
3. **Backward compatibility preserved.** All changes are additive; existing 28 routers and 31 routes untouched; new DB columns via `COLUMN_MIGRATIONS`; existing seed preserved.
4. **Reuse over rewrite.** New modules follow the shape of `quest_centre.py`/`habit_xp.py`; new pages follow `QuestCentreDashboard.tsx`; new hooks follow `useQuestCentreData.ts`.
5. **Demo-first AI.** Every AI surface works with the built-in deterministic fallback so the app runs offline; real provider responses activate when `AI_API_KEY` is set.
6. **Multi-user auth (Phase 5) is the single deliberate architecture change** and is kept small (password hash + row scoping + compatible login) strictly to enable F2/F7/F8.

---

# PART 7 — Dependency Analysis

| Layer | New dependency | Purpose | Where added |
|---|---|---|---|
| Backend | `httpx` | call AI provider from `ai_client.py` | Phase 1 |
| Backend | `numpy` | vector embeddings/cosine similarity fallback | Phase 3 |
| Backend | `pypdf` | PDF text extraction | Phase 4 |
| Backend | `python-docx` | DOCX text extraction | Phase 4 |
| Backend | `python-multipart` | multipart upload endpoints | Phase 6 |
| Backend | `passlib[bcrypt]` (or `bcrypt`) | password hashing for multi-user auth | Phase 5 |
| Backend | `faiss-cpu` *(optional)* | opt-in vector index (swap behind `vector_store.py`) | Phase 3 |
| Frontend | — *(recharts, react-query, date-fns already present)* | charts, data fetching | G4/G8/G9/G13 |
| Env | `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET`, `DEFAULT_SLEEP_TARGET_HOURS` | config | Phases 1–2 |

**Ordering constraints:** G1 must precede all; G2–G4 feed G5; G1+G4 feed G6; G1 feeds G8/G9/G10; G1 feeds G11; G11 feeds G12/G13; G13 feeds G14; everything feeds G15/G16.

---

# PART 8 — Risk Assessment

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | AI provider unavailable/rate-limited | High | Medium | `ai_client.py` demo fallback + timeouts + graceful degradation; UI shows "demo mode" |
| R2 | Planner scope creep into full PPO | Medium | High | Heuristic engine ships first (Phases 29–33); PPO is opt-in, off by default, documented experimental (Phase 34) |
| R3 | Multi-user auth regression on existing app | Medium | High | Additive columns, backward-compatible `/api/auth/login`, full regression gate at Phase 5 |
| R4 | Document parsing edge cases (scanned PDFs, encodings) | High | Low | Text length caps, graceful "no extractable text" message, supported-format allowlist |
| R5 | Vector index staleness / memory growth | Medium | Medium | Incremental chunk index + rebuild endpoint + cap chunks per document |
| R6 | Social privacy (recommendations expose habits) | Medium | Medium | Opt-in profile visibility; local-only vs. friends-only leaderboard tabs |
| R7 | Theme/layout regressions from new pages | Low | Medium | Reuse shared components; vitest + `tsc -b` per phase; visual check in Phase 98 |
| R8 | SQLite concurrency under vector ops | Low | Low | Single-writer pattern; index rebuilt outside request hot path |

---

# PART 9 — THE 99-PHASE ROADMAP

> Phase template (project convention): `#### Phase N — Title` with `Objective` / `Modify` / `Create` / `Deps` / `Complexity` / `Risks` / `Validation` / `Completion` fields. Groups G1–G16 are dependency-ordered.

## GROUP G1 — Foundations: AI service, config, vector store, uploads, multi-user auth (Phases 1–7)

#### Phase 1 — AI client scaffold + config
- **Objective:** Add a provider-agnostic AI client and its settings.
- **Modify:** `backend/app/config.py`, `.env.example`, `backend/requirements.txt`
- **Create:** `backend/app/services/ai_client.py`
- **Deps:** none | **Complexity:** low
- **Risks:** env-name drift | **Validation:** `python -c "from app.services.ai_client import complete; print(complete('hi'))"` returns demo text without keys
- **Completion:** `ai_client.complete(prompt, system)` works with real `AI_BASE_URL`/`AI_API_KEY`/`AI_MODEL` **and** a deterministic fallback when unset; config exposes `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `AI_TIMEOUT_S`.

#### Phase 2 — Config hygiene & upload settings
- **Objective:** Document and validate all new settings.
- **Modify:** `backend/app/config.py`, `.env.example`
- **Create:** — | **Deps:** Phase 1 | **Complexity:** low
- **Risks:** none | **Validation:** settings resolve with safe defaults (`UPLOAD_DIR=./uploads`, `MAX_UPLOAD_MB=20`, `APP_SECRET`)
- **Completion:** every new env var documented in `.env.example`; invalid values fall back to defaults.

#### Phase 3 — Vector store abstraction
- **Objective:** Reusable embedding/cosine retrieval used by chat-QA and friend-recs.
- **Modify:** `backend/app/services/__init__.py`
- **Create:** `backend/app/services/vector_store.py`
- **Deps:** Phase 1 | **Complexity:** medium
- **Risks:** index memory | **Validation:** `pytest` test adds 3 vectors, queries nearest neighbour, gets expected id; optional `faiss-cpu` path selected via env
- **Completion:** `VectorStore.add(ids, vectors)`, `.query(vector, k)`, `.delete(ids)`; numpy default + FAISS backend swap.

#### Phase 4 — Text extraction service
- **Objective:** Extract text from PDF, DOCX, TXT uploads.
- **Modify:** `backend/requirements.txt`
- **Create:** `backend/app/services/text_extractor.py`, `backend/tests/test_text_extractor.py`
- **Deps:** Phase 3 | **Complexity:** medium
- **Risks:** binary/scan PDFs | **Validation:** fixture files (txt/pdf/docx) each return expected substring; unsupported type raises `UnsupportedFormat`
- **Completion:** `extract(file_bytes, filename) -> str` handles txt/pdf/docx with length cap; unit tests green.

#### Phase 5 — Multi-user auth foundation
- **Objective:** Enable real identity + row scoping for social features, without breaking existing login.
- **Modify:** `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/app/routers/auth.py`, `backend/app/database.py`
- **Create:** `backend/app/tests/test_auth.py` (add to existing suite) | **Deps:** none | **Complexity:** medium
- **Risks:** R3 | **Validation:** existing `POST /api/auth/login` still returns first user; new `POST /api/auth/signup` hashes password; scoped queries only return owned rows
- **Completion:** `User.password_hash`/`email` columns added via `COLUMN_MIGRATIONS`; signup/login/token endpoints; auth dependency `get_current_user` available; full regression gate green.

#### Phase 6 — Upload infrastructure
- **Objective:** Multipart upload endpoint + static serving + validation.
- **Modify:** `backend/main.py` (mount static), `backend/app/config.py`
- **Create:** `backend/app/routers/uploads.py`, `backend/tests/test_uploads.py`
- **Deps:** Phase 4, Phase 5 | **Complexity:** medium
- **Risks:** R4 | **Validation:** POST a small PDF → 201 + stored file; oversize file → 413; disallowed extension → 400
- **Completion:** `POST /api/uploads` validates size/type, stores under `UPLOAD_DIR`, returns URL; files served statically.

#### Phase 7 — G1 verification gate
- **Objective:** Prove foundations did not regress the suite.
- **Modify:** — | **Create:** — | **Deps:** Phases 1–6 | **Complexity:** low
- **Risks:** none | **Validation:** `pytest` (baseline 200 + new tests) green; `tsc -b` clean (frontend untouched)
- **Completion:** all G1 tests pass; demo AI call returns content; uploads flow works end-to-end.

## GROUP G2 — Mood tracking: backend (Phases 8–14)

#### Phase 8 — MoodLog model + schema
- **Objective:** Persist structured mood entries.
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Create:** `backend/app/models/mood_log.py`, `backend/app/schemas/mood.py`
- **Deps:** Phase 5 | **Complexity:** low
- **Risks:** none | **Validation:** `from app.models import MoodLog`; `MoodLogResponse` validates
- **Completion:** `MoodLog(id, user_id, mood, energy, note, logged_at)` with `mood in {stressed, focused, relaxed}`.

#### Phase 9 — Mood CRUD router
- **Objective:** `/api/mood` endpoints.
- **Modify:** `backend/main.py`
- **Create:** `backend/app/routers/mood.py`, `backend/tests/test_mood.py`
- **Deps:** Phase 8 | **Complexity:** low
- **Risks:** none | **Validation:** create/list/delete round-trip; auth-scoped
- **Completion:** `POST/GET/DELETE /api/mood` (list supports date range), tests green.

#### Phase 10 — Mood→session-parameter mapping service
- **Objective:** Map mood to session intensity.
- **Create:** `backend/app/services/mood.py`
- **Deps:** Phase 9 | **Complexity:** low
- **Risks:** none | **Validation:** `session_params('stressed')` returns shorter focus, gentler break, easier difficulty; table-driven
- **Completion:** `services/mood.session_params(mood) -> {focus_minutes, break_type, difficulty}`; documented mapping table.

#### Phase 11 — Mood analytics aggregation
- **Objective:** Trends and averages over mood history.
- **Modify:** `backend/app/routers/mood.py`
- **Create:** — | **Deps:** Phase 9 | **Complexity:** low
- **Risks:** none | **Validation:** seeded entries produce avg energy + mood distribution JSON
- **Completion:** `GET /api/mood/analytics` returns daily trend + dominant mood + energy avg.

#### Phase 12 — Mood × journal/daily-log correlation
- **Objective:** Correlate mood with daily logs for insight.
- **Modify:** `backend/app/services/mood.py`
- **Create:** — | **Deps:** Phase 11 | **Complexity:** low
- **Risks:** none | **Validation:** endpoint joins `MoodLog` ↔ `DailyLog` by day and returns a correlation summary
- **Completion:** `GET /api/mood/insights` returns per-day mood + journal/daily-log snippet pairing.

#### Phase 13 — Weekly mood report
- **Objective:** 7-day summary payload for the frontend.
- **Modify:** `backend/app/routers/mood.py`
- **Create:** — | **Deps:** Phase 11 | **Complexity:** low
- **Risks:** none | **Validation:** seeded week returns 7 buckets (empty days as zeros)
- **Completion:** `GET /api/mood/weekly` returns day→{mood, energy} series; used by the mood chart.

#### Phase 14 — G2 verification gate
- **Objective:** Verify mood domain end-to-end.
- **Modify:** — | **Create:** — | **Deps:** Phases 8–13 | **Complexity:** low
- **Risks:** none | **Validation:** mood tests green; manual curl CRUD works; no regression
- **Completion:** mood endpoints stable and covered.

## GROUP G3 — Sleep tracker: backend (Phases 15–21)

#### Phase 15 — SleepLog model + schema
- **Create:** `backend/app/models/sleep_log.py`, `backend/app/schemas/sleep.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 5 | **Complexity:** low | **Risks:** none
- **Validation:** model + schema import clean | **Completion:** `SleepLog(id, user_id, date, bedtime, wake_time, quality, notes)`.

#### Phase 16 — Sleep CRUD router
- **Create:** `backend/app/routers/sleep.py`, `backend/tests/test_sleep.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 15 | **Complexity:** low | **Risks:** none
- **Validation:** create/update/list/delete round-trip | **Completion:** `/api/sleep` CRUD green.

#### Phase 17 — Sleep analytics service
- **Create:** `backend/app/services/sleep.py`
- **Deps:** Phase 16 | **Complexity:** low | **Risks:** none
- **Validation:** avg hours, consistency (stddev), deviation from target computed from seeded logs | **Completion:** `services/sleep.analytics(logs, target_hours) -> {avg_hours, consistency, deviation, nights_under}`.

#### Phase 18 — Bedtime/wake recommendation
- **Modify:** `backend/app/services/sleep.py`
- **Create:** — | **Deps:** Phase 17 | **Complexity:** low | **Risks:** none
- **Validation:** with target 8h and wake 07:00 → recommends 23:00; alerts if recent avg < 6h | **Completion:** `recommend_bedtime(target_hours, wake_time, history)` + alert text.

#### Phase 19 — Sleep-aware schedule adjustment
- **Modify:** `backend/app/services/sleep.py`, `backend/app/routers/sleep.py`
- **Create:** — | **Deps:** Phase 18 | **Complexity:** medium | **Risks:** none
- **Validation:** given sleep deficit, returns suggested protected rest blocks / reduced evening study | **Completion:** `GET /api/sleep/recommendations` returns bedtime/wake + schedule-shift hints consumable by the planner.

#### Phase 20 — Sleep widget payload
- **Modify:** `backend/app/routers/sleep.py`
- **Create:** — | **Deps:** Phase 19 | **Complexity:** low | **Risks:** none
- **Validation:** `/api/sleep/summary` returns last-7-days series + today's status | **Completion:** summary payload ready for dashboard widget.

#### Phase 21 — G3 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 15–20 | **Complexity:** low | **Risks:** none
- **Validation:** sleep tests green; full suite still 200+ | **Completion:** sleep domain complete and covered.

## GROUP G4 — Study analytics: backend (Phases 22–28)

#### Phase 22 — StudySession model + schema
- **Create:** `backend/app/models/study_session.py`, `backend/app/schemas/study.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 5 | **Complexity:** low | **Risks:** none
- **Validation:** model import; `StudySessionResponse` validates | **Completion:** `StudySession(id, user_id, course_id, started_at, minutes, focus_score, source)`.

#### Phase 23 — Study session CRUD
- **Create:** `backend/app/routers/study.py`, `backend/tests/test_study.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 22 | **Complexity:** low | **Risks:** none
- **Validation:** CRUD + auto-tag `source='pomodoro'|'manual'` | **Completion:** `/api/study/sessions` green.

#### Phase 24 — Derive analytics from pomodoro sessions
- **Modify:** `backend/app/routers/study.py`
- **Create:** — | **Deps:** Phase 23 | **Complexity:** medium | **Risks:** none
- **Validation:** completing a pomodoro produces a study session for its linked course | **Completion:** pomodoro-completion hook writes `StudySession` (source=pomodoro).

#### Phase 25 — Study analytics service
- **Create:** `backend/app/services/study_analytics.py`
- **Deps:** Phase 23 | **Complexity:** medium | **Risks:** none
- **Validation:** seeded sessions produce per-subject hours, completion rate, weak/strong classification | **Completion:** `analytics(sessions, assignments, exams) -> {subject_hours, completion_rate, strengths, weaknesses, weekly_focus_hours}`.

#### Phase 26 — Analytics + grades correlation
- **Modify:** `backend/app/routers/study.py`
- **Create:** — | **Deps:** Phase 25 | **Complexity:** medium | **Risks:** none
- **Validation:** with assignment grades present, returns focus-vs-grade trend points | **Completion:** `GET /api/study/analytics` includes focus-hours × grade correlation series.

#### Phase 27 — Planner input feed
- **Modify:** `backend/app/services/study_analytics.py`
- **Create:** — | **Deps:** Phase 26 | **Complexity:** low | **Risks:** none
- **Validation:** output shape documented and importable by the scheduler | **Completion:** analytics exposes a stable `planner_input` contract (subjects, loads, priorities).

#### Phase 28 — G4 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 22–27 | **Complexity:** low | **Risks:** none
- **Validation:** study tests green; regression gate | **Completion:** analytics domain complete; feeds G5/G6.

## GROUP G5 — Smart study scheduler: backend (Phases 29–35)

#### Phase 29 — StudyPlan model + schema
- **Create:** `backend/app/models/study_plan.py`, `backend/app/schemas/planner.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 27 | **Complexity:** low | **Risks:** none
- **Validation:** model import | **Completion:** `StudyPlan(id, user_id, week_start, status, items_json)` where items = {day, slot, subject, duration, type, energy}.

#### Phase 30 — Heuristic planner engine v1
- **Create:** `backend/app/services/planner/__init__.py`, `backend/app/services/planner/engine.py`
- **Deps:** Phase 29 | **Complexity:** high | **Risks:** R2
- **Validation:** unit test: due-soon + weak subject gets earlier/higher allocation; energy windows respected | **Completion:** deterministic greedy allocation over priorities/due dates/energy windows; output validated against `StudyPlan`.

#### Phase 31 — Planner generate endpoint
- **Create:** `backend/app/routers/planner.py`, `backend/tests/test_planner.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 30 | **Complexity:** medium | **Risks:** R2
- **Validation:** `POST /api/planner/generate` returns a plan; empty data → 400 with message | **Completion:** plan generation wired; tests green.

#### Phase 32 — Plan approval workflow
- **Modify:** `backend/app/routers/planner.py`
- **Create:** — | **Deps:** Phase 31 | **Complexity:** medium | **Risks:** none
- **Validation:** accept/regenerate/delete round-trip; accepted plan persists status=accepted | **Completion:** `POST /api/planner/{id}/accept`, `POST /api/planner/regenerate`, `DELETE /api/planner/{id}`.

#### Phase 33 — Adaptive loop (reward from study sessions)
- **Modify:** `backend/app/services/planner/engine.py`
- **Create:** — | **Deps:** Phase 32, Phase 26 | **Complexity:** high | **Risks:** R2
- **Validation:** completing a session adjusts next week's weights; log shows reward signal | **Completion:** plan items carry `reward_signal`; engine re-weights by completion; still deterministic.

#### Phase 34 — Experimental PPO module (opt-in, off by default)
- **Create:** `backend/app/services/planner/rl_ppo.py`
- **Modify:** `.env.example` (`PLANNER_RL_ENABLED=false`)
- **Deps:** Phase 33 | **Complexity:** high | **Risks:** R2
- **Validation:** module imports; disabled by default; enabling runs a tiny toy MDP test | **Completion:** documented experimental PPO policy-gradient scaffold, clearly gated off; **not** wired to the live planner.

#### Phase 35 — G5 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 29–34 | **Complexity:** low | **Risks:** none
- **Validation:** planner tests green; heuristic plan validated by fixture; full regression | **Completion:** smart scheduler backend complete (PPO stays opt-in).

## GROUP G6 — AI chatbot + document Q&A: backend (Phases 36–42)

#### Phase 36 — Chat/Document models + schema
- **Create:** `backend/app/models/chat_message.py`, `backend/app/models/document.py`, `backend/app/schemas/chat.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 5 | **Complexity:** low | **Risks:** none
- **Validation:** imports clean | **Completion:** `ChatMessage(id, user_id, role, content, doc_ids, created_at)`, `Document(id, user_id, name, kind, file_url, status, chunk_count)`.

#### Phase 37 — Document ingestion endpoint
- **Create:** `backend/app/routers/documents.py`, `backend/tests/test_documents.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 36, Phase 6, Phase 4 | **Complexity:** medium | **Risks:** R4
- **Validation:** upload → extract → chunk → index; status=ready with chunk_count | **Completion:** `POST /api/documents` (multipart) ingests, chunks, and indexes; `GET/DELETE /api/documents`.

#### Phase 38 — Vector index build/query for documents
- **Modify:** `backend/app/services/vector_store.py`
- **Create:** `backend/app/services/retrieval.py`
- **Deps:** Phase 37, Phase 3 | **Complexity:** medium | **Risks:** R5
- **Validation:** query by keyword returns top-k chunks from the right document | **Completion:** `retrieval.retrieve(query, user_id, k) -> [chunk texts + doc ids]`; incremental indexing.

#### Phase 39 — Chat endpoint with retrieval + prompt-injection guard
- **Create:** `backend/app/routers/chat.py`, `backend/tests/test_chat.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 38 | **Complexity:** high | **Risks:** R1, prompt-injection
- **Validation:** seeded doc + question → answer cites source chunk (demo fallback returns "based on: …"); history stored | **Completion:** `POST /api/chat` runs retrieve→compose→generate→persist; system prompt constrains to retrieved context.

#### Phase 40 — Conversation history & delete
- **Modify:** `backend/app/routers/chat.py`
- **Create:** — | **Deps:** Phase 39 | **Complexity:** low | **Risks:** none
- **Validation:** thread GET returns ordered messages; delete clears thread | **Completion:** `GET /api/chat`, `DELETE /api/chat`.

#### Phase 41 — Reindex/refresh + orphan cleanup
- **Modify:** `backend/app/routers/documents.py`
- **Create:** — | **Deps:** Phase 38 | **Complexity:** medium | **Risks:** R5
- **Validation:** `POST /api/documents/{id}/reindex` rebuilds; deleting doc removes chunks | **Completion:** reindex endpoint; chunk cascade cleanup; cap enforced.

#### Phase 42 — G6 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 36–41 | **Complexity:** low | **Risks:** none
- **Validation:** chat + documents tests green; demo-mode chat returns content | **Completion:** AI backend complete; ready for UI.

## GROUP G7 — AI chatbot + document Q&A: frontend (Phases 43–49)

#### Phase 43 — API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 42 | **Complexity:** low | **Risks:** none
- **Validation:** `tsc -b` clean; functions reference real endpoints | **Completion:** `chatApi`, `documentApi` functions + `ChatMessage`, `DocumentItem` types.

#### Phase 44 — Chat page `/ai-chat`
- **Create:** `frontend/src/pages/AIChat.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 43 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest renders composer; send posts message; demo response renders | **Completion:** message list + composer + streaming-friendly render + route/side link.

#### Phase 45 — Document upload UI + library
- **Create:** `frontend/src/components/chat/DocumentLibrary.tsx`, `frontend/src/components/chat/UploadDropzone.tsx`
- **Modify:** `frontend/src/pages/AIChat.tsx`
- **Deps:** Phase 44 | **Complexity:** medium | **Risks:** R4
- **Validation:** upload shows progress + status; list/delete works | **Completion:** dropzone (type/size validation), library grid, ingestion status badges.

#### Phase 46 — Source-cited Q&A interaction
- **Modify:** `frontend/src/pages/AIChat.tsx`
- **Create:** `frontend/src/components/chat/SourceChip.tsx`
- **Deps:** Phase 45 | **Complexity:** medium | **Risks:** none
- **Validation:** answer with `doc_ids` renders source chips; follow-up appends to thread | **Completion:** cited sources UI + thread continuation.

#### Phase 47 — Dashboard AI assistant widget
- **Create:** `frontend/src/components/chat/AIAssistantWidget.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 44 | **Complexity:** medium | **Risks:** R7
- **Validation:** widget opens chat panel reusing chat logic; collapses on mobile | **Completion:** quick-assist surface reusing `/api/chat`.

#### Phase 48 — States + responsiveness + a11y
- **Modify:** `frontend/src/pages/AIChat.tsx`
- **Create:** — | **Deps:** Phase 46 | **Complexity:** low | **Risks:** none
- **Validation:** loading/empty/error states; keyboard Enter submit; focus ring visible | **Completion:** a11y + responsive pass; oxlint clean.

#### Phase 49 — G7 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 43–48 | **Complexity:** low | **Risks:** none
- **Validation:** vitest chat/document tests; `tsc -b`; `npm run build` | **Completion:** chat/doc-QA UI complete end-to-end (works in demo mode).

## GROUP G8 — Mood-driven customization: frontend (Phases 50–56)

#### Phase 50 — Mood input widget + daily prompt
- **Create:** `frontend/src/components/mood/MoodSelector.tsx`
- **Modify:** `frontend/src/pages/Pomodoro.tsx`
- **Deps:** Phase 14 | **Complexity:** low | **Risks:** none
- **Validation:** vitest toggles mood and persists via api | **Completion:** 3-state selector (stressed/focused/relaxed) + energy slider.

#### Phase 51 — useMood hook + api functions
- **Create:** `frontend/src/hooks/useMood.ts`
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Deps:** Phase 50 | **Complexity:** low | **Risks:** none
- **Validation:** hook fetches today + saves; typecheck clean | **Completion:** `moodApi` functions + `useMood` (today, save, analytics).

#### Phase 52 — Session-design readout
- **Create:** `frontend/src/components/mood/SessionDesignCard.tsx`
- **Modify:** `frontend/src/pages/Pomodoro.tsx`
- **Deps:** Phase 51, Phase 10 | **Complexity:** medium | **Risks:** none
- **Validation:** selecting "stressed" shows shorter focus / gentle break / easier difficulty | **Completion:** card renders `session_params` from `/api/mood` mapping.

#### Phase 53 — Mood-aware Pomodoro
- **Modify:** `frontend/src/pages/Pomodoro.tsx`, `frontend/src/components/pomodoro/SettingsModal.tsx`
- **Create:** — | **Deps:** Phase 52 | **Complexity:** medium | **Risks:** R7
- **Validation:** pomodoro default duration + break type follow mood unless overridden | **Completion:** mood drives session defaults; manual override persists.

#### Phase 54 — Mood on planner + schedule display
- **Modify:** `frontend/src/pages/StudyPlanner.tsx` (from G5 UI), `frontend/src/pages/Schedule.tsx`
- **Create:** `frontend/src/components/mood/EnergyLegend.tsx`
- **Deps:** Phase 52, Phase 33 | **Complexity:** medium | **Risks:** R7
- **Validation:** schedule rows tinted by energy; planner shows mood-informed blocks | **Completion:** energy coloring + planner mood hints.

#### Phase 55 — Mood history chart
- **Create:** `frontend/src/components/mood/MoodTrendChart.tsx`
- **Modify:** `frontend/src/pages/LifePlannerDashboard.tsx` (mood section) or new `/mood`
- **Deps:** Phase 51, Phase 13 | **Complexity:** medium | **Risks:** none
- **Validation:** recharts renders 7-day mood/energy series from `/api/mood/weekly` | **Completion:** trend chart + insights text.

#### Phase 56 — G8 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 50–55 | **Complexity:** low | **Risks:** none
- **Validation:** vitest mood tests; `tsc -b`; build | **Completion:** mood-driven customization fully usable.

## GROUP G9 — Sleep tracker: frontend (Phases 57–63)

#### Phase 57 — Sleep API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 21 | **Complexity:** low | **Risks:** none
- **Validation:** typecheck clean | **Completion:** `sleepApi` functions + `SleepLog` type.

#### Phase 58 — Sleep log page `/sleep`
- **Create:** `frontend/src/pages/Sleep.tsx`, `frontend/src/components/sleep/SleepLogForm.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 57 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest adds a log; list renders; route + nav present | **Completion:** log entry (bedtime/wake/quality) + history list.

#### Phase 59 — Sleep analytics charts
- **Create:** `frontend/src/components/sleep/SleepWeekChart.tsx`
- **Modify:** `frontend/src/pages/Sleep.tsx`
- **Deps:** Phase 58 | **Complexity:** medium | **Risks:** none
- **Validation:** chart renders weekly hours + consistency from `/api/sleep/summary` | **Completion:** weekly hours bars + consistency indicator.

#### Phase 60 — Recommendations panel
- **Create:** `frontend/src/components/sleep/SleepRecommendations.tsx`
- **Modify:** `frontend/src/pages/Sleep.tsx`
- **Deps:** Phase 59, Phase 19 | **Complexity:** low | **Risks:** none
- **Validation:** renders bedtime/wake + alert when deficit | **Completion:** recommendation card from `/api/sleep/recommendations`.

#### Phase 61 — Sleep-aware schedule hints UI
- **Modify:** `frontend/src/pages/StudyPlanner.tsx`, `frontend/src/pages/Schedule.tsx`
- **Create:** `frontend/src/components/sleep/SleepHintBanner.tsx`
- **Deps:** Phase 60 | **Complexity:** low | **Risks:** R7
- **Validation:** banner appears when plan conflicts with rest | **Completion:** non-blocking hint surfaced on schedule/planner.

#### Phase 62 — Dashboard sleep widget
- **Create:** `frontend/src/components/sleep/SleepStatusWidget.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 60 | **Complexity:** low | **Risks:** R7
- **Validation:** widget shows last night + streak | **Completion:** compact dashboard card linking to `/sleep`.

#### Phase 63 — G9 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 57–62 | **Complexity:** low | **Risks:** none
- **Validation:** vitest sleep tests; `tsc -b`; build | **Completion:** sleep tracker UI complete.

## GROUP G10 — Smart content & break suggestions (Phases 64–70)

#### Phase 64 — Suggestion model + schema
- **Create:** `backend/app/models/suggestion.py`, `backend/app/schemas/suggestion.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 28 | **Complexity:** low | **Risks:** none
- **Validation:** imports clean | **Completion:** `Suggestion(id, user_id, kind, title, body, ref_id, created_at, seen)`; kind ∈ {content, break, review}.

#### Phase 65 — Suggestion engine service
- **Create:** `backend/app/services/suggestions.py`
- **Deps:** Phase 64, Phase 26 | **Complexity:** medium | **Risks:** none
- **Validation:** seeded weak subject → review suggestion; long focus → break suggestion | **Completion:** rule engine over study analytics (weak → review, low completion → content, streak → break).

#### Phase 66 — Creative breaks catalog + API
- **Modify:** `backend/app/seed/__init__.py`
- **Create:** `backend/app/services/breaks.py`
- **Deps:** Phase 65 | **Complexity:** low | **Risks:** none
- **Validation:** `breaks.catalog()` returns ≥ 6 items across mini-game/mindfulness/stretch | **Completion:** static catalog + `GET /api/suggestions/breaks`.

#### Phase 67 — Suggestions endpoints
- **Create:** `backend/app/routers/suggestions.py`, `backend/tests/test_suggestions.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 65 | **Complexity:** low | **Risks:** none
- **Validation:** list/acknowledge/refresh round-trip | **Completion:** `GET /api/suggestions`, `POST /api/suggestions/{id}/seen`, `POST /api/suggestions/generate`.

#### Phase 68 — Suggestions UI panel
- **Create:** `frontend/src/components/suggestions/SuggestionPanel.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 67 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest renders suggestions + dismiss | **Completion:** dashboard panel with content/break/review cards + acknowledge.

#### Phase 69 — Break suggestions in pomodoro
- **Modify:** `frontend/src/pages/Pomodoro.tsx`
- **Create:** `frontend/src/components/suggestions/BreakPrompt.tsx`
- **Deps:** Phase 68 | **Complexity:** medium | **Risks:** none
- **Validation:** break transition offers a creative-break option from catalog | **Completion:** pomodoro break screen suggests activities.

#### Phase 70 — G10 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 64–69 | **Complexity:** low | **Risks:** none
- **Validation:** suggestions tests green; vitest; build | **Completion:** smart suggestions complete.

## GROUP G11 — Social backend: friends, recommendations, contests, leaderboard (Phases 71–77)

#### Phase 71 — Friend + FriendRequest models + schema
- **Create:** `backend/app/models/friend.py`, `backend/app/schemas/friend.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 5 | **Complexity:** medium | **Risks:** none
- **Validation:** imports clean | **Completion:** `Friend(user_id, friend_id, created_at)`, `FriendRequest(from_id, to_id, status, created_at)`.

#### Phase 72 — Friendship endpoints
- **Create:** `backend/app/routers/friends.py`, `backend/tests/test_friends.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 71 | **Complexity:** medium | **Risks:** R6
- **Validation:** send/accept/decline/list round-trip with auth scoping | **Completion:** `/api/friends`, `/api/friends/requests` (send/accept/decline), `/api/friends`.

#### Phase 73 — Friend recommendation service (KNN-lite)
- **Create:** `backend/app/services/social.py`
- **Deps:** Phase 72, Phase 26, Phase 3 | **Complexity:** high | **Risks:** R6, R5
- **Validation:** with ≥2 users sharing habit vectors, returns ranked candidates by cosine; excludes existing friends | **Completion:** `recommend_friends(user) -> [{user, score, reason}]` over study-habit vectors.

#### Phase 74 — Leaderboard endpoint
- **Create:** `backend/app/routers/leaderboard.py`, `backend/tests/test_leaderboard.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 72 | **Complexity:** medium | **Risks:** R6
- **Validation:** rankings by XP, focus-hours, streak; local vs friends scopes | **Completion:** `GET /api/leaderboard?scope=local|friends&metric=xp|hours|streak` (single indexed query, no N+1).

#### Phase 75 — Contest + ContestParticipant models + endpoints
- **Create:** `backend/app/models/contest.py`, `backend/app/schemas/contest.py`, `backend/app/routers/contests.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 72, Phase 74 | **Complexity:** high | **Risks:** none
- **Validation:** create/join/progress/rank round-trip; standings recompute on metric events | **Completion:** `/api/contests` (create/join/leave/list), `/api/contests/{id}/standings`.

#### Phase 76 — Weekly friend goals
- **Modify:** `backend/app/routers/contests.py`, `backend/app/models/contest.py`
- **Create:** — | **Deps:** Phase 75 | **Complexity:** medium | **Risks:** none
- **Validation:** collaborative goal (e.g., 10h combined) tracks aggregate progress | **Completion:** goal-type contest with combined metric + progress endpoint.

#### Phase 77 — G11 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 71–76 | **Complexity:** low | **Risks:** none
- **Validation:** social tests green; auth scoping verified; regression | **Completion:** social backend complete (auth-scoped).

## GROUP G12 — Social frontend (Phases 78–84)

#### Phase 78 — Social API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 77 | **Complexity:** low | **Risks:** none
- **Validation:** typecheck clean | **Completion:** `friendsApi`, `leaderboardApi`, `contestApi` functions + types.

#### Phase 79 — Friends page `/friends`
- **Create:** `frontend/src/pages/Friends.tsx`, `frontend/src/components/friends/FriendCard.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 78 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest renders requests + add + list | **Completion:** friend list, requests inbox, add-by-name, recommendations row.

#### Phase 80 — Leaderboard page `/leaderboard`
- **Create:** `frontend/src/pages/Leaderboard.tsx`, `frontend/src/components/social/LeaderboardTable.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 78 | **Complexity:** medium | **Risks:** R7
- **Validation:** tabs switch scope+metric; current user highlighted | **Completion:** leaderboard with local/friends scopes and XP/hours/streak metrics.

#### Phase 81 — Contests page `/contests`
- **Create:** `frontend/src/pages/Contests.tsx`, `frontend/src/components/social/ContestCard.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 78 | **Complexity:** medium | **Risks:** R7
- **Validation:** join/leave + standings render; progress bars update | **Completion:** contest browsing, joining, standings with live progress.

#### Phase 82 — Public profile/stats page
- **Create:** `frontend/src/pages/Profile.tsx`
- **Modify:** `frontend/src/App.tsx`
- **Deps:** Phase 78 | **Complexity:** medium | **Risks:** R6
- **Validation:** renders public XP/hours/streak/achievements given user id | **Completion:** `/profile/:id` for friend comparisons (visibility-gated).

#### Phase 83 — Social nav + dashboard summary
- **Modify:** `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/pages/Dashboard.tsx`
- **Create:** `frontend/src/components/social/SocialSummary.tsx`
- **Deps:** Phases 79–81 | **Complexity:** low | **Risks:** R7
- **Validation:** sidebar groups social links; summary card links out | **Completion:** navigation + dashboard summary widget.

#### Phase 84 — G12 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 78–83 | **Complexity:** low | **Risks:** none
- **Validation:** vitest social tests; `tsc -b`; build | **Completion:** social UI complete.

## GROUP G13 — Progress timeline + social feed (Phases 85–90)

#### Phase 85 — TimelineEvent model + emitter service
- **Create:** `backend/app/models/timeline_event.py`, `backend/app/services/timeline.py`
- **Modify:** `backend/app/models/__init__.py`
- **Deps:** Phase 77 | **Complexity:** medium | **Risks:** none
- **Validation:** quest complete / session complete / contest result each emit an event | **Completion:** `TimelineEvent(id, user_id, kind, title, payload, created_at)`; emitter hooked into quest/study/contest completion.

#### Phase 86 — Timeline aggregation endpoint
- **Create:** `backend/app/routers/timeline.py`, `backend/tests/test_timeline.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 85 | **Complexity:** low | **Risks:** none
- **Validation:** seeded events return ordered, date-bucketed timeline | **Completion:** `GET /api/timeline` (paged, filtered by kind/date).

#### Phase 87 — Interactive timeline frontend
- **Create:** `frontend/src/pages/Timeline.tsx`, `frontend/src/components/timeline/TimelineChart.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 86 | **Complexity:** medium | **Risks:** R7
- **Validation:** recharts timeline renders sessions/tasks/milestones; filters work | **Completion:** `/timeline` with hover details + kind filters.

#### Phase 88 — Social feed backend endpoint
- **Create:** `backend/app/routers/feed.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 85, Phase 72 | **Complexity:** medium | **Risks:** R6
- **Validation:** friends' streaks/contest highlights/achievements appear in feed | **Completion:** `GET /api/feed` aggregates friend timeline events + contest highlights.

#### Phase 89 — Social feed frontend
- **Create:** `frontend/src/components/social/FeedStream.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 88 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest renders feed items with actor/type icons | **Completion:** feed stream panel on dashboard (or `/feed`).

#### Phase 90 — G13 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 85–89 | **Complexity:** low | **Risks:** none
- **Validation:** timeline + feed tests green; vitest; build | **Completion:** progress visualization complete.

## GROUP G14 — Achievements, badges & gamification integration (Phases 91–95)

#### Phase 91 — Achievement + AchievementUnlock models + seed catalog
- **Create:** `backend/app/models/achievement.py`, `backend/app/schemas/achievement.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/seed/__init__.py`
- **Deps:** Phase 85 | **Complexity:** medium | **Risks:** none
- **Validation:** seed inserts ≥ 8 achievements; unlocks table composes | **Completion:** `Achievement(id, key, title, desc, icon, condition_json)`, `AchievementUnlock(user_id, achievement_id, unlocked_at)`.

#### Phase 92 — Achievement service + endpoint
- **Create:** `backend/app/services/achievements.py`, `backend/app/routers/achievements.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 91 | **Complexity:** medium | **Risks:** none
- **Validation:** rule-based checks (streak≥7, 100 quests, first contest win) unlock; endpoint lists with progress | **Completion:** `check_and_unlock(user)` on event + `GET /api/achievements` (locked/unlocked + progress).

#### Phase 93 — Achievements page `/achievements`
- **Create:** `frontend/src/pages/Achievements.tsx`, `frontend/src/components/achievements/AchievementCard.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 92 | **Complexity:** medium | **Risks:** R7
- **Validation:** badge grid renders with locked/unlocked + progress | **Completion:** achievements gallery with unlock glow (reuse reward-glow pattern).

#### Phase 94 — Integrate achievements into RPG + quest centre headers
- **Modify:** `frontend/src/components/rpg/RpgHeader.tsx`, `frontend/src/components/questcentre/StatusWindowWidget.tsx`
- **Create:** `frontend/src/components/achievements/AchievementBanner.tsx`
- **Deps:** Phase 93 | **Complexity:** low | **Risks:** R7
- **Validation:** recent unlock shows toast + header badge count | **Completion:** unlock toast + badge count surfaced across gamified surfaces.

#### Phase 95 — G14 verification gate
- **Create:** — | **Modify:** — | **Deps:** Phases 91–94 | **Complexity:** low | **Risks:** none
- **Validation:** achievement tests green; vitest; full regression | **Completion:** achievements integrated with existing gamification.

## GROUP G15 — Settings, exports & polish (Phases 96–97)

#### Phase 96 — Settings page extensions
- **Create:** `frontend/src/pages/Settings.tsx`, `frontend/src/components/settings/PreferenceForm.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Deps:** Phases 56, 63 | **Complexity:** medium | **Risks:** R7
- **Validation:** profile (email/visibility), AI model pick, mood/sleep defaults, notification prefs persist; theme switcher reused | **Completion:** `/settings` with persisted preferences + `UserProfile` extension.

#### Phase 97 — Data export + iCal + UX polish
- **Create:** `backend/app/routers/exports.py`, `backend/app/services/ical.py`, `frontend/src/utils/pdfExport.ts`
- **Modify:** `backend/main.py`
- **Deps:** Phase 96 | **Complexity:** medium | **Risks:** none
- **Validation:** JSON export + study-plan `.ics` download; empty-state/a11y pass on new pages | **Completion:** `GET /api/exports/json`, `GET /api/exports/planner.ics`; polish sweep.

## GROUP G16 — Verification, documentation, finalization (Phases 98–99)

#### Phase 98 — Full regression + smoke test
- **Modify:** `frontend/README.md`
- **Create:** — | **Deps:** Phases 1–97 | **Complexity:** high | **Risks:** R7, R8
- **Validation:** `pytest` (baseline + all new suites) green; `tsc -b`; `npm run build`; vitest; oxlint; fresh-DB smoke test on a temp DB covering representative GET/POST paths (auth, mood, sleep, study, planner, chat, documents, friends, leaderboard, contests, timeline, achievements, exports)
- **Completion:** all gates green; no regressions in the 200 baseline tests.

#### Phase 99 — Documentation & final checklist
- **Modify:** `frontend/README.md` (new routes, endpoints, env vars, theme), `backend/requirements.txt` (final)
- **Create:** — | **Deps:** Phase 98 | **Complexity:** low | **Risks:** none
- **Validation:** README documents all new pages/endpoints/env/theme; plan STATUS updated to COMPLETE | **Completion:** project docs current; final validation checklist (below) fully satisfied.

---

# PART 10 — Testing Strategy

- **Backend (pytest + FastAPI TestClient):** per-domain test modules mirroring the existing suite (`test_mood.py`, `test_sleep.py`, `test_study.py`, `test_planner.py`, `test_chat.py`, `test_documents.py`, `test_friends.py`, `test_leaderboard.py`, `test_contests.py`, `test_timeline.py`, `test_achievements.py`, `test_exports.py`, `test_uploads.py`, `test_text_extractor.py`, `test_auth.py`). Shared `conftest.py` in-memory DB + `seed_database()` reuse.
- **Frontend (vitest + Testing Library):** component tests for chat page, document library, mood selector, sleep form/chart, suggestion panel, friends/leaderboard/contests, timeline, achievements, settings — mirroring `src/test/*.test.tsx` style.
- **Type safety:** `tsc -b` must stay clean every phase.
- **Gate cadence:** a verification-gate phase closes each group (7 gates + final), exactly matching how the project already ships.
- **Smoke test (Phase 98):** fresh SQLite DB, uvicorn, representative endpoint sweep — the project's established full-stack check.

---

# PART 11 — Success Criteria

1. **Feature parity:** All 8 reference capabilities (F1–F8) exist in Student Life OS; F7/F8 exceed the spec by wiring into the existing gamification engine.
2. **Zero regression:** The 200-test backend baseline, `tsc -b`, `npm run build`, and 25 vitest tests remain green after every group.
3. **Offline-first AI:** Every AI surface works in deterministic demo mode with no API keys; real provider optional.
4. **Architecture preserved:** Same router/model/schema/service layout, `migrate_schema()` pattern, theme system, and shared components; no duplicated existing logic.
5. **Maintainability:** PPO stays opt-in/experimental; all new modules tested, documented, and README-covered.

---

# PART 12 — Final Validation Checklist

- [ ] Exactly 99 phases across G1–G16, each with Objective / Modify / Create / Deps / Complexity / Risks / Validation / Completion
- [ ] Backend: all new routers registered in `backend/main.py`; all new columns via `COLUMN_MIGRATIONS`
- [ ] Backend: `pytest` baseline 200 + all new suites green (Phase 98)
- [ ] Frontend: new routes in `App.tsx` + `Sidebar.tsx`; `tsc -b` clean; `npm run build` clean; vitest green
- [ ] AI demo fallback verified without keys; provider mode verified with `AI_API_KEY`
- [ ] Multi-user auth additive & backward compatible (existing login intact)
- [ ] No duplicate services/components; existing 28 routers and 31 routes untouched functionally
- [ ] `.env.example` documents all new vars; `requirements.txt` updated
- [ ] README documents new pages, endpoints, env vars, and any new theme
- [ ] Plan `STATUS` marked COMPLETE with the Phase 98 smoke-test evidence appended
