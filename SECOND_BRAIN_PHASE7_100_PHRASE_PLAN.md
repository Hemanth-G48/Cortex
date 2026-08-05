# Second Brain Integration — Phase 7 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 7 — AI Tutor & Assessment (Ideas 61–70)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1–6 plans
(`SECOND_BRAIN_PHASE{1,2,3,4,5,6}_100_PHRASE_PLAN.md`).

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (6): Idea 62 (doubt solving), 64 (mock tests), 65 (interview prep), 67 (adaptive difficulty), 68 (mistake analysis), 70 (skill mapping)
- 🟡 partial / extends existing code (4): Idea 61 (the existing `AIChat`), 63 (the quiz machinery), 66 (`grade-answer`), 69 (existing XP/quest/character services)

**Prerequisites: Phases 3, 5, and 6 must be complete** — the tutor is RAG over the Phase 3 search
service; questions/mocks use Phase 5 topics + grading scheme; mastery, `learning_events`, and
`revision_schedule` from Phase 6 power adaptivity, mistake analysis, and capture XP.

**Scope:** A RAG-grounded tutor with mandatory citations, doubt solving, practice question banks,
mock tests, interview mode, advanced answer grading, adaptive difficulty, explain-my-mistake
analysis, knowledge-capture/revision XP, and skill mapping. **Personalization and long-term memory
are Phase 8 and out of scope** — but the `user_memory` seam (Idea 79) is stubbed here.

**The flagship gap this phase closes:** today's `/api/ai/chat` injects only assignments/courses
into the prompt — **zero retrieval from the vault**. Idea 61 is the single highest-value change in
the whole roadmap.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 7 reuses |
|---|---|---|
| Non-RAG chat | `backend/app/routers/ai.py` (`POST /api/ai/chat`) + `local_chat_response` fallback + `AIChat.tsx` | The shell to upgrade: keep the fallback, add retrieval + citations |
| Answer grading | `backend/app/routers/ai.py` (`POST /api/ai/grade-answer`) + `demo_grade_answer` | The grading base for Ideas 65–66 (extend, keep request shape) |
| Quiz + XP precedent | `QuizAttempt` model, `quiz_stats.grant_quiz_xp` (once-per-quiz passing XP) | Question banks + the "reward once, no double-count" pattern |
| Practice surfaces | quizzes router + `useQuiz.ts` hook | Practice/mock runners reuse these flows |
| Phase 3 search | `app/services/kb/search.py` (`KbSearcher`, hybrid) | The retrieval backbone for the tutor (Idea 61) |
| Phase 5 output | `topics`, subject `parsed_json` (grading scheme) | Question banks + mock-test paper structure |
| Phase 6 output | `mastery.py`, `learning_events`, `revision_schedule` | Adaptive difficulty, mistake→revision tasks, XP |
| Budget guard | `KB_DAILY_GEN_LIMIT` (Phase 4) | Caps every tutor/grade/question generation call |

**File conventions:** services → `backend/app/services/kb/{tutor,questions,mocks,skills}.py`;
new models → `backend/app/models/kb/*.py` (`PracticeQuestion`, `MockTest`, `MockTestAttempt`,
`UserSkill`); routers → `backend/app/routers/kb_tutor.py` (+ `kb_practice.py`); tests →
`backend/tests/test_kb_*.py`. Register every new router in `main.py`, every model in
`models/__init__.py`.

**Two hard rules for Phase 7:**
- **Rule A — Tutor answers must cite sources:** every generated answer carries `[source: path]` markers; empty retrieval → \"not found in your Second Brain\" + capture prompt, never hallucination.
- **Rule B — Budgets + scoping:** all LLM calls respect `KB_DAILY_GEN_LIMIT` and work via deterministic fallbacks when `AI_ENABLED=false`; every new table/query is user-scoped.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---

## Group 1 — Idea 61 🟡: RAG-grounded AI tutor (phrases 1–10)

1. **Create `app/services/kb/tutor.py`** — the RAG orchestrator: query → retrieve (Phase 3 `KbSearcher`, hybrid) → assemble context → generate → verify citations. 🟡
2. **Add `POST /api/kb/tutor/chat`** — `{message, session_id?}` per-user; the vault-aware counterpart of `/api/ai/chat`. 🟡
3. **Retrieve the top-K chunks** (hybrid mode) for every user message — no more zero-retrieval prompts. 🟡
4. **Assemble the system prompt** — retrieved chunks as numbered context blocks + `[source: path]` markers + a strict "cite or say you don't know" instruction. 🟡
5. **Wire the `user_memory` seam (stub)** — Phase 8 (Idea 79) strengths/weaknesses injected here when present; omit gracefully otherwise. 🟡
6. **Empty-retrieval path** — response "I don't have this in your Second Brain" + a capture prompt (no hallucination). 🟡
7. **Post-generation citation check** — answers missing `[source: …]` markers are regenerated once (budget-aware) or flagged. 🟡
8. **Add rolling session history** — `tutor_sessions`/`tutor_messages` (or reuse a chat log table) capped to a rolling window. 🟡
9. **Budget-cap + fallback** — respect `KB_DAILY_GEN_LIMIT`; fall back to the existing `local_chat_response` when `AI_ENABLED=false`. 🟡
10. **Frontend:** extend `AIChat.tsx` to call the tutor endpoint + render source chips under each answer. 🟡


## Group 2 — Idea 62 🔴: AI doubt solving (phrases 11–20)

11. **Add `POST /api/kb/tutor/doubt`** — `{question, step_where_stuck}` per-user, routed through the tutor's RAG pipeline. 🔴
12. **Find candidate blocking concepts** — intersect retrieved chunks with the topic DAG (`DEPENDS_ON`, Phase 5/6) + `kb_concepts`. 🔴
13. **Explain the gap first** — the blocking concept's definition + the relevant note re-explains *before* re-walking the problem. 🔴
14. **Re-walk the original problem** — step-by-step from the gap, citing chunks per step. 🔴
15. **Log to `learning_events`** — `event_type=doubt` on the resolved topic (feeds mastery/progress). 🔴
16. **Offer follow-ups** — "review the prerequisite" + "try a practice question" actions. 🔴
17. **Deterministic fallback** — retrieve related chunks + list the blocking concepts (no LLM) when `AI_ENABLED=false`. 🔴
18. **Write `backend/tests/test_kb_doubt.py`** — blocking-concept detection (mocked), gap-first response shape, event logging, fallback. 🔴
19. **Frontend:** doubt-ask input in the tutor panel ("I'm stuck on…"). 🔴
20. **api.ts:** `endpoints.tutor.doubt`. 🔴


## Group 3 — Idea 63 🟡: AI-generated practice questions (phrases 21–30)

21. **Define the `PracticeQuestion` model (`practice_questions`)** — `id, user_id, topic_id (FK), question, options (JSON), answer, explanation, bloom_level, difficulty, source_chunk_ids (JSON), status (pending|approved|rejected), question_hash (unique per user)`. 🟡
22. **Register the model** in `models/__init__.py`. 🟡
23. **Create `app/services/kb/questions.py`** — topic context → `generate_json` question-bank schema (`{questions: [{q, options, answer, explanation, bloom_level}]}`), budget-capped. 🟡
24. **Add `POST /api/kb/practice/generate`** — `{topic_id, count, difficulty}` returns candidates for review (nothing auto-committed). 🟡
25. **Dedupe by `question_hash`** — normalized question text; duplicates skipped. 🟡
26. **Add approve/reject endpoints** — approved questions enter the reusable bank (`status=approved`). 🟡
27. **Deterministic fallback** — template questions per Bloom level from the topic's outcomes when `AI_ENABLED=false`. 🟡
28. **Write `backend/tests/test_kb_practice_questions.py`** — generation (mocked), hash dedupe, review lifecycle, fallback. 🟡
29. **Frontend:** practice bank per topic (list, generate, approve/reject). 🟡
30. **api.ts:** `endpoints.practiceQuestions` (generate/list/approve). 🟡


## Group 4 — Idea 64 🔴: Mock tests & exam simulations (phrases 31–40)

31. **Define `MockTest` (`mock_tests`)** — `id, user_id, subject_id (FK), title, structure_json, duration_mins, status (draft|active|completed), created_at`. 🔴
32. **Define `MockTestAttempt` (`mock_test_attempts`)** — `id, user_id, mock_test_id, started_at, finished_at, answers (JSON), score, total, per_topic (JSON)`. 🔴
33. **Register both models** in `models/__init__.py`. 🔴
34. **Build the paper generator** — section structure from the Phase 5 grading scheme (`parsed_json` weights); question counts by topic weight. 🔴
35. **Assemble from the approved bank first**, generate missing questions on demand (budget-capped). 🔴
36. **Add the timed runner** — `POST /api/kb/mocks/{id}/start` + `…/submit` with a server-side duration check. 🔴
37. **Results analytics** — per-section and per-topic accuracy breakdown in the submit response. 🔴
38. **History view** — `GET /api/kb/mocks` + `GET /api/kb/mocks/{id}/attempts`. 🔴
39. **Write `backend/tests/test_kb_mock_tests.py`** — paper assembly from weights, timer enforcement, scoring + per-topic breakdown, history. 🔴
40. **Frontend:** mock-test runner (timer, sections) + results + history. 🔴


## Group 5 — Idea 65 🔴: Interview preparation (phrases 41–50)

41. **Add `POST /api/kb/interview/start`** — `{skill, level}` per-user; the skill comes from the Group 10 map (stub interface until Idea 70 lands). 🔴
42. **Generate interview questions** — conceptual + problem-style from the skill's topics (via the question generator, budget-capped). 🔴
43. **Answer grading via the existing `grade-answer` service** — extend it (Group 6) rather than build a new grader. 🔴
44. **Feedback with cited corrections** — wrong/missed points link back to the vault chunks that cover them. 🔴
45. **Define the `InterviewSession` model (`interview_sessions`)** — `id, user_id, skill, level, questions (JSON), answers (JSON), scores, status, created_at`. 🔴
46. **Register the model** in `models/__init__.py`. 🔴
47. **Aggregate the session score** into the skill-level computation (Idea 70). 🔴
48. **Write `backend/tests/test_kb_interview.py`** — question generation, grading call-through (mocked), feedback citations, session persistence. 🔴
49. **Frontend:** interview-mode UI — question → answer → scored feedback loop. 🔴
50. **api.ts:** `endpoints.interview` (start/answer/finish). 🔴


## Group 6 — Idea 66 🟡: Answer grading & feedback — advanced (phrases 51–60)

51. **Extend the `grade-answer` endpoint with an advanced mode** — `{mode: "advanced"}` returning partial credit + structured feedback (keep the existing request shape backward-compatible). 🟡
52. **Build the rubric prompt** — Bloom level + key points derived from the topic's chunks (retrieve via Phase 3 search). 🟡
53. **Structured output via `generate_json`** — `{score (0–100), strengths[], misconceptions[], action_items[]}`. 🟡
54. **Score partial credit** — key-point coverage drives the score, not binary right/wrong. 🟡
55. **Persist grade results to `learning_events`** — `event_type=grade, value=score` (feeds mastery + progress). 🟡
56. **Extend the deterministic fallback** — keyword-overlap `demo_grade_answer` gains partial scoring + canned strengths/next-steps. 🟡
57. **Write `backend/tests/test_kb_grading.py`** — rubric assembly, partial-credit math, structured shape, event logging, fallback. 🟡
58. **Frontend:** grading feedback panel — score, strengths, misconceptions, action items (on practice + interview). 🟡
59. **api.ts:** extend `endpoints.ai.gradeAnswer` with the advanced mode. 🟡
60. **Budget-cap grading calls** against `KB_DAILY_GEN_LIMIT`. 🟡


## Group 7 — Idea 67 🔴: Adaptive question difficulty (phrases 61–70)

61. **Create the difficulty-selection service** (`app/services/kb/adaptive.py`) — mastery (Phase 6 Group 8) gates the next question's difficulty tier. 🔴
62. **Track correctness per difficulty** — per (user, topic): attempts and accuracy by tier, from practice/mock answers + `learning_events`. 🔴
63. **Implement the IRT-lite update rule** — simple accuracy-threshold adjustment after each answer (raise/lower next tier). 🔴
64. **Add `POST /api/kb/practice/session`** — `{topic_id}` opens an adaptive queue; each response includes `{question, difficulty, reason}`. 🔴
65. **Add `POST /api/kb/practice/answer`** — records the answer, updates adaptive state + mastery (event `event_type=practice`). 🔴
66. **Persist adaptive state** — per (user, topic) row (new small table or fields on the topic mastery row). 🔴
67. **Tier bounds** — clamp difficulty to available tiers; fall back to medium when few questions exist. 🔴
68. **Write `backend/tests/test_kb_adaptive.py`** — mastery-gated selection, IRT-lite updates, state persistence, clamping. 🔴
69. **Frontend:** adaptive practice mode — difficulty badge, streak of correct, session end summary. 🔴
70. **api.ts:** `endpoints.practice.session` + `.answer`. 🔴


## Group 8 — Idea 68 🔴: Explain-my-mistake analysis (phrases 71–80)

71. **Add `POST /api/kb/practice/mistake-analysis`** — `{question_id, student_answer}`; compares the student answer against the model solution. 🔴
72. **Pinpoint the divergence** — which key point / step the student's reasoning missed (LLM, budget-capped; fallback = keyword diff). 🔴
73. **Recommend the note to re-read** — retrieve the most relevant vault chunk for the missed key point. 🔴
74. **Recommend the concept to review** — the blocking `kb_concepts` entry with its definition. 🔴
75. **Create a revision task** — insert into `revision_schedule` (Phase 6 Group 2) so the mistake becomes scheduled review. 🔴
76. **Log the analysis** — `learning_events` `event_type=mistake` + the generated walkthrough stored (new `mistake_analyses` table or JSON event). 🔴
77. **Deterministic fallback** — point to the correct answer + the relevant chunk, no LLM walkthrough. 🔴
78. **Write `backend/tests/test_kb_mistakes.py`** — divergence detection, chunk/concept recommendations, revision-task creation, fallback. 🔴
79. **Frontend:** mistake-walkthrough panel after any wrong answer (practice + mocks). 🔴
80. **api.ts:** `endpoints.practice.mistakeAnalysis`. 🔴


## Group 9 — Idea 69 🟡: Knowledge capture & revision XP (phrases 81–90)

81. **Emit XP on revision completion** — when a `revision_schedule` review is graded, award `KB_XP_REVISION`. 🟡
82. **Emit XP on daily-note creation** — a new `doc_date` document (Phase 4 Idea 35) awards `KB_XP_DAILY_NOTE`. 🟡
83. **Emit XP on brain-dump filing** — quick-filing a draft (Phase 4 Idea 40) awards `KB_XP_DUMP_FILED`. 🟡
84. **Reuse the existing gamification services** — `habit_xp`, quests, and character XP (mirror `grant_quiz_xp`'s once-per-event guard); **no new gamification system**. 🟡
85. **Add the `KB_XP_REWARDS` config block** — `{revision, daily_note, dump_filed}` amounts with zero-defaults for determinism. 🟡
86. **Guard against double-counting** — each event type grants once per unique trigger (revision id / document id), mirroring the once-per-quiz rule. 🟡
87. **Surface in existing UI** — XP toasts + habit-tracker/quest-centre entries (extend existing components). 🟡
88. **Write `backend/tests/test_kb_capture_xp.py`** — each trigger grants once, no double-count, disabled-by-default config respected. 🟡
89. **Include in the weekly summary** — Phase 6 progress analytics add "capture XP earned" to the weekly notification. 🟡
90. **api.ts:** reuse existing reward endpoints; no new surface needed. 🟡


## Group 10 — Idea 70 🔴: Skill mapping (phrases 91–100)

91. **Seed a versioned skill taxonomy** — CS/ML/DSA/domain skills JSON (e.g. `backend/app/data/skills.json`) with per-skill topic keywords. 🔴
92. **Define the `UserSkill` model (`user_skills`)** — `id, user_id, skill_id, level (1–5), mastery (0–1), updated_at`, unique `(user_id, skill_id)`. 🔴
93. **Register the model** in `models/__init__.py`. 🔴
94. **LLM-mapping topics/outcomes → skills** — `generate_json` per subject (budget-capped); rule-based keyword fallback. 🔴
95. **Derive levels from mastery** — Phase 6 `mastery.py` scores per contributing topic aggregate into `UserSkill.level`. 🔴
96. **Incorporate interview scores** — Group 5 session scores adjust the relevant skill level. 🔴
97. **Add `GET /api/kb/skills`** — the profile view (skill, level, mastery, contributing topics). 🔴
98. **Add an export endpoint** — JSON/markdown skills summary (portfolio/resume use). 🔴
99. **Write `backend/tests/test_kb_skills.py`** — mapping (mocked + fallback), level math, interview-score effect, export. 🔴
100. **Docs:** mark Ideas 61–70 done in the master plan; add the Phase 7 runbook (tutor citation rules, budgets, question workflow). 🔴

---

## Definition of Done — Phase 7

- [ ] The tutor answers from the vault via hybrid retrieval, always citing `[source: path]`, and refuses (with a capture prompt) when retrieval is empty.
- [ ] Doubt-solving identifies the blocking concept, explains the gap first, re-walks the problem, and logs a learning event.
- [ ] Practice questions generate into a reviewable bank (hash-deduped, Bloom-tagged, difficulty-tiered) with worked solutions.
- [ ] Mock tests assemble from the grading scheme + question bank, run with a timer, and return per-topic analytics + history.
- [ ] Interview mode generates questions, grades answers via the extended grader, and gives cited feedback.
- [ ] Advanced grading returns partial credit + strengths/misconceptions/action items and persists to `learning_events`.
- [ ] Adaptive practice picks difficulty from mastery via the IRT-lite rule and persists per-(user, topic) state.
- [ ] Wrong answers produce a mistake walkthrough (divergence, note to re-read, concept to review) and create a revision task.
- [ ] Capture/revision XP flows through existing habit/quest/character services with no double-counting.
- [ ] Skill mapping produces a mastery-derived skill profile with export.
- [ ] All LLM calls respect `KB_DAILY_GEN_LIMIT`; deterministic fallbacks work with `AI_ENABLED=false`; every query is user-scoped.

## Verification checklist

```bash
# Backend: Phase 7 test suite (run from backend/)
python -m pytest tests/test_kb_tutor.py tests/test_kb_doubt.py tests/test_kb_practice_questions.py \
  tests/test_kb_mock_tests.py tests/test_kb_interview.py tests/test_kb_grading.py \
  tests/test_kb_adaptive.py tests/test_kb_mistakes.py tests/test_kb_capture_xp.py \
  tests/test_kb_skills.py -q

# Full regression (Phases 1–6 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. POST /api/kb/tutor/chat with a question → cited answer; try something absent → capture prompt
# 2. Generate practice questions for a topic → approve → bank grows (dedupe works)
# 3. POST /api/kb/mocks/.../start + submit → per-topic analytics
# 4. Answer wrong → mistake analysis creates a revision task in the due list
# 5. GET /api/kb/skills → mastery-derived levels; export works

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phase 8 is out of scope:** personalization and long-term learning memory (Ideas 71–80) — the tutor's `user_memory` seam (Idea 79) is stubbed and must degrade gracefully.
- **Citation discipline is the core rule** — retrieval-grounded answers only; empty retrieval means "not in your Second Brain", never invention.
- **Reuse over rebuild:** the tutor extends `AIChat`; grading extends `grade-answer`; question banks ride the quiz/`QuizAttempt` patterns; XP reuses `habit_xp`/quests/characters — no parallel systems.
- **Budget caps are mandatory:** tutor turns, doubt solves, question generation, grading, and interview feedback all count against `KB_DAILY_GEN_LIMIT`.
- **Per-user scoping is non-negotiable** — every bank, mock, session, skill row, and event filters `user_id`; ownership tests mirror `test_ownership.py`.

