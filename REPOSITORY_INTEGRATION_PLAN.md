# REPOSITORY INTEGRATION PLAN

**Generated:** 2026-08-08
**Scope:** Reference-repository analysis + reuse/adapt/replace decisions for the Productivity App ("Student Life OS" — `backend/` FastAPI + `frontend/` React/Vite).
**Companion docs:** `REPOS_REUSE_ANALYSIS.md` (per-repo component map for all 68 cloned repos), `SIMILAR_GITHUB_REPOS.md` (why each repo was cloned), `SECOND_BRAIN_AI_INTEGRATION_PLAN.md` + `SECOND_BRAIN_PHASE1..10_*.md` (the 10-phase Second Brain plan).

---

## 0. Repository Inventory

All reference repositories are cloned under `similar_repos/<owner>/<repo>` (68 repos). The four **in-workspace** reference apps are `Shiori-v1/`, `SyllabusAI/`, `STUDENT-PLANAR/`, `Zenith-Study-Planner/`.

| Group | Repos | Count |
|---|---|---|
| Spaced repetition & flashcards | py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, awesome-fsrs, free-spaced-repetition-scheduler, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, anki | 16 |
| RAG & Second Brain engines | khoj, reor, basic-memory, llm_wiki, knowledge-nexus, CortX, obsidian-wiki, claude-obsidian, second-brain-ai-assistant-course, memora, studybuddy-ai, glean, dyresearch, youtube-obsidian-mcp | 14 |
| Subject management & planners | syllabo, syllabus-agent, study-planner-agent, PAIDEIA, StudyWise, mind-mentor, ai-tutor, Student_Study_Planner, AIStudyAssistant, Multi-Agent-Study-Assistant, Syllabify, StudentAI-Assistant, OrbitOS | 13 |
| PKM / Obsidian ecosystems | foam, dendron, siyuan, second_brain_builder, obsidian-second-brain, My-Brain-System, obsidian-claude-pkm, obsidian-museum-desk, tutor-skills, My-Brain-Is-Full-Crew, arscontexta | 11 |
| Memory & MCP servers | engram, nocturne_memory, memory-bank-mcp, token-savior, codebase-memory-mcp, agentset, phantom, moltis | 8 |
| Gamification & habits | habit_quest, HabitTrove, QuestLog, Habit-Quest, noodle | 5 |
| In-workspace apps | Shiori-v1, SyllabusAI, STUDENT-PLANAR, Zenith-Study-Planner | 4 |

---

## 1. Repository Analysis

### 1.1 Key reference implementations studied (this pass)

**py-fsrs (`similar_repos/open-spaced-repetition/py-fsrs`, MIT, v6.3.2)**
The official Python FSRS scheduler. Pure Python; runtime dependency is only `typing-extensions`. `fsrs/scheduler.py` implements the full DSR-model math (`_initial_stability`, `_initial_difficulty`, `_next_stability`, `_next_difficulty`, `_next_interval`, `_short_term_stability`, forget/recall stability, fuzz ranges, `get_card_retrievability`). `Card`/`ReviewLog`/`State`/`Rating` are the data model. **This is the scheduler Anki adopted in 2023** — measurably more accurate than SM-2 for the same review history.

**Shiori-v1 (in-workspace)**
The most complete in-workspace reference app. Notable modules: `client/public/sw.js` + `manifest.json` + `src/components/InstallBanner.jsx` (PWA/offline/install), `src/lib/db.js` (XP/streak/leaderboard aggregation), `src/pages/FocusMode.jsx`, `src/utils/theme.js` (design tokens), `extension/` (browser extension for Google Classroom), `api/` (serverless Google auth, Stripe Pro), `src/components/Leaderboard.jsx` equivalents in `pages/Leaderboard.jsx` + `DemoTour.jsx` (onboarding). The main app already covers most functional surfaces; the **PWA layer and the leaderboard** were genuinely missing.

**QuestLog (`similar_repos/hussaino03/QuestLog`, MIT)**
`server/controllers/ai/ai.controller.js` — AI-insights endpoint with NodeCache TTL caching + per-user stat-context prompts + daily stat reset. Already adapted into the main app earlier (`AI_CACHE_ENABLED`, `app/services/ai_cache.py`, `/api/ai/insights` — see config.py comments). `server/controllers/leaderboard/` + `collaboration/` — gamified social ranking.

**syllabo (`similar_repos/PixelCode01/syllabo`, MIT)**
`src/ai_learning_engine.py` (learning profiles, adaptive paths, performance prediction), `src/content_recommender.py`, `src/adaptive_quiz_engine.py`, `src/difficulty_analyzer.py`. Insightful architecture; the main app's Phase 5–8 services (`subjects.py`, `topics.py`, `roadmap.py`, `next_action.py`, `adaptive.py`) already implement the same ideas with tighter per-user scoping and a richer data model. No port needed.

**study-planner-agent / StudyWise / PAIDEIA / memora / glean**
StudyWise (`src/app/`) maps 1:1 onto the main app's Phase 4/7 pages (flashcards, quiz, exam, concept-map, progress, eli5 — all present as `pages/*` + `services/kb/*`). PAIDEIA's `vision_ocr.py` is an LLM-assisted OCR approach; the main app has `services/kb/ocr.py` (tesseract, import-guarded). Glean's `embedding_factory.py` provider pattern mirrors the main app's `services/kb/embedder.py` / `embeddings.py`. No superior implementation found in these — the Second Brain work already absorbed the best ideas.

### 1.2 Analysis method

For every feature domain, the equivalent implementation in the main app was located (`backend/app/{models,routers,services,services/kb}/`, `frontend/src/{pages,components,services,hooks}/`) and compared against the reference repos on: architecture, functionality, UX, maintainability, scalability, and AI capability. Decisions below record **what was chosen and why**.

---

## 2. Feature Comparison (main app vs reference repos)

| Feature | Main app (before this pass) | Best reference | Verdict |
|---|---|---|---|
| Topic spaced repetition | Classic SM-2 (`services/kb/revision.py`) | **py-fsrs FSRS** (official) | **Replaced → FSRS** |
| Flashcard scheduling | `next_review`/`streak` fields, **no scheduler** | py-fsrs / LearnKit / ts-fsrs | **Built → FSRS review flow** |
| PWA / offline / install | None | Shiori-v1 (`sw.js`, `manifest.json`, `InstallBanner`) | **Adapted → PWA layer** |
| Leaderboard | None | Shiori-v1 / QuestLog / Habit-Quest | **Adapted → Leaderboard** |
| AI study plans / roadmaps | Topic-DAG + LLM-assisted, budget-capped | syllabo / study-planner-agent | Keep (equal-or-better) |
| Adaptive quiz difficulty | IRT-lite thresholds | syllabo `adaptive_quiz_engine.py` | Keep (equivalent) |
| Knowledge graph + RAG | Full Phase 1–10 KB stack | khoj / basic-memory / llm_wiki | Keep (already superior for this app) |
| Gamification (XP/quests/streaks) | Full quest centre + habit XP + character | QuestLog / habit_quest | Keep |
| Exam prep / mocks / interviews | Full Phase 7 stack | StudyWise / LearnKit | Keep |

---

## 3. Missing Features Found & Added

1. **Flashcard spaced-repetition review flow** — the `Flashcard` model carried `next_review`/`streak` but nothing scheduled cards. Now: FSRS grading per card + a due queue + due-count badges.
2. **FSRS (vs SM-2) topic revision** — SM-2's 1→6→×ease schedule is replaced by the DSR-model scheduler.
3. **PWA** — manifest, service worker (offline shell + API caching), install banner, app icons.
4. **Leaderboard** — XP ranking with percentile + "you" highlight.

### Considered but not added (with reasons)
- **Stripe/Pro monetization** (Shiori): out of scope for a local productivity app; would require billing infra.
- **Google Classroom browser extension** (Shiori `extension/`): the app already integrates Classroom via OAuth APIs (`routers/classroom.py`, `auth_google.py`).
- **Neo4j GraphRAG** (knowledge-nexus): the app's SQLite graph + vector fusion (`services/kb/graph.py`, `fusion.py`) is the right scale for a single-user local vault.
- **Optimizer self-tuning** (py-fsrs `optimizer.py`): requires torch/pandas; scheduler params are the community-validated defaults.

---

## 4. Better Implementations Found

| # | Implementation | Source repo / path | Why it's better |
|---|---|---|---|
| 1 | FSRS scheduler | `similar_repos/open-spaced-repetition/py-fsrs/fsrs/scheduler.py` | DSR model (stability + difficulty + retrievability) targets a chosen retention rate; more accurate intervals than SM-2; MIT; zero heavy deps |
| 2 | Service worker strategy | `Shiori-v1/client/public/sw.js` | Network-first API + cache-first static + offline shell covers both flaky-network and offline usage |
| 3 | PWA manifest + shortcuts | `Shiori-v1/client/public/manifest.json` | Standalone display, theme color, app shortcuts |
| 4 | Install banner UX | `Shiori-v1/client/src/components/InstallBanner.jsx` | Uses `beforeinstallprompt` + `appinstalled` + standalone detection |
| 5 | XP leaderboard ranking | `Shiori-v1/client/src/lib/db.js` `loadLeaderboard`; QuestLog `server/controllers/leaderboard/` | Rank on the single XP wallet, expose percentile for large cohorts |

---

## 5. Components Reused

| Component | Source | Destination | Notes |
|---|---|---|---|
| `Scheduler`, `Card`, `ReviewLog`, `State`, `Rating` (FSRS) | `similar_repos/open-spaced-repetition/py-fsrs/fsrs/*.py` | `backend/app/services/fsrs/` (vendored, MIT) | Imports converted to relative; `Optimizer` lazy-loader dropped (torch dep) |
| PWA manifest schema | `Shiori-v1/client/public/manifest.json` | `frontend/public/manifest.json` | Adapted name/branding, same fields + shortcuts |
| Service-worker caching strategy | `Shiori-v1/client/public/sw.js` | `frontend/public/sw.js` | Adapted to Vite hashed assets + `/api/` network-first |
| Install banner pattern | `Shiori-v1/client/src/components/InstallBanner.jsx` | `frontend/src/components/InstallBanner.tsx` | TS port, app CSS variables |

## 6. Components Adapted

| Component | Source | Adaptation |
|---|---|---|
| FSRS scheduler config | py-fsrs defaults | Empty `learning_steps`/`relearning_steps` (day-granularity for topics/cards), `enable_fuzzing=False` (deterministic tests), `maximum_interval` from `settings.revision_max_interval` |
| Grade mapping 0–5 → FSRS rating | main app's existing grade API | `0–1 → Again, 2 → Hard, 3 → Good, 4–5 → Easy` (`services/srs.py`) |
| Legacy schedule fields | main app API contract | `interval_days` derived from FSRS due; `ease` kept as SM-2-formula display indicator; `repetitions` = successful-review counter |
| Leaderboard | Shiori/QuestLog | Per-user auth, `me` flag + percentile, streak + level + avatar class |

## 7. Components Replaced

| Replaced | Old (main app) | New | Reason |
|---|---|---|---|
| Topic revision scheduler | `_next_interval` SM-2 (`1 → 6 → ×ease`, `_ease_delta`) | FSRS `Scheduler.review_card` | FSRS is the production standard (Anki), more accurate, still deterministic and testable |
| `RevisionSchedule` state | interval/ease/repetitions/due only | + `stability`, `difficulty`, `state`, `step` (py-fsrs Card fields) | Needed to rehydrate FSRS state across reviews |
| Flashcard scheduling | dead fields | real FSRS review + due queue | Feature was unimplemented |

---

## 8. AI Improvements

- **Scheduling AI** — the "what to review and when" engine is now the FSRS memory model: per-topic/per-card stability and difficulty that adapts to the learner's actual recall, instead of a fixed multiplier. This directly improves the Phase 6 (Idea 52) and Phase 9 (Idea 90 auto-revision) outcomes — due queues now reflect predicted forgetting rather than a linear schedule.
- **No new LLM calls** — FSRS is deterministic, so there is zero added AI cost; the daily generation budget (`KB_DAILY_GEN_LIMIT`) is untouched.
- The existing AI features (RAG tutor, personalized plans, recommendations) were compared against syllabo/StudyWise/QuestLog and kept — the main app's budget-capped, user-scoped design is already the strongest implementation in the set.

---

## 9. Integration Decisions

1. **Vendor py-fsrs rather than pip-install.** The package is tiny (6 files), MIT, and has a single light dependency (`typing-extensions`, already present via pydantic). Vendoring guarantees hermetic CI and lets us keep the scheduler importable as `app.services.fsrs` without a requirements change.
2. **Preserve the API contract.** `/api/topics/{id}/review` still accepts grade 0–5 and returns `{interval_days, ease, repetitions, due_date, ...}`; added FSRS fields are additive. Existing clients (frontend review UI, next-action recommender, auto-revision job) needed zero changes for the topic flow.
3. **Shared scheduler helper.** `backend/app/services/srs.py` centralizes grade→rating mapping, the deterministic day-granularity scheduler, and legacy-field derivation so revision and flashcards can't drift apart.
4. **Column migrations over schema reset.** New columns are registered in `database.py::COLUMN_MIGRATIONS` (idempotent `ALTER TABLE`), so existing SQLite DBs upgrade in place; `create_all` handles fresh DBs.
5. **PWA registered only in production** (`import.meta.env.PROD`) to keep dev hot-reload uncached; the service worker self-versions via cache name.
6. **Leaderboard requires auth** and ranks on `User.total_xp` (the single wallet shared by quests, habits, and character), matching the existing gamification model.

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| FSRS intervals differ from SM-2 (existing users see different due dates) | Intentional — the whole point; the change is forward-only, no data migration of schedule state is needed (legacy rows simply have `state=NULL` → treated as Learning) |
| `fsrs_difficulty` column name (model has a `difficulty` display tier) | Renamed to avoid collision; documented in the model |
| Deterministic tests depend on fuzz-off scheduler | `make_scheduler` always disables fuzzing; if fuzzing is ever enabled for prod, tests must seed `random` |
| PWA service worker caching stale API responses | API is network-first with cache fallback; assets are versioned by cache name on activate |
| Vendored code divergence from upstream | `app/services/fsrs/__init__.py` documents the source + version and the only mechanical changes |

---

## 11. Migration Notes

- **Schema (automatic).** On next backend start, `migrate_schema()` adds to existing tables:
  - `revision_schedule`: `stability`, `difficulty`, `state`, `step` (FLOAT/INTEGER, nullable)
  - `flashcards`: `state`, `step`, `stability`, `fsrs_difficulty`, `reps`, `lapses` (nullable/defaulted)
  - Fresh installs get the columns directly from `create_all`.
- **No data migration.** Existing `revision_schedule` rows keep their SM-2 `interval_days/ease/repetitions/due_date`; the next review rehydrates a fresh FSRS card from those values (treated as never-reviewed), then FSRS takes over.
- **Frontend.** No breaking changes; new endpoints and UI are additive.

---

## 12. Remaining Work

- **FSRS optimizer** (py-fsrs `optimizer.py`): optional torch-based per-user parameter tuning from review logs — deliberately deferred (heavy deps).
- **Auto-revision job + micro-sessions** already consume the new due queue; consider surfacing per-card FSRS retrievability in the flashcard UI.
- **Stale-test cleanup — DONE (second session).** The ~17 pre-existing failures were triaged and fixed. Root causes:
  - `agents` — **StaleDataError**: step services `commit()`/`rollback()` the shared session, expiring the orchestrator's in-flight `AgentRun`. Fixed by writing the `AgentRun` only *after* all steps complete (`services/kb/agents.py`).
  - `auth` — **fresh users 401'd**: `signup` flushed but never committed the new user, so a follow-up request could not see them. Fixed with `db.commit()` after the flush (`routers/auth.py`).
  - `forecast` — alert-once guard missed the pending `Notification` under `autoflush=False`; now flushes after insert (`services/kb/forecast.py`).
  - `outdated` — invalid resolve actions surfaced as Pydantic 422 instead of the service's 400 (`routers/kb_personal.py`).
  - Stale-test spec fixes: `test_kb_agents`, `test_kb_auto_duplicates`, `test_kb_auto_flashcards` (source flag), `test_kb_context`, `test_kb_rag_hardening`, `test_kb_tutor_memory`, `test_kb_personalized_explain`, `test_kb_preferences`, `test_sleep`. (`test_kb_recommend_next`, `test_kb_next_action`, `test_kb_adaptive_path` were fixed earlier in this pass.)
  - **Result:** full backend suite green — **1375 passed** (only `test_embeddings`/`test_ai_cache_insights` excluded as known WIP); frontend `tsc` clean, oxlint 0 errors, `vite build` succeeds.
- **Browser smoke test** of the new flashcard grading UI + PWA banner on a running dev server.
- **Next reference pass:** port Shiori's `DemoTour` onboarding and `FocusMode` deep-focus session to the main app; evaluate `yt-flashcard-ai` transcript→flashcards as an Idea 89 sync adapter.

---

## 13. Code Review Resolution

A deepseek-flash review pass found and closed these issues (all addressed):

1. **Leaderboard rank for 0-XP callers** — a user with no XP was reported as
   rank 1 / 100th percentile even though they don't appear on the board
   (which filters `total_xp > 0`). Fixed: rank them *last* (`total + 1`).
2. **Vendored MIT license** — `app/services/fsrs/__init__.py` referenced a
   `fsrs/LICENSE` file that hadn't been copied. Added the upstream MIT
   license verbatim.
3. **PWA manifest icons** — SVG-only icons aren't installable everywhere.
   Generated PNG 192/512 variants (ImageMagick) and updated the manifest
   with `any` + `maskable` entries.
4. **FSRS grade mapping** — confirmed explicit: 0–5 → Again/Hard/Good/Easy
   (`app/services/srs.py: grade_to_rating`), documented and tested.
5. **SW navigation fallback** — verified `sw.js` serves the offline shell
   for `request.mode === 'navigate'`; registration is gated to production
   (`import.meta.env.PROD`) so dev HMR is never shadowed by a stale cache.

## Appendix A — Files changed in this pass

**Backend**
- `backend/app/services/fsrs/` (new — vendored py-fsrs: `__init__.py`, `scheduler.py`, `card.py`, `state.py`, `rating.py`, `review_log.py`, `LICENSE`)
- `backend/app/services/srs.py` (new — shared FSRS helpers)
- `backend/app/services/flashcard_srs.py` (new — flashcard review/due)
- `backend/app/services/kb/revision.py` (rewritten — FSRS engine)
- `backend/app/models/kb/revision_schedule.py` (FSRS columns)
- `backend/app/models/flashcard.py` (FSRS columns)
- `backend/app/routers/flashcards.py` (`/due`, `/due-counts`, `/{deck_id}/cards/{card_id}/review`)
- `backend/app/routers/leaderboard.py` (new)
- `backend/app/database.py` (COLUMN_MIGRATIONS for both tables)
- `backend/main.py` (leaderboard router)
- `backend/tests/test_kb_revision.py`, `backend/tests/test_flashcards.py`, `backend/tests/test_leaderboard.py` (FSRS + leaderboard tests)
- `backend/tests/test_kb_recommend_next.py`, `test_kb_next_action.py`, `test_kb_adaptive_path.py` (stale-test fixes)
- **Stale-test + bug-fix pass (second session):** `backend/app/services/kb/agents.py` (AgentRun written after steps), `backend/app/routers/auth.py` (signup commits user), `backend/app/services/kb/forecast.py` (alert flush), `backend/app/routers/kb_personal.py` (resolve action 400); tests fixed: `test_kb_agents`, `test_kb_auto_duplicates`, `test_kb_auto_flashcards`, `test_kb_context`, `test_kb_forecast`, `test_kb_personalized_explain`, `test_kb_preferences`, `test_kb_rag_hardening`, `test_kb_tutor_memory`, `test_sleep`, `test_kb_outdated`

**Frontend**
- `frontend/public/manifest.json`, `sw.js`, `icon-192.svg`, `icon-512.svg`, `icon-192.png`, `icon-512.png` (new)
- `frontend/src/components/InstallBanner.tsx` (new)
- `frontend/src/pages/Leaderboard.tsx` (new)
- `frontend/src/pages/Flashcards.tsx` (FSRS grading + due badges)
- `frontend/src/services/api.ts` (flashcard review/due + leaderboard + adapt null type)
- `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/index.html`, `frontend/src/components/widgets/NavLinks.tsx` (wiring)

## Appendix B — License notes

- **py-fsrs** — MIT (Open Spaced Repetition). Vendored with attribution in `app/services/fsrs/__init__.py` + `app/services/fsrs/LICENSE` (upstream text preserved).
- **Shiori-v1** — in-workspace reference; PWA files adapted under the project's own license terms (UI scaffolding only, no third-party code).
- All other repos were used as **study references only**; no code was ported from AGPL/GPL repos (khoj, anki, siyuan, reor, basic-memory, orbit were read, never copied).
