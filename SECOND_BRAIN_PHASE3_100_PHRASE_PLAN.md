# Second Brain Integration — Phase 3 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 3 — Search & Retrieval (Ideas 21–30)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to the Phase 1 and Phase 2 plans
(`SECOND_BRAIN_PHASE1_100_PHRASE_PLAN.md`, `SECOND_BRAIN_PHASE2_100_PHRASE_PLAN.md`).

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (7): Idea 22 (semantic search), 23 (hybrid/RRF), 24 (query expansion), 25 (citations), 27 (health), 28 (gap detection), 29 (feedback learning)
- 🟡 partial / extends existing code (3): Idea 21 (the `MaterialSearch` UI + `q` filter exist), Idea 26 (empty `.deepeval/` dir exists at repo root), Idea 30 (per-domain search UIs exist)

**Prerequisites: Phases 1 and 2 must be complete** — this phase consumes `kb_chunks`
(`char_start/end`, `heading_path`, `token_estimate`), `kb_documents` (metadata, `ocr_used`,
`doc_date`), `kb_concepts` (aliases for expansion), `kb_edges` (health/backlinks), the persistent
vector store, `embeddings.py`, and the `kb` router/service conventions.

**Scope:** Keyword FTS, semantic search, hybrid RRF fusion, query expansion, citation-aware result
cards, a retrieval evaluation harness, knowledge-health analysis, missing-knowledge detection,
search feedback learning, and a global unified search box. **RAG, note intelligence, and content
generation are Phase 4 (Ideas 31–40) and out of scope** — only the retrieval quality bar is built
here. Idea 28's topic-coverage mapping depends on Phase 5 (Idea 38); a stub interface is built now.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 3 reuses |
|---|---|---|
| Search UI pattern | `frontend/src/components/curriculum/MaterialSearch.tsx` | The existing search box + results pattern to extend for vault search |
| Title-only keyword filter | `backend/app/routers/materials.py` (`list_unit_materials`, `q` param) | The `q` filter precedent; FTS replaces/augments `ilike` for vault |
| Empty eval dir (stub) | `.deepeval/` (repo root, empty) | Seam for the eval harness (Idea 26) — fixtures + scripts can live here or under `backend/tests/fixtures/` |
| Chunk citation fields | Phase 1 (Group 7) | `char_start/end`, `heading_path` on `kb_chunks` — the citation spine |
| PDF page boundaries | Phase 1 (Group 5, phrase 41) | Page numbers for "open at page N" |
| Concepts + aliases | Phase 2 (Group 5) | `kb_concepts.aliases` for synonym/abbreviation expansion (Idea 24) |
| Embeddings + vector store | Phase 2 (Groups 1–2) | `embeddings.py`, persistent store, `sync_index` for semantic retrieval |
| Daily-budget guard | `backend/app/config.py` (`SUMMARY_DAILY_LIMIT` pattern) | Cost caps on LLM rerank / query rewrite |
| Notifications router | `backend/app/routers/notifications.py` | Daily gap digest delivery (Idea 28) |
| PDF reader | `frontend/src/pages/` `PDFReader` | "Open in reader" action on citation cards (Idea 25) |

**File conventions:** search services → `backend/app/services/kb/search.py` (+ `query.py`, `health.py`);
routers → `backend/app/routers/kb_search.py` (+ extend `kb_documents.py`); CLI → `backend/app/cli/kb.py`;
eval fixtures → `backend/tests/fixtures/kb_eval/*.json`; tests → `backend/tests/test_kb_*.py`. Register
every new router in `main.py`; every new model in `models/__init__.py`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---

## Group 1 — Idea 21 🟡: Full-text search with FTS5 (phrases 1–10)

1. **Add `KB_FTS_ENABLED` (default True) and `KB_FTS_MIN_TOKEN` (default 2) to `config.py`** in a commented section. 🟡
2. **Create the SQLite FTS5 virtual table `kb_fts`** (dev) — external-content table over `kb_chunks` (content = `chunk.content`, plus `document_id`, `user_id`), created idempotently at startup. 🟡
3. **Add sync triggers** — AFTER INSERT/UPDATE/DELETE on `kb_chunks` maintaining `kb_fts`, so the index never drifts from rows. 🟡
4. **Add the Postgres path (prod)** — generated `tsvector` column + GIN index over the same fields, behind a small `FtsBackend` abstraction. 🟡
5. **Build a query builder** (`app/services/kb/fts.py`) — tokenization, prefix matching, phrase support, `AND`/`OR`, and proper escaping of FTS special chars. 🟡
6. **Enforce per-user filtering** — every FTS query JOINs back to `kb_chunks.user_id` (never a global index query). 🟡
7. **Add snippet generation** — SQLite `snippet()`/`highlight()` with `<mark>`-friendly marker tokens for result previews. 🟡
8. **Add `GET /api/kb/search?q=&mode=keyword`** — the keyword-only path first, returning ranked chunks + snippets (mode=hybrid lands in Group 3). 🟡
9. **Write `backend/tests/test_kb_fts.py`** — indexing, prefix/phrase queries, per-user isolation, snippet markers, trigger sync on delete. 🟡
10. **Add `rebuild-fts` to the KB CLI** (`python -m app.cli.kb rebuild-fts`) for index rebuilds after migrations. 🟡


## Group 2 — Idea 22 🔴: Semantic search API (phrases 11–20)

11. **Extend `GET /api/kb/search` (or add `POST`) with `mode=semantic`** — natural-language queries embed via `embeddings.py`. 🔴
12. **Create `app/services/kb/search.py`** — the `KbSearcher` orchestrating FTS + vector + (later) fusion; single entry point for all modes. 🔴
13. **Embed the query with `embeddings.py`** and cosine-retrieve from the persistent store (Phase 2 Group 2); guard zero-vector/`AI_ENABLED=false` → fall back to FTS only. 🔴
14. **Map store ids → chunk rows** — the store keeps `kb_chunk:{id}` ids; resolve to chunk + document in one query. 🔴
15. **Normalize scores** — min-max per retriever so FTS bm25-ish and cosine scores are comparable before any merge. 🔴
16. **Return the unified result shape** — `{chunk_id, document_id, title, snippet, score, mode, source_path}`. 🔴
17. **Merge keyword + semantic results** (simple union/score-combine now; RRF replaces this in Group 3). 🔴
18. **Write `backend/tests/test_kb_semantic_search.py`** — mocked embeddings, dimension mismatch fallback, zero-vector fallback, per-user isolation. 🔴
19. **Frontend:** vault search page/component reusing the `MaterialSearch.tsx` pattern — query box, mode toggle, ranked results. 🔴
20. **Add `endpoints.kb.search` to `frontend/src/services/api.ts`** (query, mode, filters, pagination). 🔴


## Group 3 — Idea 23 🔴: Hybrid retrieval with RRF fusion (phrases 21–30)

21. **Add `KB_RRF_K` (default 60) and `KB_SEARCH_MODE` (default `hybrid`; also `keyword` or `semantic`) to `config.py`.** 🔴
22. **Implement Reciprocal Rank Fusion** — `score = sum(1/(k + rank))` across retriever rank lists, deduped by chunk id. 🔴
23. **Run FTS and vector retrievers for every hybrid query** (both already return ranks from Groups 1–2) and fuse them. 🔴
24. **Add optional LLM/cross-encoder rerank** of the fused top-N (budget-capped via the `SUMMARY_DAILY_LIMIT` guard pattern; skip when `AI_ENABLED=false`). 🔴
25. **Keep the fusion deterministic** — stable tie-break by document recency, then chunk id, so tests and pagination are reproducible. 🔴
26. **Surface which retrievers contributed** — response `sources: ["fts", "semantic"]` per result for debuggability + the eval harness. 🔴
27. **Write `backend/tests/test_kb_hybrid.py`** — fixture where keyword and semantic each miss what the other finds; fused top-k must contain both. 🔴
28. **Config knob `KB_SEARCH_MODE` honored end-to-end** — keyword-only, semantic-only, and hybrid all return the same response shape. 🔴
29. **Add pagination + total-count to the search response** so the UI can page without re-running the fusion. 🔴
30. **Frontend mode toggle** (Keyword / Semantic / Hybrid) bound to `KB_SEARCH_MODE` in the vault search UI. 🔴


## Group 4 — Idea 24 🔴: Query expansion & spelling tolerance (phrases 31–40)

31. **Create `app/services/kb/query.py`** — the query normalizer + expander pipeline, applied before retrieval in every mode. 🔴
32. **Normalize queries** — lowercase, strip punctuation, tokenize; reject empty/too-short queries with a clear 400. 🔴
33. **Expand synonyms from `kb_concepts.aliases`** (Phase 2 Group 5) — map query tokens to canonical names and add them as OR terms. 🔴
34. **Expand abbreviations** — alias entries like "ML" → "machine learning" (curated via the concept UI; seeded with common CS terms). 🔴
35. **Add typo tolerance** — FTS prefix matching (phase 1 already enables) + Levenshtein-ish token suggestions when a token yields zero hits. 🔴
36. **Add optional LLM query rewrite** — only when hybrid retrieval returns zero results (budget-capped, `AI_ENABLED` guarded). 🔴
37. **Record the original + expanded query** on the search response (`original_query`, `expanded_query`) for the eval harness (Group 6) and feedback logs (Idea 29). 🔴
38. **Write `backend/tests/test_kb_query_expansion.py`** — alias expansion, abbreviation, typo suggestion, zero-hit LLM rewrite (mocked), short-query 400. 🔴
39. **Add `KB_QUERY_EXPANSION_ENABLED` (default True)** — kill switch so behavior is comparable in the eval harness. 🔴
40. **Frontend:** show "expanded: …" hint when the query was rewritten/expanded. 🔴


## Group 5 — Idea 25 🔴: Citation-aware result cards (phrases 41–50)

41. **Confirm chunk citation fields exist** — `char_start/end`, `heading_path` (Phase 1 Group 7) and per-page PDF boundaries (Phase 1 Group 5); backfill any documents missing them via the reindex CLI. 🔴
42. **Extend the search result schema** — add `source_path`, `heading`, `page`, `char_start`, `char_end`, `document_id`, `doc_type`. 🔴
43. **Build the backend citation resolver** — chunk → document row + `source_path` (relative vault path or `/uploads/...` for PDFs). 🔴
44. **Build the `CitationResultCard` frontend component** — title, source path, heading breadcrumb, page badge, snippet, score. 🔴
45. **Render highlighted snippets** — wrap matched terms in `<mark>` from the FTS highlight markers (Group 1, phrase 7). 🔴
46. **Add "Open in vault" action** — resolves to the file path (or an Obsidian URI for vault sources) and opens the note/PDF at the page. 🔴
47. **Add "Open in reader" action** — reuse the existing `PDFReader` page for PDF results at the exact page. 🔴
48. **Wire click-through tracking** — result clicks logged into the `kb_search_events` table (built in Group 9 / Idea 29). 🔴
49. **Write `backend/tests/test_kb_citations.py`** — snippet markers, page/heading resolution, open-in-vault path building, PDF vs markdown variants. 🔴
50. **Frontend:** result cards linkable/deep-linkable — a result URL opens the search page with that card expanded. 🔴


## Group 6 — Idea 26 🟡: Retrieval evaluation harness (phrases 51–60)

51. **Define the golden-set format** — `{query, relevant_chunk_ids[], subject}` JSON fixtures; create `backend/tests/fixtures/kb_eval/` (the root `.deepeval/` dir stays as a stub seam for future integration). 🟡
52. **Seed golden queries per subject area** — at least 10 queries per domain (cybersecurity, ML, DS, theory) drawn from the real vault topics, each with curated relevant chunk ids. 🟡
53. **Create `python -m app.cli.kb eval`** — runs retrieval offline over the golden set, in all three `KB_SEARCH_MODE`s, and prints metrics. 🟡
54. **Implement metric computation** — `recall@k`, `precision@k`, and `MRR` (mean reciprocal rank) over the fused rankings. 🟡
55. **Add a `kb_eval_runs` table** — stores query, mode, metrics, timestamp per run for trend tracking. 🟡
56. **Wire eval into CI** — a pytest marker (`@pytest.mark.eval`) that runs the harness on a small subset so regressions fail fast without slowing the suite. 🟡
57. **Baseline snapshot** — record current scores before any retrieval change; every future change compares against it in the runbook. 🟡
58. **Add an LLM-faithfulness stub** — placeholder metric column for Phase 4 answer-groundedness (documented, not yet computed). 🟡
59. **Write `backend/tests/test_kb_eval.py`** — harness runs end-to-end on a tiny fixture set; metrics are mathematically correct on a known ranking. 🟡
60. **Write the eval runbook** — how to add golden queries, run the CLI, and read the dashboard numbers. 🟡


## Group 7 — Idea 27 🔴: Knowledge health analysis (phrases 61–70)

61. **Create `app/services/kb/health.py`** — a set of pure, testable signal functions over `kb_documents`/`kb_edges`. 🔴
62. **Detect orphans** — documents with no incoming/outgoing edges and no `MENTIONS` (candidates for merging or deletion). 🔴
63. **Detect dead links** — `WIKILINK`/`BACKLINK` edges whose target document no longer exists. 🔴
64. **Detect stale notes** — `updated_at` older than `KB_STALE_DAYS` (default 90, configurable) and never re-visited. 🔴
65. **Detect unindexed files** — documents missing embeddings, chunks, or tags (incomplete ingest). 🔴
66. **Compute coverage gaps** — subjects with few or no documents (interface stub for Idea 28 / Phase 5 mapping). 🔴
67. **Add `GET /api/kb/health`** — aggregates all signals with a 0–100 health score (weighted) + per-signal breakdown, per-user. 🔴
68. **Cache health per source** — recompute on scan/ingest completion, refresh on demand via `?refresh=true`. 🔴
69. **Write `backend/tests/test_kb_health.py`** — each detector with crafted fixtures; score math; per-user isolation. 🔴
70. **Frontend:** Insights/health page — cards per signal with "fix" actions (open doc, remove dead edge, reindex). 🔴


## Group 8 — Idea 28 🔴: Missing knowledge detection (phrases 71–80)

71. **Define the topic→coverage interface** — `topic_coverage(db, user_id) -> {topic, covered_docs, coverage}` backed by a stub now (Phase 5 Idea 38 will feed real subject topics). 🔴
72. **Compute per-topic coverage** — count documents/chunks whose concepts/tags intersect each topic (reuse `MENTIONS` edges + tags). 🔴
73. **Flag zero/weak topics** — coverage below `KB_GAP_THRESHOLD` (default 0.2) becomes a "gap". 🔴
74. **Emit "You have no notes on X" alerts** — via the existing notifications router, per-user, coalesced daily (not per event). 🔴
75. **Add capture prompts** — gap alerts deep-link to quick-capture (Phase 4) with the topic pre-filled. 🔴
76. **Add `GET /api/kb/gaps`** — the gap list (topic, coverage, suggested capture) for the Insights page. 🔴
77. **Write `backend/tests/test_kb_gaps.py`** — stub topic source, threshold math, alert coalescing, per-user isolation. 🔴
78. **Frontend:** gaps list on the Insights page with "capture note" CTA per gap. 🔴
79. **Ground gaps in real evidence** — a topic is only a gap when nothing in the vault mentions it (search returns zero); never flag from a stale index. 🔴
80. **Wire gap recompute into health** — `GET /api/kb/health` includes a `gaps` count and per-gap drill-down. 🔴


## Group 9 — Idea 29 🔴: Search feedback & learning (phrases 81–90)

81. **Define the `KbSearchEvent` model (`kb_search_events`)** — `id, user_id, query, mode, result_ids (JSON), clicked_id, rating (-1|0|1), created_at`. 🔴
82. **Register the model in `models/__init__.py`**; per-user scoping + an index on `(user_id, created_at)`. 🔴
83. **Log every search server-side** — the search endpoint records the query + top result ids automatically (no extra frontend work needed for coverage). 🔴
84. **Add `POST /api/kb/search/feedback`** — thumbs up/down (+ optional clicked result id) from the `CitationResultCard`. 🔴
85. **Track implicit clicks** — the click-through hook from Idea 25 (phrase 48) writes `clicked_id`. 🔴
86. **Batch feedback analysis** — a weekly job computes per-user weights: boost sources/users' preferred documents, demote disliked ones (stored as `preferred_sources`). 🔴
87. **Apply learned weights at query time** — a per-user score multiplier on fused results (behind `KB_LEARNING_ENABLED`, default False until eval shows improvement). 🔴
88. **Write `backend/tests/test_kb_search_events.py`** — event logging on search, feedback endpoint, click tracking, batch weight computation. 🔴
89. **Privacy:** events are per-user, deletable via an export/purge endpoint; document retention in the runbook. 🔴
90. **Frontend:** feedback thumbs on result cards + a "preferred sources" hint (only when learning is enabled). 🔴


## Group 10 — Idea 30 🟡: Global unified search box (phrases 91–100)

91. **Add `POST /api/search`** — the aggregating endpoint that fans out to vault (Idea 22), materials (`q` filter), subjects/units (curriculum), tasks, and assignments. 🟡
92. **Wrap each domain's existing search behind a small interface** — `{id, title, domain, snippet, url, score}` per hit so the UI is uniform. 🟡
93. **Fan out in parallel** (asyncio/threadpool) with a hard per-domain cap and a global result cap (e.g. 50) to bound latency. 🟡
94. **Add type facets** — `?domains=vault,materials,tasks` and result grouping per domain in the response. 🟡
95. **Write `backend/tests/test_global_search.py`** — fan-out coverage, per-domain caps, facet filtering, empty-result shape, per-user scoping per domain. 🟡
96. **Add `endpoints.search.global` to `api.ts`** with typed per-domain results. 🟡
97. **Build the command-palette UI** — Ctrl+K overlay (keyboard-first) with grouped results, arrow-key navigation, and Enter-to-open (per-domain URL). 🟡
98. **Reuse the vault search page for deep results** — palette opens the full domain page when a domain's results are expanded. 🟡
99. **Frontend tests** — palette render, keyboard nav, grouping (vitest, mirroring existing frontend test patterns). 🟡
100. **Docs:** mark Ideas 21–30 done in the master plan; add the search runbook (modes, weights, eval, learning toggle). 🟡

---

## Definition of Done — Phase 3

- [ ] `kb_fts` (FTS5) is trigger-synced, per-user filtered, and returns highlighted snippets; Postgres `tsvector` path documented.
- [ ] `POST/GET /api/kb/search` supports `keyword`, `semantic`, and `hybrid` modes with one response shape (chunk + document + snippet + score + citations).
- [ ] RRF fusion is deterministic, mode-switchable via `KB_SEARCH_MODE`, and covered by a where-each-retriever-misses test.
- [ ] Query expansion (aliases/abbreviations/typos/LLM rewrite) is kill-switchable and reports `original_query`/`expanded_query`.
- [ ] Result cards show source path, heading, page, highlighted snippet, and open-in-vault/reader actions.
- [ ] The eval harness runs golden queries in CI (marked), records `recall@k`/`precision@k`/`MRR`, and stores runs in `kb_eval_runs`.
- [ ] `GET /api/kb/health` reports orphans, dead links, stale notes, unindexed files, coverage gaps, and a 0–100 score.
- [ ] Gap detection flags zero/weak topics with evidence, delivers coalesced alerts, and deep-links to capture.
- [ ] Search events are logged, feedback endpoints work, and learned weights are behind an opt-in flag.
- [ ] `POST /api/search` returns facet-grouped, domain-capped results; Ctrl+K palette navigates every domain.

## Verification checklist

```bash
# Backend: Phase 3 test suite (run from backend/)
python -m pytest tests/test_kb_fts.py tests/test_kb_semantic_search.py tests/test_kb_hybrid.py \
  tests/test_kb_query_expansion.py tests/test_kb_citations.py tests/test_kb_eval.py \
  tests/test_kb_health.py tests/test_kb_gaps.py tests/test_kb_search_events.py \
  tests/test_global_search.py -q

# Eval harness (offline, prints metrics)
python -m app.cli.kb eval

# Full regression (Phase 1 + 2 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. Start the app; scan a small fixture vault (Phase 1); let ingest embed chunks (Phase 2)
# 2. GET /api/kb/search?q=word&mode=keyword → FTS hits with <mark> snippets
# 3. mode=hybrid with a natural-language query → fused ranked results with citation fields
# 4. GET /api/kb/health and /api/kb/gaps → non-empty, sane
# 5. POST /api/search → grouped results across vault/materials/tasks

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phase 4 is out of scope:** RAG chat, note intelligence, summaries, flashcards, and content generation (Ideas 31–40) — this phase builds the retrieval quality bar they will sit on.
- **Idea 28 depends on Phase 5 (Idea 38)** for real subject topics; the interface + stub built here (phrase 71) is the seam.
- **FTS5 (dev) vs `tsvector` (prod)** are two backends behind one `FtsBackend` — dev tests run on SQLite FTS5; prod uses Postgres GIN. Never write backend-specific SQL into routers.
- **All AI calls stay budget-capped** (LLM rerank, query rewrite) reusing the `SUMMARY_DAILY_LIMIT` guard pattern.
- **Per-user scoping is non-negotiable** — every FTS query, vector retrieval, health/gap computation, and feedback log filters `user_id`.
- **Learning (Idea 29) ships default-off** until the eval harness proves weight adjustments improve `recall@k`/`MRR`.

