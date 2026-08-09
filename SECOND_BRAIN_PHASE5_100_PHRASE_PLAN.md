# Second Brain Integration — Phase 5 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 5 — Subject Management Core (Ideas 41–50)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1–4 plans
(`SECOND_BRAIN_PHASE{1,2,3,4}_100_PHRASE_PLAN.md`).

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (4): Idea 43 (semester detection), 46 (topic dependency graph), 48 (difficulty), 50 (learning outcomes)
- 🟡 partial / extends existing code (6): Ideas 41, 42, 44, 45, 47, 49 extend the existing curriculum models/router, the shallow `/api/ai/syllabus` endpoint, and the `SyllabusImport` page

**Implementation status: ✅ COMPLETE** — backend (10/10 test files, 83/83 tests) and frontend all landed.
Backend: `SubjectProfile`/`Topic`/`Roadmap`/`TopicDependency` models, `subjects.py` (propose/confirm/reject
+ semester detection), `syllabus.py` (chunked parse + merge + fallback), `topics.py` (extraction,
synonym folding, Bloom, difficulty/time, outcomes→goals), `units.py` (name + embedding matching),
`dependencies.py` (cycle-safe topic DAG, Kahn topo order), `roadmap.py` (versioned weekly plans),
`budget.py`-capped LLM calls with deterministic fallbacks, and the `/api/subjects` router.
Frontend: `SyllabusImport` reworked to the Phase 5 proposal flow (parsed preview + review step),
`Subjects` page (semester + status facets), `SubjectWorkspace` page (unit match table, topic review
grid with difficulty/time/outcomes, dependency editor, roadmap view), and `endpoints.subjects`
(import/proposals/topics/matchUnits/dependencies/roadmap/timeBudget/outcomes/pacing) in `api.ts`.

**Prerequisites: Phases 1–4 must be complete** — this phase consumes `kb_documents`/`kb_chunks`
(syllabus ingestion), `kb_concepts` (topic canonicalization), `kb_edges` (`DEPENDS_ON`), the
Phase 2 embeddings (unit matching), and the Phase 4 budget guard (`KB_DAILY_GEN_LIMIT`). It writes
into the existing `curriculum_subjects` / `curriculum_units` / `materials` tables.

**Scope:** Automatic subject creation from syllabi, deep syllabus parsing, semester/term detection,
topic extraction + normalization, unit/lecture segmentation, topic dependency graphs, learning
roadmaps, difficulty and time estimation, and learning-outcome tracking. **Study planning/execution
and the AI tutor are Phases 6–7 and out of scope** — the topic graph and roadmaps built here are
their input. Idea 28 (Phase 3) consumes this phase's topic→coverage mapping.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 5 reuses |
|---|---|---|
| Curriculum models | `backend/app/models/curriculum_subject.py`, `curriculum_unit.py`, `curriculum_course.py` | The write-targets: `CurriculumSubject` (name/code/semester/credits), `CurriculumUnit` (unit_number/name) |
| Curriculum router | `backend/app/routers/curriculum.py` | Existing CRUD + `main.py` registration; new endpoints extend it or a new `subjects.py` |
| Shallow syllabus endpoint | `backend/app/routers/ai.py` (`POST /api/ai/syllabus`) | Currently extracts **assignments + due dates only** with `demo_syllabus` fallback — Idea 42 replaces/augments it |
| Syllabus import UI | `frontend/src/pages/` `SyllabusImport` (from the SyllabusAI work) | The review flow to extend for proposals + parsed preview |
| Text extraction + materials | `backend/app/services/text_extractor.py`, `Material` model | Syllabus PDF/DOCX/MD ingestion path |
| Concept canonicalization | Phase 2 (Group 5) — `kb_concepts` | Topic synonym folding (Idea 44) |
| Typed edges | Phase 2 (Group 6) — `kb_edges` (`DEPENDS_ON`, `MENTIONS`) | Topic dependency graph (Idea 46) |
| Embeddings + store | Phase 2 (Groups 1–2) | Unit↔syllabus matching by cosine similarity (Idea 45) |
| Budget guard | Phase 4 — `KB_DAILY_GEN_LIMIT` | Caps every LLM parse/extraction call |
| Goals model + router | `backend/app/models/` Goals + goals endpoints | Learning-outcome linking (Idea 50) |

**File conventions:** services → `backend/app/services/kb/subjects.py` (+ `syllabus.py`, `roadmap.py`);
new models → `backend/app/models/kb/*.py` (`SubjectProfile`, `Topic`, `Roadmap`); routers →
`backend/app/routers/kb_subjects.py`; tests → `backend/tests/test_kb_*.py`. Register every new
router in `main.py` and every model in `models/__init__.py`; column adds on *existing* tables go
through `COLUMN_MIGRATIONS` in `database.py`.

**Cost rule for all of Phase 5:** every LLM path (parse, extract, dependency seed, roadmap) is
budget-capped by `KB_DAILY_GEN_LIMIT` and must keep working via deterministic fallbacks when
`AI_ENABLED=false`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---


---

## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))

Every idea in Phase 5 (Subject Management Core) has reusable components in the cloned reference repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.

- **Idea 41 — Automatic subject creation:** syllabo · study-planner-agent (models.py Subject)
- **Idea 42 — Syllabus parsing:** syllabus-agent (utils.py extract_topics_from_text) · syllabo · PAIDEIA · study-planner-agent · Syllabify · EduAI (syllabus app)
- **Idea 43 — Semester & calendar detection:** syllabo · Student_Study_Planner · EduAI
- **Idea 44 — Topic extraction & normalization:** syllabus-agent · PAIDEIA · syllabo · StudyWise
- **Idea 45 — Unit & lecture segmentation:** PAIDEIA · syllabo · EduAI
- **Idea 46 — Topic dependency graph:** PAIDEIA (learning graph) · mind-mentor (knowledge graph) · knowledge-nexus (Neo4j) · obsidian-wiki
- **Idea 47 — Learning roadmap generation:** Multi-Agent-Study-Assistant (roadmaps) · study-planner-agent (generate_plan) · syllabo · StudyWise · PAIDEIA · OrbitOS
- **Idea 48 — Difficulty estimation:** syllabo (difficulty_analyzer.py) · studybuddy-ai · syllabus-agent
- **Idea 49 — Time estimation:** syllabus-agent (build_study_plan) · study-planner-agent · syllabo
- **Idea 50 — Learning-outcome extraction:** syllabo · PAIDEIA · syllabus-agent

> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines (khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, dendron. Repos without a license file are STUDY only.

## Group 1 — Idea 41 🟡: Automatic subject creation (phrases 1–10)

1. **Define the `SubjectProfile` model (`subject_profiles`)** — `id, user_id, curriculum_subject_id (nullable), raw_syllabus_text, parsed_json, semester, status (proposed|confirmed|rejected), created_at, updated_at`. 🟡
2. **Register `SubjectProfile` in `models/__init__.py`**; new table via `create_all`. 🟡
3. **Create `app/services/kb/subjects.py`** — the subject service: propose, confirm, reject, and CRUD helpers. 🟡
4. **Add `POST /api/subjects/import`** — accepts syllabus text or file (reuse `text_extractor`), runs Idea 42 parsing, and returns a *proposed* profile (no writes to curriculum tables yet). 🟡
5. **Draft the subject profile via `generate_json`** — strict schema: `{name, code, credits, units: [{title, topics}]}`; deterministic fallback from the fallback syllabus parser. 🟡
6. **Add `GET /api/subjects/proposals`** — list pending proposals per user for the review screen. 🟡
7. **Add `POST /api/subjects/proposals/{id}/confirm`** — writes `curriculum_subject` + `curriculum_unit` rows (existing tables) and links the profile; `reject` marks it rejected. 🟡
8. **Write `backend/tests/test_kb_subject_auto.py`** — propose, confirm (writes curriculum rows), reject, per-user isolation. 🟡
9. **Frontend:** extend the `SyllabusImport` page with a review step — edit name/code/credits, confirm/reject, before any DB write. 🟡 ✅ `frontend/src/pages/SyllabusImport.tsx` (review form + confirm/reject)
10. **api.ts:** `endpoints.subjects.import` + `endpoints.subjects.proposals` (list/confirm/reject). 🟡 ✅ `endpoints.subjects` in `frontend/src/services/api.ts`


## Group 2 — Idea 42 🟡: Syllabus parsing (phrases 11–20)

11. **Create `app/services/kb/syllabus.py`** — the parse pipeline: extract → chunk → LLM parse → store; supersedes the shallow `/api/ai/syllabus` assignments-only logic. 🟡
12. **Define the strict parse schema** — `{title, semester, credits, grading, units: [{title, description, topics: [{name, outcomes}], deadlines}]}` via `generate_json`. 🟡
13. **Ingest syllabus files** — PDF/DOCX/MD through `text_extractor` (Phase 1); cap at `MAX_EXTRACTED_CHARS`. 🟡
14. **Chunk long syllabi** — parse per-chunk then merge unit/topic lists (reuse the Phase 1 chunker), deduping merged items. 🟡
15. **Build the deterministic fallback parser** — extend `ai_fallback.demo_syllabus` to also emit units/topics from heading + numbered-line heuristics. 🟡
16. **Store raw + parsed** — `raw_syllabus_text` + `parsed_json` on `subject_profiles`; re-parse on content change (hash check). 🟡
17. **Add `GET /api/subjects/{id}/profile`** — returns raw text + parsed JSON + parse status per user. 🟡
18. **Budget-cap every parse call** against `KB_DAILY_GEN_LIMIT`; clear 429-style message when exhausted. 🟡
19. **Write `backend/tests/test_kb_syllabus_parse.py`** — mocked LLM happy path, fallback path, PDF ingestion, chunk-merge, schema validation. 🟡
20. **Frontend:** parsed-syllabus preview (units + topics) on the import flow before confirmation. 🟡 ✅ `SyllabusImport.tsx` (units→topics preview cards)


## Group 3 — Idea 43 🔴: Semester & calendar detection (phrases 21–30)

21. **Add a `semester` field on `SubjectProfile`** (string, e.g. "Fall 2026") and a `semester` column on `curriculum_units` via `COLUMN_MIGRATIONS` (Phase 1 already has `doc_date` on documents for cross-referencing). 🔴
22. **Implement detection heuristics** — keyword scan ("Spring/Fall/Summer/Winter", "Semester", "Term", year tokens) over syllabus text + filename. 🔴
23. **Cross-check with existing dates** — assignment/exam due dates (existing models) imply the term; pick the majority-matching term. 🔴
24. **Default to the current term** when the syllabus is silent — use server date (existing `daily_schedule`/app dates). 🔴
25. **Write the detected term** onto the profile + all linked units when confirmed. 🔴
26. **Add `GET /api/subjects?semester=` filtering** — semester facet across subjects/units. 🔴
27. **Write `backend/tests/test_kb_semester.py`** — keyword cases, date cross-check, silent-default, per-user isolation. 🔴
28. **Frontend:** semester facet in the subject list + display on subject/unit cards. 🔴 ✅ `frontend/src/pages/Subjects.tsx` (facet chips + per-card semester badge)
29. **api.ts:** `subjects.list({semester})` filter param. 🔴 ✅ `endpoints.subjects.list({semester, status})`
30. **Expose the term to roadmap bucketing** — Group 7 reads `semester` start/end dates for deadline-aware planning. 🔴


## Group 4 — Idea 44 🟡: Topic extraction & normalization (phrases 31–40)

31. **Define the `Topic` model (`topics`)** — `id, user_id, subject_id (FK), unit_id (nullable FK), name, normalized_name, bloom_level, difficulty (E|M|H), first_pass_mins, review_mins, mastery_mins, outcomes (JSON), status (pending|confirmed|merged|rejected), created_at`. 🟡
32. **Register `Topic` in `models/__init__.py`**; unique constraint on `(user_id, subject_id, normalized_name)`. 🟡
33. **Extract topics from parsed syllabus units** via `generate_json` (budget-capped, strict `{name, bloom_level, outcomes}` schema). 🟡
34. **Normalize topic names** — lowercase/trim + synonym folding through `kb_concepts` canonicalization (reuse Phase 2 Group 5 helpers). 🟡
35. **Maintain a per-subject topic thesaurus** — `topic_aliases` mapping variant names → canonical topic (new small table or reuse `kb_tags` pattern). 🟡
36. **Add a human review grid** — `GET /api/subjects/{id}/topics?status=pending` + confirm/merge/reject endpoints. 🟡
37. **Tag Bloom levels** — LLM assignment with rule-based fallback on keywords ("analyze", "design", "recall"). 🟡
38. **Write `backend/tests/test_kb_topics.py`** — extraction, synonym folding, review lifecycle, Bloom fallback, dedupe by normalized name. 🟡
39. **Frontend:** topic review grid (confirm/merge/reject chips) + topic list per subject. 🟡 ✅ `frontend/src/pages/SubjectWorkspace.tsx` (Topics tab)
40. **api.ts:** `endpoints.subjects.topics` (list/confirm/merge/reject). 🟡 ✅ `endpoints.subjects.topics`


## Group 5 — Idea 45 🟡: Unit & lecture segmentation (phrases 41–50)

41. **Add `GET /api/subjects/{id}/match-units`** — compares parsed syllabus units against existing `curriculum_units` for the subject. 🟡
42. **Match by name/code first** — normalized string similarity (token overlap / Levenshtein) on unit titles. 🟡
43. **Fall back to embedding matching** — cosine similarity on unit name + description via the Phase 2 embeddings service (skip when `AI_ENABLED=false`). 🟡
44. **Return candidate matches with scores** — `{parsed_unit, candidate_unit_id|null, score}` for a confirmation UI. 🟡
45. **Add `POST /api/subjects/{id}/match-units/confirm`** — accepts the mapping; links each parsed unit → `curriculum_unit.id`. 🟡
46. **Assign topics to units** — on confirm, set `Topic.unit_id` from the mapping (topics without a unit stay `unit_id=NULL`). 🟡
47. **Flag unmatched units** — returned as "create new" suggestions the user can accept or skip. 🟡
48. **Write `backend/tests/test_kb_unit_match.py`** — name matching, embedding fallback (mocked), confirm writes links, unmatched flow. 🟡
49. **Frontend:** unit-match confirmation step in the import flow (side-by-side table). 🟡 ✅ `SubjectWorkspace.tsx` (Overview tab → Match Units table)
50. **api.ts:** `endpoints.subjects.matchUnits` + `.confirm`. 🟡 ✅ `endpoints.subjects.matchUnits`


## Group 6 — Idea 46 🔴: Topic dependency graph (phrases 51–60)

51. **Extend the `kb_edges` model for topic targets** — `target_type=topic` support so `DEPENDS_ON` links topics (Phase 2 Group 6 edge model). 🔴
52. **Seed dependencies from syllabus analysis** — LLM pass over parsed units requesting `{topic_a, depends_on: [topic_b]}` (budget-capped). 🔴
53. **Refine with concept prerequisites** — reuse concept-level `DEPENDS_ON` edges from Phase 2; topic mentions of a concept inherit its dependencies. 🔴
54. **Add a mastery-adjustment seam (stub)** — performance data (Phase 6/7 quiz results) can later re-weight edges; define the interface now. 🔴
55. **Detect cycles** — topological check on every insert; reject edges that create a cycle with a 409. 🔴
56. **Add `GET /api/subjects/{id}/dependencies`** — the subject's topic DAG (nodes + edges) for the UI and roadmap engine. 🔴
57. **Add manual edge endpoints** — `POST /api/topics/dependencies` (add `DEPENDS_ON`, `provenance=manual`) and delete. 🔴
58. **Write `backend/tests/test_kb_topic_deps.py`** — LLM seed, concept inheritance, cycle rejection, manual add/remove. 🔴
59. **Frontend:** dependency editor on the subject page — simple DAG list view with add/remove controls. 🔴 ✅ `SubjectWorkspace.tsx` (Dependencies tab)
60. **Expose topological-order helpers** in the service — reused by roadmap generation (Group 7). 🔴


## Group 7 — Idea 47 🟡: Learning roadmap generation (phrases 61–70)

61. **Define the `Roadmap` model (`roadmaps`)** — `id, user_id, subject_id (FK), version (int), status (draft|active|archived), plan_json, created_at`. 🟡
62. **Register `Roadmap` in `models/__init__.py`**; versioning = new rows, old ones stay queryable. 🟡
63. **Create `app/services/kb/roadmap.py`** — topological sort over the topic DAG (Idea 46 helpers) as the backbone order. 🟡
64. **Bucket topics into weeks** — respecting dependency order + weekly time budget (from Idea 49 estimates). 🟡
65. **Constrain by deadlines** — exams/assignments (existing models) force topics before their due weeks; semester end caps the plan. 🟡
66. **Add `POST /api/subjects/{id}/roadmap/generate`** — creates a new version; `GET …/roadmap` returns the active one. 🟡
67. **Deterministic fallback** — when `AI_ENABLED=false`: syllabus order + equal weekly split (no LLM needed; graph still used). 🟡
68. **Write `backend/tests/test_kb_roadmap.py`** — topo ordering, weekly bucketing, deadline constraint, versioning, fallback. 🟡
69. **Frontend:** week-by-week roadmap view on the subject page (topics per week, checkable). 🟡 ✅ `SubjectWorkspace.tsx` (Roadmap tab)
70. **api.ts:** `endpoints.subjects.roadmap` (generate/get). 🟡 ✅ `endpoints.subjects.roadmap`


## Group 8 — Idea 48 🔴: Difficulty estimation (phrases 71–80)

71. **Add `difficulty` (E|M|H) + `difficulty_confidence` (0–1) to `Topic`** — the base column already exists on the model; ensure migration coverage. 🔴
72. **LLM rubric estimation** — `generate_json` over topic name + description + outcome verbs, using a fixed rubric prompt (budget-capped). 🔴
73. **Cross-subject concept overlap** — a topic that mentions concepts known to be hard elsewhere (from `kb_concepts` usage) gets an upward bias. 🔴
74. **Note-density factor** — chunk count for the topic (Phase 1/2 data): more content → higher first-pass difficulty. 🔴
75. **Observed-mastery seam (stub)** — quiz-attempt slope (Phase 6/7) will later adjust difficulty; define the interface now. 🔴
76. **Combine into a single E/M/H with confidence** — weighted vote of rubric + overlap + density; store on `Topic`. 🔴
77. **Add `PATCH /api/topics/{id}`** — manual difficulty override (`provenance=manual`), never re-estimated. 🔴
78. **Write `backend/tests/test_kb_difficulty.py`** — rubric (mocked), overlap bias, density, override, confidence math. 🔴
79. **Frontend:** difficulty badges (E/M/H colored) on topics + inline edit. 🔴 ✅ `TopicCard` (E/M/H badge + set buttons)
80. **Feed roadmap pacing** — hard topics get earlier starts + more sessions in Group 7. 🔴


## Group 9 — Idea 49 🟡: Time estimation (phrases 81–90)

81. **Add the three time fields to `Topic`** — `first_pass_mins`, `review_mins`, `mastery_mins` (already on the model; confirm migration coverage). 🟡
82. **Implement the estimation formula** — volume (chunk count / chars) × difficulty factor (E:1, M:1.5, H:2) × base rates, computed in a pure service function. 🟡
83. **Per-user pacing multiplier** — default 1.0, stored on the user; `learning_events` (Phase 8 seam) will later tune it automatically. 🟡
84. **Add the calibrate UI** — a slider on the subject page writes the multiplier (`PUT /api/users/me/pacing`). 🟡
85. **Recompute estimates on change** — when materials/topics change (reindex completes), refresh `*_mins` for affected topics. 🟡
86. **Add `GET /api/subjects/{id}/time-budget`** — per-topic estimates + weekly totals for the roadmap engine and UI. 🟡
87. **Write `backend/tests/test_kb_time_est.py`** — formula math, difficulty factors, multiplier effect, recompute-on-change. 🟡
88. **Frontend:** per-topic time display (first-pass/review/mastery) + the calibrate slider. 🟡 ✅ `TopicCard` times + pacing multiplier input
89. **api.ts:** `endpoints.subjects.timeBudget` + `endpoints.user.pacing`. 🟡 ✅ `endpoints.subjects.timeBudget` + `endpoints.subjects.pacing`
90. **Feed weekly bucketing** — Group 7 roadmap uses `*_mins` to fill weekly budgets realistically. 🟡


## Group 10 — Idea 50 🔴: Learning-outcome extraction (phrases 91–100)

91. **Add `outcomes` (JSON list) to `Topic`** — each outcome `{text, status (pending|done), completed_at}`. 🔴
92. **Parse outcome lines from the syllabus** — "Upon completion, students can…" sections mapped to their units/topics (from parsed syllabus). 🔴
93. **LLM expansion** — `generate_json` converts verb phrases to measurable outcomes ("can derive X", "can solve Y"), budget-capped. 🔴
94. **Fallback extraction** — rule-based split of outcome sentences when `AI_ENABLED=false`. 🔴
95. **Add `GET /api/topics/{id}/outcomes`** and `POST …/{outcome_index}/complete` — per-user checkboxes with timestamps. 🔴
96. **Link outcomes to the existing Goals model** — completing an outcome creates/updates a linked goal row (reuse the goals router helpers). 🔴
97. **Write `backend/tests/test_kb_outcomes.py`** — parsing, LLM expansion (mocked), fallback, checkbox lifecycle, goal linkage. 🔴
98. **Frontend:** outcomes checklist on the topic/unit view (progress ring), "add outcome" manual entry. 🔴 ✅ `TopicCard` (checkbox list + done/total + add form)
99. **api.ts:** `endpoints.topics.outcomes` (list/complete). 🔴 ✅ `endpoints.subjects.outcomes` (get/add/expand/complete)
100. **Docs:** mark Ideas 41–50 done in the master plan; add the Phase 5 runbook (parse schemas, budgets, review flows). 🔴 ✅ master plan Ideas 41–50 marked ✅; runbook below.

---

## Definition of Done — Phase 5

- [x] A syllabus (text or PDF/DOCX/MD) imports into a *proposed* subject profile — nothing written until the user confirms in the review screen.
- [x] Parsing produces structured units, topics, outcomes, grading, and deadlines (strict schema); a deterministic fallback exists.
- [x] Semester/term is detected (keywords + date cross-check, current-term default) and stored on profile + units.
- [x] Topics are extracted, synonym-folded into canonical names, Bloom-tagged, and human-reviewable (confirm/merge/reject).
- [x] Parsed units match existing `curriculum_units` (name + embedding) with a confirmation step; topics link to units.
- [x] The topic dependency DAG is seeded, refined from concept edges, cycle-safe, manually editable, and exposes topological order.
- [x] Roadmaps generate as versioned week-by-week plans (dependency order + time budgets + deadline constraints) with a fallback.
- [x] Difficulty (E/M/H + confidence) and time estimates (first-pass/review/mastery) are computed, overridable, and recalibrated.
- [x] Learning outcomes are parsed, expanded, checkable, and link to the Goals model.
- [x] All LLM calls respect `KB_DAILY_GEN_LIMIT`; everything works deterministically with `AI_ENABLED=false`.
- [x] Every query stays user-scoped; ownership tests pass.

## Verification checklist

```bash
# Backend: Phase 5 test suite (run from backend/)
python -m pytest tests/test_kb_subject_auto.py tests/test_kb_syllabus_parse.py \
  tests/test_kb_semester.py tests/test_kb_topics.py tests/test_kb_unit_match.py \
  tests/test_kb_topic_deps.py tests/test_kb_roadmap.py tests/test_kb_difficulty.py \
  tests/test_kb_time_est.py tests/test_kb_outcomes.py -q

# Full regression (Phases 1–4 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. POST /api/subjects/import with a syllabus PDF/text → proposal appears
# 2. Review + confirm → curriculum_subject + units created (existing tables)
# 3. GET /api/subjects/{id}/topics → confirm/merge topics; Bloom + difficulty set
# 4. GET /api/subjects/{id}/dependencies → topic DAG; try a cycle → 409
# 5. POST /api/subjects/{id}/roadmap/generate → week-by-week plan, versioned
# 6. Complete a learning outcome → linked goal updates

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phases 6–7 are out of scope:** study planning/execution and the AI tutor — this phase produces the topic graph, roadmaps, and estimates they execute.
- **Phase 3's Idea 28 depends on this phase:** the topic→coverage mapping (Group 8 of the Phase 3 plan) consumes `Topic` rows — keep `normalized_name` stable.
- **Review-before-write is the rule:** proposals, topic confirmations, unit matches, and dependency edges all require user confirmation; AI proposes, the user disposes.
- **Existing curriculum tables stay the source of truth** — `curriculum_subjects`/`curriculum_units`/`materials`; new KB tables (`subject_profiles`, `topics`, `roadmaps`) reference them, never duplicate them.
- **Mastery-based seams (difficulty, time, dependency weights) are stubbed now** — they wire to Phase 6/7 performance data and Phase 8 `learning_events` later.
- **Per-user scoping is non-negotiable** — every profile, topic, roadmap, and edge filters `user_id`; ownership tests mirror `test_ownership.py`.

---

## Phase 5 Runbook (phrase 100)

### Parse schemas

The syllabus parser (`app/services/kb/syllabus.py`) emits the strict schema stored on
`subject_profiles.parsed_json`:

```jsonc
{
  "title": "Data Structures",
  "semester": "Fall 2026",           // string term, or null
  "credits": 3,
  "grading": "40% exams, 30% assignments, 30% labs",
  "units": [
    {
      "title": "Arrays & Linked Lists",
      "description": null,
      "topics": [{ "name": "Dynamic arrays", "outcomes": ["can analyse amortized cost"] }],
      "deadlines": ["Midterm 2026-10-15"]
    }
  ]
}
```

`Topic.outcomes` is a JSON list of `{text, status (pending|done), completed_at}`. Roadmap
`plan_json` is `{weekly_budget_minutes, weeks: [{week, topic_ids, topics, est_mins}]}`.

### AI budgets

Every Phase 5 LLM path — syllabus parse (`syllabus`), topic extraction + difficulty
(`difficulty`), dependency seed (`dependencies`), outcome expansion (`outcomes`) — calls
`budget_allows`/`record_generation` against `KB_DAILY_GEN_LIMIT`. When the budget is exhausted
or `AI_ENABLED=false`, deterministic fallbacks in `app/services/ai_fallback.py` keep every
feature working: `demo_syllabus_parse`, `demo_topic_deps`, `demo_difficulty`,
`demo_outcome_expand`. The roadmap generator is fully algorithmic (no LLM).

### Review flows (AI proposes, the user disposes)

1. **Proposal:** `POST /api/subjects/import` (text) or `/import-file` (PDF/DOCX/MD/TXT) → a
   `proposed` `SubjectProfile` row. Nothing touches `curriculum_subjects` yet.
2. **Confirm:** `POST /api/subjects/{id}/confirm` writes `curriculum_subject` + `curriculum_unit`
   rows (existing tables) and links the profile. `reject` marks it `rejected`.
3. **Topics:** `POST /api/subjects/{id}/topics/generate` → `pending` `Topic` rows (deduped by
   normalized name). Review via list + confirm/reject/merge endpoints; difficulty/time are
   estimated at generation and editable via `PATCH /api/subjects/topics/{id}`.
4. **Unit match:** `GET /api/subjects/{id}/match-units` proposes name (then embedding) matches;
   `POST …/match-units/confirm` persists the mapping and assigns `Topic.unit_id`.
5. **Dependencies:** `POST /api/subjects/{id}/dependencies/generate` seeds edges from the LLM
   (syllabus-order fallback); manual add/remove via the DAG endpoints. Cycle-creating inserts
   return **409**.
6. **Roadmap:** `POST /api/subjects/{id}/roadmap/generate` creates a new versioned plan
   (previous active → archived). Deadline + weekly budget are optional inputs.
7. **Outcomes:** checklist endpoints mark outcomes done and upsert a linked `goals` row
   (title = `"{Topic}: {outcome}"`, year = completion year) — the existing goals UI picks it up.

### Ownership

All Phase 5 tables (`subject_profiles`, `topics`, `roadmaps`, `topic_dependencies`) filter by
`user_id` on every query; all router endpoints resolve the current user via
`get_current_user`. Ownership coverage lives in the Phase 5 test files (each mirrors
`test_ownership.py`).

