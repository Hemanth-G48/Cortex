# Second Brain Integration — Phase 6 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 6 — Study Planning & Execution (Ideas 51–60)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1–5 plans
(`SECOND_BRAIN_PHASE{1,2,3,4,5}_100_PHRASE_PLAN.md`).

**Implementation status: ✅ COMPLETE** — backend (10 KB test files: study-plan, revision, exam-prep,
assignment-intel, labs, attendance, progress, mastery, next-action, micro-session) and frontend
(plan view, due-reviews list, exam-prep page, labs tab, attendance view, progress dashboard,
mastery bars, "Study now" card, micro-session launch) all landed.

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (4): Idea 53 (exam prep mode), 55 (labs), 56 (attendance), 59 (recommended study order)
- 🟡 partial / extends existing code (6): Ideas 51, 52, 54, 57, 58, 60 extend the existing `StudyPlan` model + `study_plans` router, `/api/ai/study-plan`, tasks/reminders/daily-schedule, the analytics service, and Pomodoro

**Prerequisites: Phase 5 must be complete** — this phase executes what Phase 5 produced: the
topic graph (`topics`, `normalized_name`, difficulty, time estimates, outcomes), `roadmaps`, the
subject `parsed_json` (grading scheme, deadlines), and `DEPENDS_ON` edges. It also consumes
Phase 3–4 budget guards (`KB_DAILY_GEN_LIMIT`) and search (assignment hints, lab prep).

**Scope:** AI-personalized study plans, spaced-repetition revision scheduling, exam-prep mode,
assignment intelligence, lab + attendance tracking, subject progress analytics, weak/strong topic
mastery, a "what should I study now" recommender, and Pomodoro-linked micro-sessions. **The AI
tutor and assessment engine are Phase 7 and out of scope** — but the `learning_events` spine and
mastery seams built here are exactly what Phase 7 feeds.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 6 reuses |
|---|---|---|
| Study plan shell | `backend/app/models/study_plan.py` (`StudyPlan`: subject, exam_date, `weeks_json`) + `study_plans.py` router | The base to upgrade — **note: no `user_id` today** (must be added) |
| AI study plan endpoint | `backend/app/routers/ai.py` (`POST /api/ai/study-plan`) + `ai_fallback.demo_study_plan` | The 4-week-text-plan generator to replace with topic/roadmap-grounded plans |
| Daily schedule | `DailyScheduleItem` (`category`: School \| Study Time \| Break) + `daily_schedule` router | Materialization surface for due reviews + sessions |
| Exams + assignments | `Exam` model (`assignment.py`), assignments router | Exam-prep mode + assignment intelligence |
| Tasks + reminders + notifications | tasks, reminders, notifications routers | Subtasks, due reminders, weekly summaries, attendance alerts |
| Pomodoro | `pomodoro` router | Micro-session launch target (Idea 60) |
| Analytics + visuals | analytics router/service + existing StudyHeatmap-style charts | Progress dashboard charts (Idea 57) |
| Phase 5 output | `topics` (difficulty/time/outcomes), `roadmaps`, subject `parsed_json`, topic DAG | Plan/revision/exam-prep inputs |
| Missing today | **No `learning_events` table exists** — Ideas 57/58 need it as the event spine | Create it in Group 7 |

**File conventions:** services → `backend/app/services/kb/{plans,revision,mastery,sessions}.py`;
new models → `backend/app/models/kb/*.py` (`RevisionSchedule`, `LearningEvent`, `Lab`, `Attendance`);
routers → `backend/app/routers/kb_study.py` (or extend `study_plans.py`); tests →
`backend/tests/test_kb_*.py`. Register every new router in `main.py`, every model in
`models/__init__.py`; column adds on existing tables (e.g. `study_plans.user_id`) go through
`COLUMN_MIGRATIONS`.

**Cost rule:** every LLM path (plan generation, subtask breakdown) is budget-capped by
`KB_DAILY_GEN_LIMIT` and must work deterministically with `AI_ENABLED=false`. **Per-user scoping
is non-negotiable** — every new table and query filters `user_id`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---


---

## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))

Every idea in Phase 6 (Study Planning & Execution) has reusable components in the cloned reference repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.

- **Idea 51 — Personalized study plans (AI-driven):** study-planner-agent (generate_plan) · mind-mentor (study-plan) · Multi-Agent-Study-Assistant · syllabo · StudyWise
- **Idea 52 — Revision scheduling (spaced repetition):** py-fsrs · ts-fsrs · fsrs-rs · obsidian-spaced-repetition (FSRS+SM-2) · LearnKit (fsrs.ts/lkrs.ts) · infinition (SM-2) · org-fc (SM-2 + FSRS) · hashcards · memo · orbit · fsrs4anki · anki (rslib scheduler)
- **Idea 53 — Exam preparation mode:** StudyWise (exam page) · EduAI (practice) · syllabo · Student_Study_Planner
- **Idea 54 — Assignment intelligence:** QuestLog (tasks) · noodle (modules) · EduAI
- **Idea 55 — Lab tracking:** QuestLog (collaboration) · EduAI
- **Idea 56 — Attendance monitoring:** EduAI · habit_quest (streak patterns)
- **Idea 57 — Subject progress analytics:** QuestLog (analytics.controller.js) · StudyWise (progress) · mind-mentor (insights) · HabitTrove · syllabo
- **Idea 58 — Weak & strong topic detection:** QuestLog (AI insights) · StudyWise · syllabo · PAIDEIA
- **Idea 59 — Recommended study order:** syllabo (content_recommender.py) · Multi-Agent-Study-Assistant · StudyWise
- **Idea 60 — Micro-session & focus integration:** mind-mentor (timer) · habit_quest · HabitTrove

> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines (khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, dendron. Repos without a license file are STUDY only.

## Group 1 — Idea 51 🟡: Personalized study plans (AI-driven) (phrases 1–10)

1. **Add `user_id` to the `StudyPlan` model** via `COLUMN_MIGRATIONS` (the existing model has no owner) + register in `models/__init__.py`. 🟡
2. **Define a typed `weeks_json` schema** — `[{week, topic_ids[], chunk_refs[], hours_estimate}]` replacing the free-text weeks format. 🟡
3. **Create `app/services/kb/plans.py`** — plan generation from the Phase 5 roadmap, vault coverage, and user availability. 🟡
4. **Add `POST /api/subjects-ai/{id}/study-plan`** — request `{hours_per_day, weeks}`; generates a topic-grounded plan (LLM-assisted, budget-capped). 🟡
5. **Regenerate on schedule change** — new plan versions via the Phase 5 `Roadmap` versioning pattern; the old plan stays queryable. 🟡
6. **Deterministic fallback** — roadmap topological order → equal weekly split when `AI_ENABLED=false`. 🟡
7. **Persist to the existing `StudyPlan` table** so current study-plan UIs keep working (extend, don't fork). 🟡
8. **Write `backend/tests/test_kb_study_plan.py`** — generation from roadmap, availability constraint, versioning, fallback, per-user isolation. 🟡
9. **Frontend:** plan view shows topic-grounded weeks (topic names + time), replacing the plain-week UI. 🟡
10. **api.ts:** `endpoints.subjects.studyPlan` (generate/get). 🟡


## Group 2 — Idea 52 🟡: Revision scheduling — spaced repetition (phrases 11–20)

11. **Define the `RevisionSchedule` model (`revision_schedule`)** — `id, user_id, topic_id (FK, unique), interval_days, ease, repetitions, due_date, last_reviewed_at`. 🟡
12. **Register the model** + a `KB_REVISION_*` config block (initial interval, minimum ease, max interval). 🟡
13. **Implement the SM-2-style update** — `apply_review(grade 0–5)` adjusts interval/ease/due per the classic algorithm, in a pure service function. 🟡
14. **Add `POST /api/topics/{id}/review`** — `{grade}` updates the schedule and logs a learning event (Group 7 spine). 🟡
15. **Add `GET /api/reviews/due`** — the user's due topics (per-user), the revision queue. 🟡
16. **Daily job: materialize due reviews** into `daily_schedule`/tasks + reminders (reuse the existing daily-schedule + reminders routers). 🟡
17. **First-review creation** — a topic enters the schedule when first studied (from micro-session or manual mark). 🟡
18. **Quiz-outcome seam (stub)** — Phase 7 quiz accuracy will drive `apply_review` automatically; define the interface now. 🟡
19. **Write `backend/tests/test_kb_revision.py`** — SM-2 math across grade sequences, due materialization, per-user isolation. 🟡
20. **Frontend:** "Due reviews" list on the dashboard (topic, due date, review button). 🟡


## Group 3 — Idea 53 🔴: Exam preparation mode (phrases 21–30)

21. **Add `POST /api/subjects-ai/{id}/exam-prep?exam_id=`** — generates a reverse-scheduled revision plan from the exam date (existing `Exam` model). 🔴
22. **Derive topic weights from the grading scheme** — the Phase 5 subject `parsed_json` (exam weight per unit) scales topic priority. 🔴
23. **Prioritize gaps + weak topics** — consume the Phase 3 gap list + Group 8 mastery scores (stub-safe when absent). 🔴
24. **Build the reverse schedule** — topics bucketed backwards from exam day, hardest/most-weighted earliest. 🔴
25. **Create daily tasks + reminders** — each exam day's plan materializes into the tasks + reminders routers. 🔴
26. **Add the countdown widget** — `GET /api/subjects-ai/{id}/exam-prep` returns `{exam_date, days_left, daily_tasks[]}`. 🔴
27. **Deterministic fallback** — reverse roadmap order, equal buckets, when `AI_ENABLED=false`. 🔴
28. **Write `backend/tests/test_kb_exam_prep.py`** — reverse scheduling, weight scaling, task materialization, countdown math. 🔴
29. **Frontend:** exam-prep page (countdown, per-day plan, start-session buttons). 🔴
30. **api.ts:** `endpoints.subjects.examPrep` (generate/get). 🔴


## Group 4 — Idea 54 🟡: Assignment intelligence (phrases 31–40)

31. **Extend the assignments router with `POST /api/assignments/{id}/plan`** — LLM subtask breakdown + per-subtask hour estimates (budget-capped). 🟡
32. **Create subtasks as tasks** — reuse the existing tasks router; each subtask gets a due date spaced backwards from the assignment deadline. 🟡
33. **Attach reminders** — via the reminders router, one reminder per subtask due date. 🟡
34. **Link assignments to covered topics** — match the assignment title/description to topics (normalized-name + concept overlap). 🟡
35. **Fetch hint chunks** — retrieve the top relevant vault chunks for the assignment (Phase 3 search) as "hints". 🟡
36. **Deterministic fallback** — equal-split subtasks + volume-based hour estimate when `AI_ENABLED=false`. 🟡
37. **Write `backend/tests/test_kb_assignment_intel.py`** — breakdown (mocked), subtask/task creation, hints, fallback. 🟡
38. **Frontend:** "Plan assignment" panel on the Assignments page (subtask list + hints + create). 🟡
39. **api.ts:** `endpoints.assignments.plan`. 🟡
40. **Keep the existing assignments flow untouched** — this is an additive endpoint on the current router. 🟡


## Group 5 — Idea 55 🔴: Lab tracking (phrases 41–50)

41. **Define the `Lab` model (`labs`)** — `id, user_id, subject_id (FK), title, lab_date, status (scheduled|done|missed), pre_requisite_topic_ids (JSON), notes, submission_url`. 🔴
42. **Register the model** in `models/__init__.py`. 🔴
43. **Create the labs router** — CRUD + `GET /api/subjects/{id}/labs` per-user. 🔴
44. **Lab prep: "read before lab"** — pulls the top relevant vault chunks for each pre-requisite topic (Phase 3 search) as prep reading. 🔴
45. **Completion logs a learning event** — `event_type=lab` into the Group 7 spine (mastery + progress). 🔴
46. **Link labs to assignments** — a lab's `submission_url` connects to the related assignment flow. 🔴
47. **Write `backend/tests/test_kb_labs.py`** — CRUD, prep-chunk retrieval (mocked search), event logging, per-user isolation. 🔴
48. **Frontend:** labs tab on the subject page (schedule, prep reading, mark-done). 🔴
49. **api.ts:** `endpoints.labs` (list/create/update/complete). 🔴
50. **Dashboard:** next-lab reminder card. 🔴


## Group 6 — Idea 56 🔴: Attendance monitoring (phrases 51–60)

51. **Define the `Attendance` model (`attendance`)** — `id, user_id, subject_id (FK), class_date, present (bool), note`, unique on `(user_id, subject_id, class_date)`. 🔴
52. **Register the model** in `models/__init__.py`. 🔴
53. **Create the attendance router** — `POST /api/attendance` (mark), `GET /api/subjects/{id}/attendance` (history). 🔴
54. **Build the quick-tap UI** — today's classes per subject with present/absent toggle (extend the schedule/class view). 🔴
55. **Compute analytics** — attendance % + streaks per subject (pure service functions, testable). 🔴
56. **Add falling-pattern alerts** — N consecutive misses (configurable) → notification via the notifications router. 🔴
57. **Write `backend/tests/test_kb_attendance.py`** — mark + unique constraint, streak/percent math, alert trigger, per-user isolation. 🔴
58. **Frontend:** attendance view per subject (calendar strip + % badge). 🔴
59. **api.ts:** `endpoints.attendance` (mark/list/analytics). 🔴
60. **Dashboard widget:** this-week attendance summary. 🔴


## Group 7 — Idea 57 🟡: Subject progress analytics (phrases 61–70)

61. **Define the `LearningEvent` model (`learning_events`)** — `id, user_id, topic_id (nullable FK), event_type (study|quiz|revision|lab|session|outcome), value (float, e.g. accuracy|minutes), created_at` — **the missing event spine**. 🟡
62. **Register the model** + index on `(user_id, topic_id, created_at)`. 🟡
63. **Log events from every Phase 6 surface** — reviews (Group 2), exam-prep tasks, labs (Group 5), sessions (Group 10), outcomes (Phase 5). 🟡
64. **Create the aggregation service** — topics mastered, hours logged, coverage %, quiz trend, roadmap completion vs. semester timeline. 🟡
65. **Add `GET /api/subjects-ai/{id}/progress`** — the per-subject dashboard payload. 🟡
66. **Add a weekly summary notification** — reuse the notifications router (topics mastered, hours, weak topics). 🟡
67. **Extend the existing analytics visuals** — StudyHeatmap-style charts fed by the aggregation service (extend, don't fork). 🟡
68. **Write `backend/tests/test_kb_progress.py`** — event aggregation, hours/masters math, weekly summary content, per-user isolation. 🟡
69. **Frontend:** subject progress dashboard (charts + semester-timeline overlay). 🟡
70. **api.ts:** `endpoints.subjects.progress`. 🟡


## Group 8 — Idea 58 🟡: Weak & strong topic detection (phrases 71–80)

71. **Create `app/services/kb/mastery.py`** — a Bayesian-ish mastery score per topic (0–1) from attempts, accuracy, and recency. 🟡
72. **Update mastery from each `learning_event`** — quiz accuracy and review grades (Groups 7 + 2) feed the score. 🟡
73. **Add confidence + thresholds** — classify weak / strong / unknown with a confidence bound; below-minimum data stays `unknown`. 🟡
74. **Add `GET /api/subjects-ai/weak-topics`** — the ranked weak list (per subject or global), with confidence. 🟡
75. **Expose mastery in topic lists** — `GET /api/subjects/{id}/topics` gains `mastery` + `classification` fields. 🟡
76. **Write `backend/tests/test_kb_mastery.py`** — score math, threshold classification, unknown handling, event-driven updates. 🟡
77. **Frontend:** mastery bars on topic cards + a weak-topics view. 🟡
78. **api.ts:** `endpoints.subjects.weakTopics` + topic `mastery` fields. 🟡
79. **Recompute-on-write, not on-read** — mastery updates when events are logged (keeps reads cheap). 🟡
80. **Feed exam prep (Idea 53) and next-action (Idea 59).** 🟡


## Group 9 — Idea 59 🔴: Recommended study order (phrases 81–90)

81. **Create `app/services/kb/next_action.py`** — the "what should I study right now" scoring engine. 🔴
82. **Define the scoring function** — readiness (prerequisites mastered from the topic DAG) + weakness (Group 8) + due reviews (Group 2) + exam proximity (Group 3). 🔴
83. **Add `KB_NEXT_ACTION_WEIGHTS` to `config.py`** — per-factor weights with a default sane balance. 🔴
84. **Block unready topics** — a topic whose prerequisites aren't mastered is never recommended; the missing prerequisite is recommended instead. 🔴
85. **Add `GET /api/subjects-ai/next-action`** — returns the top recommendation (or top-3), each with the reason breakdown. 🔴
86. **Surface on the dashboard + daily schedule** — a "Study now" card with one-tap action (opens the topic / starts a session). 🔴
87. **Write `backend/tests/test_kb_next_action.py`** — scoring math, blocking logic, tie-breaks, per-user isolation. 🔴
88. **Frontend:** "Study now" card on the dashboard + schedule. 🔴
89. **api.ts:** `endpoints.subjects.nextAction`. 🔴
90. **One-tap action wires to micro-sessions (Group 10).** 🔴


## Group 10 — Idea 60 🟡: Micro-session & focus integration (phrases 91–100)

91. **Create `app/services/kb/sessions.py`** — the session factory: `{topic, chunk_id, practice_task, duration_mins (15–45), source}`. 🟡
92. **Generate sessions from roadmap + next-action** — each recommendation maps to a concrete micro-session (topic + specific chunk + practice task). 🟡
93. **Define the `MicroSession` model (`micro_sessions`)** — `id, user_id, topic_id, chunk_id, practice_task, duration_mins, status (suggested|started|done), created_at, completed_at`. 🟡
94. **Register the model** in `models/__init__.py`. 🟡
95. **Add `POST /api/sessions/start`** — marks started and returns the session context for the focus flow. 🟡
96. **One-tap Pomodoro launch** — "start pomodoro" from a session creates a Pomodoro with the session context (reuse the pomodoro router). 🟡
97. **Completion logs a `learning_event`** — `event_type=session`, `value=minutes` → feeds mastery + progress (Groups 7–8). 🟡
98. **Daily-schedule integration** — propose sessions in free daily slots (reuse `daily_schedule` items). 🟡
99. **Write `backend/tests/test_kb_micro_session.py`** — factory output, start/complete lifecycle, pomodoro link (mocked), event logging. 🟡
100. **Docs:** mark Ideas 51–60 done in the master plan; add the Phase 6 runbook (schedulers, weights, event types). 🟡

---

## Definition of Done — Phase 6

- [ ] `StudyPlan` gains `user_id`; plans are topic-grounded (roadmap + availability) and versioned; existing study-plan UI keeps working.
- [ ] `RevisionSchedule` implements SM-2 updates; due reviews materialize into the daily schedule + reminders.
- [ ] Exam-prep mode reverse-schedules from the exam date with grading-scheme weights, gaps, and weak topics; countdown widget works.
- [ ] Assignment planning creates subtask tasks + reminders + hint chunks; assignments link to topics.
- [ ] Labs are tracked (CRUD, prep reading, submission link) and log learning events.
- [ ] Attendance is logged with streaks/percent analytics and falling-pattern alerts.
- [ ] `learning_events` exists and aggregates into per-subject progress (mastered, hours, coverage, trend); weekly summary notifies.
- [ ] Weak/strong topic classification with confidence is exposed and recomputed on writes.
- [ ] "Study now" returns a ranked, reason-backed recommendation that never suggests blocked topics.
- [ ] Micro-sessions generate from recommendations, launch Pomodoro one-tap, and log completion events.
- [ ] All LLM calls respect `KB_DAILY_GEN_LIMIT`; deterministic fallbacks work with `AI_ENABLED=false`; every query is user-scoped.

## Verification checklist

```bash
# Backend: Phase 6 test suite (run from backend/)
python -m pytest tests/test_kb_study_plan.py tests/test_kb_revision.py tests/test_kb_exam_prep.py \
  tests/test_kb_assignment_intel.py tests/test_kb_labs.py tests/test_kb_attendance.py \
  tests/test_kb_progress.py tests/test_kb_mastery.py tests/test_kb_next_action.py \
  tests/test_kb_micro_session.py -q

# Full regression (Phases 1–5 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. POST /api/subjects-ai/{id}/study-plan (after Phase 5 roadmap exists) → topic-grounded weeks
# 2. POST /api/topics/{id}/review {grade} → SM-2 due date moves; due list updates
# 3. POST /api/subjects-ai/{id}/exam-prep?exam_id= → countdown plan with daily tasks
# 4. Mark attendance + a lab done → GET /api/subjects-ai/{id}/progress reflects them
# 5. GET /api/subjects-ai/next-action → one ranked recommendation; start session → pomodoro

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phase 7 is out of scope:** the AI tutor, practice questions, mock tests, and grading (Ideas 61–70) — but the `learning_events` spine and mastery seams built here are exactly what Phase 7 will feed (quiz accuracy → mastery → review scheduling).
- **`learning_events` doesn't exist today** — creating it (Group 7, phrase 61) is the single most load-bearing change in this phase; everything else logs into it.
- **`StudyPlan` has no `user_id`** — adding it via `COLUMN_MIGRATIONS` (phrase 1) is a prerequisite for any per-user planning.
- **Extend, don't fork:** study plans, assignments, daily schedule, reminders, pomodoro, and analytics keep their existing tables/routers; new KB tables reference them.
- **Per-user scoping is non-negotiable** — every new table and query filters `user_id`; ownership tests mirror `test_ownership.py`.

