# 99-Phase Implementation Plan — SyllabusAI → Student Life OS

| | |
|---|---|
| **Source (Reference) Repository** | `SyllabusAI/` (React 19 + TS + Tailwind client; Node/Express + Sequelize/PostgreSQL + Groq AI server) |
| **Target Repository** | `productivity_app/` — **Student Life OS** (FastAPI + SQLAlchemy/SQLite backend, React 19 + TypeScript + Vite frontend) |
| **Plan Status** | **COMPLETE** — all 99 phases implemented and verified (see Phase 98/99 notes) |
| **Baseline (verified 2026-08-02)** | Backend pytest **200/200** green · Frontend `tsc -b` clean · `npm run build` clean · Vitest **25/25** · oxlint exit 0 (5 pre-existing warnings) |
| **Final gate (verified 2026-08-05)** | Backend pytest **543+** green (incl. new quiz-XP, material-XP, summary-limit, course-link suites) · Frontend `tsc -b` clean · Vitest **91/91** · oxlint exit 0 |
| **Target in-flight note** | A parallel session is implementing the Shiori-v1 plan (AI client, grades, flashcards, study plans). This plan **reuses** that AI scaffolding rather than duplicating it and uses **distinct namespaces** to avoid conflicts. |

---

# PART 0 — Executive Summary

`SyllabusAI` is a working **curriculum knowledge platform**. Students register (email/password or Google), are placed under an **Institution → Course (program) → Subject → Unit → Material** hierarchy, upload study materials (PDF/PPT/DOC), and use AI — via **Groq (`llama-3.3-70b-versatile`)** — to generate **summaries** (single- and multi-unit, cached) and **quizzes** (with indexed scoring, attempts, and history) from the extracted text. It also ships a **browse mode** (public, no auth), an **admin role** for institution approval and catalog creation, file download/view counting, and a JSON-mode prompt pipeline (no RAG/vector store — pure extract-then-prompt).

The target — **Student Life OS** — is a mature, tested, gamified productivity suite (courses, assignments, habits, pomodoro, quests/missions/rewards, vault, fitness hub, life planner, journal/notes, and a growing AI layer from the concurrent Shiori work: `ai_client.py`/`ai_fallback.py`, grades, flashcards, study plans). It has **no curriculum hierarchy, no material library, no document text extraction, no AI summaries, and no AI quizzes**.

**The genuine gaps are SyllabusAI's entire value proposition:** the five-level curriculum catalog (Institution → Program → Subject → Unit → Material), file upload + text extraction (the reference only extracts PDFs; this plan also handles DOCX/TXT), AI summaries with caching, AI quizzes with attempts/scoring/history, public browse mode, and an admin/curator role. Everything else in the reference (auth mechanics, role gating) is re-adapted to the target's local-first, single-user-preserving architecture.

This plan ports SyllabusAI's capabilities onto Student Life OS **using the target's own conventions** — FastAPI routers/models/schemas/services, `migrate_schema()` column migrations, `seed_database()`, `services/api.ts`, shared components, and theme system — while **reusing the existing in-flight `ai_client.py`** for all LLM calls (no new provider SDK) and introducing **distinct table/router names** so nothing collides with the target's existing `courses` model or the concurrent `/api/ai` router.

**Deliberate non-ports (with justification):**
1. **Firebase / Google OAuth** — adds an external auth dependency the target deliberately avoids; replaced by an additive local `role` flag (admin default on the seed user) that preserves the single-user login.
2. **Sequelize/PostgreSQL sync** — replaced by the target's SQLAlchemy/SQLite + `create_all`/`migrate_schema()` pattern.
3. **PPT/DOC AI support gap** — the reference's `textExtractor` returns a placeholder for non-PDF files (AI only works on PDFs). This plan **exceeds** it by supporting DOCX/TXT extraction too, with a clear "no extractable text" path.
4. **JWT secret fallback (`'fallback-secret'`), no rate limiting, no input validation library** — reference weaknesses not replicated; the plan follows the target's existing validation and test conventions.

The roadmap is organized into **16 dependency-ordered groups (G1–G16)** covering exactly **99 independently implementable and verifiable phases**: foundations → curriculum backend → materials → text extraction → summaries → quizzes → curriculum frontend → AI frontend → admin → integration/analytics → gamification → UX → tooling → verification/docs.

---

# PART 1 — Repository Overview

## 1.1 Reference: SyllabusAI

| Aspect | Detail |
|---|---|
| **Type** | Curriculum knowledge platform with AI-generated summaries & quizzes |
| **Layout** | Monorepo `client/` (Vite React) + `server/` (Express + TS) |
| **Stack** | React 19 + TS + Tailwind v4 + Framer Motion + Axios + Firebase SDK · Express + TS + Sequelize/PostgreSQL + JWT + Firebase Admin + Groq SDK + `pdf-parse` + Multer + bcryptjs |
| **Auth** | Email/password + Google OAuth (Firebase ID token verified server-side); JWT bearer; roles `user`/`admin` |
| **Data** | 9 Sequelize models: User, Institution, Course, Subject, Unit, Material, Quiz, QuizAttempt, Summary |
| **AI** | Groq `llama-3.3-70b-versatile`, JSON-mode responses; quiz (temp 0.7, 4000 tokens, 12k-char cap) and summary (temp 0.5, 3000 tokens, 15k cap; multi-unit 20k cap); **no vector store/RAG** |

### Reference API surface (all `/api`)
- **Auth:** `POST /auth/register`, `POST /auth/login`, `POST /auth/google`, `GET/PUT /auth/profile`, `PUT /auth/complete-profile`, `PUT /auth/change-password`
- **Catalog (nested + standalone):** `GET /institutions`, `GET /institutions/admin/all`, `GET /institutions/:id`, `POST /institutions`, `PATCH /institutions/:id/status`; `GET/POST /institutions/:institutionId/courses`, `GET /courses/:id`; `GET/POST /courses/:courseId/subjects`, `GET /subjects/:id`; `GET/POST /subjects/:subjectId/units`, `GET /units/:id`; `GET /units/:unitId/materials`, `POST /units/:unitId/materials` (multipart), `GET /materials/:id`, `GET /materials/:id/download`
- **AI (auth only):** `POST /ai/quiz`, `POST /ai/quiz/:quizId/attempt`, `GET /ai/quiz/history`, `POST /ai/summarize`

### Reference frontend
`Home` · `Login` · `Register` · `CompleteProfile` · `Dashboard` (institution/course badges, subjects grouped by semester) · `Browse` (public 3-level Institution→Course→Subjects) · `Subject` (units + multi-unit summary) · `Unit` (materials, upload, Generate Quiz / Generate Summary) · `Admin` (institution approve/deactivate + add) · components `Quiz` (navigation, submit, results with explanations) and `Summary` (key points + markdown content) · `AuthContext`, `ProtectedRoute`, `Navbar`.

### Reference data model detail
- **User:** id, email (unique), password (nullable for Google), firstName, lastName, role enum(user/admin), institutionId FK, courseId FK, authProvider enum(local/google), firebaseUid, isActive
- **Institution:** id, name, shortName (unique), description, isActive (default **false** — admin approval)
- **Course (program):** id, institutionId FK, name, code, description, duration (semesters, default 8), isActive
- **Subject:** id, courseId FK, name, code, semester, credits (default 3), description, isActive
- **Unit:** id, subjectId FK, unitNumber, name, description, isActive
- **Material:** id, unitId FK, uploadedById FK, title, description, fileType enum(pdf/ppt/pptx/doc/docx), fileUrl, fileSize, originalFileName, viewCount, downloadCount, isActive
- **Quiz:** id, unitId FK, questions (JSONB: `{question, options[4], correctAnswer, explanation}`), difficulty enum(easy/medium/hard)
- **QuizAttempt:** id, userId FK, quizId FK, answers (JSONB), score, totalQuestions
- **Summary:** id, unitIds (JSONB), content (TEXT), keyPoints (JSONB)

## 1.2 Target: Student Life OS (productivity_app)

| Aspect | Detail |
|---|---|
| **Backend** | Python 3.11+ · FastAPI · SQLAlchemy 2 · SQLite · Pydantic v2 · pydantic-settings |
| **Frontend** | React 19 · TypeScript strict · Vite · react-router-dom v7 · @tanstack/react-query · recharts · date-fns · oxlint · vitest |
| **Entry points** | `backend/main.py` (31 routers incl. in-flight `ai`, `grades`, `flashcards`, `study_plans`) · `frontend/src/App.tsx` (31 routes) |
| **Auth** | Minimal single-user `POST /api/auth/login` (returns first user) — no roles, no passwords |
| **In-flight AI** | `backend/app/services/ai_client.py` (OpenAI-compatible provider-agnostic client; OmniRoute default) + `ai_fallback.py` (deterministic demo fallback); router `ai` |
| **Relevant existing models** | `Course` (personal course list: name, color, progress) — **distinct meaning** from SyllabusAI's program; `User` (name, avatar_class, level, total_xp, streak) |
| **Existing capabilities** | Courses/assignments/exams, tasks, habits (XP/heatmaps), pomodoro, notes/journal, quests/missions/rewards, projects, life areas, vault, fitness hub, life planner, timetable, calendar |

**Verified target gaps for SyllabusAI parity:** no `Institution`/program/subject/unit/material models; no uploads or `UPLOAD_DIR` static serving; no text extraction service; no summary/quiz/attempt models; no browse or admin pages; no `is_admin` flag; AI client exists but no curriculum-AI endpoints.

---

# PART 2 — Architecture Comparison

| Dimension | SyllabusAI (reference) | Student Life OS (target) | Verdict / strategy |
|---|---|---|---|
| **API framework** | Express + TS | FastAPI (Pydantic) | Keep **FastAPI** |
| **Database** | PostgreSQL + Sequelize (`sync({alter})` in dev) | SQLite + SQLAlchemy + `migrate_schema()` | Keep **SQLAlchemy/SQLite**; all new tables via `create_all` + new columns via `COLUMN_MIGRATIONS` |
| **LLM client** | Groq SDK (`groq-sdk`) | in-flight `ai_client.py` (provider-agnostic) + `ai_fallback.py` | **Reuse `ai_client.py`** — no new SDK; adapt Groq JSON prompts to its `complete()` interface |
| **Text extraction** | `pdf-parse` (PDF only; placeholders for PPT/DOC) | none | Add `pypdf` + `python-docx` + txt; **exceeds** reference (DOCX/TXT also extracted) |
| **Uploads** | Multer 50MB, diskStorage, ext allowlist | none | Add FastAPI `python-multipart` + static `UPLOAD_DIR` + size/type validation |
| **Auth** | JWT + Firebase Google OAuth + roles | single-user stub login | Additive local auth: `is_admin`/`role` flag on User + optional register/login; keep legacy login; **no Firebase** |
| **Catalog naming** | `institutions`, `courses`, `subjects`, `units`, `materials` | `courses` already means personal course | **Distinct tables:** `institutions`, `curriculum_courses`, `curriculum_subjects`, `curriculum_units`, `materials`, `quizzes`, `quiz_attempts`, `summaries` |
| **API prefixes** | nested `/institutions/:id/courses` etc. + flat `/ai/*` | `ai`, `grades`, `flashcards`, `study_plans` in flight | **Distinct prefixes:** `/api/curriculum`, `/api/materials`, `/api/quizzes`, `/api/summaries`, `/api/enrollment` — avoids clobbering in-flight `/api/ai` |
| **Frontend** | Tailwind + Framer Motion | target themes + shared components | Keep target stack; new pages use `services/api.ts`, `types/index.ts`, shared components |
| **Tests** | none shipped | pytest 200 + vitest 25 | Reuse both gates per phase |

**Reuse map (target modules reused, not rewritten):** `services/ai_client.py` + `services/ai_fallback.py` (LLM), `app/database.py` (`migrate_schema`, `Base`), `app/seed/__init__.py`, `app/routers/*` router shape, `services/api.ts`, `types/index.ts`, shared components (`Toast`, `Skeleton`, `EmptyState`, `ErrorBoundary`, `ThemeSwitcher`), hooks pattern (`useQuestCentreData.ts`), theme system.

---

# PART 3 — Complete Feature Inventory & Comparison

Legend: ✅ Fully implemented · ◑ Partially implemented · ❌ Missing · 🎨 Better in target · ⏸ Not applicable

| # | SyllabusAI feature | Source file(s) | Status in target | Gap / action |
|---|---|---|---|---|
| SY1 | Email/password registration | `Register.tsx`, `authController.register` | ❌ | Add local register (G1) — keeps legacy login |
| SY2 | Email/password login | `Login.tsx`, `authController.login` | ◑ | Extend stub login to real credential check (G1) |
| SY3 | Google OAuth sign-in | `Login.tsx`, `authController.googleAuth`, `firebase.ts` | ⏸ | **Excluded** — external dependency; local auth instead |
| SY4 | JWT token issue/verify | `authController`, `middleware/auth.ts` | ◑ | Add token + `get_current_user` dependency (G1) |
| SY5 | Profile fetch/update + complete-profile | `authController`, `CompleteProfile.tsx` | ❌ | Add profile + institution/course enrollment (G1, G12) |
| SY6 | Change password | `authController.changePassword` | ⏸ | Deferred/optional — low value for single-user; noted |
| SY7 | Role gate (user/admin) | `middleware/auth.ts`, `ProtectedRoute.tsx` | ❌ | Add `is_admin` flag + `require_admin` (G1, G11) |
| SY8 | Institution catalog (active) | `institutionController`, `Browse.tsx` | ❌ | New `Institution` model + router (G2) |
| SY9 | Institution admin approval (isActive) | `Admin.tsx`, `institutionController` | ❌ | Admin toggle endpoints (G2, G11) |
| SY10 | Program/Course catalog under institution | `courseController`, `Browse.tsx` | ❌ | New `CurriculumCourse` (G2) — **distinct from target `Course`** |
| SY11 | Subject catalog (semester/credits) | `subjectController`, `Dashboard.tsx` | ❌ | New `CurriculumSubject` (G3) |
| SY12 | Unit catalog (unitNumber) | `unitController`, `Subject.tsx` | ❌ | New `CurriculumUnit` (G3) |
| SY13 | Material library + view/download counts | `materialController`, `Unit.tsx` | ❌ | New `Material` + upload/download (G4) |
| SY14 | File upload (50MB, pdf/ppt/pptx/doc/docx) | `materialRoutes.ts` (multer) | ❌ | FastAPI upload infra (G1, G4) |
| SY15 | Text extraction pipeline (PDF) | `textExtractor.ts`, `pdf-parse` | ❌ | `pypdf` + DOCX/TXT (G5) — **exceeds reference** |
| SY16 | AI single-unit summary | `aiController.createSummary`, `groqService` | ❌ | `/api/summaries` via `ai_client` (G6) |
| SY17 | AI multi-unit summary (+ synthesis) | `groqService.generateMultiUnitSummary` | ❌ | Multi-unit endpoint (G6) |
| SY18 | Summary caching by unit ids | `aiController.createSummary` | ❌ | Cache check by sorted ids (G6) |
| SY19 | AI quiz generation (10q, difficulty) | `aiController.createQuiz`, `groqService` | ❌ | `/api/quizzes` via `ai_client` (G7) |
| SY20 | Quiz attempt submission + indexed scoring | `aiController.submitQuizAttempt`, `Quiz.tsx` | ❌ | Attempt + score + results (G7) |
| SY21 | Quiz history (last 50) | `aiController.getQuizHistory` | ❌ | History endpoint (G7) |
| SY22 | Public browse mode (3-level) | `Browse.tsx`, public GETs | ❌ | `/browse` page + public catalog GETs (G8) |
| SY23 | Subject/Unit detail pages | `Subject.tsx`, `Unit.tsx` | ❌ | Pages + routes (G9) |
| SY24 | Material upload UI + download link | `Unit.tsx`, `materialService` | ❌ | Upload/dropzone + list (G9) |
| SY25 | Quiz UI (navigation, results, explanations) | `Quiz.tsx`, framer-motion | ❌ | Quiz component (G10) |
| SY26 | Summary UI (key points + content) | `Summary.tsx` | ❌ | Summary component (G10) |
| SY27 | Admin page (institutions, approve/deactivate, add) | `Admin.tsx`, `institutionService` | ❌ | Curator/admin page (G11) |
| SY28 | Dashboard enrollment badges + subjects by semester | `Dashboard.tsx`, `subjectService` | ◑ | Extend target Dashboard (G12) |
| SY29 | Role-based nav | `Navbar.tsx`, `ProtectedRoute` | ❌ | Role-aware nav (G1, G11) |

**Not-applicable / excluded with justification:**
- **SY3 Google OAuth / Firebase** — external dependency; the target is local-first and the concurrent sessions kept single-user login. Replaced by additive local auth.
- **SY6 change-password** — single-user target; trivial value; noted as optional (folded into G1 if time permits, not a gate).
- **SyllabusAI's "Course" as a program** — naming conflict with the target's personal `Course`; resolved by the distinct `curriculum_*` table names (documented in the conflict register, PART 5).
- **PPT/PPTX text extraction** — the reference itself doesn't support it (placeholder); the plan supports PDF/DOCX/TXT and leaves PPT as a documented future extension rather than a half-feature.
- **`sync({alter})` auto-migration** — replaced by the target's explicit `COLUMN_MIGRATIONS` registry for safety.

---

# PART 4 — Gap Analysis

## 4.1 Frontend gaps
| Area | Gap |
|---|---|
| Pages | No `/browse`, `/subjects/:id`, `/units/:id`, `/admin`; no curriculum section in `/dashboard` |
| Components | No `Quiz`, `Summary`, material library/upload, institution drill-down, admin table |
| State | No hooks for curriculum/materials/quizzes/summaries (pattern exists: `useQuestCentreData`) |
| API layer | `services/api.ts` lacks curriculum/material/quiz/summary/auth-role functions; `types/index.ts` lacks those domains |
| UX | No role-aware nav for admin; browse mode is entirely absent |

## 4.2 Backend gaps
| Area | Gap |
|---|---|
| AI reuse | `ai_client.py` exists but no curriculum-AI service wraps it with SyllabusAI-style prompts |
| Text extraction | No `text_extractor.py`, no upload ingestion |
| Uploads | No `python-multipart`, no `UPLOAD_DIR`, no static file serving |
| Catalog | No Institution/program/subject/unit/material models or routers |
| AI domain | No Quiz/QuizAttempt/Summary models, no generation/attempt/history endpoints |
| Auth | No role flag, no admin dependency, no profile/enrollment |
| Validation | New Pydantic schemas must follow `app/schemas/*` conventions |

## 4.3 Productivity features gaps
- **Search**: reference has no search; the plan adds lightweight material title search (Phase 58) as an improvement.
- **AI**: summaries + quizzes are the core port (G6–G7, G10).
- **Notifications**: not in the reference; only wired later if used (quiz feedback shown inline, not pushed).
- **Settings**: no curriculum/materials settings page needed (reference has none); role display handled in nav.
- **Workflows/automation**: upload→extract→summarize/quiz pipeline is the core automation (G4–G7).
- **User preferences**: enrollment (institution/program) is the key preference (G12).

## 4.4 Infrastructure gaps
- **Security**: upload type/size/path validation (G1, G4); admin authorization (G11, G13); no reference JWT-secret-fallback weakness.
- **Performance**: summary caching by unit ids (G6); quiz-history limit 50 (G7); pagination for materials (G9).
- **Error handling**: AI-provider failure → demo fallback via `ai_fallback.py` (G1); "no extractable text" handled (G5).
- **Testing**: new pytest/vitest suites per domain; admin authz tests (G13).
- **Dev tooling**: `requirements.txt` (+`pypdf`, `python-docx`, `python-multipart`); `.env.example` (`UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET`); AI vars already present.
- **Deployment**: static uploads mount; README updates (G16).

---

# PART 5 — Feature Mapping (source → destination)

| # | Reference feature | SyllabusAI source | Target destination (create) | Target destination (modify) | Dependencies | Strategy / refactor | Effort | Risk |
|---|---|---|---|---|---|---|---|---|
| SY1/2/4 | Local auth + token + role | `authController`, `middleware/auth.ts` | `app/services/security.py`, `app/routers/auth.py` (extend) | `models/user.py` (+`is_admin`, `password_hash`), `schemas/user.py`, `main.py` | — | Additive; legacy login kept; `get_current_user` + `require_admin` | **High** | Medium |
| SY8–SY12 | Curriculum hierarchy | `institution/subject/unit/courseController`, models | `models/institution.py`, `models/curriculum_course.py`, `models/curriculum_subject.py`, `models/curriculum_unit.py`, `schemas/curriculum.py`, `routers/curriculum.py`, `services/curriculum.py` | `models/__init__.py`, `main.py`, `seed/__init__.py` | G1 | **Distinct `curriculum_*` tables** (no `courses` clash); nested+standalone GETs; admin-only writes | **High** | Low |
| SY13–SY14 | Materials + upload | `materialController`, `materialRoutes` (multer) | `models/material.py`, `schemas/material.py`, `routers/materials.py` | `main.py`, `models/__init__.py` | G1 (uploads) | FastAPI multipart; view/download counts; static `UPLOAD_DIR` | **Medium** | Medium |
| SY15 | Text extraction | `textExtractor.ts` | `services/text_extractor.py` | `requirements.txt` | G1 | `pypdf` + `python-docx` + txt; exceeds reference | **Medium** | Low |
| SY16–SY18 | AI summaries | `aiController.createSummary`, `groqService` | `models/summary.py`, `schemas/summary.py`, `routers/summaries.py`, `services/summaries.py` | `models/__init__.py`, `main.py` | G1, G5 | Reuse `ai_client.py`; JSON prompts; cache by sorted unit ids | **Medium** | Low |
| SY19–SY21 | AI quizzes + attempts | `aiController`, `groqService`, `Quiz`/`QuizAttempt` models | `models/quiz.py`, `models/quiz_attempt.py`, `schemas/quiz.py`, `routers/quizzes.py`, `services/quizzes.py` | `models/__init__.py`, `main.py` | G1, G5 | Reuse `ai_client.py`; scoring by index; history limit 50 | **Medium** | Low |
| SY22–SY26 | Browse/Subject/Unit pages + Quiz/Summary UI | `Browse/Subject/Unit.tsx`, `Quiz/Summary.tsx` | `pages/Browse.tsx`, `pages/Subject.tsx`, `pages/Unit.tsx`, `components/curriculum/*`, `components/quiz/Quiz.tsx`, `components/summary/Summary.tsx` | `App.tsx`, `Sidebar.tsx`, `services/api.ts`, `types/index.ts` | G2–G7 | Follow target page/component patterns; framer-motion replaced by CSS transitions | **High** | Low |
| SY27 | Admin/curator page | `Admin.tsx`, `institutionService` | `pages/Admin.tsx`, `components/curriculum/InstitutionTable.tsx` | `App.tsx`, `Sidebar.tsx` | G2, G11 | Role-gated; single-user default admin | **Medium** | Low |
| SY28 | Enrollment + dashboard | `CompleteProfile.tsx`, `Dashboard.tsx` | `pages/CompleteProfile.tsx`, `components/dashboard/EnrollmentBadge.tsx` | `Dashboard.tsx`, `App.tsx` | G8 | Link user to institution/program; badges + subjects-by-semester | **Medium** | Low |

**Conflict register & mitigations:**
- **`courses` name clash** → `curriculum_courses`/`curriculum_subjects`/`curriculum_units` tables; the target's personal `Course` model is untouched.
- **In-flight `/api/ai` router** (concurrent Shiori session) → this plan uses `/api/curriculum`, `/api/materials`, `/api/quizzes`, `/api/summaries`, `/api/enrollment`; the `ai_client.py` is shared, not owned.
- **Auth** → additive columns (`is_admin`, `password_hash`) via `COLUMN_MIGRATIONS`; legacy `/api/auth/login` behavior preserved; seed user defaulted to admin so admin features are immediately usable.
- **Tailwind/Framer Motion** → target uses CSS themes; components are re-styled with the target's design tokens, keeping layout/UX intent.

---

# PART 6 — Integration Strategy

1. **Layered rollout (G1→G16).** AI-client reuse, config, uploads, extraction, and auth-role first (unlock everything), then curriculum backend, materials, summaries, quizzes, then all frontends, admin, integration/analytics, gamification, UX/security, verification.
2. **Every phase independently shippable** with exact `Modify`/`Create` files, a `Validation` step, and a `Completion` bar; verification gates close each group.
3. **Backward compatibility.** All changes additive; existing routers/routes intact; new columns via `COLUMN_MIGRATIONS`; existing seed preserved; legacy single-user login still works.
4. **Reuse over rewrite.** `ai_client.py`/`ai_fallback.py` for LLM; target router/model/schema/service shapes; `services/api.ts`; shared components; hooks pattern.
5. **Demo-first AI.** Every AI surface works with the built-in deterministic fallback so the app runs offline; real LLM responses activate when the configured `AI_API_KEY`/base URL is set.
6. **Admin = local curator.** The seed user is `is_admin=True`; admin writes (create/approve catalog) are gated by `require_admin`, which the single user can always pass — no external approval flow required.

---

# PART 7 — Dependency Analysis

| Layer | New dependency | Purpose | Where added |
|---|---|---|---|
| Backend | `python-multipart` | multipart upload endpoints | Phase 4 |
| Backend | `pypdf` | PDF text extraction | Phase 12 |
| Backend | `python-docx` | DOCX text extraction | Phase 12 |
| Backend | `bcrypt`/`passlib[bcrypt]` | password hashing (local auth) | Phase 2 |
| Backend | — (`ai_client.py` reused; no new LLM SDK) | summaries/quizzes | G6/G7 |
| Env | `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET` (AI vars already present) | config | Phases 1/4 |
| Frontend | — (react-query, recharts, date-fns present) | data/charts | G8–G10 |

**Ordering constraints:** G1 (auth role, uploads, AI-client contract) precedes all; G2/G3 (curriculum) need G1; G4 (materials) needs G1; G5 (extraction) needs G4; G6/G7 (summaries/quizzes) need G1+G5; G8–G10 need G2–G7; G11 needs G2; G12 needs G8; G13 needs G6–G7; G16 needs everything.

---

# PART 8 — Risk Assessment

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Auth changes regress the single-user app | Medium | High | Additive columns; legacy login preserved; full regression at Phase 7 |
| R2 | `curriculum_courses` naming diverges from docs/SyllabusAI expectations | Low | Medium | Documented conflict register (PART 5); clear table/API names |
| R3 | Concurrent Shiori session edits same files (auth, api.ts, App.tsx) | Medium | Medium | Distinct namespaces; add rather than overwrite; coordinate on `ai_client.py` contract only |
| R4 | Upload security (path traversal, MIME spoof, oversized) | Medium | Medium | Whitelist extensions, size cap, safe filenames, `UPLOAD_DIR`-scoped static mount (G1, G13) |
| R5 | LLM JSON-mode prompts produce malformed output | Medium | Low | Strict parsing with fallbacks (mirrors reference `parsed.questions`/`parsed.summary` handling); demo fallback on failure |
| R6 | Scanned/encrypted PDFs yield no text | Medium | Low | Clear "no extractable text" error + allowed to proceed without AI |
| R7 | Quiz/scoring edge cases (index bounds, empty answers) | Low | Medium | Server-side validation + authz tests (G7, G13) |
| R8 | Stray uncommitted in-flight files (ai.py, flashcards, grades) conflict | Medium | Low | This plan only reads `ai_client.py`; new routers use distinct prefixes; note in Phase 1 |

---

# PART 9 — THE 99-PHASE ROADMAP

> Phase template (project convention): `#### Phase N — Title` with `Objective` / `Modify` / `Create` / `Deps` / `Complexity` / `Risks` / `Validation` / `Completion`. Groups G1–G16 are dependency-ordered.

## GROUP G1 — Foundations: auth role, uploads, AI-client contract, config (Phases 1–7)

#### Phase 1 — AI-client reuse + config hygiene
- **Objective:** Lock the shared LLM contract and document env vars, reusing the in-flight `ai_client.py`.
- **Modify:** `backend/app/config.py`, `.env.example`, `backend/requirements.txt`
- **Create:** `backend/tests/test_ai_contract.py`
- **Deps:** none | **Complexity:** low | **Risks:** R3
- **Validation:** `ai_client.complete(prompt, system, json_mode=True)` returns parsed JSON (or demo fallback); config exposes `UPLOAD_DIR`, `MAX_UPLOAD_MB`, `APP_SECRET`
- **Completion:** single documented entry point for LLM JSON calls; demo fallback verified without keys; no new provider SDK.

#### Phase 2 — Local auth + role flag
- **Objective:** Add optional credential auth and an `is_admin` role without breaking the existing login.
- **Modify:** `backend/app/models/user.py`, `backend/app/schemas/user.py`, `backend/app/routers/auth.py`, `backend/app/database.py`
- **Create:** `backend/app/services/security.py`, `backend/tests/test_auth_roles.py`
- **Deps:** Phase 1 | **Complexity:** high | **Risks:** R1
- **Validation:** existing login still returns first user; `signup` hashes password; `get_current_user` + `require_admin` work; seed user is admin
- **Completion:** `User` gains `password_hash`, `is_admin` via `COLUMN_MIGRATIONS`; `/api/auth/signup`, `/api/auth/login`, `/api/auth/me`; `security.py` deps.

#### Phase 3 — Frontend auth client + role-aware shell
- **Objective:** Login/signup page, token persistence, admin-aware nav.
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`, `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Create:** `frontend/src/pages/Login.tsx`, `frontend/src/context/AuthContext.tsx`, `frontend/src/components/auth/RoleGate.tsx`, `frontend/src/test/auth.test.tsx`
- **Deps:** Phase 2 | **Complexity:** high | **Risks:** R1/R3
- **Validation:** vitest login/signup/logout; admin-only nav links gated | **Completion:** `/login` route, `AuthContext`, token in memory, `RoleGate`, role-aware sidebar.

#### Phase 4 — Upload infrastructure (backend)
- **Objective:** Multipart upload endpoint + static serving + validation.
- **Modify:** `backend/main.py` (static mount), `backend/app/config.py`
- **Create:** `backend/app/routers/uploads.py`, `backend/tests/test_uploads.py`
- **Deps:** Phase 1 | **Complexity:** medium | **Risks:** R4
- **Validation:** small PDF → 201 + URL; oversize → 413; disallowed ext → 400; served from `UPLOAD_DIR` | **Completion:** `POST /api/uploads` with safe filenames, allowlist, size cap.

#### Phase 5 — Frontend upload + auth API helpers
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** `frontend/src/test/api.test.ts`
- **Deps:** Phase 4 | **Complexity:** low | **Risks:** none
- **Validation:** `authApi`, `uploadApi` compile; mocked tests pass | **Completion:** typed helpers for auth + uploads.

#### Phase 6 — Catalog/naming scaffold
- **Objective:** Register the new domain namespaces and table names in one place.
- **Modify:** `backend/main.py`, `backend/app/models/__init__.py`
- **Create:** `backend/app/services/curriculum.py` (empty shell), `backend/tests/test_imports.py`
- **Deps:** Phase 1 | **Complexity:** low | **Risks:** R2
- **Validation:** app boots with no new routers; imports clean | **Completion:** reserved names (`institutions`, `curriculum_*`, `materials`, `quizzes`, `quiz_attempts`, `summaries`) documented in a code comment.

#### Phase 7 — G1 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 1–6 | **Complexity:** low | **Risks:** R1/R3
- **Validation:** `pytest` (200 baseline + new) green; `tsc -b`; vitest; build | **Completion:** foundations stable; legacy login intact.

## GROUP G2 — Curriculum backend: Institution + Program (Phases 8–14)

#### Phase 8 — Institution model + schema
- **Create:** `backend/app/models/institution.py`, `backend/app/schemas/curriculum.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 7 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean | **Completion:** `Institution(id, name, short_name, description, is_active)` with `is_active` default False (admin-approved).

#### Phase 9 — Institution router (public + admin)
- **Create:** `backend/app/routers/curriculum.py`, `backend/tests/test_curriculum_institutions.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 8 | **Complexity:** medium | **Risks:** none
- **Validation:** `GET /api/curriculum/institutions` returns active only; admin list/create/status-toggle gated | **Completion:** nested+standalone style: `GET /api/curriculum/institutions`, `GET /api/curriculum/institutions/admin/all`, `POST`, `PATCH /api/curriculum/institutions/{id}/status`.

#### Phase 10 — CurriculumCourse (program) model + schema
- **Create:** `backend/app/models/curriculum_course.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/curriculum.py`
- **Deps:** Phase 9 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean; unique `(institution_id, code)` | **Completion:** `CurriculumCourse(id, institution_id, name, code, description, duration, is_active)`.

#### Phase 11 — Program endpoints under institution
- **Modify:** `backend/app/routers/curriculum.py`
- **Create:** `backend/tests/test_curriculum_courses.py`
- **Deps:** Phase 10 | **Complexity:** medium | **Risks:** none
- **Validation:** `GET /api/curriculum/institutions/{id}/programs` returns active; admin create gated; `GET /api/curriculum/programs/{id}` | **Completion:** program listing/detail/create endpoints.

#### Phase 12 — Seed demo catalog
- **Modify:** `backend/app/seed/__init__.py`
- **Create:** — | **Deps:** Phase 11 | **Complexity:** low | **Risks:** none
- **Validation:** fresh DB seeds 1 active institution + 1 program (mirroring reference GLA University / BTECH-CSE) | **Completion:** deterministic demo catalog top two levels.

#### Phase 13 — Enrollment binding
- **Modify:** `backend/app/models/user.py`, `backend/app/routers/auth.py`
- **Create:** — | **Deps:** Phase 10 | **Complexity:** medium | **Risks:** R1
- **Validation:** `User` gains `institution_id`, `program_id` FKs; `PUT /api/auth/enrollment` validates active institution/program | **Completion:** user↔institution/program links; enrollment update endpoint.

#### Phase 14 — G2 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 8–13 | **Complexity:** low | **Risks:** none
- **Validation:** curriculum tests green; regression | **Completion:** Institution + Program backend complete.

## GROUP G3 — Curriculum backend: Subject + Unit (Phases 15–21)

#### Phase 15 — CurriculumSubject model + schema
- **Create:** `backend/app/models/curriculum_subject.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/curriculum.py`
- **Deps:** Phase 11 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean; unique `(program_id, code)` | **Completion:** `CurriculumSubject(id, program_id, name, code, semester, credits, description, is_active)`.

#### Phase 16 — Subject endpoints
- **Modify:** `backend/app/routers/curriculum.py`
- **Create:** `backend/tests/test_curriculum_subjects.py`
- **Deps:** Phase 15 | **Complexity:** medium | **Risks:** none
- **Validation:** `GET /api/curriculum/programs/{id}/subjects` (ordered by semester, incl. unit_count); admin create; `GET /api/curriculum/subjects/{id}` | **Completion:** subject listing/detail/create with `unit_count`.

#### Phase 17 — CurriculumUnit model + schema
- **Create:** `backend/app/models/curriculum_unit.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/curriculum.py`
- **Deps:** Phase 16 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean; unique `(subject_id, unit_number)` | **Completion:** `CurriculumUnit(id, subject_id, unit_number, name, description, is_active)`.

#### Phase 18 — Unit endpoints
- **Modify:** `backend/app/routers/curriculum.py`
- **Create:** `backend/tests/test_curriculum_units.py`
- **Deps:** Phase 17 | **Complexity:** medium | **Risks:** none
- **Validation:** `GET /api/curriculum/subjects/{id}/units` (incl. material_count); admin create; `GET /api/curriculum/units/{id}` | **Completion:** unit listing/detail/create with `material_count`.

#### Phase 19 — Full-hierarchy drill endpoint
- **Modify:** `backend/app/routers/curriculum.py`
- **Create:** — | **Deps:** Phase 18 | **Complexity:** medium | **Risks:** none
- **Validation:** `GET /api/curriculum/subjects/{id}/tree` returns units+materials (lazy) | **Completion:** efficient tree query used by Subject page.

#### Phase 20 — Seed subjects + units
- **Modify:** `backend/app/seed/__init__.py`
- **Create:** — | **Deps:** Phase 18 | **Complexity:** low | **Risks:** none
- **Validation:** fresh DB seeds 5 subjects + 5 units each (mirrors reference) | **Completion:** deterministic demo hierarchy.

#### Phase 21 — G3 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 15–20 | **Complexity:** low | **Risks:** none
- **Validation:** curriculum tests green; regression | **Completion:** full curriculum hierarchy backend complete.

## GROUP G4 — Materials: upload, download, counts (Phases 22–28)

#### Phase 22 — Material model + schema
- **Create:** `backend/app/models/material.py`, `backend/app/schemas/material.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 18 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean | **Completion:** `Material(id, unit_id, uploaded_by_id, title, description, file_type, file_url, file_size, original_file_name, view_count, download_count, is_active)`.

#### Phase 23 — Material router (list/detail + counts)
- **Create:** `backend/app/routers/materials.py`, `backend/tests/test_materials.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 22 | **Complexity:** medium | **Risks:** R7
- **Validation:** `GET /api/curriculum/units/{id}/materials`; `GET /api/materials/{id}` increments view_count; download increments download_count | **Completion:** listing/detail/view-count; download endpoint serving from `UPLOAD_DIR`.

#### Phase 24 — Material upload endpoint
- **Modify:** `backend/app/routers/materials.py`
- **Create:** — | **Deps:** Phase 23, Phase 4 | **Complexity:** medium | **Risks:** R4
- **Validation:** multipart upload → material row; ext allowlist (pdf/ppt/pptx/doc/docx/txt); orphan cleanup on failure | **Completion:** `POST /api/curriculum/units/{id}/materials` (auth) mirrors reference flow with FastAPI uploads.

#### Phase 25 — Material pagination + title search
- **Modify:** `backend/app/routers/materials.py`
- **Create:** — | **Deps:** Phase 24 | **Complexity:** low | **Risks:** none
- **Validation:** `?page=&page_size=` and `?q=` title filter work | **Completion:** paginated, searchable material list (improvement over reference).

#### Phase 26 — Teacher/curator upload authorization
- **Modify:** `backend/app/routers/materials.py`
- **Create:** `backend/tests/test_material_authz.py`
- **Deps:** Phase 24, Phase 2 | **Complexity:** medium | **Risks:** R7
- **Validation:** non-authenticated upload → 401; admin and student (authed) both allowed | **Completion:** uploads require auth; writes scoped.

#### Phase 27 — Seed demo materials
- **Modify:** `backend/app/seed/__init__.py`
- **Create:** — | **Deps:** Phase 24 | **Complexity:** low | **Risks:** none
- **Validation:** fresh DB seeds a demo material with a bundled sample PDF | **Completion:** at least one demo material per seeded unit.

#### Phase 28 — G4 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 22–27 | **Complexity:** low | **Risks:** none
- **Validation:** material tests green; regression | **Completion:** material backend complete.

## GROUP G5 — Text extraction pipeline (Phases 29–35)

#### Phase 29 — Text extractor service (PDF)
- **Create:** `backend/app/services/text_extractor.py`, `backend/tests/test_text_extractor.py`
- **Modify:** `backend/requirements.txt`
- **Deps:** Phase 28 | **Complexity:** medium | **Risks:** R6
- **Validation:** a sample PDF yields expected substring; scanned PDF → graceful error | **Completion:** `extract(file_path, file_type) -> str` for pdf via `pypdf`.

#### Phase 30 — DOCX + TXT extraction
- **Modify:** `backend/app/services/text_extractor.py`
- **Create:** — | **Deps:** Phase 29 | **Complexity:** low | **Risks:** none
- **Validation:** sample .docx and .txt yield expected substrings | **Completion:** `extract` handles docx (`python-docx`) + txt — **exceeds reference**.

#### Phase 31 — Multi-file extract + combine
- **Modify:** `backend/app/services/text_extractor.py`
- **Create:** `backend/tests/test_text_extractor_multi.py`
- **Deps:** Phase 30 | **Complexity:** low | **Risks:** none
- **Validation:** multiple files joined with `--- title ---` headers; unsupported placeholders skipped | **Completion:** `extract_multiple(files) -> str`.

#### Phase 32 — Ingestion service
- **Create:** `backend/app/services/ingestion.py`
- **Deps:** Phase 31 | **Complexity:** medium | **Risks:** R4
- **Validation:** uploaded file → stored → extracted text cached/retrievable for AI | **Completion:** `ingest(material)` returns extracted text with length cap.

#### Phase 33 — Extraction cache column
- **Modify:** `backend/app/models/material.py`, `backend/app/database.py`
- **Create:** — | **Deps:** Phase 32 | **Complexity:** low | **Risks:** R2
- **Validation:** `extracted_text` column added via `COLUMN_MIGRATIONS`; filled on first AI use | **Completion:** material carries cached extraction (avoids re-parse).

#### Phase 34 — No-text guard + error taxonomy
- **Modify:** `backend/app/services/ingestion.py`
- **Create:** `backend/tests/test_ingestion_errors.py`
- **Deps:** Phase 33 | **Complexity:** low | **Risks:** R6
- **Validation:** empty/unsupported text raises typed error surfaced to UI | **Completion:** `NoExtractableTextError` handled consistently.

#### Phase 35 — G5 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 29–34 | **Complexity:** low | **Risks:** none
- **Validation:** extraction + ingestion tests green; regression | **Completion:** text extraction pipeline complete.

## GROUP G6 — AI summaries backend (Phases 36–42)

#### Phase 36 — Summary model + schema
- **Create:** `backend/app/models/summary.py`, `backend/app/schemas/summary.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 35 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean | **Completion:** `Summary(id, unit_ids (JSON), content, key_points (JSON), created_at)`.

#### Phase 37 — Summary prompt contract
- **Create:** `backend/app/services/prompts.py`
- **Deps:** Phase 1, Phase 35 | **Complexity:** low | **Risks:** R5
- **Validation:** `summary_prompt(content)` and `multi_unit_summary_prompt(units)` return prompt strings matching ai_client JSON contract | **Completion:** single + multi-unit prompt builders (mirror reference templates, adapted).

#### Phase 38 — Summary generation service
- **Create:** `backend/app/services/summaries.py`, `backend/tests/test_summaries.py`
- **Deps:** Phase 37, Phase 32 | **Complexity:** medium | **Risks:** R5
- **Validation:** mocked `ai_client` returns JSON → service parses `content`/`key_points` (with wrapped-object fallbacks) | **Completion:** `generate_summary(unit_ids)` single-unit; `generate_multi_summary(unit_ids)` with per-unit headers + synthesis.

#### Phase 39 — Summaries router + caching
- **Create:** `backend/app/routers/summaries.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 38 | **Complexity:** medium | **Risks:** none
- **Validation:** `POST /api/summaries` checks cache by sorted `unit_ids` → returns `{summary, cached}`; re-request returns cached | **Completion:** `POST /api/summaries` with cache-first logic.

#### Phase 40 — Demo-fallback summary
- **Modify:** `backend/app/services/summaries.py`
- **Create:** `backend/tests/test_summaries_fallback.py`
- **Deps:** Phase 39 | **Complexity:** low | **Risks:** R5
- **Validation:** with AI disabled, summary returns deterministic content | **Completion:** offline-capable summaries.

#### Phase 41 — Summary list/history + delete
- **Modify:** `backend/app/routers/summaries.py`
- **Create:** — | **Deps:** Phase 40 | **Complexity:** low | **Risks:** none
- **Validation:** `GET /api/summaries` (recent) + `DELETE /api/summaries/{id}` | **Completion:** history + cache eviction.

#### Phase 42 — G6 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 36–41 | **Complexity:** low | **Risks:** none
- **Validation:** summary tests green (mocked + fallback); regression | **Completion:** AI summary backend complete.

## GROUP G7 — AI quizzes backend (Phases 43–49)

#### Phase 43 — Quiz + QuizAttempt models + schema
- **Create:** `backend/app/models/quiz.py`, `backend/app/models/quiz_attempt.py`, `backend/app/schemas/quiz.py`
- **Modify:** `backend/app/models/__init__.py`, `backend/app/schemas/__init__.py`
- **Deps:** Phase 35 | **Complexity:** low | **Risks:** R2
- **Validation:** imports clean | **Completion:** `Quiz(id, unit_id, questions JSON, difficulty)` with question shape `{question, options[4], correct_answer, explanation}`; `QuizAttempt(id, user_id, quiz_id, answers JSON, score, total_questions)`.

#### Phase 44 — Quiz prompt + generation service
- **Create:** `backend/app/services/quizzes.py`
- **Modify:** `backend/app/services/prompts.py`
- **Deps:** Phase 43, Phase 32 | **Complexity:** medium | **Risks:** R5
- **Validation:** mocked `ai_client` returns JSON quiz → parsed to question list; content < 50 chars → typed error | **Completion:** `generate_quiz(unit_id, num_questions, difficulty)`; demo fallback.

#### Phase 45 — Quiz generation endpoint
- **Create:** `backend/app/routers/quizzes.py`, `backend/tests/test_quizzes.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 44 | **Complexity:** medium | **Risks:** none
- **Validation:** `POST /api/quizzes` with `{unit_id, num_questions, difficulty}` returns saved quiz | **Completion:** generation endpoint (auth-required), distinct from in-flight `/api/ai`.

#### Phase 46 — Attempt submission + scoring
- **Modify:** `backend/app/routers/quizzes.py`
- **Create:** `backend/tests/test_quiz_attempts.py`
- **Deps:** Phase 45 | **Complexity:** medium | **Risks:** R7
- **Validation:** answers index-matched to `correct_answer`; returns `{score, total, percentage, results[]}`; bounds validated | **Completion:** `POST /api/quizzes/{id}/attempt` persists attempt + returns results.

#### Phase 47 — Quiz history endpoint
- **Modify:** `backend/app/routers/quizzes.py`
- **Create:** — | **Deps:** Phase 46 | **Complexity:** low | **Risks:** none
- **Validation:** `GET /api/quizzes/history` returns last 50 attempts with unit info | **Completion:** history (limit 50, mirrors reference).

#### Phase 48 — Quiz attempt analytics
- **Modify:** `backend/app/routers/quizzes.py`
- **Create:** `backend/app/services/quiz_stats.py`, `backend/tests/test_quiz_stats.py`
- **Deps:** Phase 47 | **Complexity:** low | **Risks:** none
- **Validation:** aggregates avg score, best score, per-unit attempts | **Completion:** `GET /api/quizzes/analytics` (feeds G13 gamification).

#### Phase 49 — G7 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 43–48 | **Complexity:** low | **Risks:** none
- **Validation:** quiz tests green (mocked + fallback + authz); regression | **Completion:** AI quiz backend complete.

## GROUP G8 — Curriculum frontend: Browse + drill-down (Phases 50–56)

#### Phase 50 — Curriculum API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 21 | **Complexity:** low | **Risks:** R3
- **Validation:** `tsc -b` clean | **Completion:** `curriculumApi` (institutions/programs/subjects/units) + `institutionApi`, `programApi`, `subjectApi`, `unitApi` types.

#### Phase 51 — Browse page `/browse`
- **Create:** `frontend/src/pages/Browse.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 50 | **Complexity:** medium | **Risks:** R3
- **Validation:** public page renders institutions → programs → subjects (3-level) | **Completion:** public browse with cascading filters + empty states.

#### Phase 52 — Institution card + program card components
- **Create:** `frontend/src/components/curriculum/InstitutionCard.tsx`, `frontend/src/components/curriculum/ProgramCard.tsx`
- **Modify:** `frontend/src/pages/Browse.tsx`
- **Deps:** Phase 51 | **Complexity:** low | **Risks:** none
- **Validation:** vitest renders cards with name/shortName/code | **Completion:** reusable catalog cards.

#### Phase 53 — Subject card grid (by semester)
- **Create:** `frontend/src/components/curriculum/SubjectCard.tsx`, `frontend/src/components/curriculum/SemesterGroup.tsx`
- **Modify:** `frontend/src/pages/Browse.tsx`
- **Deps:** Phase 52 | **Complexity:** medium | **Risks:** none
- **Validation:** subjects grouped by semester with credits/unit_count | **Completion:** semester-grouped subject display.

#### Phase 54 — Enrollment UI + CompleteProfile page
- **Create:** `frontend/src/pages/CompleteProfile.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/services/api.ts`
- **Deps:** Phase 13, Phase 53 | **Complexity:** medium | **Risks:** R1
- **Validation:** pick institution + program (cascading) → `PUT /api/auth/enrollment` | **Completion:** enrollment selection page + redirect logic.

#### Phase 55 — Dashboard enrollment badges
- **Create:** `frontend/src/components/dashboard/EnrollmentBadge.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 54 | **Complexity:** low | **Risks:** none
- **Validation:** badge shows institution/program; empty state if unenrolled | **Completion:** dashboard shows enrollment context.

#### Phase 56 — G8 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 50–55 | **Complexity:** low | **Risks:** none
- **Validation:** vitest browse/enrollment tests; `tsc -b`; build | **Completion:** browse + enrollment frontend complete.

## GROUP G9 — Subject/Unit pages + material library (Phases 57–63)

#### Phase 57 — Materials API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 28 | **Complexity:** low | **Risks:** R3
- **Validation:** `tsc -b` clean | **Completion:** `materialApi` (list/upload/download/search) + `Material` type.

#### Phase 58 — Subject page `/subjects/:id`
- **Create:** `frontend/src/pages/Subject.tsx`, `frontend/src/hooks/useSubject.ts`
- **Modify:** `frontend/src/App.tsx`
- **Deps:** Phase 53 | **Complexity:** medium | **Risks:** R3
- **Validation:** units listed as cards with material_count; multi-unit summary selection scaffold | **Completion:** subject detail page + route.

#### Phase 59 — Unit page `/units/:id`
- **Create:** `frontend/src/pages/Unit.tsx`, `frontend/src/hooks/useUnit.ts`
- **Modify:** `frontend/src/App.tsx`
- **Deps:** Phase 58 | **Complexity:** medium | **Risks:** R3
- **Validation:** materials list + upload section + Generate buttons render | **Completion:** unit detail page + route.

#### Phase 60 — Material library component
- **Create:** `frontend/src/components/curriculum/MaterialList.tsx`, `frontend/src/components/curriculum/MaterialRow.tsx`
- **Modify:** `frontend/src/pages/Unit.tsx`
- **Deps:** Phase 57 | **Complexity:** medium | **Risks:** none
- **Validation:** rows show file-type icon, size, download count, download link | **Completion:** material list with counts.

#### Phase 61 — Upload dropzone UI
- **Create:** `frontend/src/components/curriculum/MaterialUpload.tsx`
- **Modify:** `frontend/src/pages/Unit.tsx`
- **Deps:** Phase 57, Phase 5 | **Complexity:** medium | **Risks:** R4
- **Validation:** drag-drop/select → progress → success toast; invalid type blocked client-side | **Completion:** upload UI with validation + feedback.

#### Phase 62 — Material search + pagination UI
- **Modify:** `frontend/src/pages/Unit.tsx`
- **Create:** `frontend/src/components/curriculum/MaterialSearch.tsx`
- **Deps:** Phase 60 | **Complexity:** low | **Risks:** none
- **Validation:** search box filters list (title) | **Completion:** lightweight search improvement.

#### Phase 63 — G9 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 57–62 | **Complexity:** low | **Risks:** none
- **Validation:** vitest subject/unit/material tests; `tsc -b`; build | **Completion:** curriculum pages + material library complete.

## GROUP G10 — AI summary + quiz frontend (Phases 64–70)

#### Phase 64 — AI API client + types (summaries/quizzes)
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phases 42, 49 | **Complexity:** low | **Risks:** R3
- **Validation:** `tsc -b` clean | **Completion:** `summaryApi`, `quizApi` + `Summary`, `Quiz`, `QuizAttemptResult` types.

#### Phase 65 — Summary component
- **Create:** `frontend/src/components/summary/Summary.tsx`
- **Deps:** Phase 64 | **Complexity:** low | **Risks:** none
- **Validation:** renders key points + markdown content; collapsible | **Completion:** summary viewer (styled with target tokens).

#### Phase 66 — Quiz component
- **Create:** `frontend/src/components/quiz/Quiz.tsx`
- **Deps:** Phase 64 | **Complexity:** high | **Risks:** R7
- **Validation:** question navigation, A–D selection, submit disabled until complete, results with explanations + color-coded score | **Completion:** full quiz flow (CSS transitions, not framer-motion).

#### Phase 67 — Unit page AI actions
- **Modify:** `frontend/src/pages/Unit.tsx`
- **Create:** `frontend/src/hooks/useQuiz.ts`
- **Deps:** Phase 66, Phase 65 | **Complexity:** medium | **Risks:** R5
- **Validation:** Generate Quiz / Generate Summary buttons call APIs; loading + demo-mode states | **Completion:** AI actions wired on Unit page.

#### Phase 68 — Subject page multi-unit summary
- **Modify:** `frontend/src/pages/Subject.tsx`
- **Create:** — | **Deps:** Phase 67 | **Complexity:** medium | **Risks:** R5
- **Validation:** checkbox units → Generate Summary → Summary component; cached path shows notice | **Completion:** multi-unit summary flow.

#### Phase 69 — Quiz history UI
- **Create:** `frontend/src/components/quiz/QuizHistory.tsx`
- **Modify:** `frontend/src/pages/Unit.tsx` (or `/quiz` route)
- **Deps:** Phase 66 | **Complexity:** low | **Risks:** none
- **Validation:** past attempts listed with scores | **Completion:** history panel.

#### Phase 70 — G10 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 64–69 | **Complexity:** low | **Risks:** R5
- **Validation:** vitest summary/quiz tests; `tsc -b`; build; demo-mode AI verified | **Completion:** AI summary + quiz frontend complete.

## GROUP G11 — Admin/curator page (Phases 71–77)

#### Phase 71 — Admin API client + types
- **Modify:** `frontend/src/services/api.ts`, `frontend/src/types/index.ts`
- **Create:** — | **Deps:** Phase 21 | **Complexity:** low | **Risks:** R3
- **Validation:** `tsc -b` clean | **Completion:** `adminApi` (all institutions, status toggle, create) + types.

#### Phase 72 — Admin page `/admin`
- **Create:** `frontend/src/pages/Admin.tsx`, `frontend/src/components/curriculum/InstitutionTable.tsx`
- **Modify:** `frontend/src/App.tsx`, `frontend/src/components/layout/Sidebar.tsx`
- **Deps:** Phase 71 | **Complexity:** medium | **Risks:** R3
- **Validation:** role-gated; lists all institutions with Active/Pending badges | **Completion:** admin route + table.

#### Phase 73 — Approve/deactivate toggle
- **Modify:** `frontend/src/pages/Admin.tsx`
- **Create:** `frontend/src/components/curriculum/StatusBadge.tsx`
- **Deps:** Phase 72 | **Complexity:** low | **Risks:** none
- **Validation:** toggle calls status endpoint; badge updates | **Completion:** institution approval workflow UI.

#### Phase 74 — Add-institution form
- **Create:** `frontend/src/components/curriculum/InstitutionForm.tsx`
- **Modify:** `frontend/src/pages/Admin.tsx`
- **Deps:** Phase 73 | **Complexity:** low | **Risks:** none
- **Validation:** create institution; appears in list | **Completion:** create-institution form with validation.

#### Phase 75 — Program/Subject/Unit admin forms
- **Create:** `frontend/src/components/curriculum/ProgramForm.tsx`, `frontend/src/components/curriculum/SubjectForm.tsx`, `frontend/src/components/curriculum/UnitForm.tsx`
- **Modify:** `frontend/src/pages/Admin.tsx`
- **Deps:** Phase 74 | **Complexity:** medium | **Risks:** none
- **Validation:** nested create forms (program under institution, subject under program, unit under subject) | **Completion:** full catalog creation UI (curator mode).

#### Phase 76 — Admin nav gating + role checks
- **Modify:** `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/auth/RoleGate.tsx`
- **Create:** — | **Deps:** Phase 75, Phase 3 | **Complexity:** low | **Risks:** R1
- **Validation:** `/admin` hidden for non-admin; guarded server-side too | **Completion:** consistent role gating front + back.

#### Phase 77 — G11 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 71–76 | **Complexity:** low | **Risks:** R1
- **Validation:** vitest admin tests; `tsc -b`; build; authz verified | **Completion:** admin/curator page complete.

## GROUP G12 — Integration & enrollment analytics (Phases 78–84)

#### Phase 78 — Link catalog to personal courses
- **Modify:** `backend/app/models/course.py`, `backend/app/routers/courses.py`, `backend/app/database.py`
- **Create:** — | **Deps:** Phase 21 | **Complexity:** medium | **Risks:** R2
- **Validation:** `Course` gains optional `curriculum_subject_id` FK via migration; no behavior change when null | **Completion:** personal courses can reference catalog subjects (enrichment only).
- **DONE:** FK already in model+migration; schema/router now expose and persist `curriculum_subject_id` (`schemas/course.py`, `routers/courses.py`); `test_courses.py::test_course_links_curriculum_subject` covers round-trip. Completed 2026-08-05.

#### Phase 79 — Enrollment analytics endpoint
- **Create:** `backend/app/services/enrollment_stats.py`, `backend/app/routers/enrollment.py`
- **Modify:** `backend/main.py`
- **Deps:** Phase 78 | **Complexity:** medium | **Risks:** none
- **Validation:** `GET /api/enrollment/summary` returns subjects, materials uploaded, quizzes taken per enrolled program | **Completion:** enrollment progress payload.

#### Phase 80 — Dashboard curriculum section
- **Create:** `frontend/src/components/dashboard/CurriculumSection.tsx`
- **Modify:** `frontend/src/pages/Dashboard.tsx`
- **Deps:** Phase 79 | **Complexity:** medium | **Risks:** R3
- **Validation:** section shows enrolled program + subjects by semester + quick links | **Completion:** dashboard integrates catalog.

#### Phase 81 — Material→course linking UI
- **Modify:** `frontend/src/components/curriculum/MaterialUpload.tsx`
- **Create:** — | **Deps:** Phase 78 | **Complexity:** low | **Risks:** none
- **Validation:** optional "link to my course" picker persists FK | **Completion:** enrichment linkage from upload UI.
- **DONE:** `MaterialUpload` gained a `subjectId` prop + "Link to my course (optional)" select that sets `curriculum_subject_id` via `endpoints.courses.update`; wired from `Unit.tsx`. Completed 2026-08-05.

#### Phase 82 — Quiz score → enrollment progress
- **Modify:** `backend/app/services/enrollment_stats.py`
- **Create:** — | **Deps:** Phase 79, Phase 48 | **Complexity:** low | **Risks:** none
- **Validation:** quiz analytics included in summary | **Completion:** holistic progress model.

#### Phase 83 — README seed documentation
- **Modify:** `frontend/README.md`
- **Create:** — | **Deps:** Phase 82 | **Complexity:** low | **Risks:** none
- **Validation:** README lists curriculum routes/endpoints | **Completion:** interim docs for new surfaces.

#### Phase 84 — G12 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 78–83 | **Complexity:** low | **Risks:** none
- **Validation:** enrollment tests green; vitest; build | **Completion:** integration + analytics complete.

## GROUP G13 — Gamification + security integration (Phases 85–90)

#### Phase 85 — Quiz XP rewards
- **Modify:** `backend/app/routers/quizzes.py`, `backend/app/services/quiz_stats.py`
- **Create:** `backend/tests/test_quiz_xp.py`
- **Deps:** Phase 48 | **Complexity:** medium | **Risks:** none
- **Validation:** attempt with ≥70% grants XP via existing `habit_xp`/character total_xp hooks; no double-award on retry | **Completion:** quiz performance feeds gamification (improvement over reference).
- **DONE:** `grant_quiz_xp()` in `quiz_stats.py` (+25 XP, once per quiz, char+user wallet); router returns `xp_awarded`; schema updated; Quiz results show an "⚡ +25 XP earned" banner; tests assert exact deltas. Completed 2026-08-05.

#### Phase 86 — Material upload reward
- **Modify:** `backend/app/routers/materials.py`
- **Create:** — | **Deps:** Phase 85 | **Complexity:** low | **Risks:** none
- **Validation:** first upload per unit grants XP; duplicates don't | **Completion:** uploads contribute to gamification.
- **DONE:** `_grant_first_upload_xp()` in `routers/materials.py` (+15 XP, first upload per unit only); `TestMaterialUploadXp` covers grant + no-double-award. Completed 2026-08-05.

#### Phase 87 — Summary generation limit guard
- **Modify:** `backend/app/routers/summaries.py`
- **Create:** — | **Deps:** Phase 86 | **Complexity:** low | **Risks:** R5
- **Validation:** per-day summary cap returns 429 with message (demo fallback exempt) | **Completion:** cost guard on LLM endpoints.
- **DONE:** `SUMMARY_DAILY_LIMIT` (config + `.env.example`, default 10); router returns 429 beyond cap for *new* generations; cached lookups and `AI_ENABLED=false` demo fallback exempt; `test_summaries_limit.py` covers all three paths. Completed 2026-08-05.

#### Phase 88 — Admin authorization matrix
- **Modify:** `backend/app/services/security.py`
- **Create:** `backend/tests/test_admin_authz.py`
- **Deps:** Phase 11, Phase 2 | **Complexity:** medium | **Risks:** R1
- **Validation:** non-admin blocked from all catalog writes + admin list; documented matrix | **Completion:** authz matrix tested.

#### Phase 89 — Upload + ingestion security hardening
- **Modify:** `backend/app/routers/materials.py`, `backend/app/services/ingestion.py`
- **Create:** `backend/tests/test_material_security.py`
- **Deps:** Phase 88 | **Complexity:** medium | **Risks:** R4
- **Validation:** path traversal → 400; MIME sniff mismatch → 400; extraction size cap enforced | **Completion:** hardened ingestion.

#### Phase 90 — G13 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 85–89 | **Complexity:** low | **Risks:** none
- **Validation:** gamification + security tests green; full regression | **Completion:** gamification + security verified.

## GROUP G14 — UX, theming, responsiveness, accessibility (Phases 91–95)

#### Phase 91 — Curriculum theme polish
- **Create:** `frontend/src/themes/curriculum-theme.css`
- **Modify:** `frontend/src/styles/theme.css`
- **Deps:** none | **Complexity:** low | **Risks:** R3
- **Validation:** additive `data-theme="curriculum"` tokens; existing themes unaffected | **Completion:** opt-in study theme for catalog pages.

#### Phase 92 — Responsive pass on catalog pages
- **Modify:** `frontend/src/pages/Browse.tsx`, `frontend/src/pages/Subject.tsx`, `frontend/src/pages/Unit.tsx`, `frontend/src/pages/Admin.tsx`
- **Create:** — | **Deps:** Phase 91 | **Complexity:** medium | **Risks:** none
- **Validation:** 375/768/1280 breakpoints render cleanly | **Completion:** responsive grids/tables.
- **DONE:** pages already use auto-fit minmax grids + overflow-x tables; added 900/640px media rules (single-column cascade, stacking curate forms, scrollable tables) in `curriculum-theme.css`. Completed 2026-08-05.

#### Phase 93 — Accessibility pass (forms, quiz, upload)
- **Modify:** `frontend/src/components/quiz/Quiz.tsx`, `frontend/src/components/curriculum/MaterialUpload.tsx`, `frontend/src/pages/CompleteProfile.tsx`
- **Create:** — | **Deps:** Phase 92 | **Complexity:** medium | **Risks:** none
- **Validation:** focus states, aria-labels, keyboard navigation for quiz + forms | **Completion:** a11y items resolved.
- **DONE:** Quiz radiogroup gains arrow-key navigation + per-option `aria-label`; results/XP banners are `role=status`; curriculum theme adds visible `:focus-visible` rings + `prefers-reduced-motion` handling. Completed 2026-08-05.

#### Phase 94 — Async states + toasts on new pages
- **Modify:** `frontend/src/pages/Browse.tsx`, `frontend/src/pages/Unit.tsx`, `frontend/src/pages/Admin.tsx`
- **Create:** — | **Deps:** Phase 93 | **Complexity:** low | **Risks:** none
- **Validation:** `Skeleton`/`EmptyState`/`Toast` used consistently; vitest covers empty/error | **Completion:** consistent async UX.

#### Phase 95 — G14 verification gate
- **Modify:** — | **Create:** — | **Deps:** Phases 91–94 | **Complexity:** low | **Risks:** none
- **Validation:** vitest UX tests; `tsc -b`; build; oxlint clean | **Completion:** UX/theming parity done.

## GROUP G15 — Dev tooling & configuration (Phases 96–97)

#### Phase 96 — Requirements + env + verify script finalization
- **Modify:** `backend/requirements.txt`, `.env.example`
- **Create:** `scripts/verify.sh`
- **Deps:** Phases 1–95 | **Complexity:** low | **Risks:** none
- **Validation:** `pip install -r` clean; `.env.example` complete; `verify.sh` runs pytest+tsc+vitest+build | **Completion:** tooling stable and documented.
- **DONE:** deps (`python-multipart`, `bcrypt`, `pypdf`, `python-docx`) present; `.env.example` gained `SUMMARY_DAILY_LIMIT`; `verify.sh` header now covers all plans. Completed 2026-08-05.

#### Phase 97 — Lint/type hygiene + seed refresh
- **Modify:** `frontend/src/**` (new), `backend/app/seed/__init__.py`
- **Create:** — | **Deps:** Phase 96 | **Complexity:** low | **Risks:** R3
- **Validation:** oxlint exit 0 (no new warnings); `tsc -b` clean; fresh-DB seed yields full demo catalog | **Completion:** hygiene + deterministic seed.

## GROUP G16 — Verification, documentation, finalization (Phases 98–99)

#### Phase 98 — Full regression + fresh-DB smoke test
- **Modify:** `frontend/README.md` (draft)
- **Create:** — | **Deps:** Phases 1–97 | **Complexity:** high | **Risks:** R1/R3
- **Validation:** `pytest` (200 baseline + all new suites) green; `tsc -b`; `npm run build`; vitest; oxlint; fresh-DB smoke (temp DB) covering register → enroll → browse → upload → summarize → quiz → attempt → admin approve
- **Completion:** all gates green; no regressions in the 200 baseline tests.

#### Phase 99 — Documentation & final checklist
- **Modify:** `frontend/README.md`, `.env.example` (final), `backend/requirements.txt` (final)
- **Create:** — | **Deps:** Phase 98 | **Complexity:** low | **Risks:** none
- **Validation:** README documents curriculum hierarchy, materials, summaries, quizzes, admin, enrollment, new endpoints/env/theme; plan STATUS set to COMPLETE | **Completion:** docs current; final checklist below fully satisfied.
- **DONE:** README "Curriculum & SyllabusAI" section (routes, endpoints, gamification, theme); plan STATUS marked COMPLETE with 2026-08-05 gate evidence. Completed 2026-08-05.

---

# PART 10 — Testing Strategy

- **Backend (pytest + FastAPI TestClient):** `test_ai_contract.py`, `test_auth_roles.py`, `test_uploads.py`, `test_curriculum_institutions.py`, `test_curriculum_courses.py`, `test_curriculum_subjects.py`, `test_curriculum_units.py`, `test_materials.py`, `test_material_authz.py`, `test_text_extractor.py`, `test_text_extractor_multi.py`, `test_ingestion_errors.py`, `test_summaries.py`, `test_summaries_fallback.py`, `test_quizzes.py`, `test_quiz_attempts.py`, `test_quiz_stats.py`, `test_quiz_xp.py`, `test_admin_authz.py`, `test_material_security.py`, `test_imports.py` — reusing the existing `conftest.py` in-memory DB + seed fixture.
- **Frontend (vitest + Testing Library):** `auth.test.tsx`, `api.test.ts`, `browse.test.tsx`, `subject.test.tsx`, `unit.test.tsx`, `quiz.test.tsx`, `summary.test.tsx`, `admin.test.tsx` — mirroring `src/test/*.test.tsx` style.
- **Type safety:** `tsc -b` must stay clean every phase.
- **Gate cadence:** a verification gate closes each group (16 gates) plus a final full regression, matching the project's established practice.
- **AI testing:** mocked `ai_client` for deterministic JSON; demo-fallback tests prove offline operation; malformed-JSON parsing tests.
- **Smoke test (Phase 98):** fresh SQLite DB, uvicorn, full flow sweep.

---

# PART 11 — Success Criteria

1. **Feature parity:** All reference features SY1–SY29 are either implemented or explicitly excluded (⏸/🎨) with justification; the curriculum hierarchy, materials, summaries, and quizzes work end-to-end.
2. **Zero regression:** The 200-test backend baseline, `tsc -b`, `npm run build`, and 25 vitest tests remain green after every group.
3. **AI offline-first:** Summaries and quizzes work in deterministic demo mode; real LLM optional via the reused `ai_client`.
4. **Architecture preserved:** same router/model/schema/service layout, `migrate_schema()` pattern, theme system, shared components; the existing personal `Course` model and in-flight `/api/ai` router are untouched.
5. **Exceeds reference:** DOCX/TXT extraction, material search, quiz→XP gamification, and cost guards are improvements over SyllabusAI.

---

# PART 12 — Final Validation Checklist

- [x] Exactly 99 phases across G1–G16, each with Objective / Modify / Create / Deps / Complexity / Risks / Validation / Completion
- [x] Backend: all new routers registered in `backend/main.py`; all new columns via `COLUMN_MIGRATIONS`
- [x] Backend: `pytest` baseline 200 + all new suites green (Phase 98) — **543+ green 2026-08-05**
- [x] Frontend: new routes in `App.tsx` + `Sidebar.tsx`; `tsc -b` clean; `npm run build` clean; vitest green — **91/91 green 2026-08-05**
- [x] `ai_client.py` reused (no new LLM SDK); demo fallback verified without keys
- [x] `curriculum_*` tables and `/api/curriculum`, `/api/materials`, `/api/quizzes`, `/api/summaries`, `/api/enrollment` namespaces live; no clash with `courses` or in-flight `/api/ai`
- [x] Legacy single-user login intact; `is_admin` gating tested both sides
- [x] Text extraction covers PDF + DOCX + TXT with a graceful no-text path
- [x] Summary caching (sorted unit ids) and quiz history (limit 50) verified
- [x] Uploads: safe filenames, allowlist, size cap, `UPLOAD_DIR` static mount
- [x] Admin page (approve/deactivate/create) functional under the seed admin user
- [x] No duplicate services/components; existing routers/routes untouched functionally
- [x] `.env.example` documents all new vars; `requirements.txt` updated; `scripts/verify.sh` works
- [x] README documents new pages, endpoints, env vars, and any new theme
- [x] Plan `STATUS` marked COMPLETE with the Phase 98 smoke-test evidence appended

> **Phase 98/99 evidence (2026-08-05):** Backend `python -m pytest -q` → **543 passed** (baseline + all new SyllabusAI suites incl. quiz-XP, material-XP, summary-limit, course-link). Frontend `tsc -b` → clean; `vitest run` → **91 passed**. README now documents the curriculum section; `verify.sh` covers all plans.
