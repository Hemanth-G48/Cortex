# Second Brain Integration — Phase 8 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 8 — Personalization & Learning Memory (Ideas 71–80)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1–7 plans
(`SECOND_BRAIN_PHASE{1,2,3,4,5,6,7}_100_PHRASE_PLAN.md`).

**Audit status (from §2 of the master plan):** all 10 ideas are **🔴 genuinely new** — this is the
least-built area of the roadmap. The app has personalization-adjacent data (XP, streaks, quiz
history) but **no preference profile, no `user_memory` store, and no adaptive loop**.

**Prerequisites: Phases 2, 3, 5, 6, and 7 must be complete** — this phase consumes `kb_concepts`,
`kb_edges`, the topic graph + roadmaps (Phase 5), `mastery.py` + `learning_events` +
`revision_schedule` (Phase 6), and the tutor + question bank (Phase 7). It **fills the two
`user_memory` stubs left behind**: Phase 4 Idea 32 (explanations) and Phase 7 Idea 61 (tutor).

**Scope:** Learning-preference profile, concept-level gap detection, personalized explanations,
learned-concept recall in the tutor, cross-subject \"what to study next\", connect-suggestions for
new notes, missing-note suggestions, outdated-note detection, the durable `user_memory` store, and
adaptive learning paths. **Automation and advanced AI are Phases 9–10 and out of scope** — but the
memory store built here (Idea 79) is the substrate Idea 99 (trajectory forecasting) will use.

**Implementation status: ✅ COMPLETE** — backend (10 test files: preferences, concept gaps,
personalized explain, tutor memory, recommend-next, connect, missing notes, outdated, memory,
adaptive paths) and frontend all landed. Backend: `kb_personal.py` router, `preferences.py`,
`gaps.py`, `memory.py`, `connect.py`, `suggestions.py`, `outdated.py`, `adapt.py`; the
`UserPreference` / `UserMemory` / `MissingNoteSuggestion` / `OutdatedNote` models; and the Phase 7
tutor + Phase 4 explain seams now read real `user_memory` (Rule A enforced). Frontend:
`LearningPreferences` settings section + onboarding survey, concept gaps + missing-note suggestions
+ outdated review queue on `KbInsights`, `NextUpCard` on the Dashboard, connect-suggestions panel in
the Knowledge Base drawer, tutor "you've studied" chips, and the roadmap adapt button + "Plan
updated" diff banner in `SubjectWorkspace`.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 8 reuses |
|---|---|---|
| `user_memory` stubs | Phase 4 (Idea 32, phrase 16) + Phase 7 (Idea 61, phrase 5) | The two seams this phase implements with real data |
| Event spine | Phase 6 — `learning_events` | Every interaction (quiz, tutor, revision, note) feeds memory updates |
| Mastery engine | Phase 6 — `mastery.py` (weak/strong, confidence) | The strength signal behind `user_memory` |
| Revision scheduler | Phase 6 — `revision_schedule` | Due-review factor in recommendations + adaptive paths |
| Recommender precedent | Phase 6 — Idea 59 (`next_action.py`) | Cross-subject extension for Idea 75 |
| Concept layer | Phase 2 — `kb_concepts`, `kb_edges` | The atom level for gaps (Idea 72), anchors (Idea 73), memory (Idea 79) |
| Gap + health | Phase 3 — Idea 28 (topic gaps), Idea 27 (staleness) | Concept-gap + outdated-note inputs |
| Quality + versions | Phase 4 — Idea 39 (quality), Phase 1 — Idea 9 (versions) | Outdated-note signals (contradiction + stale + changed materials) |
| Capture pipeline | Phase 4 — Idea 40 (brain-dump filing / draft notes) | One-tap \"create draft note\" for suggestions (Idea 77) |
| Search feedback logs | Phase 3 — Idea 29 (`kb_search_events`) | Retrieval-miss signal for concept gaps |
| Budget guard | `KB_DAILY_GEN_LIMIT` | Caps LLM contradiction scans + suggestion generation |

**File conventions:** services → `backend/app/services/kb/{memory,gaps,recommend,outdated}.py`;
new models → `backend/app/models/kb/*.py` (`UserPreference`, `UserMemory`, `MissingNoteSuggestion`,
`OutdatedNote`); routers → `backend/app/routers/kb_personal.py`; tests → `backend/tests/test_kb_*.py`.
Register every new router in `main.py`, every model in `models/__init__.py`.

**Two hard rules for Phase 8:**
- **Rule A — Never claim what memory doesn't hold:** the tutor/explanations may only reference
  concepts present in `user_memory` (strength > 0); no inferred \"you must know X\".
- **Rule B — Budgets + scoping:** every LLM call (contradiction scans, suggestion generation)
  respects `KB_DAILY_GEN_LIMIT`; every new table and query is user-scoped.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new — all Phase 8 ideas are new)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---


---

## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))

Every idea in Phase 8 (Personalization & Learning Memory) has reusable components in the cloned reference repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.

- **Idea 71 — Learning preference profile:** mind-mentor (profile/settings) · Multi-Agent-Study-Assistant (profiling) · dyresearch (config_manager.py) · glean (preference.py schema)
- **Idea 72 — Knowledge-gap detection (concept level):** llm_wiki (gap analysis) · Multi-Agent-Study-Assistant (gap analysis) · obsidian-wiki (graph_analysis.py)
- **Idea 73 — Personalized explanations:** mind-mentor · EduAI · StudyWise
- **Idea 74 — Remember previously learned concepts:** engram (memory store) · nocturne_memory · basic-memory · claude-obsidian
- **Idea 75 — Recommend what to study next:** QuestLog (AI recommendations) · syllabo (content_recommender.py) · StudyWise
- **Idea 76 — Connect new concepts to existing notes:** llm_wiki (graph) · claude-obsidian (connect skill) · obsidian-second-brain (obsidian-connect) · obsidian-wiki
- **Idea 77 — Suggest missing notes:** llm_wiki · obsidian-wiki (graph_analysis) · My-Brain-Is-Full-Crew
- **Idea 78 — Detect outdated notes:** claude-obsidian (lint_engine.py) · obsidian-wiki (lint.py, trust.py)
- **Idea 79 — Long-term learning memory store:** engram (internal/store) · nocturne_memory (db/) · basic-memory (repository/) · memory-bank-mcp · token-savior
- **Idea 80 — Adaptive learning paths:** Multi-Agent-Study-Assistant · syllabo · StudyWise

> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines (khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, dendron. Repos without a license file are STUDY only.

## Group 1 — Idea 71 🔴: Learning preference profile (phrases 1–10)

1. **Define the `UserPreference` model (`user_preferences`)** — `id, user_id (unique), depth (overview|deep_dive), examples_vs_theory (0–1), style (concise|detailed), session_length_mins, explanation_style (plain|analogy|formal), onboarding_completed (bool), updated_at`. 🔴
2. **Register the model** in `models/__init__.py`. 🔴
3. **Add `GET/PUT /api/users/me/preferences`** — per-user CRUD with clamped/validated values (no arbitrary strings). 🔴
4. **Add the onboarding survey flow** — a small first-run questionnaire writing these fields (extend the existing onboarding/settings UI). 🔴
5. **Create `app/services/kb/preferences.py`** — `preferences_prompt(user)` renders the profile into a prompt snippet (shared by tutor + explanations). 🔴
6. **Inject preferences into the tutor system prompt** — Phase 7 Group 1 context assembly gains style/depth lines. 🔴
7. **Inject preferences into explanations** — Phase 4 Idea 32 prompt variants read `style`/`depth` from the profile. 🔴
8. **Infer adjustments from behavior (stretch)** — session-length and depth-toggle signals (from `learning_events`) nudge defaults with provenance `inferred`. 🔴
9. **Write `backend/tests/test_kb_preferences.py`** — CRUD, clamping, prompt rendering, inference nudge, per-user isolation. 🔴
10. **Frontend:** preferences section in settings; onboarding survey step. 🔴


## Group 2 — Idea 72 🔴: Knowledge-gap detection — concept level (phrases 11–20)

11. **Create `app/services/kb/gaps.py`** — the concept-level gap engine (extends the Phase 3 topic-level gap logic). 🔴
12. **Map quiz/practice errors to concepts** — wrong answers on questions tagged with `kb_concepts` (Phase 7 bank + Phase 5 topics) become per-concept error counts. 🔴
13. **Incorporate retrieval misses** — `kb_search_events` (Phase 3 Idea 29) where the user searched but found nothing flag missing concepts. 🔴
14. **Compute the gap formula** — `gap = low mastery (Phase 6) + low exposure + error count`, per concept, per user. 🔴
15. **Report with suggested capture sources** — each gap lists the top relevant vault chunks to read/capture (retrieval). 🔴
16. **Add `GET /api/kb/gaps/concepts`** — ranked concept gaps with evidence (errors, misses, mastery). 🔴
17. **Write `backend/tests/test_kb_concept_gaps.py`** — error mapping, miss incorporation, formula math, ranked output. 🔴
18. **Frontend:** concept-gap list on the Insights page (per concept: why it's a gap + capture CTA). 🔴
19. **api.ts:** `endpoints.kb.gaps.concepts`. 🔴
20. **Feed Idea 75 (recommend-next) and Idea 77 (missing-note suggestions).** 🔴


## Group 3 — Idea 73 🔴: Personalized explanations (phrases 21–30)

21. **Extend `app/services/kb/explain.py`** (Phase 4 Idea 32) to accept `user_memory` input — the stub becomes real. 🔴
22. **Anchor on known concepts** — retrieval boosts chunks adjacent to the user's `user_memory` concepts (strength > threshold) as "known anchors". 🔴
23. **Add the "link to what you know" prompt template** — renders the anchor list so the explanation builds on it. 🔴
24. **Apply style + depth from preferences** — `UserPreference` fields pick the prompt variant (Group 1). 🔴
25. **Track follow-up acceptance implicitly** — if the user asks "simpler" or repeats, nudge the inferred style preference (with provenance `inferred`). 🔴
26. **Fallback** — standard explanation (no anchors, default style) when memory or preferences are empty. 🔴
27. **Write `backend/tests/test_kb_personalized_explain.py`** — anchor selection, prompt rendering, style/depth variants, inference nudge, fallback. 🔴
28. **Frontend:** explanation panel shows "Builds on: X, Y" chips (the anchors). 🔴
29. **api.ts:** `endpoints.kb.explain` extended params (depth + style). 🔴
30. **Budget-cap** every personalized explanation against `KB_DAILY_GEN_LIMIT`. 🔴


## Group 4 — Idea 74 🔴: Remember previously learned concepts (phrases 31–40)

31. **Implement the tutor's `user_memory` read** — Phase 7 Group 1 (phrase 5) stub now loads real memory rows. 🔴
32. **Add the "Known context" section to the tutor system prompt** — top concepts by strength with last-seen dates. 🔴
33. **Enable reference phrasing** — instruct the model to say "as you saw in your notes on X" only for concepts in the known list. 🔴
34. **Update memory on interactions** — quiz, tutor turn, revision, and note views call the memory service (Group 9) to bump strength/exposure. 🔴
35. **Enforce Rule A** — a post-check strips references to concepts not in memory (never invent prior knowledge). 🔴
36. **Write `backend/tests/test_kb_tutor_memory.py`** — known-context rendering, reference phrasing, enforcement, memory bumps. 🔴
37. **Frontend:** tutor answers render "you studied X" chips from the memory-driven context. 🔴
38. **api.ts:** tutor endpoint unchanged in shape; memory is server-side. 🔴
39. **Per-user isolation** — memory reads/writes scoped to `user_id`. 🔴
40. **Log every reference** into `learning_events` (event_type=recall) for later trajectory analysis. 🔴


## Group 5 — Idea 75 🔴: Recommend what to study next (phrases 41–50)

41. **Extend `next_action.py` (Phase 6 Idea 59) to cross-subject scope** — the scoring engine gains subject coverage + concept-gap factors (Group 2). 🔴
42. **Composite factors** — readiness (topic DAG deps mastered), due reviews (Phase 6), weakness (mastery), concept gaps (Group 2), exam proximity (Phase 6 Idea 53). 🔴
43. **Add `KB_RECOMMEND_WEIGHTS` to `config.py`** — per-factor weights with defaults. 🔴
44. **Add `GET /api/kb/recommend/next`** — the single best next action with an explainable reason breakdown (`reasons[]`). 🔴
45. **Render on the dashboard + daily schedule** — a "Next up" card (reuse the Phase 6 Study-now card pattern). 🔴
46. **Never recommend blocked topics** — missing prerequisites route the recommendation to the prerequisite first. 🔴
47. **Write `backend/tests/test_kb_recommend_next.py`** — factor math, blocking, reason output, cross-subject ranking, per-user isolation. 🔴
48. **Frontend:** "Next up" card with reasons + one-tap start (session/review). 🔴
49. **api.ts:** `endpoints.kb.recommend.next`. 🔴
50. **Respect preferences** — session-length preference shapes the suggested session duration. 🔴


## Group 6 — Idea 76 🔴: Connect new concepts to existing notes (phrases 51–60)

51. **Add a post-ingestion hook** — after a document is chunked (Phase 1 Group 10 pipeline), retrieve top similar existing documents (Phase 2 embeddings) + shared concepts. 🔴
52. **Create `app/services/kb/connect.py`** — ranks connection candidates: similar docs, shared concepts, extending/contradicting signals. 🔴
53. **Add `GET /api/kb/documents/{id}/connect-suggestions`** — the candidate list with reasons. 🔴
54. **Add `POST /api/kb/documents/{id}/connect` (confirm)** — creates `kb_edges` with `provenance=manual` (Phase 2 edge model). 🔴
55. **Flag contradicting candidates** — hand them to Idea 78's contradiction queue (pre-seeded candidates). 🔴
56. **Suppress already-connected docs** — existing edges exclude their targets from suggestions. 🔴
57. **Write `backend/tests/test_kb_connect.py`** — candidate ranking, confirm creates edges, suppression, contradiction hand-off. 🔴
58. **Frontend:** "Connect this note" panel on a new document's detail view. 🔴
59. **api.ts:** `endpoints.kb.documents.connectSuggestions` + `.connect`. 🔴
60. **Wire the hook into the ingest job** so suggestions exist by the time the user opens the doc. 🔴


## Group 7 — Idea 77 🔴: Suggest missing notes (phrases 61–70)

61. **Define the `MissingNoteSuggestion` model (`missing_note_suggestions`)** — `id, user_id, concept_id (FK), topic_id (nullable), reason, outline_template (JSON), linked_material_ids (JSON), status (suggested|accepted|dismissed), created_at`. 🔴
62. **Register the model** in `models/__init__.py`. 🔴
63. **Create `app/services/kb/suggestions.py`** — ranks "you study X but have no note on it" from Group 2 gaps + Phase 3 topic coverage. 🔴
64. **Generate the outline template** — suggested headings for the missing note (budget-capped LLM or deterministic heading template). 🔴
65. **Add `GET /api/kb/suggestions/missing-notes`** — ranked list with reasons + linked materials. 🔴
66. **Add `POST …/{id}/accept`** — one-tap creates a draft note (Phase 4 Idea 40 quick-capture flow) pre-filled with the outline. 🔴
67. **Add `POST …/{id}/dismiss`** — never re-suggested. 🔴
68. **Write `backend/tests/test_kb_missing_notes.py`** — ranking, outline generation, accept→draft creation, dismiss dedupe. 🔴
69. **Frontend:** suggestions list on Insights + "create draft" action. 🔴
70. **Daily digest** — coalesced notifications of new suggestions (reuse notifications router). 🔴


## Group 8 — Idea 78 🔴: Detect outdated notes (phrases 71–80)

71. **Create `app/services/kb/outdated.py`** — three detectors: contradiction, staleness, changed-materials. 🔴
72. **Contradiction candidate pairs** — documents flagged similar by embeddings + recency (newer vs older) become LLM-check candidates. 🔴
73. **LLM contradiction check** — budget-capped `generate_json` verdict (`contradicts|supports|unrelated`) over the pair; deterministic keyword fallback. 🔴
74. **Stale detection** — no updates / no reads in `KB_STALE_DAYS` (reuse Phase 3 health signal) → candidate. 🔴
75. **Changed-materials detection** — a note whose referenced materials changed `content_hash` (Phase 1) → candidate. 🔴
76. **Define the `OutdatedNote` model (`outdated_notes`)** — `id, user_id, document_id, reason (contradiction|stale|material_changed), evidence_json, status (open|updated|archived|dismissed), created_at`. 🔴
77. **Add `GET /api/kb/outdated`** — the review queue; `POST …/{id}/resolve` with the chosen action. 🔴
78. **Write `backend/tests/test_kb_outdated.py`** — each detector, LLM verdict (mocked + fallback), review lifecycle. 🔴
79. **Frontend:** outdated review queue (diff link, "mark updated"/"archive"/"dismiss"). 🔴
80. **Notify on new contradictions** — coalesced, via notifications router. 🔴


## Group 9 — Idea 79 🔴: Long-term learning memory store (phrases 81–90)

81. **Define the `UserMemory` model (`user_memory`)** — `id, user_id, concept_id (FK kb_concepts.id), strength (0–1), exposure_count, last_seen, source (quiz|tutor|revision|note|practice), updated_at`, unique `(user_id, concept_id)`. 🔴
82. **Register the model** in `models/__init__.py` + index on `(user_id, strength)`. 🔴
83. **Create `app/services/kb/memory.py`** — `get_memory(user_id)`, `bump(user_id, concept_ids, delta)`, `decay(user_id)`. 🔴
84. **Wire event handlers** — quiz results, tutor turns, revision grades, note views, and practice answers (all via `learning_events`) call `bump`. 🔴
85. **Implement strength decay** — exponential half-life (config `KB_MEMORY_HALF_LIFE_DAYS`) so unused concepts fade. 🔴
86. **Add `GET /api/kb/memory`** — the per-user memory snapshot (concepts, strength, last seen), paginated. 🔴
87. **Write `backend/tests/test_kb_memory.py`** — bump accumulation, decay math, event-driven updates, per-user isolation. 🔴
88. **Frontend:** optional memory view (strength bars) — low priority, read-only. 🔴
89. **Consumed by** Groups 3–4 (anchors, known context), Idea 75 (factors), and Idea 80 (adaptation). 🔴
90. **This is the substrate for Idea 99** (learning-trajectory forecasting, Phase 10) — keep the schema stable. 🔴


## Group 10 — Idea 80 🔴: Adaptive learning paths (phrases 91–100)

91. **Create `app/services/kb/adapt.py`** — recomputes a subject's roadmap (Phase 5 Idea 47) from current mastery + due reviews + gaps. 🔴
92. **Define recompute triggers** — mastery changes beyond a threshold, new gaps (Group 2), due-review floods, or exam-date changes. 🔴
93. **Produce the plan diff** — `{added_reviews, removed_topics, reordered[], reason}` so changes are explainable. 🔴
94. **Add `POST /api/subjects-ai/{id}/roadmap/adapt`** — manual trigger; auto-trigger via event hooks behind a config flag. 🔴
95. **Preserve versioning** — a new `Roadmap` version replaces the active one; the old stays archived (Phase 5 pattern). 🔴
96. **Skip mastered topics** — strength above threshold removes them from the plan (unless due for review). 🔴
97. **Insert reviews for gaps** — newly detected gaps inject revision sessions into the nearest week. 🔴
98. **Write `backend/tests/test_kb_adaptive_path.py`** — diff computation, trigger thresholds, mastered-skip, gap-insert, versioning. 🔴
99. **Frontend:** "Plan updated" banner with the diff (+2 reviews, −1 topic) and a view switch to the previous version. 🔴
100. **Docs:** mark Ideas 71–80 done in the master plan; add the Phase 8 runbook (memory decay, weights, budgets). 🔴

---

## Definition of Done — Phase 8

- [x] `user_preferences` exists, is editable, and is injected into tutor + explanation prompts; onboarding survey works.
- [x] Concept-level gaps combine quiz errors, retrieval misses, and mastery, with suggested capture sources.
- [x] Explanations anchor on known concepts and follow the user's style/depth preferences (with fallback).
- [x] The tutor references only concepts actually in `user_memory` ("as you saw in your notes on X") — never invents prior knowledge.
- [x] "Next up" recommends the single best cross-subject action with explainable reasons.
- [x] New documents get connect-suggestions (similar docs, shared concepts) with confirm → manual edges.
- [x] Missing-note suggestions rank by gap + coverage and create one-tap draft notes; dismissed ones stay dismissed.
- [x] Outdated notes are detected (contradiction / stale / changed materials) and flow through a review queue.
- [x] `user_memory` accumulates strength/exposure from all interactions, decays over time, and feeds every consumer.
- [x] Roadmaps adapt to mastery/gaps with versioned plan diffs and a visible "plan updated" notice.
- [x] All LLM calls respect `KB_DAILY_GEN_LIMIT`; deterministic fallbacks work with `AI_ENABLED=false`; every query is user-scoped.

## Verification checklist

```bash
# Backend: Phase 8 test suite (run from backend/)
python -m pytest tests/test_kb_preferences.py tests/test_kb_concept_gaps.py \
  tests/test_kb_personalized_explain.py tests/test_kb_tutor_memory.py \
  tests/test_kb_recommend_next.py tests/test_kb_connect.py tests/test_kb_missing_notes.py \
  tests/test_kb_outdated.py tests/test_kb_memory.py tests/test_kb_adaptive_path.py -q

# Full regression (Phases 1–7 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. PUT /api/users/me/preferences → tutor + explain responses change style/depth
# 2. Answer a quiz question wrong → GET /api/kb/gaps/concepts shows the concept with evidence
# 3. Chat with the tutor → references "as you saw in your notes on X" only for known concepts
# 4. GET /api/kb/recommend/next → one explainable recommendation; start it
# 5. Ingest a new doc → connect suggestions appear; accept → edge created
# 6. GET /api/kb/memory → strength decays over time (config half-life)
# 7. POST /api/subjects-ai/{id}/roadmap/adapt → plan diff banner in the UI

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phases 9–10 are out of scope:** automation and advanced AI — but `user_memory` (Group 9) is the documented substrate for Idea 99 (trajectory forecasting), so keep its schema stable.
- **Memory discipline is the core rule (Rule A):** the tutor and explanations may only reference concepts actually in `user_memory`; a post-check enforces it.
- **The two `user_memory` stubs are filled here** — Phase 4 Idea 32 (explanations) and Phase 7 Idea 61 (tutor) both degrade gracefully when memory is empty.
- **Reuse over rebuild:** memory rides `learning_events` (Phase 6) as its write bus; gaps extend Phase 3 Idea 28; recommendations extend Phase 6 Idea 59; adaptation extends Phase 5 roadmaps.
- **Per-user scoping is non-negotiable** — every preference, memory row, suggestion, and outdated-note row filters `user_id`; ownership tests mirror `test_ownership.py`.

