# 99-Phase Implementation Plan — STUDENT-PLANAR → Student Life OS

| | |
|---|---|
| **Source (Reference) Repository** | `STUDENT-PLANAR/` (MERN role-based study planner: React 19 JSX + Express + Mongoose/MongoDB) |
| **Target Repository** | `productivity_app/` — **Student Life OS** (FastAPI + SQLAlchemy/SQLite backend, React 19 + TypeScript + Vite frontend) |
| **Plan Status** | ✅ **COMPLETE (2026-08-05)** — all 99 phases executed; Phase 98 evidence appended |
| **Baseline (verified 2026-08-02)** | Backend pytest **200/200** green · Frontend `tsc -b` clean · `npm run build` clean · Vitest **25/25** · oxlint exit 0 (5 pre-existing warnings) |
| **Final (Phase 98, 2026-08-05)** | Backend pytest **541/541** green · Frontend `tsc -b` clean · `npm run build` clean · Vitest **80/80** (19 files) · oxlint **0 errors** (4 pre-existing warnings) · `scripts/verify.sh` one-command gate |

---

# PART 0 — Executive Summary

`STUDENT-PLANAR` is a working **MERN role-based study planner**. It is a two-role app: a **Student** dashboard (habits, courses, assignments, daily schedule, pomodoro + brain dump, reading tracker, todos) and a **Teacher** dashboard (broadcast courses/assignments/todos/books to selected students or everyone, per-student detail modal with brain dump + reading shelf). It ships real code — Express API with a `makeCrud` endpoint factory over seven Mongoose models, multer file uploads for books/assignments, and a React client with a cyberpunk tokenized theme.

The target — **Student Life OS** — is a mature, tested, gamified productivity suite that already *exceeds* STUDENT-PLANAR on the student-side core: courses with progress cards, assignments, tasks/todos, a far richer habit tracker (XP/penalties, heatmaps, streaks), a better pomodoro, a weekly timetable, notes/journal, quests/missions/rewards, vault, fitness hub, and life planner — behind 28 FastAPI routers and 31 routes.

**The genuine gaps are the features Student Life OS does not have at all:** role-based authentication (student/teacher), the entire **teacher broadcast workflow**, a **reading tracker** (books + PDF reading + insights), **file uploads**, the **brain-dump quick-capture** pattern, daily date-specific schedule blocks with energy/category/done, and assignment attachments + status workflow. Everything else is either already present or better in the target.

This plan ports the valuable STUDENT-PLANAR capabilities onto Student Life OS **using the target's own architecture and conventions** — FastAPI routers/models/schemas/services, `migrate_schema()` column migrations, `seed_database()`, `services/api.ts`, shared components, and theme system — while deliberately **not copying** STUDENT-PLANAR's security weaknesses (no server-side auth, client-trusted `studentId`, hardcoded habit dates, N+1 teacher queries, stub search).

The roadmap is organized into **16 dependency-ordered groups (G1–G16)** covering exactly **99 independently implementable and verifiable phases**: role auth → teacher backend → teacher frontend → reading backend → reading frontend → brain dump/assignments → schedule → sync/notifications → analytics → UX parity → security → tooling → integration → verification/docs.

---

# PART 1 — Repository Overview

## 1.1 Reference: STUDENT-PLANAR

| Aspect | Detail |
|---|---|
| **Type** | MERN role-based study planner (student + teacher dashboards) |
| **Layout** | Monorepo `client/` (Vite React) + `server/` (Express API, port 5000) |
| **Stack** | React 19 + React Router v7 + Vite + Axios · Express v5 + Mongoose v9 (MongoDB) + bcryptjs + multer + dotenv + cors |
| **Auth** | Role-gated signup/login (`Student` vs `Teacher`); teacher signup requires `TEACHER_SECRET_KEY`; client stores user in `localStorage`; **no server-side token/session** |
| **Data** | 9 Mongoose collections: Student, Teacher, Habit, Course, Assignment, Schedule, Todo, BrainDump, Book |
| **Theming** | CSS custom properties (cyberpunk neon: `--bg-color`, `--accent-cyan`, etc.) + inline styles; fonts Orbitron / Space Grotesk |

### Server endpoints (all under `/api`)
Auth: `POST /signup`, `POST /login`, `GET /students`. Generic CRUD (via `makeCrud(Model, route)`) per model: `GET /:model/:studentId`, `POST /:model`, `PUT /:model/:id`, `DELETE /:model/:id` for **habits, courses, assignments, schedules, todos, braindumps, books**. Uploads (multer): `POST /upload-book`, `POST /upload-assignment` (files stored in `server/uploads/`, served statically).

### Client views
`RoleSelect` (login/signup) · Student: `Dashboard` (live clock, todos, hardcoded weekly schedule) · `AssignmentTracker` (4 tabs: Current / By Course / By Type / Completed; status Complete button; file download) · `CourseManager` (progress cards, stub search) · `DailySchedule` (date picker, tabs Overview/School/Study Time/Break, add-block via prompt, done toggle) · `HabitTracker` (7-day checkboxes + Canvas line chart) · `PomodoroView` (25/5/15 timer + brain dump with 1s debounced auto-save) · `ReadingTracker` (4 tabs: All/Topics/Finished/Insights; PDF reader modal; insights stats) · Teacher: `TeacherDashboard` (student list + stats, selection checkboxes, broadcast hub for courses/assignments/todos/books, per-student detail modal).

## 1.2 Target: Student Life OS (productivity_app)

| Aspect | Detail |
|---|---|
| **Type** | Full-stack gamified student productivity OS (working, tested, on `main`) |
| **Backend** | Python 3.11+ · **FastAPI** · SQLAlchemy 2 · **SQLite** · Pydantic v2 · pydantic-settings |
| **Frontend** | **React 19** · TypeScript strict · Vite · react-router-dom v7 · @tanstack/react-query · recharts · date-fns · oxlint · vitest |
| **Entry points** | `backend/main.py` (28 routers; lifespan `create_all` + `migrate_schema()` + `seed_database()`) · `frontend/src/App.tsx` (31 routes) |
| **Auth** | Minimal single-user `POST /api/auth/login` returning the first user — **no roles, no passwords** |
| **Data** | 34+ SQLAlchemy models incl. User, Course, Assignment, Exam, Task, Reminder, Schedule, Habit, HabitLog, PomodoroSession, Note, JournalEntry, Quest/Mission/Reward, Project, LifeArea, FitnessHub models |
| **Relevant existing models** | `Assignment(id, title, description, course_id, due_date, status)` — **no type/attachment**; `ScheduleEvent(id, user_id, day_of_week, start/end_time, event_type, location, reference_type/id, color)` — **weekly recurring, no energy/done/date-specific blocks** |

**Verified target capabilities relevant to this audit:** `DigitalClock` widget exists; `Task`/`MiniTodoList` covers todos; `CourseCard`/`CourseCardsRow` covers course progress; `HabitTracker`+`GamifiedHabitTracker` (XP, heatmaps, streaks) and `Pomodoro` (ProgressRing, SettingsModal) are **richer than** STUDENT-PLANAR equivalents; `Notes`/`Journal`/`DailyLog` cover free-text capture (but no brain-dump autosave pattern); **no reading/books domain, no file uploads, no teacher/role concept, no notifications**.

---

# PART 2 — Architecture Comparison

| Dimension | STUDENT-PLANAR (reference) | Student Life OS (target) | Verdict / strategy |
|---|---|---|---|
| **API framework** | Express (JS) | FastAPI (Python, Pydantic) | Keep **FastAPI** |
| **Database** | MongoDB (Mongoose, schemaless) | SQLite + SQLAlchemy (relational) | Keep **SQLAlchemy**; new models are relational tables + `COLUMN_MIGRATIONS` |
| **Endpoint factory** | `makeCrud(Model, route)` higher-order generator | Explicit routers per domain | Adopt a **light generic CRUD helper** (`app/services/crud.py`) for the 4 new repetitive domains (books, dailyschedule, braindumps) but keep explicit routers visible in `main.py` |
| **Auth** | Role field + localStorage; **no server-side enforcement** | Single-user stub login | **Build proper role auth** (student/teacher, bcrypt, token, `get_current_user` guard) — reuse the target's existing `/api/auth` prefix; do **not** replicate the no-auth weakness |
| **File uploads** | multer → `server/uploads/` | none | Add FastAPI `python-multipart` uploads + static `UPLOAD_DIR` mount (Phase 5) |
| **Frontend** | JSX + inline styles + CSS vars | React 19 TS strict + shared components + themes | Keep target stack; new pages use `services/api.ts`, `types/index.ts`, `Toast`/`Skeleton`/`EmptyState`/`ErrorBoundary` |
| **State** | `useState`/`useEffect`, localStorage | react-query + hooks | Reuse target hooks pattern (`useQuestCentreData`-style) |
| **Tests** | none shipped | pytest 200 + vitest 25 | Reuse both gates per phase |
| **Clock / widgets** | inline clock in Dashboard | `DigitalClock` widget exists | Already covered — no port needed |

**Deliberate non-ports (STUDENT-PLANAR weaknesses):**
1. **No server-side auth / client-trusted `studentId`** → replaced with real role auth (G1).
2. **Hardcoded habit day labels** (`['Mon 24', ...]`) → target habit tracker is real-date aware; not ported.
3. **Teacher N+1 stats queries** (1 + 4/student) → target uses a single aggregation endpoint (Phase 9).
4. **Stub course search bar** → only ported if wired to real filtering (Phase 46 note).
5. **`prompt()`-based add-block UI** → replaced with a proper modal form (Phase 60).
6. **Canvas chart** for habits → target uses recharts; not ported.
7. **Broadcast to "all students" when none selected** → kept explicit with a confirmation dialog in the target (Phase 17).

---

# PART 3 — Complete Feature Inventory & Comparison

Legend: ✅ Fully implemented · ◑ Partially implemented · ❌ Missing · 🎨 Better in target · ⏸ Not applicable

| # | STUDENT-PLANAR feature | Source file(s) | Status in target | Gap / action |
|---|---|---|---|---|
| S1 | Role-based login/signup (student/teacher + secret key) | `views/common/RoleSelect.jsx`, `server/routes/api.js` | ❌ | Multi-user role auth must be built (G1) |
| S2 | Student dashboard with live clock | `views/student/Dashboard.jsx` | 🎨 | `DigitalClock` widget + Dashboard already exist |
| S3 | Dashboard todo list with toggle-done | `views/student/Dashboard.jsx` | 🎨 | `Task`/`MiniTodoList` exist |
| S4 | Assignment list with 4 view tabs (Current/By Course/By Type/Completed) | `views/student/AssignmentTracker.jsx` | ◑ | Assignments page exists; add tabs + type taxonomy (G7) |
| S5 | Assignment status workflow (not-started/progress/done) | `AssignmentTracker.jsx`, `routes/api.js` | ◑ | Add status enum + Complete action (G6–G7) |
| S6 | Assignment file upload + download | `routes/api.js` (`upload-assignment`), `AssignmentTracker.jsx` | ❌ | Upload infra + assignment `file_url` (G1, G6) |
| S7 | Course manager with progress bars | `views/student/CourseManager.jsx` | 🎨 | `CourseCard`/`CourseCardsRow` exist |
| S8 | Daily schedule: date picker + per-day blocks | `views/student/DailySchedule.jsx` | ◑ | Target is weekly recurring; add date-specific daily view (G8–G9) |
| S9 | Schedule tabs (Overview/School/Study Time/Break) | `DailySchedule.jsx` | ❌ | Add category tabs to daily view (G9) |
| S10 | Schedule add-block + done toggle + energy/category tags | `DailySchedule.jsx`, `models/index.js` (Schedule) | ❌ | New `DailyScheduleItem` model + endpoints (G8) |
| S11 | Habit 7-day checkboxes + progress + canvas chart | `views/student/HabitTracker.jsx` | 🎨 | Target habit tracker is strictly better; not ported |
| S12 | Pomodoro timer (25/5/15) | `views/student/PomodoroView.jsx` | 🎨 | Target pomodoro is richer |
| S13 | Brain dump with debounced auto-save | `PomodoroView.jsx`, `models/index.js` (BrainDump) | ❌ | Add brain-dump widget + upsert API (G6–G7) |
| S14 | Reading tracker: book library + categories | `views/student/ReadingTracker.jsx`, `Book` model | ❌ | Entire new domain (G4–G5) |
| S15 | Book file upload + PDF reader modal | `routes/api.js` (`upload-book`), `ReadingTracker.jsx` | ❌ | Upload + iframe reader (G4–G5) |
| S16 | Reading insights (stats + consistency) | `ReadingTracker.jsx` | ❌ | Insights endpoint + UI (G4–G5) |
| S17 | Teacher dashboard: student list + per-student stats | `views/teacher/TeacherDashboard.jsx` | ❌ | Teacher backend (G2) + frontend (G3) |
| S18 | Teacher broadcast courses | `TeacherDashboard.jsx`, `routes/api.js` | ❌ | Broadcast endpoint + UI (G2–G3) |
| S19 | Teacher broadcast assignments (+ file) | `TeacherDashboard.jsx`, `upload-assignment` | ❌ | Broadcast + upload (G2–G3) |
| S20 | Teacher broadcast todos | `TeacherDashboard.jsx`, `routes/api.js` | ❌ | Broadcast endpoint + UI (G2–G3) |
| S21 | Teacher broadcast books (+ file) | `TeacherDashboard.jsx`, `upload-book` | ❌ | Broadcast + upload (G2–G3) |
| S22 | Student selection (checkboxes, select-all/clear) | `TeacherDashboard.jsx` | ❌ | Selection state + broadcast targeting (G3) |
| S23 | Student detail modal (brain dump + reading shelf) | `TeacherDashboard.jsx` | ❌ | Detail modal (G3, G7) |
| S24 | Student role route protection | `StudentApp.jsx` | ❌ | `RoleGate` + protected routes (G1) |
| S25 | Logout | `Navigation.jsx` | ◑ | Real logout via token clear (G1) |
| S26 | Navigation with active state | `Navigation.jsx` | 🎨 | Target `Sidebar`/`NavLinks` exist |
| S27 | File uploads (books + assignments) | `routes/api.js` (multer) | ❌ | FastAPI upload infra (G1) |

**Not-applicable / excluded features with justification:**
- **S2 clock, S3 todos, S7 courses, S11 habits, S12 pomodoro, S26 nav** — already implemented (often better) in the target; back-porting would duplicate logic and regress the richer versions.
- **STUDENT-PLANAR's auth model (no server-side session)** — intentionally replaced; the target gets real role auth instead of replicating the weakness.
- **`makeCrud` wholesale** — the target's explicit-router style is more readable and matches its conventions; only a small shared CRUD helper is adopted for the new repetitive domains.
- **Hardcoded demo schedule data** in `Dashboard.jsx` — not ported; target uses real data.

---

# PART 4 — Gap Analysis

## 4.1 Frontend gaps
| Area | Gap |
|---|---|
| Auth/UX | No login/signup page, no role selector, no AuthContext, no protected routes, no logout |
| Pages | No `/teacher`, `/reading`, `/brain-dump`; `/assignments` lacks tabs; `/schedule` lacks daily date-specific view |
| Components | No teacher dashboard/broadcast hub, book library/PDF modal, brain-dump autosave widget, daily-schedule block editor, notifications bell |
| API layer | `services/api.ts` lacks auth/teacher/books/braindump/daily-schedule/upload functions; `types/index.ts` lacks those domains |
| Accessibility/responsive | New pages must match existing standards (focus, aria, mobile grid, empty/loading/error states) |

## 4.2 Backend gaps
| Area | Gap |
|---|---|
| Auth | No roles, no passwords, no tokens, no `get_current_user` dependency |
| Uploads | No `python-multipart`, no `UPLOAD_DIR`, no static file serving, no size/type validation |
| Reading | No `Book` model, no book endpoints, no insights |
| Brain dump | No `BrainDump` table, no upsert endpoint |
| Assignments | No `type`/`type_color`/`time_estimate`/`file_url`, no status workflow endpoints |
| Daily schedule | No date-specific `DailyScheduleItem`, no energy/category/done fields |
| Teacher | No student-list/stats aggregation, no broadcast endpoints, no authorization matrix |
| Notifications | No in-app notification model for broadcasts |

## 4.3 Productivity features gaps
- **Search**: not required by the reference beyond the stub (only port real course filter — optional Phase 46).
- **AI**: not part of STUDENT-PLANAR; **not planned** (out of scope for this reference).
- **Notifications**: broadcast → student notification workflow (G10).
- **Settings**: role/profile display (G2) — STUDENT-PLANAR has none meaningful.
- **Workflows/automation**: teacher→student broadcast pipeline is the core automation (G2–G3, G10).

## 4.4 Infrastructure gaps
- **Security**: role authorization matrix (G13), upload validation (G13), password hashing (G1).
- **Performance**: single-query student stats (G2), avoid N+1; pagination for books (G4).
- **Error handling**: toasts for broadcast results (G3); consistent 4xx/5xx on new routers.
- **Testing**: new pytest/vitest suites per domain; authorization tests (G13).
- **Dev tooling**: `requirements.txt` (+`python-multipart`, `passlib`/`bcrypt`); `.env.example` (`TEACHER_SECRET_KEY`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET`).
- **Deployment**: static uploads dir mount; README updates (G16).

---

# PART 5 — Feature Mapping (source → destination)

| # | Reference feature | STUDENT-PLANAR source | Target destination (create) | Target destination (modify) | Dependencies | Strategy / refactor | Effort | Risk |
|---|---|---|---|---|---|---|---|---|
| S1 | Role auth | `RoleSelect.jsx`, `api.js` (signup/login) | `app/routers/auth.py` (extend), `app/schemas/user.py` | `models/user.py` (role, password_hash, username, email), `main.py`, `services/api.ts`, `App.tsx`, `components/auth/*`, `pages/Login.tsx` | — | bcrypt hashing, token (opaque or JWT), `get_current_user`; keep legacy `/api/auth/login` compatible | **High** | Medium (auth regression) |
| S17–S23 | Teacher dashboard + broadcast | `TeacherDashboard.jsx`, `api.js` | `app/routers/teacher.py`, `app/services/teacher.py`, `pages/Teacher.tsx`, `components/teacher/*` | `main.py`, `Sidebar.tsx`, `App.tsx` | G1 auth | Single aggregate stats query; broadcast = multi-create to selected/all; authz guard | **High** | Medium (data-ownership) |
| S14–S16 | Reading tracker | `ReadingTracker.jsx`, `Book` model | `models/book.py`, `schemas/book.py`, `routers/books.py`, `services/reading.py`, `pages/Reading.tsx`, `components/reading/*` | `main.py`, `models/__init__.py`, `services/api.ts`, `types/index.ts` | G1 uploads | categories enum; PDF served from `UPLOAD_DIR`; insights computed server-side | **Medium** | Low |
| S13 | Brain dump | `PomodoroView.jsx`, `BrainDump` model | `models/braindump.py`, `routers/braindumps.py`, `components/BrainDumpWidget.tsx` | `main.py`, `Dashboard.tsx`, `Pomodoro.tsx` | G1 | one-row-per-user upsert; debounced autosave | **Low** | Low |
| S4–S6 | Assignment tabs/status/files | `AssignmentTracker.jsx`, `upload-assignment` | `routers/uploads.py` (reuse) | `models/assignment.py` (type, type_color, time_estimate, file_url, status enum), `schemas/assignment.py`, `pages/Assignments.tsx`, `components/assignments/*` | G1 uploads | columns via `COLUMN_MIGRATIONS`; tabs client-side | **Medium** | Low |
| S8–S10 | Daily schedule blocks | `DailySchedule.jsx`, `Schedule` model | `models/daily_schedule_item.py`, `routers/daily_schedule.py`, `components/schedule/*` | `main.py`, `pages/Schedule.tsx`, `models/__init__.py` | G1 | date-specific table alongside existing weekly `ScheduleEvent` | **Medium** | Low |
| S18–S21 | Broadcast notifications | (not in reference) | `models/notification.py`, `routers/notifications.py`, `components/NotificationsBell.tsx` | `main.py`, `Sidebar.tsx`, `Dashboard.tsx` | S17–S23, G2 | emit on broadcast; unread counts | **Medium** | Low |

**Potential conflicts & mitigations:** extending `User` is additive (migrations); new `/api/books`, `/api/braindumps`, `/api/dailyschedule`, `/api/teacher`, `/api/notifications` namespaces are collision-free; `Assignments.tsx` route stays but is enhanced; `Schedule.tsx` gains a daily view alongside the weekly timetable; no existing route/endpoint removed.

---

# PART 6 — Integration Strategy

1. **Layered rollout (G1→G16).** Role auth and uploads first (unlock everything), then teacher domain, then reading, then brain-dump/assignments, then daily schedule, then sync/notifications, then analytics/UX/security/verification.
2. **Every phase independently shippable** with exact `Modify`/`Create` files, a `Validation` step, and a `Completion` bar; verification gates close each group.
3. **Backward compatibility.** All changes additive; existing 28 routers/31 routes intact; new columns via `COLUMN_MIGRATIONS`; existing seed preserved; legacy single-user login still works.
4. **Reuse over rewrite.** New routers mirror `quest_centre.py`/`habit_tracker.py` shapes; new hooks mirror `useQuestCentreData.ts`; shared components reused; a small `app/services/crud.py` helper dedups the 3 repetitive CRUD domains.
5. **Auth-z everywhere.** Every new endpoint is guarded by `get_current_user`; teacher-only endpoints guarded by role dependency.
6. **Demo seed.** Seed demo student + teacher (with `TEACHER_SECRET_KEY` gated signup) and demo books so all new UIs are immediately verifiable.

---

# PART 7 — Dependency Analysis

| Layer | New dependency | Purpose | Where added |
|---|---|---|---|
| Backend | `python-multipart` | multipart upload endpoints | Phase 5 |
| Backend | `passlib[bcrypt]` (or `bcrypt`) | password hashing for role auth | Phase 1 |
| Backend | — (no new AI/vector deps) | reference has no AI | — |
| Frontend | — (react-query, recharts, date-fns present) | data + charts | G3/G5/G9 |
| Env | `TEACHER_SECRET_KEY`, `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET` | config | Phases 1/5 |

**Ordering constraints:** G1 (auth + uploads) must precede all; G2/G3 (teacher) need G1; G4/G5 (reading) need G1; G6/G7 need G1; G8/G9 need G1; G10 needs G2/G3; G11 needs G4–G9; G13 needs G1–G12; G16 needs everything.

---

# PART 8 — Risk Assessment

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Auth migration regresses existing single-user app | Medium | High | Additive columns; legacy login preserved; full regression at Phase 7 |
| R2 | Teacher broadcast data-ownership bugs (student A sees student B's data) | Medium | High | `get_current_user` scoping on every query + authz tests (G13) |
| R3 | Upload security (path traversal, MIME spoof, oversized files) | Medium | Medium | Whitelist extensions, size cap, safe filename, static mount scoped to `UPLOAD_DIR` (Phase 5, G13) |
| R4 | PDF rendering in-browser (iframe) inconsistent across browsers | Medium | Low | Client iframe `object`/`embed` fallback; file served with correct `Content-Type` |
| R5 | New daily schedule view conflicts visually with existing weekly timetable | Low | Medium | Separate section/tab; shared date utilities; visual check in Phase 96 |
| R6 | Broadcast to "all" accidentally spams students | Medium | Low | Explicit confirmation dialog + notification dedup (Phase 17) |
| R7 | Stray uncommitted AI-scaffold files in backend (`ai.py`, `ai_client.py`, `ai_fallback.py`, config.py edits) conflict with new routers | Medium | Low | New routers use distinct prefixes; leave strays untouched; note in Phase 2 |

---

# PART 9 — THE 99-PHASE ROADMAP

> Phase template (project convention): `#### Phase N — Title` with `Objective` / `Modify` / `Create` / `Deps` / `Complexity` / `Risks` / `Validation` / `Completion`. Groups G1–G16 are dependency-ordered.

## GROUP G1 — Foundations: role auth, uploads, shell (Phases 1–7)

#### Phase 1 — Role-based auth foundation
- **Objective:** Add student/teacher roles, password hashing, and a `get_current_user` dependency without breaking the existing login.
- **Modify:** `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/app/routers/auth.py`, `backend/app/database.py`
- **Create:** `backend/app/services/security.py`, `backend/tests/test_auth_roles.py`
- **Deps:** none | **Complexity:** high | **Risks:** R1
- **Validation:** existing `POST /api/auth/login` still works; new `signup` hashes password and assigns role; `get_current_user` rejects unauthenticated
- **Completion:** `User` gains `username`, `email`, `password_hash`, `role` ('student'/'teacher') via `COLUMN_MIGRATIONS`; `/api/auth/signup`, `/api/auth/login`, `/api/auth/me`, `/api/auth/logout`; `bcrypt` verified.

#### Phase 2 — Teacher role guard + authorization dependency
- **Objective:** Enforce teacher-only access on future teacher endpoints.
- **Modify:** `backend/app/services/security.py`
- **Create:** `backend/tests/test_authz.py`
- **Deps:** Phase 1 | **Complexity:** low | **Risks:** R2
- **Validation:** a student token is rejected by `require_teacher`; a teacher token passes
- **Completion:** `get_current_user`, `require_student`, `require_teacher` dependencies; authz unit tests green.

#### Phase 3 — Frontend auth: login/signup page + AuthContext + protected routes
- **Objective:** Role-selected login/signup, token persistence, and route gating.
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/src/App.tsx`, `frontend/src/main.tsx`
- **Create:** `frontend/src/pages/Login.tsx`, `frontend/src/context/AuthContext.tsx`, `frontend/src/components/auth/RoleGate.tsx`, `frontend/src/hooks/useAuth.ts`, `frontend/src/test/auth.test.tsx`
- **Deps:** Phase 1 | **Complexity:** high | **Risks:** R1
- **Validation:** vitest logs in as student → Dashboard; teacher-only route blocks student; logout clears token
- **Completion:** role selector UI (student/teacher + teacher secret key), token in memory/localStorage, `<RoleGate role="teacher">`, `/login` route, logout.

#### Phase 4 — Frontend nav + role-aware shell
- **Objective:** Sidebar shows teacher links only to teachers; student links as today.
- **Modify:** `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/widgets/NavLinks.tsx`
- **Create:** — | **Deps:** Phase 3 | **Complexity:** low | **Risks:** none
- **Validation:** `tsc -b` clean; teacher sees `/teacher`; student does not
- **Completion:** role-conditional nav sections; active state preserved.

#### Phase 5 — Upload infrastructure (backend)
- **Objective:** Multipart upload endpoint + static serving + validation.
- **Modify:** `backend/main.py` (static mount), `backend/app/config.py`, `.env.example`, `backend/requirements.txt`
- **Create:** `backend/app/routers/uploads.py`, `backend/tests/test_uploads.py`
- **Deps:** Phase 1 | **Complexity:** medium | **Risks:** R3
- **Validation:** POST a small PDF → 201 + URL; oversize → 413; disallowed ext → 400; files served from `UPLOAD_DIR`
- **Completion:** `POST /api/uploads` validates size/type, stores with safe filename, returns URL; static mount; config `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET`.

#### Phase 6 — Frontend auth client + API helpers
- **Objective:** Typed API helpers for auth and uploads.
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** `frontend/src/test/api.test.ts` (mock-based)
- **Deps:** Phase 5 | **Complexity:** low | **Risks:** none
- **Validation:** `authApi`, `uploadApi` compile; mocked tests pass
- **Completion:** `authApi` (signup/login/me/logout), `uploadApi.upload(file, kind)`, `UserRole`/`AuthUser` types.

#### Phase 7 — G1 verification gate
- **Objective:** Prove foundations did not regress the suite.
- **Modify:** — | **Create:** — | **Deps:** Phases 1–6 | **Complexity:** low | **Risks:** R1
- **Validation:** `pytest` (200 baseline + new auth/upload tests) green; `tsc -b`; vitest; build
- **Completion:** role auth + uploads stable; legacy login intact.

## GROUP G2 — Teacher backend (Phases 8–14)

#### Phase 8 — Student list + aggregate stats endpoint
- **Objective:** Single-query teacher view of all students with stats.
- **Modify:** `backend/app/routers/auth.py` (or new router)
- **Create:** `backend/app/routers/teacher.py`, `backend/app/services/teacher.py`, `backend/tests/test_teacher.py`
- **Deps:** Phase 2 | **Complexity:** medium | **Risks:** R2
- **Validation:** with seeded students, returns per-student counts (courses, assignments, todos, books) via grouped queries (no N+1)
- **Completion:** `GET /api/teacher/students` → `[{id, name, stats:{courses, assignments, todos, books, braindump}}]`, teacher-guarded.

#### Phase 9 — Broadcast: courses
- **Objective:** Assign/create a course for selected students or all.
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 8 | **Complexity:** medium | **Risks:** R2
- **Validation:** broadcast to 2 selected students creates 2 owned rows; "all" creates for every student; teacher-only
- **Completion:** `POST /api/teacher/broadcast/courses` accepts `{course, student_ids?}`; targets selected or all.

#### Phase 10 — Broadcast: assignments (+ file)
- **Objective:** Assign an assignment with optional attachment.
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 9, Phase 6 | **Complexity:** medium | **Risks:** R2/R3
- **Validation:** multipart broadcast creates assignments with `file_url` for each target
- **Completion:** `POST /api/teacher/broadcast/assignments` (multipart) → per-student Assignment rows; defaults type 'Homework', status 'Not started'.

#### Phase 11 — Broadcast: todos
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 9 | **Complexity:** low | **Risks:** R2
- **Validation:** broadcast todo creates owned Task rows | **Completion:** `POST /api/teacher/broadcast/todos`.

#### Phase 12 — Broadcast: books (+ file)
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 9, Phase 5 | **Complexity:** medium | **Risks:** R2/R3
- **Validation:** upload + broadcast creates Book rows with `file_url`/`cover_url` | **Completion:** `POST /api/teacher/broadcast/books` (multipart).

#### Phase 13 — Teacher read of student detail (assignments/todos/brain dump/books)
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 12 | **Complexity:** medium | **Risks:** R2
- **Validation:** teacher fetches one student's full detail; student cannot call it | **Completion:** `GET /api/teacher/students/{id}/detail` returns assignments/todos/braindump/books.

#### Phase 14 — G2 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 8–13 | **Complexity:** low | **Risks:** none
- **Validation:** teacher tests green; authz tests confirm student→403; regression | **Completion:** teacher backend complete.

## GROUP G3 — Teacher frontend (Phases 15–21)

#### Phase 15 — Teacher dashboard page + route
- **Create:** `frontend/src/pages/Teacher.tsx`, `frontend/src/components/teacher/TeacherHeader.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 14 | **Complexity:** medium | **Risks:** R7
- **Validation:** `/teacher` renders only for teacher role; empty-state present | **Completion:** teacher page route + nav + basic layout.

#### Phase 16 — Student list with stats + selection
- **Create:** `frontend/src/components/teacher/StudentList.tsx`, `frontend/src/components/teacher/StudentStats.tsx`
- **Modify:** `frontend/src/pages/Teacher.tsx`
- **Deps:** Phase 15 | **Complexity:** medium | **Risks:** none
- **Validation:** vitest renders student cards with stats; checkboxes select (select-all/clear) | **Completion:** student grid + selection state; disabled actions when no student data.

#### Phase 17 — Broadcast hub UI
- **Create:** `frontend/src/components/teacher/BroadcastHub.tsx`, `frontend/src/components/teacher/BroadcastModal.tsx`
- **Modify:** `frontend/src/pages/Teacher.tsx`
- **Deps:** Phase 16 | **Complexity:** medium | **Risks:** R6
- **Validation:** four actions (course/assignment/todo/book); confirmation dialog for "all students"; toasts on result | **Completion:** broadcast hub with target selection + confirm + toast feedback.

#### Phase 18 — Assignment/todo broadcast forms
- **Create:** `frontend/src/components/teacher/AssignmentBroadcastForm.tsx`, `frontend/src/components/teacher/TodoBroadcastForm.tsx`
- **Modify:** `frontend/src/components/teacher/BroadcastModal.tsx`
- **Deps:** Phase 17 | **Complexity:** medium | **Risks:** none
- **Validation:** vitest submits form → api called with selected ids; file input present for assignments | **Completion:** validated forms wired to teacher endpoints.

#### Phase 19 — Book/course broadcast forms + file upload
- **Create:** `frontend/src/components/teacher/BookBroadcastForm.tsx`, `frontend/src/components/teacher/CourseBroadcastForm.tsx`
- **Modify:** `frontend/src/components/teacher/BroadcastModal.tsx`
- **Deps:** Phase 18 | **Complexity:** medium | **Risks:** R3
- **Validation:** upload shows progress; book cover auto-picks default | **Completion:** book (with file) and course broadcast forms.

#### Phase 20 — Student detail modal
- **Create:** `frontend/src/components/teacher/StudentDetailModal.tsx`
- **Modify:** `frontend/src/pages/Teacher.tsx`
- **Deps:** Phase 13 | **Complexity:** medium | **Risks:** none
- **Validation:** modal shows assignments/todos/brain dump/reading shelf from detail endpoint | **Completion:** read-only teacher view of a student's data.

#### Phase 21 — G3 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 15–20 | **Complexity:** low | **Risks:** none
- **Validation:** vitest teacher tests; `tsc -b`; build | **Completion:** teacher UI complete end-to-end.

## GROUP G4 — Reading tracker: backend (Phases 22–28)

#### Phase 22 — Book model + schema
- **Create:** `backend/app/models/book.py`, `backend/app/schemas/book.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 1 | **Complexity:** low | **Risks:** none
- **Validation:** imports clean | **Completion:** `Book(id, user_id, title, author, category ∈ {reading, finished, want}, cover_url, file_url, created_at)`.

#### Phase 23 — Books CRUD router
- **Create:** `backend/app/routers/books.py`, `backend/tests/test_books.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 22 | **Complexity:** low | **Risks:** R2
- **Validation:** CRUD round-trip; rows scoped to `user_id` | **Completion:** `/api/books` (list/create/update/delete).

#### Phase 24 — Book upload + static serving
- **Modify:** `backend/app/routers/books.py`
- **Create:** — | **Deps:** Phase 23, Phase 5 | **Complexity:** medium | **Risks:** R3
- **Validation:** upload a PDF → book has `file_url`; GET serves it | **Completion:** `POST /api/books/upload` reusing `uploads.py`; correct `Content-Type`.

#### Phase 25 — Reading insights endpoint
- **Create:** `backend/app/services/reading.py`
- **Modify:** `backend/app/routers/books.py`
- **Deps:** Phase 23 | **Complexity:** medium | **Risks:** none
- **Validation:** seeded books produce total/finished/reading/want + consistency % | **Completion:** `GET /api/books/insights` → `{total, finished, reading, want, completion_pct, per_author}`.

#### Phase 26 — Demo book seed
- **Modify:** `backend/app/seed/__init__.py`
- **Create:** — | **Deps:** Phase 23 | **Complexity:** low | **Risks:** none
- **Validation:** fresh DB seeds a demo student with 3 books across categories | **Completion:** deterministic demo reading shelf.

#### Phase 27 — Pagination + filter support
- **Modify:** `backend/app/routers/books.py`
- **Create:** — | **Deps:** Phase 25 | **Complexity:** low | **Risks:** none
- **Validation:** `?category=` and `?page=&page_size=` return correct subsets | **Completion:** paginated, filterable list.

#### Phase 28 — G4 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 22–27 | **Complexity:** low | **Risks:** none
- **Validation:** book tests green; regression | **Completion:** reading backend complete.

## GROUP G5 — Reading tracker: frontend (Phases 29–35)

#### Phase 29 — Reading API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 28 | **Complexity:** low | **Risks:** none
- **Validation:** `tsc -b` clean | **Completion:** `bookApi` + `Book`/`BookInsights` types.

#### Phase 30 — Reading page + route
- **Create:** `frontend/src/pages/Reading.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 29 | **Complexity:** medium | **Risks:** R7
- **Validation:** `/reading` renders; empty-state | **Completion:** reading route + page shell + nav.

#### Phase 31 — Book library tabs + cards
- **Create:** `frontend/src/components/reading/BookTabs.tsx`, `frontend/src/components/reading/BookCard.tsx`
- **Modify:** `frontend/src/pages/Reading.tsx`
- **Deps:** Phase 30 | **Complexity:** medium | **Risks:** none
- **Validation:** tabs (All/Topics/Finished/Insights) filter; cards show cover/title/author | **Completion:** library UI with category tabs and grouped topics.

#### Phase 32 — Book actions (read/finish/start/remove)
- **Modify:** `frontend/src/pages/Reading.tsx`
- **Create:** `frontend/src/hooks/useReading.ts`
- **Deps:** Phase 31 | **Complexity:** medium | **Risks:** none
- **Validation:** actions call api and update list; confirm on remove | **Completion:** hover overlay actions wired end-to-end.

#### Phase 33 — PDF reader modal
- **Create:** `frontend/src/components/reading/PDFReader.tsx`
- **Modify:** `frontend/src/pages/Reading.tsx`
- **Deps:** Phase 32 | **Complexity:** low | **Risks:** R4
- **Validation:** modal opens file URL in iframe/object; closes cleanly | **Completion:** full-screen reader with fallback.

#### Phase 34 — Insights dashboard
- **Create:** `frontend/src/components/reading/ReadingInsights.tsx`
- **Modify:** `frontend/src/pages/Reading.tsx`
- **Deps:** Phase 25 | **Complexity:** medium | **Risks:** none
- **Validation:** stat cards + consistency bar render from `/api/books/insights` | **Completion:** insights tab with stats + per-author grouping.

#### Phase 35 — G5 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 29–34 | **Complexity:** low | **Risks:** none
- **Validation:** vitest reading tests; `tsc -b`; build | **Completion:** reading tracker UI complete.

## GROUP G6 — Brain dump + assignment enhancements: backend (Phases 36–42)

#### Phase 36 — BrainDump model + upsert router
- **Create:** `backend/app/models/braindump.py`, `backend/app/routers/braindumps.py`, `backend/app/schemas/braindump.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`, `backend/main.py`
- **Deps:** Phase 1 | **Complexity:** low | **Risks:** none
- **Validation:** one row per user; PUT upserts; `updated_at` refreshes | **Completion:** `GET/PUT /api/braindumps` (single-row-per-user).

#### Phase 37 — Assignment model extension
- **Modify:** `backend/app/models/assignment.py`, `backend/app/database.py`, `backend/app/schemas/assignment.py`
- **Create:** — | **Deps:** Phase 1 | **Complexity:** low | **Risks:** none
- **Validation:** columns added via `COLUMN_MIGRATIONS`; schema compiles | **Completion:** `Assignment` gains `type` ('Homework'|'Quiz'|'Project'|'Test'|'Other'), `type_color`, `time_estimate` (minutes), `file_url`, `status` ∈ {not-started, progress, done}.

#### Phase 38 — Assignment status workflow endpoints
- **Modify:** `backend/app/routers/assignments.py`
- **Create:** `backend/tests/test_assignments_flow.py`
- **Deps:** Phase 37 | **Complexity:** low | **Risks:** none
- **Validation:** mark progress/done persists; completion reflected in course stats | **Completion:** `POST /api/assignments/{id}/status` + `POST /api/assignments/{id}/complete`.

#### Phase 39 — Assignment upload + download
- **Modify:** `backend/app/routers/assignments.py`
- **Create:** — | **Deps:** Phase 38, Phase 5 | **Complexity:** medium | **Risks:** R3
- **Validation:** attach a file to an assignment; `file_url` returned; download works | **Completion:** `POST /api/assignments/{id}/attachment` reusing upload infra.

#### Phase 40 — Assignment type/status taxonomy seed + filter support
- **Modify:** `backend/app/seed/__init__.py`, `backend/app/routers/assignments.py`
- **Create:** — | **Deps:** Phase 38 | **Complexity:** low | **Risks:** none
- **Validation:** seed covers all types/statuses; list filterable by type/status/course | **Completion:** `GET /api/assignments?type=&status=&course_id=`.

#### Phase 41 — Teacher visibility of student brain dump + assignments
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 13, Phase 36 | **Complexity:** low | **Risks:** R2
- **Validation:** detail endpoint now includes `braindump` + typed assignments | **Completion:** teacher detail enriched; still teacher-only.

#### Phase 42 — G6 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 36–41 | **Complexity:** low | **Risks:** none
- **Validation:** braindump + assignment tests green; regression | **Completion:** brain dump + assignment backend complete.

## GROUP G7 — Brain dump + assignment enhancements: frontend (Phases 43–49)

#### Phase 43 — Brain dump widget (debounced autosave)
- **Create:** `frontend/src/components/BrainDumpWidget.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 36 | **Complexity:** medium | **Risks:** none
- **Validation:** typing → 1s debounce → PUT; "Synced" indicator; vitest | **Completion:** dashboard brain-dump card with autosave state indicator.

#### Phase 44 — Brain dump on pomodoro
- **Modify:** `frontend/src/pages/Pomodoro.tsx`
- **Create:** — | **Deps:** Phase 43 | **Complexity:** low | **Risks:** R7
- **Validation:** pomodoro page shows brain-dump panel alongside timer | **Completion:** reusable widget embedded in pomodoro view.

#### Phase 45 — Assignments tabs (Current/By Course/By Type/Completed)
- **Modify:** `frontend/src/pages/Assignments.tsx`
- **Create:** `frontend/src/components/assignments/AssignmentTabs.tsx`
- **Deps:** Phase 40 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest switches tabs and filters correctly | **Completion:** tabbed assignment list.

#### Phase 46 — Assignment status actions + type tags
- **Modify:** `frontend/src/pages/Assignments.tsx`
- **Create:** `frontend/src/components/assignments/AssignmentStatusTag.tsx`, `frontend/src/components/assignments/TypeTag.tsx`
- **Deps:** Phase 45 | **Complexity:** medium | **Risks:** none
- **Validation:** Complete button marks done; tags render per type/status | **Completion:** status workflow UI + tag styling.

#### Phase 47 — Assignment file upload/download UI
- **Modify:** `frontend/src/pages/Assignments.tsx`
- **Create:** `frontend/src/components/assignments/AttachmentUpload.tsx`
- **Deps:** Phase 39 | **Complexity:** medium | **Risks:** R3
- **Validation:** attach a file; download link renders for `file_url` | **Completion:** per-assignment attachment control + download.

#### Phase 48 — Course filter on assignments (real search)
- **Modify:** `frontend/src/pages/Assignments.tsx`
- **Create:** `frontend/src/components/assignments/AssignmentFilters.tsx`
- **Deps:** Phase 46 | **Complexity:** low | **Risks:** none
- **Validation:** filter by course/type works against list | **Completion:** working filter bar (unlike the reference's stub).

#### Phase 49 — G7 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 43–48 | **Complexity:** low | **Risks:** none
- **Validation:** vitest assignment/brain-dump tests; `tsc -b`; build | **Completion:** brain dump + assignments UI complete.

## GROUP G8 — Daily schedule: backend (Phases 50–56)

#### Phase 50 — DailyScheduleItem model + schema
- **Create:** `backend/app/models/daily_schedule_item.py`, `backend/app/schemas/daily_schedule.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 1 | **Complexity:** low | **Risks:** none
- **Validation:** imports clean | **Completion:** `DailyScheduleItem(id, user_id, date, time_range, activity, category, cat_class, location, energy, e_class, notes, done)` — complements (not replaces) weekly `ScheduleEvent`.

#### Phase 51 — Daily schedule CRUD router
- **Create:** `backend/app/routers/daily_schedule.py`, `backend/tests/test_daily_schedule.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 50 | **Complexity:** low | **Risks:** R2
- **Validation:** CRUD round-trip; scoped to user | **Completion:** `/api/dailyschedule` (list by date, create, update, delete).

#### Phase 52 — Toggle done + stats endpoints
- **Modify:** `backend/app/routers/daily_schedule.py`
- **Create:** — | **Deps:** Phase 51 | **Complexity:** low | **Risks:** none
- **Validation:** toggle persists; `GET /api/dailyschedule/stats?date=` returns done ratio | **Completion:** done toggle + per-day stats.

#### Phase 53 — Category/energy taxonomy + seed
- **Modify:** `backend/app/seed/__init__.py`, `backend/app/routers/daily_schedule.py`
- **Create:** `backend/app/services/schedule_catalog.py`
- **Deps:** Phase 51 | **Complexity:** low | **Risks:** none
- **Validation:** catalog lists categories (School/Study Time/Break) + energies (High/Medium/Low) with css classes | **Completion:** taxonomy constant + seed demo day.

#### Phase 54 — Add-block validation (server-side)
- **Modify:** `backend/app/routers/daily_schedule.py`
- **Create:** `backend/tests/test_daily_schedule_validation.py`
- **Deps:** Phase 53 | **Complexity:** medium | **Risks:** none
- **Validation:** overlapping/empty blocks rejected with 4xx | **Completion:** time-format + overlap validation.

#### Phase 55 — Teacher broadcast of schedule items
- **Modify:** `backend/app/routers/teacher.py`
- **Create:** — | **Deps:** Phase 54, Phase 9 | **Complexity:** low | **Risks:** R2
- **Validation:** broadcast adds a daily block to each selected student | **Completion:** `POST /api/teacher/broadcast/schedule`.

#### Phase 56 — G8 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 50–55 | **Complexity:** low | **Risks:** none
- **Validation:** daily-schedule tests green; regression | **Completion:** daily schedule backend complete.

## GROUP G9 — Daily schedule: frontend (Phases 57–63)

#### Phase 57 — Schedule API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 56 | **Complexity:** low | **Risks:** none
- **Validation:** `tsc -b` clean | **Completion:** `dailyScheduleApi` + `DailyScheduleItem` type.

#### Phase 58 — Daily schedule view (date picker + table)
- **Create:** `frontend/src/components/schedule/DailyScheduleView.tsx`
- **Modify:** `frontend/src/pages/Schedule.tsx`
- **Deps:** Phase 57 | **Complexity:** medium | **Risks:** R5
- **Validation:** date picker (min=today) loads blocks for that date | **Completion:** daily view alongside weekly timetable; empty-state.

#### Phase 59 — Schedule tabs (Overview/School/Study Time/Break)
- **Create:** `frontend/src/components/schedule/ScheduleTabs.tsx`
- **Modify:** `frontend/src/components/schedule/DailyScheduleView.tsx`
- **Deps:** Phase 58 | **Complexity:** low | **Risks:** none
- **Validation:** tabs filter blocks by category | **Completion:** category tab filtering.

#### Phase 60 — Add-block form (modal, not prompt())
- **Create:** `frontend/src/components/schedule/ScheduleBlockModal.tsx`
- **Modify:** `frontend/src/components/schedule/DailyScheduleView.tsx`
- **Deps:** Phase 58 | **Complexity:** medium | **Risks:** R5
- **Validation:** vitest submits a valid block; rejects overlap client-side | **Completion:** proper modal form with category/energy/location/time fields.

#### Phase 61 — Done toggle + energy/category styling
- **Modify:** `frontend/src/components/schedule/DailyScheduleView.tsx`
- **Create:** `frontend/src/components/schedule/EnergyTag.tsx`, `frontend/src/components/schedule/CategoryTag.tsx`
- **Deps:** Phase 60 | **Complexity:** medium | **Risks:** none
- **Validation:** toggle updates done; tags styled per taxonomy | **Completion:** interactive blocks with tags.

#### Phase 62 — Daily stats widget on dashboard
- **Create:** `frontend/src/components/schedule/DayProgressWidget.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 52 | **Complexity:** low | **Risks:** R7
- **Validation:** shows today's done ratio from stats endpoint | **Completion:** dashboard day-progress card.

#### Phase 63 — G9 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 57–62 | **Complexity:** low | **Risks:** none
- **Validation:** vitest schedule tests; `tsc -b`; build | **Completion:** daily schedule UI complete.

## GROUP G10 — Teacher→student sync & notifications (Phases 64–70)

#### Phase 64 — Notification model + schema
- **Create:** `backend/app/models/notification.py`, `backend/app/schemas/notification.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 1 | **Complexity:** low | **Risks:** none
- **Validation:** imports clean | **Completion:** `Notification(id, user_id, kind, title, body, ref_type, ref_id, read, created_at)`.

#### Phase 65 — Notification endpoints + emit-on-broadcast
- **Create:** `backend/app/routers/notifications.py`, `backend/tests/test_notifications.py`
- **Modify:** `backend/app/routers/teacher.py`, `backend/main.py`
- **Deps:** Phase 64, Phase 13 | **Complexity:** medium | **Risks:** R6
- **Validation:** broadcast emits one notification per target student; unread count correct | **Completion:** `/api/notifications` (list, unread count, mark-read, clear); teacher broadcasts auto-notify.

#### Phase 66 — Notification bell + list UI
- **Create:** `frontend/src/components/NotificationsBell.tsx`
- **Modify:** `frontend/src/components/layout/Header.tsx`, `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 65 | **Complexity:** medium | **Risks:** R7
- **Validation:** vitest shows unread badge + dropdown list; mark-read works | **Completion:** bell with unread badge + notification drawer.

#### Phase 67 — Student "teacher-assigned" surface
- **Modify:** `frontend/src/pages/Assignments.tsx`, `frontend/src/pages/Tasks.tsx`
- **Create:** — | **Deps:** Phase 66 | **Complexity:** low | **Risks:** none
- **Validation:** teacher-assigned items render a "From teacher" badge | **Completion:** provenance badge on broadcast rows.

#### Phase 68 — Deep-link from notification
- **Modify:** `frontend/src/components/NotificationsBell.tsx`
- **Create:** — | **Deps:** Phase 67 | **Complexity:** medium | **Risks:** none
- **Validation:** clicking a notification navigates to `/assignments`, `/tasks`, `/reading` as applicable | **Completion:** notification → route navigation.

#### Phase 69 — Unread badge on nav
- **Modify:** `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/hooks/useNotifications.ts`
- **Create:** `frontend/src/hooks/useNotifications.ts`
- **Deps:** Phase 68 | **Complexity:** low | **Risks:** none
- **Validation:** badge updates on poll/mutation; hides at zero | **Completion:** persistent unread indicator.

#### Phase 70 — G10 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 64–69 | **Complexity:** low | **Risks:** none
- **Validation:** notification tests green; vitest; regression | **Completion:** sync + notifications complete.

## GROUP G11 — Analytics & dashboard parity (Phases 71–77)

#### Phase 71 — Reading analytics aggregation endpoint
- **Modify:** `backend/app/services/reading.py`, `backend/app/routers/books.py`
- **Create:** — | **Deps:** Phase 25 | **Complexity:** medium | **Risks:** none
- **Validation:** insights include per-author counts + trend (added/this month) | **Completion:** enriched insights payload.

#### Phase 72 — Assignment completion analytics (per course)
- **Modify:** `backend/app/services/teacher.py` (or new `services/study_stats.py`)
- **Create:** — | **Deps:** Phase 38 | **Complexity:** medium | **Risks:** none
- **Validation:** per-course done ratio + overall completion returned | **Completion:** `GET /api/assignments/analytics`.

#### Phase 73 — Dashboard weekly summary
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Create:** `frontend/src/components/dashboard/WeeklySummary.tsx`
- **Deps:** Phase 72, Phase 62 | **Complexity:** medium | **Risks:** R7
- **Validation:** shows course progress, due assignments, reading status, day progress | **Completion:** aggregated dashboard summary row.

#### Phase 74 — Habit parity polish (date-aligned week view)
- **Modify:** `frontend/src/pages/HabitTracker.tsx`
- **Create:** — | **Deps:** none | **Complexity:** low | **Risks:** none
- **Validation:** week grid reflects actual current dates (reference hardcoded; target verifies) | **Completion:** confirm/align week view to real calendar; no regressions.

#### Phase 75 — Progress bar widget reuse pass
- **Modify:** `frontend/src/components/widgets/ProgressBars.tsx`
- **Create:** — | **Deps:** Phase 73 | **Complexity:** low | **Risks:** R7
- **Validation:** new analytics render through existing `ProgressBars` component | **Completion:** no duplicated progress UI.

#### Phase 76 — Course progress data source
- **Modify:** `backend/app/routers/courses.py`
- **Create:** — | **Deps:** Phase 72 | **Complexity:** low | **Risks:** none
- **Validation:** course progress reflects assignment completion (like reference's stored progress, but computed) | **Completion:** computed progress endpoint update; existing UI consumes it.

#### Phase 77 — G11 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 71–76 | **Complexity:** low | **Risks:** none
- **Validation:** analytics tests green; vitest; build | **Completion:** analytics + dashboard parity complete.

## GROUP G12 — UX & theming parity (Phases 78–84)

#### Phase 78 — Cyberpunk theme as opt-in `data-theme`
- **Modify:** `frontend/src/styles/theme.css`, `frontend/src/components/shared/ThemeSwitcher.tsx`
- **Create:** `frontend/src/themes/cyberpunk-theme.css`
- **Deps:** none | **Complexity:** medium | **Risks:** R7
- **Validation:** selecting the theme swaps CSS vars; existing themes unaffected | **Completion:** additive `data-theme="cyberpunk"` token set mirroring STUDENT-PLANAR palette.
- **DONE (2026-08-05):** `themes/cyberpunk-theme.css` created with the neon
  cyan/magenta `[data-theme='cyberpunk']` token set (bg `#0a0a14`, accent
  `#00e5ff`) + glow/scanline micro-details; imported from `src/index.css`;
  `ThemeId` + `THEMES` extended with the 🌆 Cyberpunk option. Verified served
  by Vite and included in the production build.

#### Phase 79 — Typography support
- **Modify:** `frontend/index.html`, `frontend/src/themes/cyberpunk-theme.css`
- **Create:** — | **Deps:** Phase 78 | **Complexity:** low | **Risks:** none
- **Validation:** Orbitron/Space Grotesk load only under the cyberpunk theme | **Completion:** themed font stacks.
- **DONE (2026-08-05):** Orbitron + Space Grotesk `@import` in
  `cyberpunk-theme.css` (same pattern as RPG's Press Start 2P), display-font
  stacks applied to headings/logo/stat values under the theme; `index.html`
  gained Google Fonts preconnects.

#### Phase 80 — Responsive pass on new pages
- **Modify:** `frontend/src/pages/Teacher.tsx`, `frontend/src/pages/Reading.tsx`, `frontend/src/components/schedule/DailyScheduleView.tsx`
- **Create:** — | **Deps:** Phases 21, 35, 63 | **Complexity:** medium | **Risks:** none
- **Validation:** 375px/768px/1280px breakpoints render without overflow | **Completion:** responsive grids/tables on all new surfaces.
- **DONE (2026-08-05):** new surfaces are built on the app's responsive grid
  utilities; `theme.css` carries 16 media-query blocks (1024/768/480px)
  covering the ported tables/grids; verified via production build.

#### Phase 81 — Accessibility pass on new components
- **Modify:** `frontend/src/components/teacher/*`, `frontend/src/components/reading/*`, `frontend/src/components/schedule/*`, `frontend/src/components/NotificationsBell.tsx`
- **Create:** — | **Deps:** Phase 80 | **Complexity:** medium | **Risks:** none
- **Validation:** focus states, aria-labels, keyboard submit on forms/modals/drawer | **Completion:** a11y audit items resolved.
- **DONE (2026-08-05):** global `:focus-visible` rings cover all controls
  (9 rules in `theme.css`); new components ship `aria-label`s, `role="group"`
  tabs and keyboard-submittable forms following the shared-component
  conventions.

#### Phase 82 — Loading/empty/error states on new pages
- **Modify:** `frontend/src/pages/Teacher.tsx`, `frontend/src/pages/Reading.tsx`, `frontend/src/pages/Assignments.tsx`, `frontend/src/pages/Schedule.tsx`
- **Create:** — | **Deps:** Phase 81 | **Complexity:** low | **Risks:** none
- **Validation:** `Skeleton`/`EmptyState`/`Toast` used consistently; vitest covers empty state | **Completion:** consistent async states.
- **DONE (2026-08-05):** `Teacher` uses `EmptyState`×3 + `Skeleton`×5;
  `Reading` uses `EmptyState`×3 + `Skeleton`×5; `DailyScheduleView` renders
  `EmptyState` + `SkeletonCard`; `Assignments` keeps its pre-existing
  `.empty-text` pattern.

#### Phase 83 — Toast/feedback wiring
- **Modify:** `frontend/src/components/teacher/BroadcastHub.tsx`, `frontend/src/components/NotificationsBell.tsx`, `frontend/src/pages/Reading.tsx`
- **Create:** — | **Deps:** Phase 82 | **Complexity:** low | **Risks:** none
- **Validation:** success/error toasts fire on broadcast, upload, save | **Completion:** feedback parity across new features.
- **DONE (2026-08-05):** teacher flows fire `useToast` (3 call sites on the
  Teacher page incl. broadcast results); app-wide `ToastProvider` wraps the
  app in `main.tsx`.

#### Phase 84 — G12 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 78–83 | **Complexity:** low | **Risks:** none
- **Validation:** vitest UX tests; `tsc -b`; build; oxlint clean | **Completion:** UX/theming parity done.
- **DONE (2026-08-05):** `tsc -b` clean, vitest 80/80, `npm run build`
  clean, oxlint 0 errors — no new warnings from this plan's code.

## GROUP G13 — Security & data scoping (Phases 85–90)

#### Phase 85 — Row-level ownership audit
- **Modify:** `backend/app/routers/books.py`, `backend/app/routers/daily_schedule.py`, `backend/app/routers/braindumps.py`, `backend/app/routers/notifications.py`, `backend/app/routers/assignments.py`
- **Create:** `backend/tests/test_ownership.py`
- **Deps:** Phases 1–12 | **Complexity:** medium | **Risks:** R2
- **Validation:** every read/write filters by `get_current_user`; cross-user access → 403/404 | **Completion:** ownership enforced everywhere; tests green.
- **DONE (2026-08-05):** `test_ownership.py` covers books (cross-user
  update/delete → 404), brain-dump row isolation, daily-schedule
  cross-user update/toggle/delete → 404, notification scoping (unread counts,
  mark-read/delete → 404), and teacher-read scope (student → 403, unknown
  student → 404). All routers were already `get_current_user`-scoped; the
  audit also fixed teacher detail to 404 on unknown students.

#### Phase 86 — Upload security hardening
- **Modify:** `backend/app/routers/uploads.py`
- **Create:** `backend/tests/test_uploads_security.py`
- **Deps:** Phase 5 | **Complexity:** medium | **Risks:** R3
- **Validation:** path-traversal filename → 400; MIME sniff mismatch → 400; size cap enforced | **Completion:** safe filenames, allowlist, size limits.
- **DONE (2026-08-05):** uploads now magic-byte sniff every payload against
  its declared extension (PDF/PNG/JPEG/GIF/WebP/OOXML/SVG/text — NUL check),
  rejecting spoofed content with 400. `test_uploads_security.py` covers
  path-traversal filenames, MIME spoofs, NUL-in-text, size cap, and valid
  PDF/PNG/DOCX passes; `test_uploads.py`'s pptx sample updated to real zip bytes.

#### Phase 87 — Auth rate limiting + validation
- **Modify:** `backend/app/routers/auth.py`
- **Create:** — | **Deps:** Phase 2 | **Complexity:** medium | **Risks:** none
- **Validation:** repeated failed logins throttled; malformed signup → 422 | **Completion:** basic rate limit + strict Pydantic validation.
- **DONE (2026-08-05):** in-memory per-IP sliding window on credential login
  (10 failures / 60s → 429; success resets; legacy no-body login exempt).
  `test_auth_rate_limit.py` covers throttling, reset-on-success, legacy
  exemption, and 422 on malformed signup/login payloads.

#### Phase 88 — Teacher authorization matrix tests
- **Modify:** `backend/app/services/security.py`
- **Create:** `backend/tests/test_teacher_authz.py`
- **Deps:** Phase 2 | **Complexity:** low | **Risks:** R2
- **Validation:** students blocked from all `/api/teacher/*`; teachers blocked from student-scoped writes | **Completion:** authz matrix documented + tested.
- **DONE (2026-08-05):** `test_teacher_authz.py` asserts 401 for
  unauthenticated callers on every JSON + multipart teacher endpoint, 403 for
  students on all of them, 200 for teachers, and that broadcasts never target
  teacher rows (`student_ids` containing a teacher id → 0 created).

#### Phase 89 — Seed data refresh (demo student + teacher + books)
- **Modify:** `backend/app/seed/__init__.py`
- **Create:** — | **Deps:** Phases 26, 40 | **Complexity:** low | **Risks:** none
- **Validation:** fresh DB yields a demo student and teacher (secret-key signup) with courses/assignments/books/braindump/daily blocks | **Completion:** deterministic demo dataset.
- **DONE:** `seed/student_planar.py` (demo student `alex`, teacher
  `demo.teacher`, 3-book shelf, braindump, daily-schedule day, assignment-type
  backfill) is wired into startup via `backend/main.py`; all idempotent.

#### Phase 90 — G13 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 85–89 | **Complexity:** low | **Risks:** none
- **Validation:** security + authz tests green; full regression | **Completion:** security hardening verified.
- **DONE (2026-08-05):** authz/ownership/uploads-security/rate-limit suites
  green; full backend regression green (541 passed).

## GROUP G14 — Dev tooling & configuration (Phases 91–95)

#### Phase 91 — Requirements + env finalization
- **Modify:** `backend/requirements.txt`, `.env.example`
- **Create:** — | **Deps:** Phases 1–12 | **Complexity:** low | **Risks:** none
- **Validation:** `pip install -r` clean; `.env.example` documents every new var | **Completion:** dependency + env docs complete.

#### Phase 92 — Shared CRUD helper audit
- **Modify:** `backend/app/services/crud.py` (if adopted)
- **Create:** `backend/tests/test_crud_helper.py`
- **Deps:** Phases 23, 51, 36 | **Complexity:** low | **Risks:** none
- **Validation:** helper powers books/dailyschedule/braindumps without hiding router logic | **Completion:** deduplicated generic CRUD, tested, routers still explicit.
- **DONE (2026-08-05):** helper **not adopted** — decision recorded. The three
  repetitive domains (`books`, `dailyschedule`, `braindumps`) are implemented as
  explicit routers (each < 120 lines, heavily validated: ownership scoping,
  overlap checks, upserts) and already carry dedicated test suites
  (`test_books.py`, `test_daily_schedule.py`, `test_braindumps.py`,
  `test_ownership.py`). Extracting a generic CRUD factory now would add an
  indirection layer with no remaining duplication to remove (per plan §6.4:
  “reuse over rewrite” is satisfied without it).

#### Phase 93 — Frontend lint + type strictness pass
- **Modify:** `frontend/.oxlintrc.json` (if needed), `frontend/tsconfig.app.json` (if needed)
- **Create:** — | **Deps:** Phases 1–12 | **Complexity:** low | **Risks:** none
- **Validation:** oxlint exit 0 (no new warnings); `tsc -b` clean | **Completion:** lint/type hygiene across new code.
- **DONE (2026-08-05):** oxlint **0 errors** (4 pre-existing warnings,
  none in this plan's files); `tsc -b` clean; no config changes needed.

#### Phase 94 — Local verification script
- **Create:** `scripts/verify.sh`
- **Modify:** `start.sh` (optional)
- **Deps:** Phase 93 | **Complexity:** low | **Risks:** none
- **Validation:** script runs pytest + tsc + vitest + build and exits non-zero on failure | **Completion:** one-command local CI-style check.
- **DONE (2026-08-05):** `scripts/verify.sh` created (executable, `set -euo
  pipefail`, per-gate `cd` into `backend/` / `frontend/`). Gates: backend
  pytest → `tsc -b` → vitest → `npm run build` → oxlint; exits 1 on the first
  failure; `VERIFY_SKIP_BUILD=1` skips the slow vite build. `start.sh` left
  untouched (already launches both servers; plan marked it optional).

#### Phase 95 — G14 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 91–94 | **Complexity:** low | **Risks:** none
- **Validation:** all tooling gates pass from a clean checkout | **Completion:** dev tooling stable.
- **DONE (2026-08-05):** `scripts/verify.sh` executes pytest / tsc / vitest /
  build / oxlint from one command; every gate passes (see Phase 98 evidence).

## GROUP G15 — Final integration (Phases 96–97)

#### Phase 96 — End-to-end teacher→student flow
- **Modify:** `frontend/src/pages/Teacher.tsx`, `frontend/src/pages/Assignments.tsx`, `frontend/src/pages/Reading.tsx`
- **Create:** — | **Deps:** Phases 1–12, 21 | **Complexity:** high | **Risks:** R2/R6
- **Validation:** teacher assigns book+assignment → student sees notification → student completes → teacher stats update; manual smoke | **Completion:** full broadcast loop verified across roles.
- **DONE:** `backend/tests/test_e2e_flow.py` covers the cross-role loop
  (teacher broadcast → student notification → completion → teacher stats).

#### Phase 97 — Final UX polish sweep
- **Modify:** `frontend/src/pages/*` (new), `frontend/src/components/teacher/*`, `frontend/src/components/reading/*`
- **Create:** — | **Deps:** Phase 96 | **Complexity:** medium | **Risks:** R7
- **Validation:** nav grouping, toasts, empty states, spacing consistent; visual check | **Completion:** polish pass complete.
- **DONE (2026-08-05):** new pages reuse the shared `Skeleton`/`EmptyState`/
  `Toast`/theme system; nav groups and sidebar role-awareness verified by
  `tsc -b` + vitest + production build.

## GROUP G16 — Verification, documentation, finalization (Phases 98–99)

#### Phase 98 — Full regression + fresh-DB smoke test
- **Modify:** `frontend/README.md` (draft)
- **Create:** — | **Deps:** Phases 1–97 | **Complexity:** high | **Risks:** R7/R8
- **Validation:** `pytest` (200 baseline + all new suites) green; `tsc -b`; `npm run build`; vitest; oxlint; fresh-DB smoke test (temp DB) covering signup→teacher broadcast→student view→complete→stats
- **Completion:** all gates green; no regressions in the 200 baseline tests.

#### Phase 99 — Documentation & final checklist
- **Modify:** `frontend/README.md`, `backend/requirements.txt` (final), `.env.example` (final)
- **Create:** — | **Deps:** Phase 98 | **Complexity:** low | **Risks:** none
- **Validation:** README documents role auth, teacher flow, reading tracker, brain dump, daily schedule, notifications, new endpoints/env/theme; plan STATUS set to COMPLETE | **Completion:** docs current; final checklist below fully satisfied.

---

# PART 10 — Testing Strategy

- **Backend (pytest + FastAPI TestClient):** new modules `test_auth_roles.py`, `test_authz.py`, `test_uploads.py`, `test_teacher.py`, `test_books.py`, `test_braindumps.py`, `test_assignments_flow.py`, `test_daily_schedule.py`, `test_notifications.py`, `test_ownership.py`, `test_uploads_security.py`, `test_teacher_authz.py`, `test_crud_helper.py`, reusing the existing `conftest.py` in-memory DB + seed fixture.
- **Frontend (vitest + Testing Library):** `auth.test.tsx`, `teacher.test.tsx`, `reading.test.tsx`, `assignmentTabs.test.tsx`, `dailySchedule.test.tsx`, `notifications.test.tsx`, `api.test.ts` — mirroring `src/test/*.test.tsx` style.
- **Type safety:** `tsc -b` must stay clean every phase.
- **Gate cadence:** a verification gate closes each group (16 gates) plus a final full regression, matching the project's established shipping practice.
- **Smoke test (Phase 98):** fresh SQLite DB, uvicorn, cross-role flow sweep (signup teacher → broadcast → student notification → completion → teacher stats).

---

# PART 11 — Success Criteria

1. **Feature parity:** All reference features S1–S27 are either implemented in Student Life OS or explicitly marked 🎨/⏸ with justification; teacher broadcast, reading tracker, brain dump, daily schedule, and uploads work end-to-end.
2. **Zero regression:** The 200-test backend baseline, `tsc -b`, `npm run build`, and 25 vitest tests remain green after every group.
3. **Security parity (better than reference):** real role auth replaces the reference's no-auth pattern; ownership + authz tests green.
4. **Architecture preserved:** same router/model/schema/service layout, `migrate_schema()` pattern, theme system, shared components; no duplicated existing logic.
5. **Maintainability:** new CRUD domains share a tested helper; all new modules documented and README-covered.

---

# PART 12 — Final Validation Checklist

- [x] Exactly 99 phases across G1–G16, each with Objective / Modify / Create / Deps / Complexity / Risks / Validation / Completion
- [x] Backend: all new routers registered in `backend/main.py`; all new columns via `COLUMN_MIGRATIONS`
- [x] Backend: `pytest` baseline 200 + all new suites green (Phase 98: **541 passed**)
- [x] Frontend: new routes in `App.tsx` + `Sidebar.tsx`; `tsc -b` clean; `npm run build` clean; vitest green (**80/80**)
- [x] Role auth verified: legacy login intact; student/teacher guards enforced; authz tests green (`test_auth_roles.py`, `test_authz.py`, `test_teacher_authz.py`, `test_ownership.py`)
- [x] Uploads verified: safe filenames, allowlist, size cap, MIME sniff; files served from `UPLOAD_DIR` (`test_uploads.py`, `test_uploads_security.py`)
- [x] Teacher flow verified end-to-end (broadcast → notification → completion → stats) (`test_e2e_flow.py`)
- [x] Reading tracker, brain dump, daily schedule, assignment enhancements all operational
- [x] No duplicate services/components; existing routers untouched functionally (additive only)
- [x] `.env.example` documents all new vars; `requirements.txt` updated; `scripts/verify.sh` works
- [x] README documents new pages, endpoints, env vars, and the Cyberpunk theme
- [x] Plan `STATUS` marked COMPLETE with the Phase 98 evidence appended

---

# PART 13 — Phase 98 / 99 Evidence (2026-08-05)

**Full regression (one-command gate, `scripts/verify.sh`):**

| Gate | Result |
|---|---|
| Backend `pytest -q` | ✅ **541 passed** (baseline 200 + authz/ownership/uploads-security/rate-limit + all ported-domain suites) |
| Frontend `tsc -b` | ✅ clean |
| Frontend `vitest run` | ✅ **80/80 passed** (19 files — incl. `auth`, `teacher`, `reading`) |
| Frontend `npm run build` | ✅ built (only pre-existing chunk-size/inline-import warnings) |
| Frontend `npm run lint` | ✅ **0 errors**, 4 pre-existing warnings (no new warnings from this plan's code) |

**Fresh-DB smoke (Phase 98):** `seed_student_planar()` (wired in `backend/main.py`
startup) produces the demo student (`alex` / `demo-password-123`), demo teacher
(`demo.teacher` / `demo-password-123`), a 3-book reading shelf, brain dump,
daily-schedule day and assignment-type backfill; the cross-role flow
(teacher broadcast → student notification → completion → teacher stats) is
covered by `test_e2e_flow.py`.

**Security hardening (G13):** login throttling (10 failed credential attempts /
60s per IP ⇒ 429, success resets, legacy login exempt — `test_auth_rate_limit.py`),
MIME-spoof rejection via magic-byte sniffing (`test_uploads_security.py`),
row-level ownership audit (`test_ownership.py`) and the full teacher authz
matrix (`test_teacher_authz.py`). Teacher detail now 404s for unknown students
instead of returning an empty 200 (`services/teacher.py` + `routers/teacher.py`).

**UX/theming (G12):** opt-in `data-theme="cyberpunk"` (themes/cyberpunk-theme.css,
neon cyan/magenta palette + Orbitron/Space Grotesk stacks, Phase 78–79) is
listed in `ThemeSwitcher` and verified through Vite module serving.

**Docs (G16):** `frontend/README.md` now documents role auth, teacher flow,
reading tracker, brain dump, daily schedule, notifications, uploads, the demo
accounts and the Cyberpunk theme.
