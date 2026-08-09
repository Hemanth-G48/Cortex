# Second Brain Integration — Phase 9 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 9 — Automation (Ideas 81–90)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1–8 plans
(`SECOND_BRAIN_PHASE{1,2,3,4,5,6,7,8}_100_PHRASE_PLAN.md`).

**Implementation status: ✅ COMPLETE** — all ten ideas landed. Backend:
`automation.py` registry/runner + ten feature modules (`auto_categorize`,
`auto_tag`, `auto_link`, `auto_duplicates`, `auto_flashcards`, `auto_summary`,
`auto_mindmap`, `auto_plan_sync`, `auto_sync`, `auto_revision`); `kb_automation`
router (`GET /api/kb/automation/jobs`, `POST /api/kb/automation/run`); sync
endpoints on `kb_sources` (`POST /api/kb/sources/{id}/sync`, `GET
.../sync-status`); `source` column on flashcard candidates + `summary_dirty`
hook in the ingest pipeline; 10 test files (Ideas 81–90). Frontend: automation
job cards with run buttons, per-source sync status + "Sync now", and the
Phase 9 endpoint block in `api.ts`. All `KB_AUTO_*` toggles default OFF.

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (7): Idea 81 (auto-categorize), 82 (scheduled auto-tag), 84 (scheduled dupes), 87 (scheduled mind maps), 88 (plan sync), 89 (external sync), 90 (auto revision tasks)
- 🟡 partial / extends existing code (3): Ideas 83, 85, 86 wrap existing proposal machinery (auto-link edges, flashcard candidates, summaries) as background jobs

**Prerequisites: Phases 1–8 must be complete** — this phase is the **scheduled job layer** over
everything built so far: the Phase 1 job queue + ingest pipeline, Phase 2 auto-tag/edge machinery,
Phase 4 summaries/flashcards/mind maps, Phase 5 roadmaps, Phase 6 `revision_schedule`/sessions,
and Phase 8 connect/adapt machinery.

**Scope:** Background jobs that auto-categorize, auto-tag, auto-link, auto-dedupe, auto-flashcard,
auto-summarize, auto-mind-map, auto-sync plans and external repositories, and auto-create revision
tasks — every one producing *reviewable proposals*, never silent writes. **Advanced AI, analytics
and platform hardening are Phase 10 and out of scope.**

**The one unifying pattern (used by every idea in this phase):**
> **Batch job** (runs on `kb_jobs`, respects `KB_DAILY_GEN_LIMIT`) → **proposals** (queued rows
> with provenance) → **user review queue** (batch approve/reject) → **applied with version-history
> logging**. Nothing commits without review; every job is a config toggle.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 9 reuses |
|---|---|---|
| Job queue | Phase 1 Idea 10 (`kb_jobs`, threadpool, resume) | The scheduler substrate every automation job runs on |
| Ingest pipeline | Phase 1 Group 10 (extract → OCR → dedupe → version → chunk) | Hook points for auto-categorize / flashcard candidates |
| Version history | Phase 1 Idea 9 (`kb_versions`) | Log moves/folder changes from categorization |
| Exact + near dupes | Phase 1 Idea 8 + Phase 2 Idea 19 | The detectors Idea 84 wraps as a nightly job |
| Auto-tag proposals | Phase 2 Idea 14 (`kb_tags`, provenance) | Idea 82's core; add the scheduled driver |
| Auto-link / connect | Phase 2 Idea 17 + Phase 8 Idea 76 | Idea 83's edge-proposal machinery |
| Summaries | Phase 4 Idea 31 (`KbSummary`, cache, hash) | Idea 86's core + `dirty` tracking |
| Flashcards | Phase 4 Idea 34 (candidate review queue) | Idea 85's core + concept hook |
| Mind maps | Phase 4 Idea 38 (`mindmap.py`, outline cache) | Idea 87's core |
| Roadmaps + adapt | Phase 5 Idea 47 + Phase 8 Idea 80 | Idea 88's plan-revision machinery |
| Revision scheduler | Phase 6 Idea 52 (`revision_schedule`) + Idea 60 sessions | Idea 90's source of due tasks |
| Source registry | Phase 1 Idea 2 (`kb_sources`) | Idea 89's adapter registry |
| Budget guard | `KB_DAILY_GEN_LIMIT` (Phase 4) | Every LLM-driven job is capped per run |
| Notifications / reminders / tasks | existing routers | Plan-change alerts + revision-task materialization |

**File conventions:** services → `backend/app/services/kb/automation.py` (registry + runner) +
per-feature modules; routers → `backend/app/routers/kb_automation.py`; tests →
`backend/tests/test_kb_*.py`. All `KB_AUTO_*` config toggles live in `config.py` in a commented
section. Every new table is user-scoped and registered in `models/__init__.py`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---


---

## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))

Every idea in Phase 9 (Automation) has reusable components in the cloned reference repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.

- **Idea 81 — Auto-categorize new notes:** CortX (agent structuring) · obsidian-second-brain (obsidian-board) · My-Brain-Is-Full-Crew (sorter agent) · claude-obsidian (wiki-fold skill)
- **Idea 82 — Auto-tag documents (scheduled):** My-Brain-Is-Full-Crew (sorter/scribe) · khoj (grouping)
- **Idea 83 — Auto-link related notes (scheduled):** llm_wiki · claude-obsidian · obsidian-second-brain (obsidian-connect) · My-Brain-Is-Full-Crew (connector)
- **Idea 84 — Auto-detect duplicates (scheduled):** hashcards · engram
- **Idea 85 — Auto-create flashcards from new notes:** LearnKit · mimocard · yt-flashcard-ai · StudyWise · studybuddy-ai
- **Idea 86 — Auto-create summaries (scheduled):** memora · StudyWise · khoj
- **Idea 87 — Auto-generate mind maps (scheduled):** second_brain_builder · StudyWise (concept-map) · mind-mentor
- **Idea 88 — Auto-update study plans on new materials:** study-planner-agent · syllabo · OrbitOS
- **Idea 89 — Auto-sync external repositories:** glean (RSS) · khoj (github_to_entries.py) · llm_wiki (file-sync.ts) · obsidian-wiki (sync.py)
- **Idea 90 — Auto-create revision tasks:** obsidian-spaced-repetition · LearnKit · py-fsrs (due cards)

> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines (khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, dendron. Repos without a license file are STUDY only.

## Group 1 — Idea 81 🔴: Auto-categorize new notes (phrases 1–10)

1. **Create `app/services/kb/categorize.py`** — proposes a folder/category per document: by source, subject (Phase 5 topics), or tag. 🔴
2. **Apply deterministic rules first** — folder-name patterns (e.g. existing vault folders from `kb_sources`) + the existing taxonomy; no LLM needed for clear cases. 🔴
3. **LLM category proposal for ambiguous docs** — `generate_json` with a fixed category list (budget-capped, `KB_DAILY_GEN_LIMIT`). 🔴
4. **Define the `CategorizeSuggestion` model (`categorize_suggestions`)** — `id, user_id, document_id, proposed_path, rule (rule|ai), status (pending|accepted|rejected), created_at`. 🔴
5. **Register the model** in `models/__init__.py`. 🔴
6. **Wire the hook into the Phase 1 ingest pipeline** — post-chunking stage queues a suggestion for new documents. 🔴
7. **Add batch review endpoints** — `GET /api/kb/categorize/queue` + `POST …/accept` (bulk) / `…/reject`. 🔴
8. **Log accepted moves to version history** — Phase 1 `kb_versions` records the path change (auditable undo). 🔴
9. **Write `backend/tests/test_kb_auto_categorize.py`** — rule priority, LLM fallback (mocked), bulk accept, version logging. 🔴
10. **Frontend:** batch categorization review queue (proposed path + accept/reject chips). 🔴


## Group 2 — Idea 82 🔴: Auto-tag documents — scheduled (phrases 11–20)

11. **Create the nightly auto-tag job** — scans documents with no tags (or untagged since last run), reusing the Phase 2 Idea 14 proposal service. 🔴
12. **Cap docs per night** — `KB_AUTO_TAG_PER_NIGHT` (default 20) respected against `KB_DAILY_GEN_LIMIT` so the budget is shared safely. 🔴
13. **Store proposals with provenance** — `kb_tags` rows (kind auto, `provenance=ai|rule`) in a pending state, not committed. 🔴
14. **Add `GET /api/kb/tags/queue`** — the nightly proposal list for batch diff-review. 🔴
15. **Add `POST /api/kb/tags/queue/accept` (bulk) / `…/reject`** — applies or discards the night's proposals. 🔴
16. **Add the `KB_AUTO_TAG_ENABLED` config toggle** (default False) + job registration in the automation runner. 🔴
17. **Write `backend/tests/test_kb_auto_tag_job.py`** — nightly selection, per-night cap, provenance, bulk accept/reject, idempotent re-run. 🔴
18. **Frontend:** tag review queue (per-doc proposed chips, confirm-all / reject-all). 🔴
19. **api.ts:** `endpoints.kb.tags.queue` (list/accept/reject). 🔴
20. **Log job stats to `kb_jobs`** — docs scanned, proposed, accepted. 🔴


## Group 3 — Idea 83 🟡: Auto-link related notes — scheduled (phrases 21–30)

21. **Create the periodic auto-link job** — embedding-cluster pass over documents, reusing the Phase 8 Idea 76 connect machinery. 🟡
22. **Cluster by embedding similarity** — batch embed + cluster (Phase 2 store); candidates = pairs above `KB_SIM_THRESHOLD` (Phase 2 Idea 17). 🟡
23. **Auto-create high-confidence edges** — pairs above a high bar (config `KB_AUTO_LINK_CONFIDENCE`) become `RELATED`/`BACKLINK` edges with `provenance=auto`. 🟡
24. **Queue low-confidence pairs** — below the bar → pending `edge` proposals for review (new small table or reuse `kb_edges.status`). 🟡
25. **Add `GET /api/kb/links/queue` + `POST …/accept|reject`** — the edge review queue. 🟡
26. **Add the `KB_AUTO_LINK_ENABLED` toggle** (default False) + `KB_AUTO_LINK_PER_RUN` cap. 🟡
27. **Write `backend/tests/test_kb_auto_link.py`** — clustering, threshold split (auto vs pending), bulk review, existing-edge dedupe. 🟡
28. **Frontend:** pending-edge review list (source → target with similarity). 🟡
29. **api.ts:** `endpoints.kb.links.queue` (list/accept/reject). 🟡
30. **Run as a `kb_jobs` job** — incremental (only new/changed docs since last pass). 🟡


## Group 4 — Idea 84 🔴: Auto-detect duplicates — scheduled (phrases 31–40)

31. **Create the nightly duplicate-scan job** — exact pass via the `content_hash` index (Phase 1 Idea 8) + near pass via sampled embedding pairs (Phase 2 Idea 19). 🔴
32. **Cap the scan** — `KB_AUTO_DUPE_PER_NIGHT` (pairs sampled) so the nightly cost stays bounded. 🔴
33. **Queue duplicate candidates** — `duplicate_of_id`, similarity, and match kind (exact|near) in a reviewable list. 🔴
34. **Add `GET /api/kb/dupes/queue` + `POST …/{id}/merge`** — merge moves content (keep canonical, re-point edges, keep version history). 🔴
35. **Add `POST …/{id}/archive|dismiss`** — non-merge resolutions. 🔴
36. **Add the `KB_AUTO_DUPE_ENABLED` toggle** (default False). 🔴
37. **Write `backend/tests/test_kb_auto_dupes.py`** — exact + near detection, merge mechanics (edges re-pointed, versions preserved), dismiss dedupe. 🔴
38. **Frontend:** duplicate review queue with diff preview (side-by-side). 🔴
39. **api.ts:** `endpoints.kb.dupes.queue` (list/merge/archive/dismiss). 🔴
40. **Exclude merged duplicates from retrieval** by default (Phase 2 Idea 19 flag). 🔴


## Group 5 — Idea 85 🟡: Auto-create flashcards from new notes (phrases 41–50)

41. **Hook after concept extraction** — when a new document gains `MENTIONS` (Phase 2 Idea 15), flag it as flashcard-eligible. 🟡
42. **Reuse the Phase 4 Idea 34 candidate generator** — same Q/A extraction, same review queue, same card-hash dedupe. 🟡
43. **Only concept-bearing notes qualify** — documents with zero `MENTIONS` are skipped (no value in carding trivia). 🟡
44. **Queue candidates automatically** — `KbFlashcardCandidate` rows with `source=auto`, pending approval before any deck write. 🟡
45. **Add the `KB_AUTO_FLASHCARDS_ENABLED` toggle** (default False) + per-run cap. 🟡
46. **Write `backend/tests/test_kb_auto_flashcards.py`** — eligibility gate, candidate queueing, dedupe against existing cards, approve→deck. 🟡
47. **Frontend:** reuse the Phase 4 flashcard review queue (auto candidates marked). 🟡
48. **api.ts:** reuse `endpoints.kb.flashcards.review`. 🟡
49. **Budget-capped generation** against `KB_DAILY_GEN_LIMIT`. 🟡
50. **Log candidates per job to `kb_jobs`** for visibility. 🟡


## Group 6 — Idea 86 🟡: Auto-create summaries — scheduled (phrases 51–60)

51. **Add a `summary_dirty` flag to `KbDocument`** (via `COLUMN_MIGRATIONS`) set on content-hash change. 🟡
52. **Create the nightly summary job** — scans `summary_dirty=true` docs, reusing the Phase 4 Idea 31 `summarize` service. 🟡
53. **Respect `KB_DAILY_GEN_LIMIT`** — prioritize by importance: changed docs first, then high-view-count docs, capped per night (`KB_AUTO_SUMMARY_PER_NIGHT`). 🟡
54. **Cache invalidation handled by the hash** — unchanged docs never re-summarized. 🟡
55. **Add the `KB_AUTO_SUMMARY_ENABLED` toggle** (default False). 🟡
56. **Write `backend/tests/test_kb_auto_summaries.py`** — dirty-flag selection, priority ordering, per-night cap, no-op on unchanged docs. 🟡
57. **Frontend:** "summary ready" indicator on document cards (pre-generated). 🟡
58. **api.ts:** no new endpoints — summaries served by the Phase 4 endpoint. 🟡
59. **Log job stats to `kb_jobs`** — scanned, summarized, skipped (budget). 🟡
60. **Fallback generation is deterministic** — `AI_ENABLED=false` still produces heading-based summaries within the cap. 🟡


## Group 7 — Idea 87 🔴: Auto-generate mind maps — scheduled (phrases 61–70)

61. **Create the batch mind-map job** — runs the Phase 4 Idea 38 `mindmap.py` pipeline over qualifying documents. 🔴
62. **Qualify by structure** — documents with more than `KB_AUTO_MINDMAP_MIN_HEADINGS` (default 4) headings are eligible. 🔴
63. **Cache the outline in `outline_json`** — pre-generated trees load instantly (no render-time latency). 🔴
64. **Skip unchanged docs** — hash check makes the job a cheap no-op on stable vaults. 🔴
65. **Add the `KB_AUTO_MINDMAP_ENABLED` toggle** (default False). 🔴
66. **Note: no LLM cost** — mind maps derive from the outline (headings + concepts), so the budget guard doesn't apply; the job is CPU/IO-bound. 🔴
67. **Write `backend/tests/test_kb_auto_mindmap.py`** — eligibility, outline caching, hash-skip, idempotent re-run. 🔴
68. **Frontend:** document cards show a "map available" affordance; opening is instant. 🔴
69. **api.ts:** reuse `endpoints.kb.mindmap` (cached output). 🔴
70. **Log job stats to `kb_jobs`.** 🔴


## Group 8 — Idea 88 🔴: Auto-update study plans on new materials (phrases 71–80)

71. **Rerun the topic-coverage mapper on material ingest** — new chunks that mention a Phase 5 topic change its coverage count. 🔴
72. **Recompute time estimates** — coverage change → Phase 5 Idea 49 estimate refresh (better coverage can shrink `first_pass_mins`). 🔴
73. **Revise plans only when deltas exceed a threshold** — `KB_PLAN_DELTA_THRESHOLD` (e.g. ±20% on a topic's estimate or mastery shift) prevents plan churn. 🔴
74. **Reuse the Phase 8 Idea 80 adapt machinery** — same versioned roadmap update + diff computation. 🔴
75. **Notify on meaningful changes** — via the existing notifications router ("plan updated for X"). 🔴
76. **Add the `KB_AUTO_PLAN_SYNC_ENABLED` toggle** (default False) + trigger wiring in the ingest job. 🔴
77. **Write `backend/tests/test_kb_auto_plan_sync.py`** — coverage rerun, estimate recompute, delta threshold, plan revision, notification. 🔴
78. **Frontend:** "plan updated" banner (reuse the Phase 8 diff view). 🔴
79. **api.ts:** reuse `endpoints.subjects.roadmap` (new version). 🔴
80. **No-op below threshold** — assert nothing changes for small deltas. 🔴


## Group 9 — Idea 89 🔴: Auto-sync external repositories (phrases 81–90)

81. **Extend the `kb_sources` registry (Phase 1 Idea 2) with a `sync_type` field** — `git|drive|clip|none`, via `COLUMN_MIGRATIONS`. 🔴
82. **Add a per-source sync cursor** — last-synced state (commit hash / Drive cursor / clip id) so only deltas import. 🔴
83. **Create the git adapter** — clone/pull, diff files since cursor, import changed files through the normal ingest pipeline. 🔴
84. **Create the Drive adapter** — list + download changed files (API, read-only scopes), map mime → `EXTRACTABLE_TYPES`. 🔴
85. **Create the clip adapter** — import saved web clippings (title/url/content → markdown document). 🔴
86. **Implement the conflict policy** — newest `mtime`/revision wins; superseded content preserved in `kb_versions` (Phase 1 Idea 9). 🔴
87. **Add `POST /api/kb/sources/{id}/sync` + `GET …/sync-status`** — manual trigger + last-sync state per source. 🔴
88. **Write `backend/tests/test_kb_sync.py`** — mock git/drive/clip adapters; delta-only import; conflict resolution; version logging. 🔴
89. **Add the `KB_SYNC_ENABLED` toggle** (default False) + per-source-type config. 🔴
90. **Frontend:** source cards show sync status + "Sync now". 🔴


## Group 10 — Idea 90 🔴: Auto-create revision tasks (phrases 91–100)

91. **Create the daily revision-materialization job** — `revision_schedule` rows with `due_date <= today` become tasks (extend the Phase 6 Idea 52 materializer). 🔴
92. **Task fields** — title (topic), deep link (topic/unit view), estimated time from Phase 5 Idea 49 estimates. 🔴
93. **Attach reminders** — via the existing reminders router, aligned to the task due date. 🔴
94. **Optionally wrap as micro-sessions** — when the topic has a recommended chunk, create a Phase 6 Idea 60 session instead of a bare task. 🔴
95. **Feed completions back** — finishing the task marks the review graded → SM-2 update (Phase 6 Idea 52). 🔴
96. **Add the `KB_AUTO_REVISION_TASKS_ENABLED` toggle** (default False). 🔴
97. **Write `backend/tests/test_kb_auto_revision_tasks.py`** — due selection, task creation fields, reminder wiring, completion→grade loop, idempotency. 🔴
98. **Frontend:** revision tasks appear on the calendar/dashboard with topic links. 🔴
99. **api.ts:** no new endpoints — tasks reuse the existing tasks API. 🔴
100. **Docs:** mark Ideas 81–90 done in the master plan; add the Phase 9 runbook (scheduler, toggles, budgets, review queues). 🔴

---

## Definition of Done — Phase 9

- [x] Every automation feature is a `kb_jobs` batch job behind a `KB_AUTO_*` toggle, default off.
- [x] Auto-categorization proposes folders (rules first, LLM for ambiguity), batches for review, and logs moves to version history.
- [x] The nightly tag job caps itself per night, stores provenance, and lands through a batch accept/reject queue.
- [x] Auto-linking creates only high-confidence edges automatically; low-confidence pairs wait in a review queue.
- [x] The nightly duplicate scan (exact + near) queues merges that re-point edges and preserve version history.
- [x] Concept-bearing notes auto-queue flashcard candidates (deduped, `source=auto`) into the existing review flow.
- [x] The nightly summary job respects the daily budget, prioritizes changed/high-view docs, and never redoes unchanged ones.
- [x] Mind maps pre-generate into a cached tree (`metadata_json`) with no LLM cost for structured documents only.
- [x] New materials re-sync plans only when deltas exceed a threshold, with notifications and versioned roadmap diffs.
- [x] External repos (git/Drive/clips) sync delta-only behind per-source cursors with a newest-wins conflict policy.
- [x] Due revision rows materialize as tasks/reminders/sessions daily; completion feeds back into SM-2 scheduling.
- [x] All LLM jobs respect `KB_DAILY_GEN_LIMIT`; every queue and table is user-scoped.

## Verification checklist

```bash
# Backend: Phase 9 test suite (run from backend/)
python -m pytest tests/test_kb_auto_categorize.py tests/test_kb_auto_tag_job.py \
  tests/test_kb_auto_link.py tests/test_kb_auto_dupes.py tests/test_kb_auto_flashcards.py \
  tests/test_kb_auto_summaries.py tests/test_kb_auto_mindmap.py tests/test_kb_auto_plan_sync.py \
  tests/test_kb_sync.py tests/test_kb_auto_revision_tasks.py -q

# Full regression (Phases 1–8 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. Enable KB_AUTO_TAG_ENABLED → run the nightly job → queue fills → bulk accept
# 2. Ingest a new concept-bearing note → flashcard candidates appear (auto)
# 3. Run the dupe scan → merge a pair → edges re-point, versions intact
# 4. Trigger /api/kb/sources/{id}/sync on a git source → deltas import, status updates
# 5. Add a due revision → daily job creates the task with link + estimate

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phase 10 is out of scope:** advanced AI, analytics, and platform hardening (Ideas 91–100) — this phase delivers the automation layer they will observe and report on.
- **Nothing auto-commits without review** — the unifying pattern is: batch job → proposals (with provenance) → review queue → apply with version logging. Silent writes are forbidden.
- **Every automation is a config toggle, default off** — `KB_AUTO_*` flags so adoption is gradual and CI stays hermetic.
- **Mind maps are the one no-LLM job** (outline-derived) — noted explicitly so the budget guard isn't misapplied.
- **Reuse over rebuild:** jobs wrap existing services (Phase 2 tags/edges, Phase 4 flashcards/summaries/mind maps, Phase 8 connect/adapt); no parallel implementations.
- **Per-user scoping is non-negotiable** — every queue, proposal, and job result filters `user_id`; ownership tests mirror `test_ownership.py`.

