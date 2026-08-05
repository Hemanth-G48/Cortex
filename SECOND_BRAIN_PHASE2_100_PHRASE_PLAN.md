# Second Brain Integration — Phase 2 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 2 — Embeddings, Indexing & Knowledge Graph (Ideas 11–20)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — the build-ready companion to
[`SECOND_BRAIN_PHASE1_100_PHRASE_PLAN.md`](./SECOND_BRAIN_PHASE1_100_PHRASE_PLAN.md).

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (5): Idea 11 (embeddings service), Idea 14 (auto-tagging), Idea 15 (concepts), Idea 19 (near-dup), Idea 20 (re-index tooling)
- 🟡 partial / extends existing code (5): Idea 12 (persist the existing in-memory store), Ideas 13, 16, 17, 18 build on Phase 1 output

**Prerequisite: Phase 1 must be complete** — this phase consumes `kb_documents`, `kb_chunks`
(with `token_estimate`), `kb_tags`, `kb_edges`, `kb_versions`, `kb_jobs`, the chunker, the markdown
parser, and the ingest-job pipeline. **Search & retrieval (Idea 21+), RAG, and hybrid search are
Phase 3 and out of scope** — the persistent index built here is their foundation.

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 2 reuses |
|---|---|---|
| In-memory vector store | `backend/app/services/vector_store.py` | `VectorStore` (`add/delete/clear/query`, cosine) + `store` singleton + `get_store()` — the interface to persist, **not** to throw away |
| Backend switch (unused) | `backend/app/config.py` | `VECTOR_STORE_BACKEND` (`numpy`\|`faiss`) — extend with `file` and `pgvector` |
| AI client pattern | `backend/app/services/ai_client.py` | Mirror for embeddings: `ai_available()`, model fallback, `AI_ENABLED` short-circuit, `httpx` style |
| Deterministic fallbacks | `backend/app/services/ai_fallback.py` | Pattern for a local/hash-based embeddings fallback so CI stays hermetic |
| Existing store tests | `backend/tests/test_vector_store.py` | Must stay green; extend, don't rewrite |
| Phase 1 seams | `SECOND_BRAIN_PHASE1_100_PHRASE_PLAN.md` | `kb_chunks.token_estimate` (batching seam), ingest-job embedding hook (Group 10, phrase 96), `kb_edges` relation types, per-user scoping rule |
| Obsidian graph data | `Obsidian Vault/.obsidian/graph.json` + `obsidian_agent.py` | Real starting data for Ideas 16–17 (backlinks/wikilinks) — read at runtime, never via git |

**Note:** `backend/app/services/vector_store_faiss.py` and `backend/app/services/retrieval.py`
are *referenced* in `vector_store.py`'s docstring/`get_store()` but **do not exist yet** — the
file backend (Idea 12) can replace the FAISS plan for dev, with pgvector for prod.

**File conventions:** services → `backend/app/services/embeddings.py` + `backend/app/services/kb/*.py`;
CLI → `backend/app/cli/kb.py`; schemas/tests follow the Phase 1 conventions
(`backend/app/schemas/kb.py`, `backend/tests/test_kb_*.py`). Register all new routers in
`main.py` and every model in `models/__init__.py`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Later groups depend on earlier ones; each
phrase is independently verifiable.

---

## Group 1 — Idea 11 🔴: Embeddings service (phrases 1–10)

1. **Add `EMBEDDINGS_MODEL` (default `text-embedding-3-small`), `EMBEDDINGS_DIM` (default 1536), and `EMBEDDINGS_BATCH_SIZE` (default 32) to `app/config.py`** in a commented section. 🔴
2. **Create `backend/app/services/embeddings.py`** mirroring `ai_client.py` — `embed_available()` (respects `AI_ENABLED`), `embed_texts(texts) -> list[list[float]]`. 🔴
3. **Implement the OpenAI-compatible call** — `POST {AI_BASE_URL}/embeddings` with `model` + `input` list, `httpx` timeout, `Authorization: Bearer` header. 🔴
4. **Add model fallback + failure handling** — on 404/network error, try fallback models (reuse `settings.ai_model_list` logic); log and return `None` so callers can fall back locally. 🔴
5. **Add a deterministic local fallback** — hash-based pseudo-vectors (seeded by content) with `EMBEDDINGS_DIM` length so `AI_ENABLED=false` and CI stay hermetic and dimensionally consistent. 🔴
6. **Validate and normalize outputs** — check returned dimension against `EMBEDDINGS_DIM` (warn + pad/truncate), ensure float32. 🔴
7. **Cache embeddings by content hash** in `kb_embeddings` (created in Group 2) — identical chunk text never re-embeds. 🔴
8. **Enforce a per-day embedding budget** — reuse the `SUMMARY_DAILY_LIMIT` guard pattern (config `EMBEDDINGS_DAILY_LIMIT`) so cost can't run away. 🔴
9. **Write `backend/tests/test_embeddings.py`** — mocked HTTP (`monkeypatch`), fallback-model retry, deterministic local fallback, dimension mismatch, budget cap, `AI_ENABLED=false` short-circuit. 🔴
10. **Expose `GET /api/ai/health` additions** — report embeddings model + availability alongside the existing AI health (extend `ai.py` router). 🔴


## Group 2 — Idea 12 🟡: Persistent vector store (phrases 11–20)

11. **Define the `KbEmbedding` model (`kb_embeddings`)** — `id, user_id, chunk_id (FK kb_chunks.id, unique), model, dim, content_hash, vector (BLOB for numpy backend / pgvector column in prod), created_at`. 🟡
12. **Register `KbEmbedding` in `models/__init__.py`**; new table covered by `create_all`, column ALTERs via `COLUMN_MIGRATIONS`. 🟡
13. **Extend the `VECTOR_STORE_BACKEND` switch** in `get_store()` — add `"file"` (default for dev) and `"pgvector"` (prod) alongside the existing numpy/faiss paths. 🟡
14. **Create `backend/app/services/vector_store_file.py`** — a file-backed numpy store behind the same `VectorStore` interface (save/load `.npy` + ids JSON to `settings.UPLOAD_DIR`/`kb_index/`). 🟡
15. **Make `kb_embeddings` the source of truth** — write embedding rows on ingest; rebuild the in-memory/file index from the table on startup. 🟡
16. **Add `pgvector` backend (prod)** — optional `pgvector` SQLAlchemy type behind the same interface, import-guarded; document in `.env.example`. 🟡
17. **Keep transactional consistency** — chunk + embedding rows commit in the same transaction as the Phase 1 ingest pipeline. 🟡
18. **Add `sync_index(db, user_id)`** — load the store from `kb_embeddings` (startup hook in `main.py` lifespan, plus after each ingest job). 🟡
19. **Write `backend/tests/test_vector_persistence.py`** — embed → write → restart a fresh store instance → load → same ids/vectors; `test_vector_store.py` must stay green. 🟡
20. **Add `GET /api/kb/stats`** — per-user counts: documents, chunks, embedded chunks, index size, coverage % (embedded/chunks). 🟡


## Group 3 — Idea 13 🟡: Metadata extraction & enrichment (phrases 21–30)

21. **Add `KbDocument` metadata fields** — `author, doc_date, source_url, language, reading_time_seconds, metadata_json` (extend the Phase 1 model + `COLUMN_MIGRATIONS` entry for existing DBs). 🟡
22. **Extract metadata from YAML frontmatter first** — reuse Phase 1 `frontmatter_json` (title, author, date, tags, url, language); frontmatter always wins. 🟡
23. **Enrich missing fields with the LLM** via `generate_json` and a strict schema (author/topic/language/date); deterministic fallback when `AI_ENABLED=false`. 🟡
24. **Compute `reading_time_seconds`** — words ÷ 200 wpm heuristic on extracted text. 🟡
25. **Detect `language`** — deterministic heuristic (character-frequency/stopword table) before spending an LLM call. 🟡
26. **Add `PUT /api/kb/documents/{id}/metadata`** for manual override — edited values are flagged `manual` and never overwritten by re-ingest. 🟡
27. **Merge rule: frontmatter > manual > LLM > defaults**, persisted in `metadata_json` with per-field provenance. 🟡
28. **Write `backend/tests/test_kb_metadata.py`** — frontmatter precedence, manual-override persistence, heuristic language, reading-time math. 🟡
29. **Frontend:** editable metadata panel on the document detail page (Phase 1 page) with source badges (frontmatter/AI/manual). 🟡
30. **Add filtering to `GET /api/kb/documents`** — `?author=&tag=&date_from=&date_to=&language=` using the new fields. 🟡


## Group 4 — Idea 14 🔴: Auto-tagging (phrases 31–40)

31. **Seed tags from inline `#tags` first** — Phase 1 parser output becomes `kb_tags` rows with `kind=inline`, provenance `rule`; these are never suggested for deletion. 🔴
32. **Add the document↔tag association table (`document_tags`)** — `document_id, tag_id, provenance (rule|ai|manual)` with unique `(document_id, tag_id)`. 🔴
33. **LLM tag proposal** — `generate_json` over the first N chunks (capped by daily budget) requesting 3–7 concise topical tags. 🔴
34. **Deterministic fallback** — TF-IDF top-n noun phrases from chunk text (no LLM) when `AI_ENABLED=false`. 🔴
35. **Create-or-reuse tags** — match existing `(user_id, name)` before creating new rows; lowercase + trim. 🔴
36. **Return suggested tags as `status=suggested`** — nothing auto-committed without user confirmation. 🔴
37. **Add `POST /api/kb/documents/{id}/tags` (apply) and `DELETE .../tags/{tag_id}`** — confirmation UI writes `provenance=manual`. 🔴
38. **Write `backend/tests/test_kb_auto_tag.py`** — inline-tag seeding, LLM proposal (mocked), fallback, create-or-reuse, apply/reject flow. 🔴
39. **Frontend:** tag chips with suggest/confirm/reject on document detail + a tag filter in the document list. 🔴
40. **Wire auto-tagging into the Phase 1 ingest job** as a post-chunking stage (after the embedding hook). 🔴


## Group 5 — Idea 15 🔴: Concept extraction & canonicalization (phrases 41–50)

41. **Define the `KbConcept` model (`kb_concepts`)** — `id, user_id, canonical_name (unique per user), definition, aliases (JSON list), created_at, updated_at`. 🔴
42. **Register `KbConcept` in `models/__init__.py`**; add a `concepts` relationship/helper on `KbDocument`. 🔴
43. **LLM concept extraction** — batched over chunk summaries, requesting `{concept, definition, aliases}`; capped by the daily AI budget (reuse `EMBEDDINGS_DAILY_LIMIT`-style guard). 🔴
44. **Deterministic fallback** — TF-IDF noun-phrase extraction (stopword + POS-lite heuristics) so the pipeline works with `AI_ENABLED=false`. 🔴
45. **Canonicalization** — lowercase, singularize, trim; store variant spellings in `aliases`; resolve synonyms into one `canonical_name`. 🔴
46. **Record `MENTIONS` edges** — document→concept with a `weight` = normalized mention frequency (feeds Group 6). 🔴
47. **Dedupe concepts per user** — `unique (user_id, canonical_name)`; merging aliases into the canonical row. 🔴
48. **Write `backend/tests/test_kb_concepts.py`** — extraction (mocked LLM + fallback), canonicalization, alias merging, dedupe, mentions weights. 🔴
49. **Add `GET /api/kb/concepts?q=&page=` (per-user)** — concept index with document counts, for the future subject-bridging features. 🔴
50. **Frontend:** concept panel on document detail (extracted concepts + definitions) and a browsable concept index page. 🔴


## Group 6 — Idea 16 🟡: Knowledge graph nodes & edges (phrases 51–60)

51. **Finalize the `kb_edges` relation vocabulary** — `WIKILINK, BACKLINK, CITES, MENTIONS, RELATED, SHARES_CONCEPT, SYNONYM_OF, DEPENDS_ON, DUPLICATE_OF`; add a `provenance (rule|auto|ai|manual)` column. 🟡
52. **Build `WIKILINK`/`BACKLINK` edges from the markdown parser output** (Phase 1, Group 4) — resolved relative paths → target `KbDocument.id`. 🟡
53. **Build `MENTIONS` edges** from Group 5 output — document→concept with weight; store concept refs via a polymorphic target (`target_type`). 🟡
54. **Add statistical co-occurrence edges** — concepts that co-occur in the same chunk get a `RELATED`/`SHARES_CONCEPT` edge with a co-occurrence weight. 🟡
55. **Add curated `DEPENDS_ON` edges** — low-volume LLM pass (capped budget) reading the concept list of each doc; manual override in UI. 🟡
56. **Create `backend/app/services/kb/graph.py`** — `add_edge`, `neighbors(doc_id)`, `concepts_of(doc_id)`, `related_docs(doc_id)` query helpers, all user-scoped. 🟡
57. **Add `GET /api/kb/graph`** — nodes (documents/concepts/tags) + edges, paginated/level-limited, optional `?relation=` filter, per-user. 🟡
58. **Add weight thresholds** — drop edges below a configurable minimum weight (`KB_EDGE_MIN_WEIGHT`) to avoid graph noise. 🟡
59. **Write `backend/tests/test_kb_graph.py`** — wikilink/backlink edges, mentions edges, co-occurrence, dedupe of identical edges, per-user isolation. 🟡
60. **Frontend hook:** document detail gains a "Links" panel fed by `graph.neighbors()` (prep for Idea 18). 🟡


## Group 7 — Idea 17 🟡: Relationship & backlink inference (phrases 61–70)

61. **Add `KB_SIM_THRESHOLD` (default 0.75) and `KB_INFER_DAILY_BUDGET` to `config.py`** for inference tuning and cost control. 🟡
62. **Implement document-pair similarity inference** — average chunk embeddings per document; pairs above `KB_SIM_THRESHOLD` get a `RELATED` edge with the cosine score as weight. 🟡
63. **Add shared-concept inference** — documents sharing ≥ N concepts get a `SHARES_CONCEPT` edge (reuse Group 6 mentions). 🟡
64. **Run inference incrementally, not N²** — only compare new/changed documents against the index (per-scan or per-source batches, via the job queue). 🟡
65. **Backlink inference** — every `WIKILINK` edge implies a `BACKLINK` edge from the target back to the source. 🟡
66. **Record `provenance=auto` on all inferred edges** and keep them suppressible in the UI. 🟡
67. **Dedupe + overwrite policy** — unique `(user_id, source, target, relation)`; recomputed edges replace older auto edges of the same relation. 🟡
68. **Write `backend/tests/test_kb_related.py`** — mocked embeddings above/below threshold, shared-concept edges, backlink symmetry, incremental scoping. 🟡
69. **Frontend "Linked notes" panel** — per-document list of inferred links with the relation label + confidence. 🟡
70. **Add `GET /api/kb/documents/{id}/related?relation=`** endpoint wrapping the inference results. 🟡


## Group 8 — Idea 18 🟡: Graph visualization & explorer (phrases 71–80)

71. **Add a force-directed graph dependency to the frontend** — `react-force-graph-2d` (or `vis-network`) in `frontend/package.json`. 🟡
72. **Extend `GET /api/kb/graph`** — `?source=&tag=&concept=&relation=&limit=` filters + `nodes`/`links` shapes ready for the viz component. 🟡
73. **Create the `KnowledgeGraphExplorer` page/component** (`frontend/src/pages/KnowledgeGraph.tsx` + route in `App.tsx` + nav link). 🟡
74. **Color-code node types** — documents / concepts / tags distinct hues; size by degree or embedding coverage. 🟡
75. **Click-through behavior** — clicking a node opens the document detail / concept index / tag filter view. 🟡
76. **Add filter controls** — source select, tag chips, concept search, relation toggle (from `GET /api/kb/graph` params). 🟡
77. **Cap the initial render** (e.g. 200 nodes) with a "load more" expander to keep the force layout responsive. 🟡
78. **Add greedy community detection (stretch)** — cluster nodes by edge density and tint cluster colors. 🟡
79. **Write tests** — backend: graph endpoint filters + pagination; frontend: component render + filter interaction (vitest). 🟡
80. **Wire the graph into `endpoints.kb.graph` in `api.ts`** and add a "Graph" nav entry under the Second Brain group. 🟡


## Group 9 — Idea 19 🔴: Duplicate & near-duplicate detection, chunk level (phrases 81–90)

81. **Add `KB_NEARDUP_THRESHOLD` (default 0.95) and a `KB_NEARDUP_METHOD` (embedding|minhash) setting** to `config.py`. 🔴
82. **Implement candidate generation** — for small vaults: chunk-pair cosine similarity over `kb_embeddings`; for large vaults: MinHash/LSH shingles (`datasketch`, optional dep, import-guarded). 🔴
83. **Verify candidates exactly** — cosine ≥ `KB_NEARDUP_THRESHOLD` on the stored embeddings before creating any edge. 🔴
84. **Create `DUPLICATE_OF` edges with `provenance=auto`** — near-dup chunk → canonical chunk/document (reuse the Group 6 edge model). 🔴
85. **Add a config flag to exclude near-dupes from retrieval by default** (`KB_EXCLUDE_NEARDUP=true`) for Phase 3 readiness. 🔴
86. **Add a duplicate-review admin flow** — `GET /api/kb/duplicates` (pairs + scores) and `POST .../merge` / `.../archive` actions (per-user). 🔴
87. **Write `backend/tests/test_kb_neardup.py`** — paraphrased passages detected above threshold, below-threshold non-matches, MinHash parity with embedding path (when available). 🔴
88. **Frontend:** "Duplicates" review queue page — pairs with diff link, merge/archive buttons. 🔴
89. **Wire near-dup detection into the re-index job** (Group 10) so it stays fresh as the vault grows. 🔴
90. **Document the trade-off** in the KB runbook — embedding path accuracy vs MinHash scalability; threshold tuning guidance. 🔴


## Group 10 — Idea 20 🔴: Backfill & re-index tooling (phrases 91–100)

91. **Create `backend/app/cli/kb.py`** — a small CLI (`python -m app.cli.kb`) with `reindex`, `backfill`, and `stats` subcommands (argparse or typer). 🔴
92. **Add dirty flags to `KbDocument`** — `embedding_dirty`, `graph_dirty`, `tags_dirty` (boolean, default true on create) driving incremental work. 🔴
93. **Implement idempotent incremental reindex** — process only dirty documents; clear each flag only after its stage succeeds. 🔴
94. **Use content hashes to skip wasted work** — unchanged `content_hash` (Phase 1) means no re-extract, no re-embed, no re-chunk. 🔴
95. **Run reindex stages in dependency order** — embeddings (Idea 11) → auto-tags (Idea 14) → concepts (Idea 15) → graph edges (Ideas 16–17) → near-dup scan (Idea 19). 🔴
96. **Reuse the Phase 1 job queue** — reindex runs as a `KbJob` (`job_type=reindex`) with progress + resume via `kb_jobs`. 🔴
97. **Add an admin endpoint** — `POST /api/kb/admin/reindex` (role-guarded, teacher/admin) with `?source_id=` to scope a rebuild. 🔴
98. **Write `backend/tests/test_kb_reindex.py`** — incremental (only dirty docs processed), idempotent re-run (no-op), dirty-flag lifecycle, job progress. 🔴
99. **Frontend:** "Reindex" / "Backfill" buttons on the Sources page + progress chip (reuse the Phase 1 jobs UI). 🔴
100. **Update docs** — mark Ideas 11–20 as implemented in the master plan; add a runbook section (settings, thresholds, cost guards, pgvector migration path). 🔴

---

## Definition of Done — Phase 2

- [ ] `embeddings.py` serves batches with fallback models + deterministic local fallback; `test_embeddings.py` passes with `AI_ENABLED=false`.
- [ ] `kb_embeddings` is the source of truth; the store survives a restart (`sync_index`); `test_vector_persistence.py` passes.
- [ ] `VECTOR_STORE_BACKEND` supports `file` (dev) and `pgvector` (prod) behind the same interface.
- [ ] Metadata (author/date/url/language/reading time) is extracted, editable, and filterable.
- [ ] Auto-tagging proposes tags with provenance; nothing is committed without confirmation.
- [ ] Concepts are extracted, canonicalized, deduped, and linked via `MENTIONS`.
- [ ] The graph exposes wikilink/backlink/mentions/related/depends edges with thresholds; `GET /api/kb/graph` works per-user.
- [ ] Near-duplicates are flagged, excludable from retrieval, and reviewable/mergeable.
- [ ] Reindex is incremental, idempotent, resumable, and triggerable via CLI + admin UI.
- [ ] Every query stays user-scoped; ownership tests pass; `test_vector_store.py` remains green.

## Verification checklist

```bash
# Backend: Phase 2 test suite (run from backend/)
python -m pytest tests/test_embeddings.py tests/test_vector_persistence.py \
  tests/test_kb_metadata.py tests/test_kb_auto_tag.py tests/test_kb_concepts.py \
  tests/test_kb_graph.py tests/test_kb_related.py tests/test_kb_neardup.py \
  tests/test_kb_reindex.py -q

# Full regression (Phase 1 + everything existing)
python -m pytest tests/ -q

# Manual smoke test
# 1. Start the app → GET /api/kb/stats (empty-but-200)
# 2. Register a source + scan (Phase 1) → verify chunks appear
# 3. Trigger ingest job → embeddings cached in kb_embeddings
# 4. GET /api/kb/graph → nodes/edges for wikilinked docs
# 5. python -m app.cli.kb reindex --source=<id> → incremental, idempotent

# Frontend (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phase 3 is out of scope:** full-text + semantic + hybrid search, RAG, and the evaluation harness (Ideas 21–30). This phase only *builds and persists* the index the search will query.
- **`vector_store_faiss.py` doesn't exist yet** — for dev use the new file backend; adopt pgvector in prod instead of adding a second optional binary dependency.
- **Every AI call respects a daily budget** — embeddings, auto-tags, concepts, and dependency edges each get a cap (reuse the `SUMMARY_DAILY_LIMIT` guard pattern) so a misbehaving vault can't run up cost.
- **Cost/scale trade-offs are documented in the runbook** (phrase 90): embedding-based near-dup accuracy vs MinHash scalability.
- **Per-user scoping is non-negotiable** — every table, query, job, and graph endpoint filters `user_id`; ownership tests mirror `test_ownership.py`.

