# Second Brain Integration — Phase 1 Implementation Plan (100 Phrases)

**Goal:** Implement **Phase 1 — Second Brain Foundation & Ingestion (Ideas 1–10)** from
[`SECOND_BRAIN_AI_INTEGRATION_PLAN.md`](./SECOND_BRAIN_AI_INTEGRATION_PLAN.md) as **100 concrete,
ordered implementation phrases** — a build-ready checklist.

**Audit status (from §2 of the master plan):**
- 🔴 genuinely new (5): Idea 1 (data model), Idea 6 (OCR), Idea 7 (chunking), Idea 8 (dedupe), Idea 10 (job queue)
- 🟡 partial / extends existing code (5): Ideas 2–5 and Idea 9 build on existing patterns and code

**Scope:** Knowledge Core data model, source registry, folder watcher, markdown parser,
PDF/arXiv ingestion, OCR, semantic chunking, content-hash dedupe, version history, and the
ingestion job queue. **Embeddings, vector persistence, and search are Phase 2 (Ideas 11–23) and
deliberately out of scope** — only the seams are prepared here (chunk `token_estimate`, the job's
embedding hook, and the already-built-but-unused `vector_store.py`).

---

## Grounding — what already exists to build on

| Piece | Where | What Phase 1 reuses |
|---|---|---|
| `Base` / `get_db` / idempotent ALTERs | `backend/app/database.py` | `COLUMN_MIGRATIONS` pattern; `create_all` covers brand-new tables |
| Settings + env overrides | `backend/app/config.py` | All new `KB_*` settings go here (commented sections, like `SUMMARY_DAILY_LIMIT`) |
| Text extraction (TXT/MD/DOCX/PDF) | `backend/app/services/text_extractor.py` | `extract()`, `EXTRACTABLE_TYPES`, `NoExtractableTextError` |
| Extract + cache cap | `backend/app/services/ingestion.py` | `MAX_EXTRACTED_CHARS = 60_000` cap pattern |
| Vector store (unused today) | `backend/app/services/vector_store.py` | **Do NOT touch in Phase 1** — it is the Phase 2 hook (Idea 12) |
| Upload security helpers | `backend/app/routers/materials.py` | Mirror `_allowed_extension`, `_rejects_path_traversal`, `_mime_sniff_rejects`, `MAX_UPLOAD_MB` (413) |
| AI client (model fallback) | `backend/app/services/ai_client.py` | `generate`/`generate_json` + `AI_ENABLED` switch; embedding hook lands in Phase 2 |
| Router registration + lifespan | `backend/main.py` | Register KB routers here; start/stop the watcher in lifespan (off in tests) |
| Per-user ownership tests | `backend/tests/test_ownership.py` | Model every KB test on this isolation pattern |

**File conventions:** models → `backend/app/models/kb/*.py`; service layer → `backend/app/services/kb/`;
routers → `backend/app/routers/kb_*.py`; schemas → `backend/app/schemas/kb.py`; tests →
`backend/tests/test_kb_*.py`. Register every model and router in `models/__init__.py` /
`routers/__init__.py` / `main.py`.

---

## How each phrase is written

`N. **Action** — what / why / where (status: 🔴 new · 🟡 extends existing)`

Phrases are numbered 1–100 and grouped 10-per-idea. Each is independently verifiable; groups must
be built in order because later ideas depend on earlier ones.

---

## Group 1 — Idea 1 🔴: Knowledge Core data model (phrases 1–10)

1. **Create the `backend/app/models/kb/` package** with an `__init__.py` — home for every Knowledge Core model (source, document, chunk, tag, edge, version, job). 🔴
2. **Define `KbSource` (`kb_sources`)** — `id, user_id (FK users.id), name, source_type (vault_folder|local_dir|upload|cloud), root_path, enabled, last_scanned_at, created_at`. 🔴
3. **Define `KbDocument` (`kb_documents`)** — `id, user_id, source_id (FK kb_sources.id), path_rel, title, doc_type, content_hash, char_count, frontmatter_json, outline_json, extracted_text, ocr_used, status (new|changed|unchanged|deleted|failed), created_at, updated_at, indexed_at`. 🔴
4. **Define `KbChunk` (`kb_chunks`)** — `id, user_id, document_id (FK kb_documents.id), seq, content, char_start, char_end, heading_path, token_estimate`. 🔴
5. **Define `KbTag` (`kb_tags`)** — `id, user_id, name, kind (inline|auto)` with a unique constraint on `(user_id, name)`. 🔴
6. **Define `KbEdge` (`kb_edges`)** — `id, user_id, source_document_id, target_document_id, relation (WIKILINK|BACKLINK|DUPLICATE_OF|RELATED), weight` — the knowledge-graph spine built by Ideas 4 and 8. 🔴
7. **Define `KbVersion` (`kb_versions`)** — `id, user_id, document_id, version_seq, content_hash, snapshot_text, created_at`. 🔴
8. **Define `KbJob` (`kb_jobs`)** — `id, user_id, job_type (scan|ingest|reindex), status (queued|running|done|failed|interrupted), total_items, processed_items, error, created_at, finished_at`. 🔴
9. **Register every KB model** in `backend/app/models/__init__.py` (imports + `__all__`); brand-new tables are covered by `Base.metadata.create_all` — only later column adds go into `COLUMN_MIGRATIONS`. 🔴
10. **Write `backend/tests/test_kb_models.py`** — create each model, verify per-user isolation and FK cascades, mirroring `backend/tests/test_ownership.py`. 🔴


## Group 2 — Idea 2 🟡: Knowledge source registry (phrases 11–20)

11. **Create the `backend/app/services/kb/__init__.py` service package** with `KbService` helpers — every query filters `user_id` (per-user scoping rule). 🟡
12. **Add `KbSourceCreate`, `KbSourceUpdate`, `KbSourceResponse` schemas** in `backend/app/schemas/kb.py`, following the existing schema module conventions. 🟡
13. **Create `backend/app/routers/kb_sources.py`** with `POST /api/kb/sources` — validate `root_path` exists on disk at registration (else return 400 with a clear message); default `enabled=True`. 🟡
14. **Add `GET /api/kb/sources` (per-user list) and `GET /api/kb/sources/{id}`** with `Depends(get_current_user)` + `Depends(get_db)` like `materials.py`. 🟡
15. **Add `PUT /api/kb/sources/{id}`** — rename, re-path, or toggle `enabled`. 🟡
16. **Add `DELETE /api/kb/sources/{id}`** — decide and implement cascade behavior for its documents (recommended: hard-delete documents + chunks + versions in one transaction). 🟡
17. **Add `POST /api/kb/sources/{id}/scan`** — enqueue a scan job (Group 10) and return the `KbJob` id. 🟡
18. **Register `kb_sources` in `backend/main.py`** — add to the router imports and `app.include_router(...)`. 🟡
19. **Add `endpoints.kb.sources.*` to `frontend/src/services/api.ts`** — `list/create/update/delete/scan`. 🟡
20. **Add a Sources management page + sidebar/nav link** (mirror an existing page's structure) with add/edit/delete/scan actions. 🟡


## Group 3 — Idea 3 🟡: Folder watcher & file scanning (phrases 21–30)

21. **Add `KB_WATCH_ENABLED` (default True) and `KB_WATCH_POLL_INTERVAL` (default 30s) to `app/config.py`** in a commented section, matching the existing style. 🟡
22. **Create `backend/app/services/kb/scanner.py`** with `scan_source(db, source)` — the core idempotent scan routine. 🟡
23. **Walk `source.root_path` with `os.walk`**, filtering to `EXTRACTABLE_TYPES` from `text_extractor.py` (`.md/.pdf/.docx/.txt`). 🟡
24. **Compute a SHA-256 `content_hash` + `mtime` per file**, and skip noise dirs: `.obsidian/`, `.git/`, `.trash/`, `.tmp/`. 🟡
25. **Upsert logic:** new file → `status=new`; hash differs from stored → `status=changed`; identical → skip (mark `unchanged`); rows whose file vanished → `status=deleted`. 🟡
26. **Record per-scan stats on `KbSource`** — `last_scanned_at`, `files_seen`, `files_added`, `files_changed`, `files_removed`. 🟡
27. **Return a scan summary dict** (`files_seen`, `added`, `changed`, `removed`, `duplicates_found`) for the API + UI. 🟡
28. **Add an optional `watchdog` observer** with a pure-polling fallback behind an import guard, so CI never needs the native dependency. 🟡
29. **Start/stop watcher threads in `main.py` lifespan** — skipped when `KB_WATCH_ENABLED=false` or under tests (tests call the scanner directly). 🟡
30. **Write `backend/tests/test_kb_scanner.py`** — temp-dir fixture with new / changed / deleted files; assert upserts and status transitions. 🟡


## Group 4 — Idea 4 🟡: Markdown parser — frontmatter & wikilinks (phrases 31–40)

31. **Add `markdown-it-py` and `python-frontmatter` to `backend/requirements.txt`** (verify they don't collide with existing pins). 🟡
32. **Create `backend/app/services/kb/markdown_parser.py`** exposing `parse_markdown(text: str) -> KbMarkdown` (dataclass with `frontmatter`, `wikilinks`, `tags`, `callouts`, `outline`). 🟡
33. **Parse YAML frontmatter** into `frontmatter_json` — `title`, `tags`, `aliases`, `date`, `created`, plus any custom keys, preserving unknown keys. 🟡
34. **Extract `[[wikilinks]]`** including `[[path/to/note|alias]]` and `[[note#heading]]` fragments; normalize targets to relative vault paths for later `kb_edges` resolution. 🟡
35. **Extract inline `#tags` and `#nested/tags`**, excluding tag-looking text inside code blocks and URLs. 🟡
36. **Detect Obsidian callouts** (`> [!note]`, `> [!warning]`, …) and code blocks (fenced + indented) so the chunker can keep them intact. 🟡
37. **Build a heading outline** — `[{level, text, char_start}]` with absolute char offsets — the input for heading-aware chunking (Group 7). 🟡
38. **Detect daily-note dates** from filenames matching `YYYY-MM-DD.md` → store `doc_date` on `KbDocument`. 🟡
39. **Persist `frontmatter_json` + `outline_json`** on `kb_documents` during scan/ingest; keep raw `extracted_text` for versioning/diff. 🟡
40. **Write `backend/tests/test_kb_markdown.py`** — frontmatter, wikilinks (incl. alias + fragment), nested tags, callouts, outline char offsets, daily-note naming, code-block exclusion. 🟡


## Group 5 — Idea 5 🟡: PDF & research-paper ingestion (phrases 41–50)

41. **Extend `text_extractor.py`'s PDF branch** to also return per-page text boundaries (page numbers + offsets) without breaking the existing `extract()` signature used by `ingestion.py`. 🟡
42. **Create `backend/app/routers/kb_documents.py`** with `POST /api/kb/documents/upload` — writes the file under `settings.UPLOAD_DIR` (UUID name, like `materials.py`) and creates a `KbDocument` row. 🟡
43. **Mirror the `materials.py` upload security:** `_allowed_extension`, `_rejects_path_traversal`, `_mime_sniff_rejects`, and the `MAX_UPLOAD_MB` → 413 check. 🟡
44. **Extract text with the existing `extract()`** and cache into `extracted_text`, capped at `MAX_EXTRACTED_CHARS = 60_000` (reuse the `ingestion.py` pattern). 🟡
45. **Create `backend/app/services/kb/arxiv.py`** — fetch paper metadata (title, authors, abstract) from the arXiv API with an `httpx` timeout, mirroring `ai_client.py`'s HTTP style. 🔴
46. **Store `metadata_json` (`arxiv_id`, `title`, `authors`, `abstract`)** on `kb_documents`; auto-detect arXiv IDs from filenames and PDF first-page text. 🔴
47. **Add an import-paper flow** — user pastes an arXiv ID (or uploads a PDF) → fetch metadata → create the document; expose it as `POST /api/kb/papers/import`. 🔴
48. **Cache arXiv lookups by ID and fail gracefully offline** — no network → skip metadata, still ingest the text (log a warning, never 500). 🔴
49. **Write `backend/tests/test_kb_arxiv.py`** (mock the arXiv API with `monkeypatch`/`respx`-style fake) plus an upload test with a sample PDF asserting the 413/400 guards. 🟡
50. **Frontend:** add vault-import + paper-import options and `endpoints.kb.documents.upload` / `endpoints.kb.papers.import` in `api.ts`; show paper metadata on the document detail view. 🟡


## Group 6 — Idea 6 🔴: OCR for scanned documents (phrases 51–60)

51. **Add optional OCR deps** (`pytesseract`, `pdf2image`, `Pillow`) as import-guarded extras in `backend/requirements.txt` — nothing may break when they're absent. 🔴
52. **Add `KB_OCR_ENABLED` (default False) and an optional tesseract binary path to `config.py`.** 🔴
53. **Add `needs_ocr` detection:** after `pypdf` extraction, if a page yields < ~50 chars, flag the document for OCR (store the flag on `KbDocument`). 🔴
54. **Create `backend/app/services/kb/ocr.py`** — `ocr_pdf(path)` renders pages to images (`pdf2image`) and runs tesseract via `pytesseract`. 🔴
55. **Merge OCR text into `extracted_text`** and set `ocr_used=True` on the document row. 🔴
56. **Graceful degradation:** missing tesseract binary or packages → log a warning and mark the document `status=failed` (never crash the scan). 🔴
57. **Cache OCR output in `extracted_text`** so re-scans of unchanged files skip OCR entirely. 🔴
58. **Hook OCR into the ingest job (Group 10)** as a per-document stage running before chunking. 🔴
59. **Write `backend/tests/test_kb_ocr.py`** — monkeypatch `pytesseract.image_to_string` to return fake text; assert `ocr_used=True` and the merged result; assert graceful failure when the binary is missing. 🔴
60. **Expose `ocr_used` in schemas + a small "OCR" badge in the document-list UI.** 🔴


## Group 7 — Idea 7 🔴: Semantic (heading-aware) chunking (phrases 61–70)

61. **Add `KB_CHUNK_SIZE` (default 1200 chars) and `KB_CHUNK_OVERLAP` (default 150) to `config.py`.** 🔴
62. **Create `backend/app/services/kb/chunker.py`** — `chunk_text(text, outline) -> list[KbChunkData]`. 🔴
63. **Split at H2/H3 boundaries first** using the Idea 4 outline, so sections stay intact; merge small sections and split oversized ones. 🔴
64. **Fall back to paragraph/sentence boundaries** for non-markdown text (PDFs, TXT) with `KB_CHUNK_OVERLAP` carry-over. 🔴
65. **Emit `char_start`/`char_end` per chunk** (for source highlighting in Phase 3 search) plus `heading_path` context. 🔴
66. **Cap input at `MAX_EXTRACTED_CHARS`** before chunking (reuse the `ingestion.py` cap). 🔴
67. **Re-chunk idempotently:** delete existing chunks for the document, insert new ones in a single transaction. 🔴
68. **Record `token_estimate` per chunk** (≈ chars/4) — the batching seam for Phase 2 embeddings (Idea 12). 🔴
69. **Write `backend/tests/test_kb_chunker.py`** — heading splits, overlap correctness, valid non-overlapping char ranges, oversized-section splitting, idempotent re-chunk. 🔴
70. **Add `GET /api/kb/documents/{id}/chunks`** (per-user) for debugging and future snippet highlighting. 🔴


## Group 8 — Idea 8 🔴: Content-hash deduplication (phrases 71–80)

71. **Add a unique constraint/index on `(user_id, content_hash)`** in `kb_documents` (via a new-table DDL or a `COLUMN_MIGRATIONS` entry + unique index creation). 🔴
72. **Before inserting during scan/ingest, look up an existing row by `(user_id, content_hash)`.** 🔴
73. **On a match, skip the duplicate insert** and record a `KbEdge` with relation `DUPLICATE_OF` pointing at the canonical (first-indexed) document. 🔴
74. **Return `duplicate_of_id`** in the upload/ingest response so callers know the file was deduped. 🔴
75. **Decide and document the dedupe policy** (recommended: keep the canonical row, link duplicates, surface them in the UI) and test it. 🔴
76. **Add `duplicates_found` to the scan summary** (Group 3, phrase 27) so users see the dedupe effect. 🔴
77. **Write `backend/tests/test_kb_dedupe.py`** — same content, different filenames → one canonical document + `DUPLICATE_OF` edge; different content → two documents. 🔴
78. **Handle the same-hash-different-source edge case** (e.g. one file registered in two vaults) — document the chosen behavior in a test. 🔴
79. **Show a "Duplicate of …" notice** in the document-list UI. 🔴
80. **Hash raw file bytes, not decoded text**, so encoding differences never cause false collisions. 🔴


## Group 9 — Idea 9 🟡: Version history & diff (phrases 81–90)

81. **In the ingest path, before updating a changed document, snapshot the previous content** into `kb_versions` (bump `version_seq`), reusing the existing `updated_at`-tracking habit from `notes.py`. 🟡
82. **Add `GET /api/kb/documents/{id}/versions`** (per-user, newest first) in `kb_documents.py`. 🟡
83. **Add `POST /api/kb/documents/{id}/restore`** — restore content from a version, writing a new version row for the rollback itself. 🟡
84. **Add `GET /api/kb/documents/{id}/diff?from=&to=`** using `difflib.unified_diff` on snapshot contents. 🟡
85. **Cap versions per document** (keep the latest 20; delete older snapshots) to bound storage growth. 🟡
86. **Store snapshots as `snapshot_text` for small documents and file paths for large ones** (past a size threshold). 🟡
87. **Only snapshot when the content hash actually changed** — metadata-only rescans must not create versions. 🟡
88. **Write `backend/tests/test_kb_versions.py`** — snapshot-on-change, restore, diff output, cap enforcement, no-op on unchanged rescans. 🟡
89. **Frontend:** version-history list + restore button + diff view on the document detail page. 🟡
90. **Route versioning through the job pipeline (Group 10)** so scan and manual reindex both snapshot consistently. 🟡


## Group 10 — Idea 10 🔴: Ingestion job queue & status (phrases 91–100)

91. **Create `backend/app/services/kb/jobs.py`** with an in-process `ThreadPoolExecutor` (e.g. `max_workers=2`) wrapping scan and ingest work. 🔴
92. **Add `submit_scan_job(db, source_id)` and `submit_ingest_job(db, document_ids)`** returning a `KbJob` row. 🔴
93. **Track job state in `kb_jobs`** — `queued → running → done | failed` with `processed_items`/`total_items` updated as the batch progresses. 🔴
94. **Add `GET /api/kb/jobs` and `GET /api/kb/jobs/{id}`** (per-user) so the UI can poll progress. 🔴
95. **Make jobs idempotent and resumable:** on startup, re-queue rows stuck in `running` (flip to `interrupted`, retry on next trigger). 🔴
96. **Run the per-document pipeline inside the ingest job, in order:** extract → OCR (if flagged) → dedupe → version snapshot → chunk → *(embedding hook reserved for Phase 2 / Idea 12)*. 🔴
97. **Give jobs their own DB session per batch** — never share a `get_db` session across worker threads (SQLite `check_same_thread=False` caveat). 🔴
98. **Keep tests hermetic:** when `AI_ENABLED=false` or the vault is tiny, run ingest inline/synchronously instead of queueing. 🔴
99. **Write `backend/tests/test_kb_jobs.py`** — submit a scan/ingest job, await completion, assert status transitions, error capture, and interrupted-resume behavior. 🔴
100. **Frontend:** "Scan now" / "Reindex" buttons + a job-progress status chip, wired through `endpoints.kb.jobs.*` in `api.ts`. 🔴

---

## Definition of Done — Phase 1

- [ ] All 7 KB tables (`kb_sources`, `kb_documents`, `kb_chunks`, `kb_tags`, `kb_edges`, `kb_versions`, `kb_jobs`) exist on a fresh DB via `create_all`.
- [ ] A user can register their Obsidian vault folder as a source, run a scan, and see documents + parsed frontmatter/wikilinks/tags in the UI.
- [ ] PDF upload → text extracted (with the materials-router security guards); arXiv import fetches metadata when online.
- [ ] OCR runs only for flagged image-only PDFs when `KB_OCR_ENABLED=true`, and degrades gracefully.
- [ ] Duplicates are detected by content hash and linked via `DUPLICATE_OF` edges.
- [ ] Changed documents get version snapshots; restore + diff endpoints work.
- [ ] Long scans run as resumable background jobs with visible progress; small/hermetic runs stay synchronous.
- [ ] Every `kb_*` query is user-scoped; ownership tests pass.

## Verification checklist

```bash
# Backend: KB test suite (run from backend/)
python -m pytest tests/test_kb_models.py tests/test_kb_scanner.py tests/test_kb_markdown.py \
  tests/test_kb_chunker.py tests/test_kb_dedupe.py tests/test_kb_versions.py \
  tests/test_kb_jobs.py tests/test_kb_ocr.py tests/test_kb_arxiv.py -q

# Full regression (nothing existing may break)
python -m pytest tests/ -q

# Manual smoke test
# 1. Start the app (uvicorn main:app)  → GET /api/health
# 2. POST /api/kb/sources pointing at a small fixture dir (NOT the 111 MB vault)
# 3. POST /api/kb/sources/{id}/scan → poll GET /api/kb/jobs/{id}
# 4. GET /api/kb/documents → verify rows + chunks + dedupe + versions

# Frontend typecheck (from frontend/)
npm run typecheck
```

## Notes & boundaries

- **Phase 2 is out of scope:** embeddings, vector persistence, and semantic search (Ideas 11–23). The chunker's `token_estimate` and the job's embedding hook are the only seams opened now.
- **`vector_store.py` stays untouched in Phase 1** — it is the Phase 2 wiring target (Idea 12).
- **Never index `Obsidian Vault/` through git** — it is 111 MB, untracked and gitignored; scanning happens at runtime through the source registry.
- **Add `.gitignore` entries for any new runtime dirs** (e.g. `backend/kb_snapshots/` if large-doc snapshots are stored on disk).
- **Wire every new model/router into `__init__.py` files and `main.py`** — a forgotten registration is the most common integration bug.

