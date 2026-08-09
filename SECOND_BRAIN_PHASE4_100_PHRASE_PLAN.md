# Second Brain Integration — Phase 4 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 4 — Note Intelligence & Content Generation (Ideas 31–40)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1–3 plans
(`SECOND_BRAIN_PHASE{1,2,3}_100_PHRASE_PLAN.md`).

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (4): Idea 36 (citation registry), 37 (concept linking UI), 38 (mind maps), 39 (note quality scoring)
- 🟡 partial / extends existing code (6): Ideas 31–35 and 40 extend the existing `summaries`, `quizzes`, `flashcards`, `daily_schedule`/`journal`, and `braindumps` machinery

**Implementation status: ✅ COMPLETE** — backend (71/71 Phase 4 tests) and frontend all landed.
Backend: `kb/summarize.py` · `kb/explain.py` · `kb/note_quizzes.py` · `kb/flashcards.py` ·
`kb/daily_notes.py` · `kb/citation_registry.py` · `kb/mindmap.py` · `kb/quality.py` ·
`kb/braindump_draft.py` + `budget.py` (the `KB_DAILY_GEN_LIMIT` guard), routers `kb_content.py`,
`kb_daily_notes.py`, `kb_citations.py`, `kb_edges.py`, `kb_mindmap.py`, `kb_quality.py`, and models
`kb_summaries`, `kb_quiz_links`, `kb_flashcard_candidates`, `kb_citations`, `kb_quality_suggestions`,
`kb_generation_log`.
Frontend: `SummaryPanel` / `ExplainPanel` / `MindMapView` / `QualityPanel` / `NoteActions` wired into the
Knowledge Base document drawer, citations list + BibTeX export, concept-linking panel (autocomplete + edge
delete), `/flashcard-review` + `/quality` pages, `TodayCaptures` on the Dashboard, and the brain-dump
"File as note" flow (title/source/tags + AI section split).

**Prerequisites: Phases 1–3 must be complete** — this phase consumes `kb_documents`
(`outline_json`, `doc_date`), `kb_chunks`, `kb_concepts`, `kb_edges` (`MENTIONS`, `RELATED`),
the search service (RAG grounding for explanations), and the persistent vector store. It also
reuses the existing curriculum-side generation services (`summaries.py`, `quizzes.py`,
`flashcard.py`, `ai_fallback.py`, `prompts.py`).

**Scope:** Vault-aware summaries, grounded AI explanations, quizzes and flashcards from your own
notes, daily-note ↔ schedule integration, a citation registry, manual concept linking, mind-map
rendering, note-quality scoring, and upgrading the brain-dump widget into the capture pipeline.
**Subject management, study planning, and the AI tutor are Phases 5–7 and out of scope** — the
content generation built here feeds them.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 4 reuses |
|---|---|---|
| Summary cache-then-generate | `backend/app/services/summaries.py` + `Summary` model (`key`-based cache) | The exact pattern to adapt for `kb_documents` (Idea 31) |
| Quiz generation + scoring | `backend/app/services/quizzes.py` + `Quiz`/`QuizAttempt` models | `generate_quiz` flow + `<50 chars → 422` gateway for note quizzes (Idea 33) |
| Flashcard decks | `backend/app/models/flashcard.py` (`FlashcardDeck`, `Flashcard` with `streak`/`next_review`) | Target model for note-derived cards (Idea 34) |
| Brain dump widget | `backend/app/models/braindump.py` (single row/user) + `braindumps` router | The dead-end textarea to upgrade into the capture pipeline (Idea 40) |
| Daily schedule + journal | `backend/app/routers/daily_schedule.py`, `journal` | Date-join targets for daily notes (Idea 35) |
| Prompt registry | `backend/app/services/prompts.py` | Add `kb_summary_prompt`, explanation variants, etc. |
| Hermetic AI fallbacks | `backend/app/services/ai_fallback.py` (`demo_quiz`, …) | Deterministic fallbacks so `AI_ENABLED=false` keeps working |
| Phase 1–3 outputs | KB docs/chunks/`outline_json`, `kb_concepts`, `kb_edges`, search service, `arxiv.py` | Citations (Idea 36), concepts (Idea 37), mind maps (Idea 38), quality (Idea 39), RAG grounding (Idea 32) |

**File conventions:** services → `backend/app/services/kb/{summarize,explain,flashcards,mindmap,quality}.py`;
routers → `backend/app/routers/kb_content.py` (or extend `kb_documents.py`); models →
`backend/app/models/kb/*.py`; tests → `backend/tests/test_kb_*.py`. Register every new router in
`main.py` and every model in `models/__init__.py`.

**Cost rule for all of Phase 4:** every generation path is budget-capped by `KB_DAILY_GEN_LIMIT`
(extending the existing `SUMMARY_DAILY_LIMIT` guard pattern) and must keep working via
deterministic fallback when `AI_ENABLED=false`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---


---

## Reference repos — what to borrow (from [REPOS_REUSE_ANALYSIS.md](./REPOS_REUSE_ANALYSIS.md))

Every idea in Phase 4 (Note Intelligence & Content Generation) has reusable components in the cloned reference repos under `similar_repos/<owner>/<repo>`. Open the listed files directly and adapt them — full per-repo detail (exact paths, reuse modes) is in `REPOS_REUSE_ANALYSIS.md`.

- **Idea 31 — AI summaries of notes & papers:** memora (generatorGPT.py) · StudyWise (notes page) · khoj (summarize) · EduAI (chat app)
- **Idea 32 — AI explanations (ELI5, analogies, derivations):** StudyWise (eli5 page) · mind-mentor
- **Idea 33 — AI quizzes generated from notes:** EduAI (practice app) · StudyWise (quiz) · studybuddy-ai · memora · Multi-Agent-Study-Assistant (quiz gen) · infinition (quiz modals)
- **Idea 34 — Flashcards generated from notes:** LearnKit (engine/scheduler) · obsidian-spaced-repetition · hashcards · mimocard · memo · recalla · yt-flashcard-ai · studybuddy-ai · org-fc
- **Idea 35 — Daily notes integration:** obsidian-second-brain (obsidian-daily command) · My-Brain-System · OrbitOS · obsidian-claude-pkm
- **Idea 36 — Citation management:** claude-obsidian (contracts.py/ledgers.py) · obsidian-wiki
- **Idea 37 — Concept linking UI:** llm_wiki (page-links-panel.tsx) · mind-mentor (knowledge graph) · obsidian-wiki
- **Idea 38 — Mind-map generation:** second_brain_builder (mermaid output) · StudyWise (concept-map) · mind-mentor · obsidian-second-brain (obsidian-architect)
- **Idea 39 — Note quality scoring:** claude-obsidian (lint_engine.py) · PAIDEIA (doctor.py) · obsidian-wiki (lint.py)
- **Idea 40 — Brain dump → structured notes:** CortX (cortx_extractor.py + agent) · second_brain_builder (generation modals) · claude-obsidian (capture.py) · obsidian-second-brain (obsidian-capture)

> ⚠️ **License check before reuse:** per `REPOS_REUSE_ANALYSIS.md`, the big PKM engines (khoj, anki, basic-memory, siyuan, reor, orbit) are **AGPL/BUSL — STUDY only, never vendor**. Port-friendly (MIT/Apache): py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, obsidian-spaced-repetition, infinition, LearnKit, org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, claude-obsidian, obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, foam, dendron. Repos without a license file are STUDY only.

## Group 1 — Idea 31 🟡: AI summaries of notes & papers (phrases 1–10)

1. **Add `KB_DAILY_GEN_LIMIT` (default 20) to `config.py`** — the Phase 4 budget cap for all content generation, extending the `SUMMARY_DAILY_LIMIT` guard pattern. 🟡 ✅ `KB_DAILY_GEN_LIMIT` in config.py + `kb/budget.py` guard
2. **Define the `KbSummary` model (`kb_summaries`)** — `id, user_id, document_id (FK, unique), content, key_points (JSON), definitions (JSON), open_questions (JSON), model, content_hash, created_at, updated_at`. 🟡
3. **Register `KbSummary` in `models/__init__.py`**; new table via `create_all`, column ALTERs via `COLUMN_MIGRATIONS`. 🟡
4. **Create `app/services/kb/summarize.py`** adapting the `summaries.py` pattern — cache by `content_hash` first, generate only on miss or content change. 🟡
5. **Add `kb_summary_prompt` to `prompts.py`** — structured output (TL;DR, key points, definitions, open questions) via `generate_json`. 🟡
6. **Build the document content source** — reuse the Phase 1 chunk text (joined, heading-prefixed) rather than raw `extracted_text`. 🟡
7. **Add `GET /api/kb/documents/{id}/summary` and `POST …/summary` (regenerate)** — per-user, returning the structured summary + `cached` flag (mirror the existing summaries response shape). 🟡 ✅ `kb/summarize.py`
8. **Deterministic fallback** — when `AI_ENABLED=false`: TL;DR = first heading + first N chars, key points = heading list (extend `ai_fallback.py`). 🟡
9. **Write `backend/tests/test_kb_summarize.py`** — cache hit, regenerate on hash change, budget cap, fallback shape, per-user isolation. 🟡
10. **Frontend:** summary panel on the document detail page (cached notice + regenerate button), wired via `endpoints.kb.documents.summary`. 🟡 ✅ `SummaryPanel.tsx`


## Group 2 — Idea 32 🟡: AI explanations — ELI5, analogies, derivations (phrases 11–20)

11. **Create `app/services/kb/explain.py`** — the explanation orchestrator: retrieve → prompt → generate → verify citations. 🟡
12. **Add `POST /api/kb/explain`** — `{concept, depth (overview|deep_dive|eli5|analogy|derivation), document_ids?}` per-user. 🟡 ✅ `kb/explain.py`
13. **Retrieve grounding chunks first** — reuse the Phase 3 `KbSearcher` to pull chunks covering the concept (hybrid mode). 🟡
14. **Add the explanation prompt variants to `prompts.py`** — one registry entry per depth, each demanding inline citations `[n]` mapped to chunk ids. 🟡
15. **Enforce mandatory citations** — response must include a `citations` list; a post-check rejects/regenerates once if missing (budget-aware). 🟡
16. **Incorporate `user_memory` strengths (stub)** — the Phase 8 seam (Idea 79): pass known/weak concepts if present, else omit. 🟡
17. **Deterministic fallback** — when `AI_ENABLED=false`: definition from `kb_concepts` + a short excerpt of the top chunk (no hallucination risk). 🟡
18. **Budget-cap every explanation** — count against `KB_DAILY_GEN_LIMIT`; return 429-style error with a clear message when exhausted. 🟡
19. **Write `backend/tests/test_kb_explain.py`** — mocked retrieval + generation, citation presence/absence handling, depth variants, fallback, budget. 🟡
20. **Frontend:** explanation panel on document/concept views with a depth selector; citations rendered as clickable source links. 🟡 ✅ `ExplainPanel.tsx`


## Group 3 — Idea 33 🟡: AI quizzes generated from notes (phrases 21–30)

21. **Add `POST /api/kb/quizzes`** — `{document_id | chunk_ids, num_questions, difficulty}` per-user, returning the existing `Quiz` schema so the Quiz UI works unchanged. 🟡 ✅ `kb/note_quizzes.py` + `KbQuizLink`
22. **Build a chunk content source for quizzes** — gather the document's chunk text (heading-prefixed) instead of `extract_text_for_units`. 🟡
23. **Reuse `generate_quiz`'s gateway** — content < 50 chars → 422 "Not enough material" (mirror `quizzes.py`). 🟡
24. **Reuse the `quiz_prompt` + `demo_quiz` fallback** — no new generation logic needed; just a new content adapter. 🟡
25. **Add the `KbQuizLink` model (`kb_quiz_links`)** — `quiz_id ↔ kb_document_id` traceability, per-user, for provenance. 🟡
26. **Record the link on quiz creation** — the note that generated a quiz stays traceable from both sides. 🟡
27. **Budget-cap generation** against `KB_DAILY_GEN_LIMIT` (shared with summaries). 🟡
28. **Write `backend/tests/test_kb_quizzes.py`** — note → quiz happy path (mocked), min-content 422, link recorded, fallback quiz. 🟡
29. **Frontend:** "Generate quiz from this note" button on the document detail → navigates to the existing Quiz page with the fresh quiz. 🟡 ✅ `NoteActions.tsx` → `/quiz`
30. **api.ts:** `endpoints.kb.quizzes.generate(documentId, …)`. 🟡


## Group 4 — Idea 34 🟡: Flashcards generated from notes (phrases 31–40)

31. **Add `POST /api/kb/documents/{id}/flashcards`** — generates *candidate* Q/A pairs from the document's concept-rich chunks. 🟡 ✅ `kb/flashcards.py`
32. **Create `app/services/kb/flashcards.py`** — candidate extraction via `generate_json` (`{question, answer, source_chunk_id}`), capped by budget. 🟡
33. **Store candidates in a review queue** — new `KbFlashcardCandidate` model (`status=pending`, per-user) so nothing enters decks un-reviewed. 🟡
34. **Dedupe against existing cards** — normalize questions (lowercase, strip punctuation); skip already-covered candidates. 🟡
35. **Auto-select or create the target deck** — use an existing `FlashcardDeck` or create "From notes" (reuse the `flashcard.py` model). 🟡
36. **Add `POST /api/kb/flashcards/review`** — approve (creates `Flashcard` rows in the deck) or reject candidates in bulk. 🟡
37. **Deterministic fallback** — when `AI_ENABLED=false`: definition-from-`kb_concepts` Q/A pairs (`What is X?` → definition). 🟡
38. **Write `backend/tests/test_kb_flashcards.py`** — candidate generation (mocked), dedupe, approve→deck, reject, fallback. 🟡
39. **Frontend:** flashcard review queue page (approve/reject chips) + "Generate cards" button on document detail. 🟡 ✅ `FlashcardReview.tsx`
40. **api.ts:** `endpoints.kb.flashcards.generate` + `endpoints.kb.flashcards.review`. 🟡


## Group 5 — Idea 35 🟡: Daily notes integration (phrases 41–50)

41. **Confirm daily-note detection** — Phase 1 already stores `doc_date` for `YYYY-MM-DD.md` filenames; backfill any missing values via the reindex CLI. 🟡
42. **Auto-tag daily notes** — when ingesting a daily note, create/attach tag `daily/YYYY-MM-DD` (`kind=rule`, auto). 🟡
43. **Create the date-join service** (`app/services/kb/daily_notes.py`) — pulls vault docs by `doc_date`, `daily_schedule_items`, and journal entries for a given date. 🟡
44. **Add `GET /api/kb/daily-notes?date=`** — aggregated `{date, documents[], schedule[], journal[]}` per-user. 🟡 ✅ `kb/daily_notes.py`
45. **Add `GET /api/kb/daily-notes/today`** — convenience wrapper using server date. 🟡
46. **Build the "What I captured today" widget** — dashboard/today component showing vault captures alongside the schedule (extend the existing Dashboard page). 🟡 ✅ `TodayCaptures.tsx` on Dashboard
47. **Add capture-to-daily-note quick action** — new vault captures surface on the matching day automatically (via `doc_date`). 🟡
48. **Write `backend/tests/test_kb_daily_notes.py`** — date join, auto-tag, today endpoint, per-user isolation. 🟡
49. **Frontend:** the Today/Dashboard widget + a date-picker drill-down into any day's captures. 🟡
50. **api.ts:** `endpoints.kb.dailyNotes(date)` + `endpoints.kb.dailyNotes.today()`. 🟡


## Group 6 — Idea 36 🔴: Citation management — BibTeX & paper citations (phrases 51–60)

51. **Define the `KbCitation` model (`kb_citations`)** — `id, user_id, document_id, cite_key, title, authors (JSON), year, venue, doi, arxiv_id, raw_text, created_at` with unique `(user_id, cite_key)`. 🔴
52. **Register `KbCitation` in `models/__init__.py`**; add a `CITES` relation to the `kb_edges` vocabulary. 🔴
53. **Parse reference lists from paper PDFs** — heuristic section detection ("References"/"Bibliography") + line regex over extracted text (Phase 1 page-aware extraction). 🔴
54. **Parse `@cite`/`[[cite:key]]` syntax in markdown** — citations referenced inline get linked to the registry. 🔴
55. **Enrich with metadata lookup** — DOI/arXiv id → title/authors/year (reuse Phase 1 `arxiv.py`; DOI lookup optional + cached). 🔴
56. **Dedupe on `cite_key`** — identical citations collapse into one registry row; add missing citations to the registry on ingest. 🔴
57. **Add `GET /api/kb/citations` (list, filter by year/venue) and `GET /api/kb/documents/{id}/citations`** — per-user. 🔴
58. **Add `GET /api/kb/citations/export?format=bibtex`** — generate BibTeX from the registry (`@article`/`@misc` with cite keys). 🔴
59. **Write `backend/tests/test_kb_citations_registry.py`** — reference-list parsing, `@cite` linking, dedupe, BibTeX export, per-user isolation. 🔴
60. **Frontend:** citation list per document + "Export BibTeX" button; citation cards link to source documents. 🔴 ✅ citations section + authed BibTeX export


## Group 7 — Idea 37 🔴: Concept linking UI (phrases 61–70)

61. **Build the reader sidebar panels** — document detail gains a "Concepts" panel (from `MENTIONS` edges) and a "Related notes" panel (from `RELATED`/`SHARES_CONCEPT`). 🔴
62. **Add `POST /api/kb/edges`** — `{source_document_id, target_id, relation, target_type (document|concept)}` per-user, always `provenance=manual`, `weight=1.0`. 🔴
63. **Add `DELETE /api/kb/edges/{edge_id}`** — lets users remove auto-inferred edges as well as their own. 🔴
64. **Add `GET /api/kb/documents/{id}/links`** — aggregated concept + related-note lists for the sidebar (wrap `graph.py` helpers). 🔴 ✅ `kb_edges.py` + `edge_id` for deletion
65. **Add concept autocomplete** — `GET /api/kb/concepts?q=` (Phase 2) powers the "link to concept" input. 🔴
66. **Wire the one-click link action** — "Link this note to concept X" creates the `MENTIONS`-style edge with `provenance=manual`. 🔴
67. **Validate edge targets** — reject self-edges and non-existent targets with 400/404. 🔴
68. **Write `backend/tests/test_kb_edge_ui.py`** — manual edge create/delete, validation, auto-edge removal, per-user isolation. 🔴
69. **Frontend:** sidebar panels + link/delete actions on the note reader. 🔴 ✅ links & concepts panel with edge delete
70. **api.ts:** `endpoints.kb.edges.create/delete` + `endpoints.kb.documents.links`. 🔴


## Group 8 — Idea 38 🔴: Mind-map generation (phrases 71–80)

71. **Create `app/services/kb/mindmap.py`** — builds a tree from the Phase 1 `outline_json` headings (root = document title). 🔴
72. **Attach concept mentions to nodes** — `MENTIONS` edges add concept chips under the heading where they appear. 🔴
73. **Add `GET /api/kb/documents/{id}/mindmap`** — per-user JSON tree `{id, label, children[], concepts[], chunk_ids[]}`. 🔴 ✅ `kb/mindmap.py`
74. **Add export endpoints** — `?format=markdown` (nested `#` outline) and `?format=opml` for external mind-map tools. 🔴
75. **Handle non-markdown documents** — fall back to `heading_path` values from chunks (PDFs/TXT) when `outline_json` is absent. 🔴
76. **Build the collapsible tree component** — frontend renders the JSON tree with expand/collapse per node. 🔴
77. **Add a "View as mind map" toggle** on the document detail page. 🔴 ✅ `MindMapView.tsx`
78. **Write `backend/tests/test_kb_mindmap.py`** — tree building from outline, concept attachment, markdown/OPML export, heading fallback. 🔴
79. **api.ts:** `endpoints.kb.mindmap(documentId, format?)`. 🔴
80. **Deep-link nodes** — clicking a tree node opens the document scrolled to that section (via `char_start`). 🔴


## Group 9 — Idea 39 🔴: Note quality scoring (phrases 81–90)

81. **Create `app/services/kb/quality.py`** — a pure, testable composite score (0–100) per document. 🔴
82. **Define the score components** — length, heading structure, link density (in/out edges), recency, and concept coverage (MENTIONS count). 🔴
83. **Add `KB_QUALITY_WEIGHTS` to `config.py`** — weight per component (defaults: length .25, headings .2, links .25, recency .1, coverage .2). 🔴
84. **Compute scores lazily and cache** — store `quality_score` + `quality_detail` on `KbDocument`; recompute on content change. 🔴
85. **Add LLM suggestions (optional, budget-capped)** — batch job proposing actions ("split this note", "add definition of X", "link to Y") stored with `status=pending|dismissed`. 🔴
86. **Add `GET /api/kb/documents/{id}/quality`** — score, per-component detail, and suggestions. 🔴
87. **Add `GET /api/kb/quality?sort=score`** — aggregate list (lowest first) for the quality work-list. 🔴
88. **Write `backend/tests/test_kb_quality.py`** — component math, weight config, caching/recompute, suggestion lifecycle. 🔴
89. **Frontend:** quality badge + suggestions panel on document detail; a quality-sorted list page. 🔴 ✅ `QualityPanel.tsx` + `QualityList.tsx`
90. **Surface quality in health** — `GET /api/kb/health` (Phase 3) gains an average-quality signal per source. 🔴


## Group 10 — Idea 40 🟡: Brain dump → structured notes migration (phrases 91–100)

91. **Create a draft `KbDocument` on brain-dump save** — the existing single-row `BrainDump` stays, but saves also upsert a draft document (`status=draft`, `source=braindump`). 🟡
92. **Add a `status` migration path** — extend the Phase 1 `KbDocument.status` values with `draft` (via `COLUMN_MIGRATIONS` if needed). 🟡
93. **Extend `BrainDumpResponse`** with `linked_document_id` so the widget can jump to the draft. 🟡
94. **Add `POST /api/kb/documents/{id}/file`** — the quick-file action: set `title`, target `source`/folder, and attach tags (moves `draft` → `new`). 🟡
95. **Add AI-assisted splitting** — long dumps get section proposals via `generate_json` (budget-capped): `{sections: [{title, char_start, char_end}]}` applied to the draft as headings. 🟡
96. **Keep the brain-dump widget backward-compatible** — unchanged textarea UX; the draft pipeline is an additive layer (existing tests keep passing). 🟡
97. **Write `backend/tests/test_kb_braindump_migration.py`** — save creates draft, quick-file transitions status, splitting (mocked), idempotency on repeated saves. 🟡
98. **Frontend:** "File as note" flow in the brain-dump widget — after save, an inline card offers title/source/tags + "split sections" for long text. 🟡 ✅ `BrainDumpWidget.tsx`
99. **api.ts:** `endpoints.kb.documents.file(id, payload)` (+ reuse `endpoints.braindumps` unchanged). 🟡
100. **Docs:** mark Ideas 31–40 done in the master plan; add the Phase 4 runbook (budget caps, fallbacks, review queues). 🟡 ✅ status header, runbook, and DoD updated

---

## Definition of Done — Phase 4

- [x] Any vault document has a cached, structured summary (TL;DR / key points / definitions / open questions) that regenerates on content change (`kb/summarize.py` + `SummaryPanel.tsx`).
- [x] Explanations work at 5 depths, are grounded in the user's own chunks, and always carry clickable citations (`kb/explain.py` + `ExplainPanel.tsx`).
- [x] Notes generate quizzes into the existing `Quiz` model/UI; the generating note is traceable via `kb_quiz_links` (`NoteActions.tsx` → `/quiz`).
- [x] Notes generate flashcard candidates that must be reviewed before entering a deck; no duplicates (`FlashcardReview.tsx`).
- [x] Daily notes (`YYYY-MM-DD.md`) auto-tag and join with the schedule + journal; the Today widget shows captures (`TodayCaptures.tsx` on the Dashboard).
- [x] Citations are parsed from PDFs and `@cite` syntax, deduped, and exportable as BibTeX (per-document list + authed export button).
- [x] Manual concept/related-note linking works from the reader; auto edges are removable (links & concepts panel + `edge_id` delete).
- [x] Any document renders as a collapsible mind map and exports Markdown/OPML (`MindMapView.tsx`).
- [x] Every note carries a quality score with per-component detail and actionable suggestions (`QualityPanel.tsx` + `/quality` work-list).
- [x] Brain-dump saves create draft documents that can be filed, tagged, and AI-split — the widget stays backward-compatible (`BrainDumpWidget.tsx`).
- [x] All generation is budget-capped (`KB_DAILY_GEN_LIMIT`) and works deterministically with `AI_ENABLED=false` (`kb/budget.py`, `ai_fallback` extensions).

## Verification checklist

```bash
# Backend: Phase 4 test suite (run from backend/)
python -m pytest tests/test_kb_summarize.py tests/test_kb_explain.py tests/test_kb_quizzes.py \
  tests/test_kb_flashcards.py tests/test_kb_daily_notes.py tests/test_kb_citations_registry.py \
  tests/test_kb_edge_ui.py tests/test_kb_mindmap.py tests/test_kb_quality.py \
  tests/test_kb_braindump_migration.py -q

# Full regression (Phases 1–3 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. Scan a small fixture vault; open a document
# 2. POST /api/kb/documents/{id}/summary → structured summary; regenerate on content change
# 3. POST /api/kb/explain {concept, depth: "eli5"} → cited explanation
# 4. Generate a quiz + flashcards → review queue → approve → existing Quiz/Deck UIs show them
# 5. GET /api/kb/documents/{id}/mindmap and /citations?format=bibtex → valid outputs
# 6. Save a brain dump → draft document appears; file it; long dump splits into sections

# Frontend (from frontend/)
npm run build   # tsc -b + vite build (there is no `typecheck` script)
```

## Phase 4 runbook (budget caps, fallbacks, review queues)

**Budget caps.** Every AI generation path (summary, explain, note quiz, flashcard candidates,
quality suggestions, brain-dump splitting) counts against `KB_DAILY_GEN_LIMIT` (default 20),
extending the `SUMMARY_DAILY_LIMIT` guard pattern via `app/services/kb/budget.py`. Exhaustion
returns a 429-style error with a clear message; the frontend surfaces it as-is.

**Deterministic fallbacks (`AI_ENABLED=false`).** Nothing in Phase 4 requires a network call:
- Summary → first heading + first N chars + heading list as key points.
- Explanation → `kb_concepts` definition + top-chunk excerpt (no hallucination risk).
- Quiz → existing `demo_quiz` pattern via the content adapter.
- Flashcards → "What is X?" → concept definition pairs.
- Brain-dump split → paragraph-boundary heading insertion.
All fallback responses carry a `fallback: true` flag so the UI can show "⚡ deterministic fallback".

**Review queues.** Flashcard candidates land in `kb_flashcard_candidates` with `status=pending`
and only enter a deck after the user approves them on `/flashcard-review` (dedupe by normalized
question on generation). Approved cards land in the auto-created "From notes" deck; nothing
enters decks un-reviewed.

**Traceability.** `kb_quiz_links` records which note generated a quiz; `kb_generation_log`
records every budget-capped generation for auditing.

**Per-user scoping** is enforced on every model (`user_id` filter) and mirrors `test_ownership.py`.

## Notes & boundaries

- **Phases 5–7 are out of scope:** subject management, study planning, and the AI tutor — this phase's generation output (summaries, quizzes, flashcards, concepts) is their input.
- **Idea 32's `user_memory` seam (Idea 79) is stubbed now** — the explanation service degrades gracefully until Phase 8 delivers real learning memory.
- **Reuse over rebuild:** quizzes and flashcards must ride the existing `Quiz`/`FlashcardDeck` models and UIs; new code is content adapters + review queues, not new quiz engines.
- **Budget caps are mandatory:** every AI generation path counts against `KB_DAILY_GEN_LIMIT`; deterministic fallbacks (extend `ai_fallback.py`) keep `AI_ENABLED=false` fully functional.
- **Per-user scoping is non-negotiable** — every summary, candidate, citation, edge, and draft filters `user_id`; ownership tests mirror `test_ownership.py`.

