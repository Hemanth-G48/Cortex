# Second Brain Integration — Phase 10 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 10 — Advanced AI, Analytics & Platform (Ideas 91–100)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the **capstone** of the ten-phase plan set
(`SECOND_BRAIN_PHASE{1..9}_100_PHRASE_PLAN.md`).

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (4): Idea 91 (multi-agent), 92 (long-term memory), 94 (graph+vector fusion), 97 (recommendation engine)
- 🟡 partial / extends existing code (6): Ideas 93, 95, 96, 98, 99, 100 harden and coordinate machinery built in Phases 1–9

**Implementation status: ✅ COMPLETE** — backend, frontend, and tests all landed.
Backend: `agents.py` (registry + orchestrator + `AgentRun`), `memory_longterm.py` (`EpisodicMemory`
+ consolidation + fact folding), `rag.py` (rewrite → multi-stage retrieve → rerank → verify →
faithfulness), `fusion.py` (`mode=graph_fused` search), `context.py` (bundle + overrides), `research.py`
(explain/related), `recommendations.py` (ranked explainable items + feedback), `reflections.py`
(weekly reflection + goal↔roadmap linkage), `forecast.py` (EWMA trajectory + at-risk alerts),
and `ai_log.py` (`AiLog` observability + `prompt_versions` + weekly report) — with 8 routers
(`kb_agents/memory/context/research/recommendations/reflections/forecast/observability`)
registered in `main.py`. Tutor prompts inject the context bundle + durable-memory block.
Frontend: `endpoints.kb.*` in `api.ts` + the `Phase10Panel` (agents · memory · research ·
recommendations · forecast · observability) mounted in the Knowledge Base page.
Tests: 10 new files covering every idea (62 Phase 10 tests).

**Prerequisites: Phases 1–9 must be complete** — this phase *orchestrates* the existing services:
the tutor (Phase 7), search/RRF + eval harness (Phase 3), summaries/flashcards (Phase 4),
roadmaps (Phase 5), `revision_schedule`/`mastery`/`learning_events` (Phase 6), `user_memory` +
recommend + adapt (Phase 8), and the automation jobs (Phase 9).

**Scope:** Multi-agent orchestration, long-term memory consolidation, production-grade RAG
hardening, graph+vector fused retrieval, context-aware responses, a research assistant, a
cross-domain recommendation engine, goal planning + weekly reflection, learning-trajectory
forecasting, and the self-improvement/observability loop. **This is the final phase — completing it
marks all 100 ideas of the master plan as done.**

**Two hard rules for Phase 10:**
- **Rule A — Every AI interaction is measured:** nothing ships without logging to `ai_logs`
  (latency, cost, retrieval, feedback) — observability is the meta-feature (Idea 100).
- **Rule B — Budgets + groundedness:** every agent step respects `KB_DAILY_GEN_LIMIT`; hardened
  RAG falls back to \"not found\" rather than answering ungrounded (Phase 7 Rule A continues to hold).

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 10 reuses |
|---|---|---|
| AI client + budget | `ai_client.py` + `KB_DAILY_GEN_LIMIT` | Every agent/step's LLM path + cost guardrail |
| Tutor + explanations | Phase 7 Idea 61 / Phase 4 Idea 32 | The pipeline RAG hardening wraps; context bundle attaches |
| Search/RRF + expansion | Phase 3 Ideas 23–24 + eval harness Idea 26 | Multi-stage retrieval + faithfulness regression |
| Graph + concepts | Phase 2 Ideas 16, 15 (`kb_edges`, `kb_concepts`) | Graph-expansion stage (Idea 94) |
| Memory substrate | Phase 8 Idea 79 (`user_memory`) + Phase 6 `learning_events` | Long-term memory (Idea 92) + forecasting (Idea 99) — **schemas must stay stable** |
| Recommend + adapt | Phase 8 Ideas 75, 80 | Recommendation engine + reflection-driven plan adjustments |
| Research pieces | Phase 1 Idea 5 (`arxiv.py`), Phase 4 Idea 31 (summaries), Idea 36 (citations) | The research assistant's parts |
| Goals + roadmap | existing goals router + Phase 5 Idea 47 | Goal planning & reflection |
| Revisio/mastery/scheduler | Phase 6 | Scheduler agent + trajectory inputs |
| Automation jobs | Phase 9 | Memory consolidation + weekly report run on `kb_jobs` |

**File conventions:** services → `backend/app/services/kb/{agents,memory_longterm,rag,forecast}.py`;
new models → `backend/app/models/kb/*.py` (`AgentRun`, `EpisodicMemory`, `AiLog`, `Reflection`);
routers → `backend/app/routers/kb_agents.py` (+ `kb_observability.py`); tests →
`backend/tests/test_kb_*.py`. Register every new router in `main.py`, every model in
`models/__init__.py`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---


---

## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))

Every idea in Phase 10 (Advanced AI, Analytics & Platform) has reusable components in the cloned reference repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.

- **Idea 91 — Multi-agent architecture:** Multi-Agent-Study-Assistant (study_agents.py) · My-Brain-Is-Full-Crew (8 agents) · dyresearch (ADK agents) · obsidian-second-brain (46 commands) · mind-mentor (mind-mentor-agents) · phantom · arscontexta
- **Idea 92 — Long-term memory system:** engram · nocturne_memory · basic-memory · token-savior · memory-bank-mcp
- **Idea 93 — Full RAG pipeline hardening:** khoj · decodingai · reor · obsidian-wiki (graphrag.py)
- **Idea 94 — Knowledge-graph + vector fusion:** knowledge-nexus (Neo4j GraphRAG) · llm_wiki · obsidian-wiki (graphrag.py) · basic-memory
- **Idea 95 — Context-aware responses:** QuestLog (AI controller w/ user stats) · mind-mentor · EduAI
- **Idea 96 — Research assistant:** dyresearch · knowledge-nexus (notion/pocket providers) · decodingai · claude-obsidian (autoresearch skill)
- **Idea 97 — Intelligent recommendation engine:** syllabo (content_recommender.py) · QuestLog · StudyWise
- **Idea 98 — Goal planning & reflection:** obsidian-claude-pkm (3-year vision → daily) · OrbitOS · My-Brain-System · obsidian-second-brain (obsidian-challenge)
- **Idea 99 — Predictive analytics & trajectory forecasting:** QuestLog (analytics) · syllabo (prediction) · StudyWise
- **Idea 100 — Self-improving assistant + observability:** claude-obsidian (ledgers.py) · token-savior · QuestLog (analytics) · decodingai (Opik integration)

> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines (khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, dendron. Repos without a license file are STUDY only.

## Group 1 — Idea 91 🔴: Multi-agent architecture (phrases 1–10)

1. **Define the agent protocol** — typed task objects `{agent, inputs, expected_output, budget}` passed between orchestrator and specialists. 🔴
2. **Create the agent registry** (`app/services/kb/agents.py`) — retriever, summarizer, quizzer, tutor, scheduler, health-checker, each wrapping an existing Phase 1–9 service. 🔴
3. **Build the orchestrator** — plans a request → spawns sequential/parallel steps → composes results (lightweight, no external framework). 🔴
4. **Every agent uses the shared `ai_client`** + `KB_DAILY_GEN_LIMIT` guardrails — no bespoke LLM calls. 🔴
5. **Add `POST /api/kb/agents/run`** — `{request, context?}`; the canonical example: "prepare me for Thursday's exam using my weakest topics" (scheduler + retriever + quizzer + tutor). 🔴
6. **Define the `AgentRun` model (`agent_runs`)** — `id, user_id, request, plan (JSON), steps (JSON), result, status, latency_ms, cost_estimate, created_at`. 🔴
7. **Register the model** in `models/__init__.py`. 🔴
8. **Deterministic fallback** — when `AI_ENABLED=false`, steps run in the same order with local fallbacks (existing `ai_fallback` + services). 🔴
9. **Write `backend/tests/test_kb_agents.py`** — orchestration of the exam-prep request (mocked agents), sequential vs parallel steps, budget enforcement, fallback. 🔴
10. **Frontend:** composed agent result view (plan → step outputs → final answer) on the tutor page. 🔴


## Group 2 — Idea 92 🔴: Long-term memory system (phrases 11–20)

11. **Define the `EpisodicMemory` model (`episodic_memory`)** — `id, user_id, event_type, summary, refs (JSON), created_at` — the episodic journal beyond the Phase 8 `user_memory` concept table. 🔴
12. **Register the model** in `models/__init__.py` + index on `(user_id, created_at)`. 🔴
13. **Create `app/services/kb/memory_longterm.py`** — append episodes from `learning_events` (Phase 6) automatically. 🔴
14. **Add the periodic consolidation job** (on `kb_jobs`) — summarize old episodes into durable facts (budget-capped `generate_json`). 🔴
15. **Fold consolidated facts back into `user_memory`** — strength bumps + new concept entries (Phase 8 Idea 79). 🔴
16. **Inject consolidated memory into prompts** — tutor + agents gain a compact "durable facts" block (keep it small — token-aware). 🔴
17. **Add `KB_MEMORY_CONSOLIDATION_DAYS` config** (default 7) + `KB_MEMORY_CONSOLIDATION_ENABLED` toggle. 🔴
18. **Write `backend/tests/test_kb_longterm_memory.py`** — episode appends, consolidation (mocked), fact folding, prompt injection, idempotent re-run. 🔴
19. **Frontend:** optional memory timeline (episodes + consolidated facts), read-only. 🔴
20. **Keep `user_memory` and `learning_events` schemas stable** — Idea 99 (forecasting) depends on them. 🔴


## Group 3 — Idea 93 🟡: Full RAG pipeline hardening (phrases 21–30)

21. **Refactor retrieval into composable pipeline stages** (`app/services/kb/rag.py`) — rewrite → multi-stage retrieve → rerank → verify citations → faithfulness check. 🟡
22. **Stage 1: query rewrite** — wrap the Phase 3 Idea 24 expansion (aliases/typos/LLM rewrite) as the first stage. 🟡
23. **Stage 2: multi-stage retrieval** — broad FTS + vector top-k (Phase 3 Idea 23) → fuse → candidate pool. 🟡
24. **Stage 3: rerank** — cross-encoder or budget-capped LLM rerank of the fused top-N. 🟡
25. **Stage 4: citation verification** — each answer claim aligned to source chunks (chunk-id map, not free text). 🟡
26. **Stage 5: faithfulness check** — post-generation groundedness score; below threshold → regenerate once or return "not found". 🟡
27. **Add `KB_RAG_STAGES` config** — per-stage enable/disable for A/B and debugging. 🟡
28. **Write `backend/tests/test_kb_rag_hardening.py`** — stage composition, rerank effect (mocked), citation alignment, faithfulness gate. 🟡
29. **Feed metrics to the Phase 3 eval harness** — golden-set recall/MRR per stage configuration. 🟡
30. **Log stage latencies + groundedness to `ai_logs`** (Group 10) — the observability contract starts here. 🟡


## Group 4 — Idea 94 🔴: Knowledge-graph + vector fusion (phrases 31–40)

31. **Implement two-stage retrieval** — vector top-k (Phase 3) → graph expansion over `kb_edges` (Phase 2) for 1–2 hops. 🔴
32. **Expand via relation types** — `DEPENDS_ON` (prerequisites), `RELATED`, `SHARES_CONCEPT`, and concept `MENTIONS` enrich the candidate set. 🔴
33. **Dedupe + rerank the expanded set** — expanded neighbors re-scored (graph proximity × vector score). 🔴
34. **Graph-aware prompts** — tutor/explanations receive prerequisite chains ("B builds on A") in the context block. 🔴
35. **Add `mode=graph_fused` to the search endpoint** — hybrid + graph expansion behind a query flag. 🔴
36. **Add `KB_GRAPH_EXPAND_HOPS` (default 2) and `KB_GRAPH_EXPAND_CAP`** (max added candidates) config. 🔴
37. **Write `backend/tests/test_kb_graph_fusion.py`** — expansion correctness, dedupe, rerank, cap enforcement, per-user isolation. 🔴
38. **Frontend:** search results label graph-expanded sources ("via: prerequisite"). 🔴
39. **api.ts:** `endpoints.kb.search` gains `mode=graph_fused`. 🔴
40. **Perf guard** — expansion never exceeds the cap; slow-path flag for large graphs. 🔴


## Group 5 — Idea 95 🟡: Context-aware responses (phrases 41–50)

41. **Create `app/services/kb/context.py`** — builds the context bundle: active subject, upcoming exams/deadlines, recent topics, question history. 🟡
42. **Attach the bundle to tutor + explain + agent requests** — one context assembly used everywhere (no drift). 🟡
43. **Inject as a prompt context block** — exam-week vs mid-semester answers differ; deadlines shape prioritization. 🟡
44. **Add `GET /api/kb/context` and `PUT /api/kb/context`** — read the current bundle; user can override (active subject etc.). 🟡
45. **Render UI context chips** — visible + editable above the tutor input ("Context: DSA • exam in 4 days"). 🟡
46. **Derive automatically** — active subject from recent sessions, deadlines from existing models, topics from `learning_events`. 🟡
47. **Write `backend/tests/test_kb_context.py`** — bundle assembly, override, prompt injection, per-user isolation. 🟡
48. **Frontend:** context chips + override control on the tutor page. 🟡
49. **api.ts:** `endpoints.kb.context` (get/put). 🟡
50. **Privacy** — the bundle is per-user, never shared across accounts. 🟡


## Group 6 — Idea 96 🟡: Research assistant (phrases 51–60)

51. **Create `app/services/kb/research.py`** — the paper workflow: ingest → summary → contributions → connections → synthesis. 🟡
52. **Summarize papers** — reuse the Phase 4 Idea 31 summary service on the paper's chunks. 🟡
53. **Extract key contributions** — `generate_json` (budget-capped): `{contributions[], novelty, limitations}`. 🟡
54. **Suggest related papers from the user's library** — citation-graph similarity + embedding similarity over `kb_citations`/documents. 🟡
55. **Cite-aware synthesis** — "explain this paper given my notes": RAG over the paper + user's chunks (tutor pipeline), citations mandatory. 🟡
56. **Add `POST /api/kb/research/explain`** — `{arxiv_id | document_id, question?}` per-user. 🟡
57. **Write `backend/tests/test_kb_research.py`** — summary reuse, contributions (mocked), related-paper ranking, cited synthesis. 🟡
58. **Frontend:** research panel on paper documents (summary, contributions, related papers, ask-about-it). 🟡
59. **api.ts:** `endpoints.kb.research` (explain/related). 🟡
60. **Budget every LLM step** against `KB_DAILY_GEN_LIMIT`. 🟡


## Group 7 — Idea 97 🔴: Intelligent recommendation engine (phrases 61–70)

61. **Create `app/services/kb/recommendations.py`** — the cross-domain engine over the Phase 8 Idea 75 recommend service. 🔴
62. **Candidate generation across domains** — study next, revisit notes, read papers, take practice sets (each domain has a candidate source). 🔴
63. **Rank by urgency × weakness × readiness** — graph + memory + schedule factors, reusing the mastered/weak signals (Phase 6). 🔴
64. **Produce explainable reasons** — "because X is due and you missed it last week" style, per candidate. 🔴
65. **Add `GET /api/kb/recommendations`** — `{items: [{domain, target, reason, score}]}`. 🔴
66. **Add `POST /api/kb/recommendations/{id}/feedback`** — accept/skip logged (feeds Idea 100 tuning). 🔴
67. **Add `KB_RECOMMENDATION_WEIGHTS` config** (defaults: urgency .4, weakness .3, readiness .3). 🔴
68. **Write `backend/tests/test_kb_recommendations.py`** — candidate generation per domain, ranking math, reasons, feedback logging. 🔴
69. **Frontend:** recommendations feed on the dashboard (domain-badged, one-tap action). 🔴
70. **api.ts:** `endpoints.kb.recommendations` (list/feedback). 🔴


## Group 8 — Idea 98 🟡: Goal planning & reflection system (phrases 71–80)

71. **Align existing Goals with roadmaps** — extend the goals router to link a goal to a subject/roadmap (Phase 5) and track progress from roadmap completion. 🟡
72. **Derive term/quarter goals from subjects** — "master DSA" style goals auto-proposed from active subjects (budget-capped, reviewable). 🟡
73. **Define the `Reflection` model (`reflections`)** — `id, user_id, week_start, content, insights (JSON), created_at`, unique `(user_id, week_start)`. 🟡
74. **Register the model** in `models/__init__.py`. 🟡
75. **Generate the weekly reflection** — from `learning_events` (what worked / what didn't / what to change), budget-capped. 🟡
76. **Push insights to the user** — via the notifications router (coalesced weekly). 🟡
77. **Apply reflection-driven plan adjustments** — reuse the Phase 8 Idea 80 adapt machinery when insights flag a change. 🟡
78. **Write `backend/tests/test_kb_goals_reflection.py`** — goal↔roadmap linkage, goal derivation, reflection generation, insight push, adapt trigger. 🟡
79. **Frontend:** goals + weekly reflection view (progress, insights, adjust-plan button). 🟡
80. **api.ts:** extend `endpoints.goals` + `endpoints.kb.reflections`. 🟡


## Group 9 — Idea 99 🟡: Predictive analytics & learning-trajectory forecasting (phrases 81–90)

81. **Create `app/services/kb/forecast.py`** — time-series over mastery/exposure events from `learning_events` + `user_memory`. 🟡
82. **Start with EWMA** — exponentially-weighted moving average of mastery per subject; linear regression as the `KB_FORECAST_MODEL=linear` option. 🟡
83. **Compute the exam-readiness score** — weighted forecast vs. exam date (Phase 6 Idea 53 exam mode inputs). 🟡
84. **Flag at-risk subjects early** — readiness below `KB_FORECAST_RISK_THRESHOLD` (default 0.5) → at-risk. 🟡
85. **Add `GET /api/kb/forecast/{subject_id}`** — trajectory points, readiness score, at-risk flag. 🟡
86. **Send early-warning alerts** — via notifications when a subject flips to at-risk (coalesced, non-spammy). 🟡
87. **Write `backend/tests/test_kb_forecast.py`** — EWMA math, readiness vs exam date, risk thresholds, alert firing. 🟡
88. **Frontend:** trajectory charts on the subject progress page (extend existing analytics visuals). 🟡
89. **api.ts:** `endpoints.kb.forecast(subjectId)`. 🟡
90. **Schema stability** — `user_memory` + `learning_events` must not break (this and Idea 92 depend on them). 🟡


## Group 10 — Idea 100 🟡: Self-improving assistant + observability (phrases 91–100)

91. **Define the `AiLog` model (`ai_logs`)** — `id, user_id, feature, request, retrieval (JSON), response, latency_ms, tokens, cost_estimate, feedback (-1|0|1), faithfulness_score, created_at`. 🟡
92. **Register the model** in `models/__init__.py` + index on `(user_id, created_at)`. 🟡
93. **Instrument every AI surface** — tutor, agents, grading, explanations, summaries, recommendations all write to `ai_logs` (extend the existing logging pattern). 🟡
94. **Collect quality signals** — user thumbs (Phase 7), faithfulness checks (Group 3), retrieval eval metrics (Phase 3). 🟡
95. **Add the weekly report job** — cost, latency p95, quality trends, top failures (on `kb_jobs`, coalesced notification). 🟡
96. **Add `prompt_versions` support** — versioned prompt templates (new table) so prompts are A/B-able. 🟡
97. **Add `GET /api/kb/observability` (admin/teacher-guarded)** — the dashboard payload (cost, latency, feedback, eval). 🟡
98. **Write `backend/tests/test_kb_observability.py`** — logging on interactions, feedback aggregation, weekly report content, A/B versioning. 🟡
99. **Frontend:** observability dashboard (charts) + weekly report view for admins. 🟡
100. **Docs:** mark Ideas 91–100 done — **all 100 ideas of the master plan complete**; add the final runbook + platform checklist. 🟡

---

## Definition of Done — Phase 10

- [x] The orchestrator composes specialist agents (retriever, summarizer, quizzer, tutor, scheduler, health-checker) with budget guardrails; `agent_runs` is recorded.
- [x] Episodic memory appends from `learning_events`, consolidates weekly into durable facts, and folds into `user_memory`.
- [x] RAG runs as composable stages (rewrite → multi-stage retrieve → rerank → verify citations → faithfulness), with a "not found" fallback when ungrounded.
- [x] Graph+vector fusion expands vector hits via graph neighbors, reranks, and feeds prerequisite chains into prompts.
- [x] A per-user context bundle (subject, deadlines, recent topics) is injected and user-overridable.
- [x] The research assistant summarizes papers, extracts contributions, suggests related papers, and answers with citations.
- [x] The recommendation engine ranks cross-domain candidates with explainable reasons; feedback is logged.
- [x] Goals link to roadmaps; weekly reflections are generated, pushed, and can trigger plan adjustments.
- [x] Per-subject trajectories forecast readiness with early at-risk alerts.
- [x] Every AI interaction logs to `ai_logs`; weekly reports + A/B prompt versions drive improvement.
- [x] All steps respect `KB_DAILY_GEN_LIMIT`; deterministic fallbacks work with `AI_ENABLED=false`; every query is user-scoped.

## Verification checklist

```bash
# Backend: Phase 10 test suite (run from backend/)
python -m pytest tests/test_kb_agents.py tests/test_kb_longterm_memory.py \
  tests/test_kb_rag_hardening.py tests/test_kb_graph_fusion.py tests/test_kb_context.py \
  tests/test_kb_research.py tests/test_kb_recommendations.py tests/test_kb_goals_reflection.py \
  tests/test_kb_forecast.py tests/test_kb_observability.py -q

# Full regression — the entire suite (Phases 1–9 + everything existing)
python -m pytest tests/ -q

# Eval harness must hold steady (Phase 3 golden sets)
python -m app.cli.kb eval

# Manual smoke test
# 1. POST /api/kb/agents/run "prepare me for Thursday's exam using my weakest topics"
# 2. Ask the tutor a question → search with mode=graph_fused → prerequisite chains in context
# 3. POST /api/kb/research/explain {arxiv_id} → summary + contributions + related papers
# 4. GET /api/kb/recommendations → explainable cross-domain items; give feedback
# 5. GET /api/kb/forecast/{subject_id} → trajectory + readiness; check at-risk alerts
# 6. GET /api/kb/observability (admin) → cost/latency/quality dashboard populated

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **This is the final phase** — completing it marks all 100 master-plan ideas as done; the master plan's §15 Milestones M1–M8 and §16 success metrics are the acceptance criteria.
- **Observability is the meta-feature (Rule A):** nothing ships without `ai_logs`; the self-improvement loop (Idea 100) compounds every other phase.
- **Schema stability is a hard contract:** `user_memory` (Phase 8) and `learning_events` (Phase 6) feed Ideas 92 and 99 — changes to them require updating both consumers in the same change.
- **Reuse over rebuild:** agents wrap existing services (no new LLM engines); RAG stages wrap the Phase 3 pipeline; the research assistant reuses `arxiv.py` + summaries + citations; recommendations extend Phase 8 Idea 75.
- **Per-user scoping is non-negotiable** — every agent run, memory row, log entry, and forecast filters `user_id`; ownership tests mirror `test_ownership.py`.

