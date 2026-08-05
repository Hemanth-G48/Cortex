# Second Brain + AI-Powered Subject Management — Integration Plan

**Project:** Student Life OS (FastAPI + React)
**Document status:** Implementation blueprint
**Scope:** Integrate a personal Second Brain (Obsidian vault, markdown, PDFs, research papers) as the central knowledge repository, and build an AI-powered subject-management layer on top of it.

---

## 1. Executive Summary

The Student Life OS currently holds many powerful islands: a SyllabusAI curriculum module (institutions → programs → subjects → units → materials), AI summaries/quizzes/flashcards, a reading tracker, a single-row brain dump widget, notes, and an OpenAI-compatible AI client (`app/services/ai_client.py`) with model fallback. What is missing is a **unifying knowledge substrate**: the application does not yet *know what the user knows*.

This plan defines how to turn the user's personal **Second Brain** — their Obsidian vault, markdown files, PDFs, and research papers — into the single source of truth the app reasons over. Every AI feature (tutor, summaries, quizzes, study plans, recommendations) will be grounded in retrieved knowledge from this repository. In parallel, an **AI subject-management layer** will automatically organize academic subjects from syllabi, detect topic dependencies, and drive personalized study plans, revision schedules, and exam preparation.

The roadmap contains **100 implementation ideas** organized into 10 phases, progressing from ingestion infrastructure → embeddings & knowledge graph → retrieval → note intelligence → subject management → study execution → AI tutor → personalization → automation → advanced multi-agent AI. It builds *on top of* the existing codebase (reusing `ai_client`, `vector_store`, `text_extractor`, `ingestion`, the curriculum models, and the existing AI routers) rather than replacing it. The guiding principle: **if information is not in the Second Brain, the app assumes the user does not know it.**

**Audit note (2026-08-05):** an audit of the current repo and your notes found that most ideas extend existing code. The one already-implemented item (quiz XP, original Idea 69) has been replaced with a new idea, so the list now stands at **56 genuinely new · 44 partial / extendable · 0 already-done** — see §2 for the full inventory and §2.4 for the corrections. Every idea heading in §11 carries a status marker from that audit.

### Guiding principles

1. **Second Brain as source of truth** — all AI answers, recommendations, and study plans must be grounded in the user's knowledge base, with citations to source notes.
2. **Build on existing infrastructure** — reuse `ai_client.py` (model fallback, `AI_ENABLED` switch), `vector_store.py`, `text_extractor.py`, and the SyllabusAI data model. Extend, don't rewrite.
3. **Progressive enhancement** — deterministic local fallbacks keep every feature working when AI is disabled (the existing pattern).
4. **Privacy-first** — the vault and its derived indexes belong to the user; per-user scoping follows the existing `get_current_user` ownership model.
5. **Never guess knowledge** — retrieval misses are surfaced honestly ("not found in your Second Brain") rather than hallucinated.

---

## 2. Current State Audit & Repo Grounding

Audited 2026-08-05 against the live repo, the user's plan documents, and the `Obsidian Vault/` in this repository. Every idea in §11 carries a status marker: 🔴 new · 🟡 partial (extends existing code) · ✅ already implemented.

### 2.1 What already exists — reuse, don't rebuild

| Existing capability | Evidence (repo) | Powers ideas |
|---|---|---|
| OpenAI-compatible AI client: `generate`, `generate_json`, JSON-block parser, model fallback chain, `AI_ENABLED` kill-switch | `backend/app/services/ai_client.py` | every AI idea |
| AI endpoints: complete, quiz, flashcards, study-plan, syllabus, chat, grade-answer (with deterministic fallbacks) | `backend/app/routers/ai.py` + `services/ai_fallback.py` | 31–34, 42, 47, 51, 61, 63, 66 |
| Cached unit summaries + unit quizzes awarding XP | `services/summaries.py`, `routers/quizzes.py`, `QuizAttemptResult.xp_awarded` | 31, 33, 63, 69 |
| Flashcard decks/cards with `streak`, `next_review` fields | `routers/flashcards.py`, `models/flashcard.py` | 34, 52, 85 |
| Study plans CRUD + AI 4-week generation | `routers/study_plans.py`, `pages/StudyPlans.tsx` | 51 |
| Curriculum (institutions → programs → subjects → units) + material uploads + text extraction (TXT/PDF/DOCX/MD) | `routers/curriculum.py`, `routers/materials.py`, `services/text_extractor.py` | 5, 7, 42, 44, 45 |
| Reading tracker + in-app PDF reader | `routers/books.py`, `components/reading/PDFReader.tsx` | 5, 25, 96 |
| Brain dump (single row per user) + Notes CRUD (`pinned`, `updated_at`) | `routers/braindumps.py`, `routers/notes.py` | 9, 40 |
| Daily schedule, journal, reminders, notifications | `routers/daily_schedule.py`, `events.py`, `notifications.py` | 35, 52, 60, 90 |
| Gamification: XP, habits, quests, characters, rewards | `services/habit_xp.py`, quest/character/reward routers | 69 |
| Analytics: focus minutes, study heatmap, assignment analytics, per-unit quiz stats | `routers/analytics.py`, `services/quiz_stats.py`, `routers/assignments.py` | 57, 58, 99 |
| In-memory vector store (numpy / optional FAISS) with cosine retrieval — **built but unused by any router or service** | `services/vector_store.py`, `tests/test_vector_store.py` | 11, 12, 22, 23 |
| AI evaluation scaffolding | `.deepeval/` at repo root | 26, 100 |

### 2.2 The user's real Second Brain

- `Obsidian Vault/` in this repo: **2,399 files / ~111 MB** — cybersecurity, machine learning, deep learning, networks, AI, recommender systems, reinforcement learning, theory of computation, web security, and more (also referenced at `/home/hemanth/Documents/Obsidian Vault`).
- The vault runs the **Obsidian Copilot** plugin → the user already has in-vault AI; the app layer must complement it (server-side index, app-integrated tutor), not duplicate it.
- Existing vault assets give several ideas real starting data: wikilinks (Idea 17), daily notes `YYYY-MM-DD.md` (Idea 35), and `networks/obsidian_agent.py`, which auto-links notes into `Networks.md` (Ideas 3, 83).
- **Repo hygiene:** `Obsidian Vault/` is untracked but *not* gitignored — add it to `.gitignore` before building a watcher over it.

### 2.3 Audit result of the 100 ideas

| Status | Count | Meaning |
|---|---|---|
| 🔴 New | **56** | Build from scratch |
| 🟡 Partial | **44** | Related code exists — extend it |
| ✅ Done | **0** | The single already-implemented item (quiz XP) was replaced by the new Idea 69 — see §2.4 |

Per phase (P1–P10): 5🟡/5🔴 · 5🟡/5🔴 · 3🟡/7🔴 · 6🟡/4🔴 · 6🟡/4🔴 · 6🟡/4🔴 · 4🟡/6🔴 · 10🔴 · 3🟡/7🔴 · 6🟡/4🔴.

### 2.4 Corrections to the plan (apply when implementing)

1. **Ideas 11–12 are cheaper than written** — the `VectorStore` already exists with tests; first wire an embeddings client into it, then persist (pgvector). A fast first milestone, not a full phase.
2. **Ideas 31/33/34/51/61 are extensions**, not greenfield — reuse the existing summaries/quizzes/flashcards/study-plan services, prompts, and UI; the real work is pointing them at vault documents.
3. **Idea 61 (RAG tutor) is the flagship gap** — today's `/api/ai/chat` injects assignments/courses only and performs zero retrieval from notes or the vault.
4. **Idea 42 (syllabus parsing) is shallow today** — `/api/ai/syllabus` extracts assignments + due dates only; full unit/topic/outcome extraction is the actual work.
5. **Idea 69 is already done** — quiz attempts already award XP (`xp_awarded`). The idea has been replaced with "knowledge capture & revision XP" (see §11).
6. **Phase 3 (search) is greenfield** — no FTS or semantic search exists; `MaterialSearch` is a simple `q` filter.
7. **SyllabusAI is also a standalone Node app** (`SyllabusAI/`) — the FastAPI port in `backend/app` is canonical; avoid drift.

---

## 3. Overall Architecture

The system is a layered architecture around a central **Knowledge Core** that both the Second Brain pipeline and the Subject-Management layer feed into, and that every AI feature reads from.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (React + Vite)                       │
│  Knowledge Explorer │ AI Tutor │ Subject Manager │ Study Planner │ ...  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ REST /api/*
┌───────────────────────────────────▼─────────────────────────────────────┐
│                            BACKEND (FastAPI)                             │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────────┐  ┌────────────────────┐  │
│  │  INGESTION LAYER │  │  KNOWLEDGE CORE       │  │  AI ORCHESTRATION  │  │
│  │  folder watcher  │  │  docs / chunks /      │  │  retrieval →       │  │
│  │  obsidian sync   │→ │  embeddings / graph   │─▶│  prompt → response │  │
│  │  pdf / ocr       │  │  search / metadata    │  │  (RAG, agents)     │  │
│  └──────────────────┘  └──────────────────────┘  └────────────────────┘  │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────────┐  ┌────────────────────┐  │
│  │  SUBJECT LAYER   │  │  LEARNING LAYER       │  │  PLATFORM LAYER    │  │
│  │  syllabus parse  │  │  study plans /        │  │  jobs / queue /    │  │
│  │  topics / graph  │  │  revision / progress  │  │  vector store /    │  │
│  └──────────────────┘  └──────────────────────┘  └────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  SQL (SQLite→Postgres)      Vector Store (numpy/FAISS→pgvector)   Vault FS (Obsidian, PDFs)
```

**Key architectural decisions**

- **Monolith with clear service boundaries.** Stay on the existing FastAPI monolith; add new `app/services/*` modules (e.g. `second_brain/`, `embeddings.py`, `retrieval.py`, `graph.py`, `subjects_ai.py`) instead of microservices. Simpler to deploy, and the existing tests/CI patterns carry over.
- **The Knowledge Core is the contract.** All models that represent ingested knowledge (`kb_documents`, `kb_chunks`, `kb_concepts`, `kb_edges`) live behind one service layer so ingestion, search, and RAG never touch SQL directly.
- **Async where it matters.** Ingestion, embedding generation, OCR, and syllabus parsing are long-running; they run in a background job queue (threadpool initially, then a proper task queue such as ARQ/Celery or Postgres-backed jobs).
- **Existing routers stay untouched.** New capabilities are additive routers (`/api/kb/*`, `/api/subjects-ai/*`, `/api/tutor/*`). Existing `/ai/*`, `/curriculum/*`, `/materials/*`, `/summaries`, `/quizzes` endpoints keep working as today.

---

## 4. System Components

| Component | Responsibility | Builds on (existing) |
|---|---|---|
| **Ingestion Pipeline** | Watch folders, parse markdown/PDF/DOCX, OCR scanned pages, extract metadata, normalize into `kb_documents` + `kb_chunks` | `services/ingestion.py`, `services/text_extractor.py` |
| **Embeddings Service** | Turn chunks into dense vectors via an OpenAI-compatible embeddings endpoint; cache per hash | `services/ai_client.py` (same provider pattern) |
| **Vector Store** | Dense retrieval (cosine); upgrade path numpy → FAISS → pgvector | `services/vector_store.py` |
| **Search Service** | Hybrid retrieval: BM25/FTS5 full-text + vector, reciprocal-rank fusion, per-user scoping | `services/vector_store.py` |
| **Knowledge Graph** | `kb_concepts` + `kb_edges` (links, mentions, dependencies, synonyms); graph queries (neighbors, paths, subgraphs) | new; feeds from wikilinks/backlinks in markdown |
| **Metadata & Tagging** | Frontmatter parsing, auto-tagging, source/author/date extraction, dedupe by content hash | new |
| **Subject Intelligence** | Syllabus parsing, topic/unit extraction, dependency graph, difficulty & time estimation | curriculum models + `materials.py` |
| **Study Engine** | Roadmaps, spaced-repetition revision, exam-prep mode, daily scheduling | `study_plans.py`, `daily_schedule.py`, `assignments.py` |
| **AI Tutor** | RAG chat over the Knowledge Core; doubt solving; practice questions; mock tests | `routers/ai.py`, `services/prompts.py` |
| **Memory & Profile** | Long-term user memory: learned concepts, preferences, gaps, trajectory | `users.py`, `habit_xp.py` patterns |
| **Automation Service** | Scheduled/event-driven jobs: auto-tag, auto-flashcard, auto-summary, auto-organize | job queue |
| **Frontend Workspaces** | Knowledge Explorer, Tutor Chat, Subject Manager, Study Planner, Insights | existing pages (Reading, Subject, Unit, SyllabusImport, AIChat) |

---

## 5. AI Architecture

### 5.1 Provider abstraction (existing)
`ai_client.py` already provides: `generate()`, `generate_json()`, `extract_json()`, model fallback chains, and the `AI_ENABLED` kill-switch. All new AI features use this client — **no feature may call the network directly**.

### 5.2 Added layers

1. **Embedding client** (`embeddings.py`) — calls `POST {AI_BASE_URL}/embeddings` (OpenAI-compatible), with deterministic hashing fallback for `AI_ENABLED=false` so tests stay hermetic. Embeddings are cached by content hash to avoid duplicate API cost.
2. **Retriever** (`retrieval.py`) — the single entry point for "give me the user's knowledge about X": hybrid search → rerank → top-k chunks with source citations. Used by tutor, summaries, flashcards, study plans, and recommendations.
3. **Prompt registry** (`prompts.py` extension) — all system prompts are centralized, versioned, and testable. Prompt templates declare which retrieved context they consume.
4. **RAG pipeline** — context assembly: retrieved chunks + graph neighbors + subject structure + user memory, formatted with source paths so answers can cite notes.
5. **Agent orchestration (Phase 10)** — an orchestrator agent coordinates specialist sub-agents (retriever, summarizer, quizzer, tutor, scheduler) via a small task protocol; every agent inherits the provider abstraction and cost guardrails.
6. **Evaluation harness** — golden-question sets per subject; retrieval hit-rate and answer-faithfulness scored offline so changes to prompts/retrieval are regression-tested.

### 5.3 Cost & safety guardrails
- Daily generation caps per feature (pattern already exists: `SUMMARY_DAILY_LIMIT`).
- Embedding budget per document; chunk count alerts.
- All generation is per-user scoped; retrieved context is filtered by `user_id` at the SQL level (never trust the model to scope).
- Citations are mandatory in tutor output; refusal to answer from outside the vault is the default when retrieval is empty.

---

## 6. Second Brain Architecture

### 6.1 Knowledge model (new tables)

```
kb_documents  — one row per ingested file/note (path, source, title, type,
                frontmatter json, content_hash, size, status, version, timestamps)
kb_chunks     — one row per text chunk (document_id, ordinal, text, token_count,
                embedding_id, char_start/end)
kb_embeddings — (chunk_id, model, vector_blob or pgvector column, created_at)
kb_concepts   — extracted concepts/entities (name, canonical_name, definition,
                first_seen_doc, confidence)
kb_edges      — typed relationships (concept→concept, doc→concept, doc→doc):
                LINK, MENTIONS, DEPENDS_ON, RELATED, SYNONYM_OF, CITES, BACKLINK
kb_tags       — tags + auto-tag provenance
kb_versions   — version history per document (snapshot of content + hash)
kb_sources    — source registry (obsidian vault path, local folder, upload, arXiv,
                web clip, git repo) + sync cursor/state
```

### 6.2 Ingestion flows
- **Obsidian vault** — primary source. Watch the vault folder (poll or `watchdog`); parse markdown incl. YAML frontmatter, wikilinks `[[Note]]`, tags `#tag`, callouts, and daily notes; store relative paths so the app and vault stay in sync.
- **Local folders / uploads** — reuse `UPLOAD_DIR`; batch-import markdown/PDF/DOCX/TXT via the existing `text_extractor`.
- **Research papers** — arXiv metadata + PDF ingestion; extract title/abstract/authors via metadata APIs; chunk PDF text; store citations.
- **Web clippings & bookmarks** — reuse the Shiori-style bookmark pipeline if present; save readable content as markdown.
- **OCR** — scanned PDFs/image notes go through a Tesseract-based step (offline, optional) before chunking.
- **Git repos / cloud drives** (stretch) — poll and diff, import changed files only.

### 6.3 Sync & versioning
- Each source has a sync cursor (mtime + hash). Changed files re-ingest; deleted files are archived (not hard-deleted) so history survives.
- `kb_versions` snapshots on every change; the UI can diff and restore.
- Duplicate detection: content-hash at document level + near-duplicate detection at chunk level (embedding similarity) with a "merge/keep both" workflow.

### 6.4 Knowledge health
- Orphan detection (notes with no links), stale-note detection (no edits + no retrieval hits in N days), missing-knowledge detection (topics referenced in subjects but with zero covering chunks in the vault).

### 6.5 Vault reality (audit)

- The user's live vault (`Obsidian Vault/`, 2,399 files, ~111 MB) is already inside the repo and uses the Obsidian **Copilot** plugin. The app's Second Brain layer complements it (server-side indexing, app-integrated tutor) rather than duplicating in-vault AI.
- Vault wikilinks, daily notes, and `networks/obsidian_agent.py` (auto-links notes into `Networks.md`) give Ideas 17, 35, and 83 real starting data.

## 7. Subject Management Architecture

### 7.1 Concept: subjects are projections over the Knowledge Core

Academic subjects are **views** that tie together (a) structured curriculum data (the existing `curriculum_subjects`/`curriculum_units` + `materials`), (b) topics parsed from syllabi, and (c) matching knowledge chunks in the Second Brain. A `subject_profile` row links a `curriculum_subject` to its syllabus source, its dependency graph, and its coverage in the vault.

```
Syllabus (PDF/doc) ─▶ syllabus parser ─▶ topics[] + units[] + outcomes[]
       │                                        │
       ▼                                        ▼
curriculum_subject ◀─ subject_profile ──▶ topic_dependency_graph
       │                                        │
       ▼                                        ▼
   materials ──────────────────────────▶ kb_chunks (coverage mapping)
```

### 7.2 Components

| Component | Responsibility |
|---|---|
| **Syllabus Parser** | Extract course title, semester, credits, unit list, topics, learning outcomes, grading scheme from syllabus text (PDF/DOCX/MD via `text_extractor`).
| **Topic Extractor** | Split syllabus into granular topics; normalize synonyms (e.g. "MLE" → "Maximum Likelihood Estimation"); attach Bloom-level tags.
| **Dependency Graph** | Infer prerequisite relations between topics (explicit from syllabus, implicit from LLM analysis, refined by quiz performance).
| **Coverage Mapper** | For each topic, compute which `kb_chunks`/materials cover it (embedding + keyword match); this drives gap detection.
| **Estimator** | Difficulty (LLM rubric + past performance) and time-to-mastery (per topic) estimates.
| **Roadmap Generator** | Produce an ordered learning path respecting dependencies, deadlines, and user pace.
| **Revision Scheduler** | Spaced-repetition schedule per topic, decaying based on quiz/recall performance, pushing into `daily_schedule`/tasks.

### 7.3 Automatic lifecycle
1. **Detect** — new syllabus document or enrollment change triggers subject creation (auto-create `curriculum_subject` + `curriculum_units` if absent).
2. **Parse** — extract topics/units/outcomes.
3. **Map** — link to existing materials and vault coverage.
4. **Plan** — generate roadmap + revision schedule.
5. **Track** — assignments, labs, attendance, quiz/grade data feed progress analytics.
6. **Adapt** — weak-topic detection reshuffles the roadmap and prioritizes review.

---

## 8. Data Flow

### 8.1 Ingestion flow (write path)
```
[Obsidian vault / upload / PDF / arXiv] ─▶ Source Watcher ─▶ Normalizer
        ─▶ text_extractor ─▶ chunker ─▶ (hash dedupe) ─▶ kb_documents/kb_chunks
        ─▶ embeddings client ─▶ vector store ─▶ kb_concepts + kb_edges (async)
        ─▶ auto-tag / auto-summary / auto-flashcard jobs ─▶ notifications
```

### 8.2 Retrieval flow (read path)
```
[User question / tutor prompt / quiz request]
        ─▶ query analyzer (expand + route: full-text vs semantic vs graph)
        ─▶ hybrid retrieval (FTS5 + vector, RRF fusion, user scoping)
        ─▶ rerank (cross-encoder or LLM) ─▶ top-k chunks + graph neighbors
        ─▶ prompt assembly (retrieved context + user memory + subject context)
        ─▶ ai_client.generate ─▶ answer with citations ─▶ UI
```

### 8.3 Learning loop (feedback path)
```
[Quiz attempt / tutor interaction / task completion]
        ─▶ performance events (per topic, per concept)
        ─▶ update mastery scores ─▶ update dependency weights
        ─▶ regenerate roadmap & revision queue ─▶ next-session recommendations
```

### 8.4 Async orchestration
Long jobs (full vault index, OCR batch, syllabus parse) run in the job queue; the UI polls status via `GET /api/kb/jobs/{id}`. Every job is idempotent and resumable so a restart never corrupts the index.

---

## 9. Technology Recommendations

### 9.1 Stack alignment (extend, don't replace)
| Layer | Today | Recommended | Rationale |
|---|---|---|---|
| API | FastAPI | FastAPI (keep) | existing routers, tests, auth |
| ORM | SQLAlchemy 2.x | SQLAlchemy (keep) | existing models |
| DB | SQLite | **Postgres + pgvector** (production); SQLite stays for dev/CI | FTS5 full-text, pgvector column, concurrency, JSONB frontmatter |
| Vector store | numpy in-memory / FAISS | **pgvector** (with `VECTOR_STORE_BACKEND` config switch kept) | single source of truth, transactional with SQL, per-user filtering in one query |
| Embeddings | none | OpenAI-compatible `/embeddings` via the existing provider; fallback to hashed local vectors | reuses `AI_BASE_URL`/`AI_API_KEY` |
| Full-text | none | Postgres FTS (or SQLite FTS5 in dev) | hybrid retrieval base |
| OCR | none | Tesseract via `pytesseract` (optional, offline) | scanned PDFs |
| Background jobs | none (sync endpoints) | threadpool → Postgres-backed queue (ARQ or Celery) | long ingestion/embedding runs |
| File watching | none | `watchdog` (or simple polling for portability) | Obsidian vault sync |
| Markdown | — | `markdown-it-py` + `frontmatter` libs | wikilinks, callouts, YAML |
| Frontend | React + Vite + TS | keep; add `@tanstack/react-query` for cache/invalidation | growing data-fetching surface |

### 9.2 Recommended libraries (backend)
- `pgvector` (SQLAlchemy `Vector` type) or `sqlite-vec` for dev parity
- `pypdf` (already present), `python-docx` (already present), `pytesseract` (optional)
- `arxiv` client or direct ArXiv API for paper metadata
- `watchdog` for folder watching; `aiosqlite`/async engine only if moving async
- `nltk`/`spaCy` optional for concept extraction; otherwise LLM-based extraction with deterministic fallback

### 9.3 Config additions (`config.py`)
```
KB_VAULT_DIR=             # path to Obsidian vault (optional)
KB_SOURCES_JSON=          # JSON list of registered sources
EMBEDDINGS_MODEL=text-embedding-3-small
EMBEDDINGS_DIM=1536
KB_CHUNK_SIZE=800         # characters
KB_CHUNK_OVERLAP=120
KB_EMBED_BATCH=64
OCR_ENABLED=false
KB_DAILY_GEN_LIMIT=40     # LLM cost guard for KB jobs
AUTO_SUMMARY_ENABLED=true
AUTO_FLASHCARD_ENABLED=true
```

---

## 10. Database Design (High-Level)

### 10.1 Knowledge core
```
kb_sources(id, user_id, kind, name, root_path, cursor, enabled, created_at)
kb_documents(id, source_id, user_id, rel_path, title, doc_type, source_kind,
             frontmatter_json, content_hash, char_count, status, version,
             ocr_used, created_at, updated_at, deleted_at)
kb_versions(id, document_id, content_hash, size, snapshot_path, created_at)
kb_chunks(id, document_id, ordinal, text, char_start, char_end,
          token_count, embedding_id, created_at)
kb_embeddings(id, chunk_id, model, dim, embedding VECTOR, created_at)
kb_concepts(id, user_id, name, canonical_name, definition, doc_count,
            confidence, first_seen_document_id, created_at)
kb_edges(id, user_id, source_kind, source_id, target_kind, target_id,
         rel_type, weight, evidence_document_id, created_at)
kb_tags(id, user_id, name, provenance, created_at)
kb_doc_tags(doc_id, tag_id)
```

### 10.2 Subject intelligence
```
subject_profiles(id, subject_id, syllabus_document_id, semester, credits,
                 status, parse_state, created_at)
topics(id, subject_id, profile_id, title, normalized_title, bloom_level,
       difficulty_est, time_est_min, mastery_score, last_reviewed_at)
topic_dependencies(id, subject_id, prereq_topic_id, postreq_topic_id,
                   confidence, source)
topic_coverage(id, topic_id, chunk_id, score, method)      # vault coverage map
topic_materials(id, topic_id, material_id, role)
learning_events(id, user_id, topic_id, kind, payload_json, created_at)  # quiz/recall/study events
roadmaps(id, subject_id, version, payload_json, created_at)              # generated plans
revision_schedule(id, user_id, topic_id, due_at, interval_days, ease,
                  status, created_at)
user_memory(id, user_id, concept_id, strength, last_seen_at, exposure_count)
```

### 10.3 Migration strategy
Follow the existing `COLUMN_MIGRATIONS` pattern in `database.py`: register new columns there, and add new tables via `Base.metadata.create_all` (extend the models `__init__` exports). For Postgres, add an Alembic-style migration story only when the production DB is introduced.

---

## 11. The 100 Implementation Ideas

> **Status legend (from the §2 audit):** 🔴 = genuinely new · 🟡 = partial / extends existing code · ✅ = already implemented.

Each idea lists: **Objective**, **Why**, **Approach**, **Dependencies**, **Priority** (Critical / High / Medium / Low), and **Complexity** (S / M / L). Ideas are grouped into 10 phases; phases build on each other but every idea is independently shippable.

---

### Phase 1 — Second Brain Foundation & Ingestion (Ideas 1–10)

### Idea 1 🔴 — Knowledge Core data model
- **Objective:** Add `kb_sources`, `kb_documents`, `kb_chunks`, `kb_embeddings`, `kb_concepts`, `kb_edges`, `kb_tags`, `kb_versions` tables plus a `kb` service layer.
- **Why:** Every later feature (search, RAG, graph, subject coverage) needs one canonical place where vault knowledge lives; without it each feature would build its own private index.
- **Approach:** New SQLAlchemy models in `app/models/kb/*.py`, registered in `models/__init__.py`; per-user scoping on every table; service module `app/services/kb/` owning all access.
- **Dependencies:** Existing `Base`/`get_db`/`COLUMN_MIGRATIONS` patterns.
- **Priority:** Critical | **Complexity:** M

### Idea 2 🟡 — Knowledge source registry
- **Objective:** A `kb_sources` table + CRUD + UI where users register vault folders, local directories, uploads, and cloud sources.
- **Why:** Users need to tell the app *where* their Second Brain lives; the registry is the control point for sync and permissions.
- **Approach:** `POST /api/kb/sources` CRUD; `root_path` stored per source; watcher service iterates registered sources on start and on-demand.
- **Dependencies:** Idea 1.
- **Priority:** Critical | **Complexity:** S

### Idea 3 🟡 — Folder watcher & file scanning
- **Objective:** Scan source folders for markdown/PDF/DOCX/TXT; detect new, changed, and deleted files via mtime + content hash.
- **Why:** The vault is a live system of notes; the app must mirror it continuously without manual import.
- **Approach:** `watchdog` (or a polling fallback) producing file events; an idempotent scanner that upserts `kb_documents` and enqueues changed files for re-chunking.
- **Dependencies:** Ideas 1–2.
- **Priority:** Critical | **Complexity:** M

### Idea 4 🟡 — Markdown parser with frontmatter & wikilinks
- **Objective:** Parse markdown into structured document data: YAML frontmatter, headings, `[[wikilinks]]`, `#tags`, callouts, code blocks, and daily-note dates.
- **Why:** Obsidian notes are rich, structured text; preserving structure (not just raw text) is what makes linking, tagging, and chunking high quality.
- **Approach:** `markdown-it-py` + `frontmatter`; a normalizer emitting a JSON outline per document stored in `frontmatter_json`; heading-aware chunking in Idea 7.
- **Dependencies:** Idea 1.
- **Priority:** High | **Complexity:** M

### Idea 5 🟡 — PDF & research-paper ingestion
- **Objective:** Ingest PDFs (lecture notes, textbooks, papers) via the existing `text_extractor`, with page-boundary metadata preserved.
- **Why:** A large fraction of a student's knowledge lives in PDFs; today they only become syllabus materials — they should also enter the Knowledge Core.
- **Approach:** Extend `text_extractor` output with page numbers; add an upload/import endpoint that routes files into `kb_documents`; optional arXiv metadata fetch (title, authors, abstract) via the ArXiv API for paper PDFs.
- **Dependencies:** Ideas 1, 4.
- **Priority:** High | **Complexity:** M

### Idea 6 🔴 — OCR for scanned documents
- **Objective:** Optical character recognition for scanned PDFs and image-based notes (Tesseract), flagged with `ocr_used`.
- **Why:** Scanned handouts are common and otherwise invisible to the knowledge base.
- **Approach:** Optional `pytesseract` pipeline; detection of image-only PDFs (low text yield from `pypdf`) triggers OCR; results cached in `kb_documents`.
- **Dependencies:** Idea 5.
- **Priority:** Medium | **Complexity:** M

### Idea 7 🔴 — Semantic chunking
- **Objective:** Split documents into retrieval-sized chunks aligned with headings/sections and paragraphs, with configurable size/overlap.
- **Why:** Retrieval quality depends on chunk quality: too-big chunks dilute answers, too-small chunks lose context.
- **Approach:** Heading-aware splitter (`KB_CHUNK_SIZE`/`KB_CHUNK_OVERLAP`), paragraph/table boundary preference; emits `kb_chunks` rows with `char_start/end` for source highlighting.
- **Dependencies:** Ideas 1, 4.
- **Priority:** Critical | **Complexity:** M

### Idea 8 🔴 — Content-hash deduplication
- **Objective:** Detect duplicate documents (same content, different filenames) via SHA-256 content hash at ingest; near-duplicate detection at chunk level later.
- **Why:** Vaults accumulate copies; duplicates pollute retrieval and waste embedding budget.
- **Approach:** `content_hash` unique-per-user index; on ingest, report "duplicate of existing doc" and offer skip/link; `kb_edges` RELATION `DUPLICATE_OF` recorded.
- **Dependencies:** Ideas 1, 3.
- **Priority:** High | **Complexity:** S

### Idea 9 🟡 — Version history & diff
- **Objective:** Snapshot every document change into `kb_versions`; expose restore and diff in the UI.
- **Why:** Notes change; users need undo and audit of what their Second Brain looked like before.
- **Approach:** On re-ingest, store the previous `content_hash` + snapshot path in `kb_versions`; endpoint `GET /api/kb/documents/{id}/versions` and `POST .../restore`.
- **Dependencies:** Idea 3.
- **Priority:** Medium | **Complexity:** M

### Idea 10 🔴 — Ingestion job queue & status
- **Objective:** Run indexing/embedding as background jobs with per-job status, progress, and idempotent resume.
- **Why:** Vaults can be thousands of files; blocking requests would break the API.
- **Approach:** In-process threadpool executor with a `kb_jobs` table (or reuse a lightweight queue); `GET /api/kb/jobs/{id}` for the UI; batch embedding (Idea 12) inside the job.
- **Dependencies:** Ideas 1–3.
- **Priority:** High | **Complexity:** M

### Phase 2 — Embeddings, Indexing & Knowledge Graph (Ideas 11–20)

### Idea 11 🔴 — Embeddings service
- **Objective:** OpenAI-compatible embeddings client (`POST {AI_BASE_URL}/embeddings`) with batch support, caching, and a deterministic local fallback.
- **Why:** Semantic retrieval and RAG require dense vectors; the provider abstraction must mirror `ai_client` so AI-disabled test/dev stays hermetic.
- **Approach:** `app/services/embeddings.py` mirroring `ai_client` structure; cache by content hash in `kb_embeddings`; config `EMBEDDINGS_MODEL`/`EMBEDDINGS_DIM`.
- **Dependencies:** Idea 1; existing `ai_client` pattern.
- **Priority:** Critical | **Complexity:** M

### Idea 12 🟡 — Persistent vector store
- **Objective:** Move from the in-memory numpy/FAISS `VectorStore` to a persistent store (pgvector in prod, sqlite-vec/numpy+file in dev) behind the same interface.
- **Why:** In-memory vectors vanish on restart and can't scale to a full vault; persistence also enables transactional consistency with SQL rows.
- **Approach:** Keep `VECTOR_STORE_BACKEND` switch; add a `pgvector` backend and a file-backed numpy backend; `kb_embeddings` becomes the source of truth.
- **Dependencies:** Idea 11.
- **Priority:** Critical | **Complexity:** L

### Idea 13 🟡 — Metadata extraction & enrichment
- **Objective:** Extract title, author, date, source URL, language, and reading time from frontmatter/content; store in `kb_documents`.
- **Why:** Structured metadata powers filtering, citations, and the citation-aware answer features.
- **Approach:** Rules for YAML frontmatter first; LLM enrichment for missing fields via `generate_json` with a strict schema; manual override in UI.
- **Dependencies:** Ideas 4, 11.
- **Priority:** High | **Complexity:** M

### Idea 14 🔴 — Auto-tagging
- **Objective:** Assign topical tags to documents (and suggest tags for new notes) with provenance (`manual` | `ai` | `rule`).
- **Why:** Users manage vaults by tags; auto-tagging keeps the Second Brain organized as it grows.
- **Approach:** Extract existing `#tags` first; LLM proposes 3–7 tags from chunk text; frequency-based rules as fallback; UI confirm/reject.
- **Dependencies:** Ideas 4, 11.
- **Priority:** High | **Complexity:** M

### Idea 15 🔴 — Concept extraction & canonicalization
- **Objective:** Extract concepts (terms/entities) from documents into `kb_concepts` with canonical names and definitions.
- **Why:** Concepts are the atoms of the knowledge graph and the bridge between notes and subjects.
- **Approach:** LLM extraction from chunk summaries (batched, capped by daily budget) plus deterministic fallback (TF-IDF noun phrases); synonym resolution into `canonical_name`.
- **Dependencies:** Ideas 11, 14.
- **Priority:** High | **Complexity:** L

### Idea 16 🟡 — Knowledge graph nodes & edges
- **Objective:** Build the typed graph: `DOC→CONCEPT MENTIONS`, `DOC→DOC LINKS/BACKLINK/CITES`, `CONCEPT→CONCEPT RELATED/SYNONYM_OF/DEPENDS_ON`.
- **Why:** A graph captures relationships no flat index can (prerequisites, chains of ideas, citation networks) and powers recommendations.
- **Approach:** Wikilink/backlink extraction from markdown (rules); concept co-occurrence edges (statistical); LLM dependency edges (curated). Graph stored in `kb_edges` + query helpers.
- **Dependencies:** Ideas 4, 15.
- **Priority:** High | **Complexity:** L

### Idea 17 🟡 — Note relationship & backlink inference
- **Objective:** Auto-discover implicit links between notes (shared concepts, similar embeddings) and surface them as backlinks/cross-references.
- **Why:** Most knowledge links are implicit; exposing them helps users find connections they didn't know existed.
- **Approach:** Chunk-embedding similarity above threshold → `RELATED` edge; shared concepts → `SHARES_CONCEPT` edge; UI "Linked notes" panel per document.
- **Dependencies:** Ideas 12, 15, 16.
- **Priority:** Medium | **Complexity:** M

### Idea 18 🟡 — Graph visualization & explorer
- **Objective:** Interactive force-directed view of the knowledge graph with filters (by source, tag, subject) and click-through to notes.
- **Why:** A visible graph turns an abstract index into an explorable map of the user's knowledge.
- **Approach:** Frontend graph component (e.g. `react-force-graph`) fed by `GET /api/kb/graph` (nodes+edges, paginated/level-limited); cluster by community detection (simple greedy) as stretch.
- **Dependencies:** Idea 16.
- **Priority:** Medium | **Complexity:** M

### Idea 19 🔴 — Duplicate & near-duplicate detection (chunk level)
- **Objective:** Flag near-duplicate chunks across documents (same passage paraphrased) and let users merge or archive.
- **Why:** Near-duplicates dilute retrieval results and inflate storage.
- **Approach:** Embedding similarity on chunk pairs within a cluster, or MinHash/LSH for scale; `DUPLICATE_OF` edges + admin workflow.
- **Dependencies:** Ideas 8, 12.
- **Priority:** Medium | **Complexity:** L

### Idea 20 🔴 — Backfill & re-index tooling
- **Objective:** CLI/admin endpoint to rebuild embeddings and graph for the whole vault or a source, idempotently and incrementally.
- **Why:** Models and chunkers improve; users must be able to re-index without data loss.
- **Approach:** `python -m app.cli.kb reindex --source=...` plus admin UI trigger; per-document dirty flags; checksums prevent wasted work.
- **Dependencies:** Ideas 10, 12.
- **Priority:** Medium | **Complexity:** M

### Phase 3 — Search & Retrieval (Ideas 21–30)

### Idea 21 🟡 — Full-text search (FTS5)
- **Objective:** Keyword full-text search across `kb_documents`/`kb_chunks` with highlight snippets.
- **Why:** Users still search by exact words; FTS is the fastest, cheapest retrieval layer and the backbone of hybrid search.
- **Approach:** SQLite FTS5 virtual tables (dev) / Postgres `tsvector` (prod); per-user filter; snippet + term highlighting; tie into the existing `MaterialSearch` UI patterns.
- **Dependencies:** Idea 1.
- **Priority:** High | **Complexity:** M

### Idea 22 🔴 — Semantic search API
- **Objective:** `POST /api/kb/search` supporting both keyword and natural-language queries returning ranked chunks with scores and source paths.
- **Why:** Natural-language search lets users find ideas they can't name in keywords.
- **Approach:** Embed query via `embeddings.py`; cosine retrieval from the vector store; merge with FTS results; return chunk + document + snippet + score.
- **Dependencies:** Ideas 11–12, 21.
- **Priority:** Critical | **Complexity:** M

### Idea 23 🔴 — Hybrid retrieval with RRF fusion
- **Objective:** Combine FTS and vector rankings via Reciprocal Rank Fusion with configurable weights.
- **Why:** Either modality alone misses results the other catches; hybrid is the industry-standard baseline for RAG quality.
- **Approach:** Run both retrievers, fuse by `1/(k+rank)`, optionally rerank top-N with a cross-encoder or a cheap LLM relevance judge.
- **Dependencies:** Ideas 21–22.
- **Priority:** High | **Complexity:** M

### Idea 24 🔴 — Query expansion & spelling tolerance
- **Objective:** Improve queries with synonyms (from `kb_concepts`), abbreviation expansion, and typo tolerance.
- **Why:** Users search "ML" or mistype terms; expansion connects their words to the canonical vocabulary of their own notes.
- **Approach:** Concept alias lookup; FTS prefix/typoglycemia handling; optional LLM query rewriting when retrieval is empty.
- **Dependencies:** Ideas 15, 21.
- **Priority:** Medium | **Complexity:** M

### Idea 25 🔴 — Citation-aware result cards
- **Objective:** Every search result shows source file path, heading context, page number, and a link to open the note/PDF at that location.
- **Why:** Grounding answers in visible, clickable sources builds trust and makes the KB verifiable.
- **Approach:** Store `char_start/end` + heading in chunks; frontend renders result cards with open-in-vault / open-in-reader actions (reuse `PDFReader`).
- **Dependencies:** Ideas 7, 22.
- **Priority:** High | **Complexity:** M

### Idea 26 🟡 — Retrieval evaluation harness
- **Objective:** A golden set of (query → relevant chunk ids) per subject area; offline metrics: recall@k, MRR, faithfulness.
- **Why:** Retrieval changes (chunking, embedding models, fusion weights) need regression measurement or quality silently drifts.
- **Approach:** Fixture queries with expected results; script runs retrieval offline and reports metrics in CI; score tracked in a dashboard.
- **Dependencies:** Ideas 22–23.
- **Priority:** Medium | **Complexity:** M

### Idea 27 🔴 — Knowledge health analysis
- **Objective:** Health dashboard: orphan notes, dead links, stale notes, unindexed files, coverage gaps by subject.
- **Why:** A second brain decays quietly; health signals tell users what to prune, merge, or complete.
- **Approach:** Graph queries for orphans/dead links; recency heuristics for staleness; aggregated `GET /api/kb/health` consumed by an Insights page.
- **Dependencies:** Ideas 16, 22.
- **Priority:** Medium | **Complexity:** M

### Idea 28 🔴 — Missing knowledge detection
- **Objective:** Compare subject topics against vault coverage; produce "you have no notes on X" alerts and suggest what to capture.
- **Why:** This is the *"if it's not in the Second Brain, you don't know it"* principle made actionable — gap detection drives capture.
- **Approach:** Topic→coverage mapping (Idea 38); topics with zero/weak coverage flagged; daily digest + capture prompts (link to quick-capture).
- **Dependencies:** Idea 38 (Phase 5), Idea 27.
- **Priority:** High | **Complexity:** M

### Idea 29 🔴 — Search feedback & learning
- **Objective:** Users can thumbs-up/down results; implicit clicks are logged; feedback tunes fusion weights per user over time.
- **Why:** Personalization of search means the retriever learns which results this user actually wants.
- **Approach:** `kb_search_events` log; batch analysis adjusts per-user weights or boosts recently-used documents; surfaced as "preferred sources".
- **Dependencies:** Ideas 23, 26.
- **Priority:** Low | **Complexity:** L

### Idea 30 🟡 — Global unified search box
- **Objective:** One search UI across vault, materials, subjects, tasks, and assignments, with type facets.
- **Why:** Users shouldn't guess which silo their knowledge lives in; one box makes the KB the front door.
- **Approach:** Aggregating endpoint fanning out to per-domain search; frontend command-palette style search (Ctrl+K) with keyboard navigation.
- **Dependencies:** Ideas 22, 21; existing tasks/materials search.
- **Priority:** High | **Complexity:** M

### Phase 4 — Note Intelligence & Content Generation (Ideas 31–40)

### Idea 31 🟡 — AI summaries of notes & papers
- **Objective:** Generate structured summaries (TL;DR, key points, definitions, open questions) for any document, cached and versioned.
- **Why:** Summaries turn raw vault content into quickly re-consumable knowledge and feed the subject layer.
- **Approach:** Extend the existing `summaries` service pattern to `kb_documents`; budget-capped (`KB_DAILY_GEN_LIMIT`); store in `kb_summaries`; regenerate on content change.
- **Dependencies:** Ideas 7, 11; existing `summaries.py`.
- **Priority:** High | **Complexity:** M

### Idea 32 🟡 — AI explanations (ELI5, analogies, derivations)
- **Objective:** Explain any vault concept at chosen depth (overview → deep dive) grounded in the user's own notes, with citations.
- **Why:** The best explanations build on what the user already knows — which only their vault contains.
- **Approach:** RAG over chunks covering the concept + `user_memory` strengths; prompt registry variants; citations mandatory.
- **Dependencies:** Ideas 15, 23, 79.
- **Priority:** High | **Complexity:** M

### Idea 33 🟡 — AI quizzes generated from notes
- **Objective:** Generate quiz questions from selected chunks/notes, reusing the existing quiz schema and `Quiz` UI.
- **Why:** Testing yourself against your own notes is the fastest feedback loop; the quiz machinery already exists.
- **Approach:** New endpoint maps `kb_document_id`/chunk set → existing quiz generation service; store `kb_quiz_links` for traceability.
- **Dependencies:** Ideas 7, 31; existing quizzes router.
- **Priority:** High | **Complexity:** M

### Idea 34 🟡 — Flashcards generated from notes
- **Objective:** Auto-create Q/A flashcards from concepts and key statements in notes, into the existing flashcard-deck model.
- **Why:** Spaced repetition over one's own notes is a proven retention technique; avoids manual card creation.
- **Approach:** Extract candidate statement/answer pairs via `generate_json`; user review queue before committing to decks; dedupe against existing cards.
- **Dependencies:** Ideas 15, 31; existing flashcards router.
- **Priority:** High | **Complexity:** M

### Idea 35 🟡 — Daily notes integration
- **Objective:** Link Obsidian daily notes to the app's daily schedule/journal; auto-tag by day; surface "what did I capture today".
- **Why:** Daily notes are where fleeting knowledge lands; connecting them to the study day closes the capture loop.
- **Approach:** Detect `YYYY-MM-DD.md` pattern; join with `daily_schedule_items` and journal entries by date; today-widget shows vault captures alongside schedule.
- **Dependencies:** Ideas 4, 3; existing daily-schedule + journal.
- **Priority:** Medium | **Complexity:** S

### Idea 36 🔴 — Citation management (BibTeX & paper citations)
- **Objective:** Extract citations from papers and notes into a citation registry; answers cite sources properly.
- **Why:** Research workflows need citations; citation-aware answers (Idea 96) are impossible without a citation registry.
- **Approach:** Parse reference lists from paper PDFs (regex/heuristic) and `@cite` syntax in markdown; store `kb_citations`; expose export as BibTeX.
- **Dependencies:** Ideas 5, 16.
- **Priority:** Medium | **Complexity:** M

### Idea 37 🔴 — Concept linking UI
- **Objective:** In the note reader/editor, show linked concepts, related notes, and one-click "link this note to concept X".
- **Why:** Explicit user curation of graph edges dramatically improves graph quality over pure inference.
- **Approach:** Reader sidebar panel fed by graph queries; quick-add edge endpoints; edges gain `provenance=manual`.
- **Dependencies:** Ideas 16–17.
- **Priority:** Medium | **Complexity:** M

### Idea 38 🔴 — Mind-map generation
- **Objective:** Render any document or topic as a hierarchical mind map (headings + concepts) exportable to Markdown/OPML.
- **Why:** Visual structure helps comprehension and revision; it converts unstructured notes into a glanceable map.
- **Approach:** Heading outline → tree; concept mentions attach to nodes; frontend tree visualization; export endpoint.
- **Dependencies:** Ideas 4, 15.
- **Priority:** Low | **Complexity:** M

### Idea 39 🔴 — Note quality scoring
- **Objective:** Per-note scores for completeness, clarity, recency, and link density; actionable suggestions ("split this note", "add definition of X").
- **Why:** Quality signals help users prune and improve their Second Brain systematically.
- **Approach:** Heuristic composite score (length, headings, links, recency, coverage) + optional LLM suggestions batch job.
- **Dependencies:** Ideas 4, 16, 27.
- **Priority:** Low | **Complexity:** M

### Idea 40 🟡 — Brain dump → structured notes migration
- **Objective:** Upgrade the existing single-row `BrainDump` widget: captured text becomes draft `kb_documents` that the user can split, tag, and file.
- **Why:** The current brain dump is a dead-end textarea; this makes every captured thought enter the knowledge pipeline.
- **Approach:** On save, create draft document (status `draft`) with quick-file UI (title, source folder, tags); AI-assisted splitting of long dumps into sections.
- **Dependencies:** Ideas 1, 3, 4; existing `braindumps` router/widget.
- **Priority:** High | **Complexity:** M

### Phase 5 — Subject Management Core (Ideas 41–50)

### Idea 41 🟡 — Automatic subject creation
- **Objective:** Detect a new subject from an uploaded syllabus or enrollment change and auto-create `curriculum_subject` (+ units) with an AI draft profile.
- **Why:** Manual subject setup is friction; the AI should own the plumbing while the user reviews.
- **Approach:** Syllabus upload → parse → propose subject metadata → user confirms in a review screen (extend `SyllabusImport` page) → write to curriculum tables.
- **Dependencies:** Idea 42; existing curriculum models/routers.
- **Priority:** High | **Complexity:** M

### Idea 42 🟡 — Syllabus parsing
- **Objective:** Parse syllabus text (PDF/DOCX/MD) into structured fields: title, semester, credits, units, topics, outcomes, grading scheme, deadlines.
- **Why:** Syllabi are the authoritative outline of a subject; structured parsing unlocks everything downstream.
- **Approach:** `text_extractor` → chunked syllabus → `generate_json` with strict schema; fallback heuristic splitter when AI disabled; store raw + parsed in `subject_profiles`.
- **Dependencies:** Ideas 1, 5; existing `ai_client`.
- **Priority:** Critical | **Complexity:** M

### Idea 43 🔴 — Semester & calendar detection
- **Objective:** Detect the academic term/semester from syllabus text and app dates; tag subjects and units with the term.
- **Why:** Semester-aware planning lets the roadmap engine respect the real academic calendar.
- **Approach:** Date-range + keyword heuristics, cross-checked with assignment/exam due dates; `semester` column on `subject_profiles`.
- **Dependencies:** Idea 42.
- **Priority:** Medium | **Complexity:** S

### Idea 44 🟡 — Topic extraction & normalization
- **Objective:** Split each unit into granular topics with normalized titles and Bloom-level tags; maintain a per-subject topic thesaurus.
- **Why:** Topics are the unit of study planning, revision, and coverage mapping — granularity matters.
- **Approach:** LLM extraction with synonym folding (use `kb_concepts` canonicalization); human review grid in UI; store in `topics`.
- **Dependencies:** Ideas 15, 42.
- **Priority:** Critical | **Complexity:** M

### Idea 45 🟡 — Unit & lecture segmentation
- **Objective:** Auto-assign syllabus topics to lectures/units matching the app's curriculum units and materials.
- **Why:** Ties the parsed syllabus to existing `curriculum_units` + uploaded materials so coverage is measurable.
- **Approach:** Embedding/name matching between parsed units and existing units/materials; suggestions presented for confirmation.
- **Dependencies:** Ideas 42, 44.
- **Priority:** High | **Complexity:** M

### Idea 46 🔴 — Topic dependency graph
- **Objective:** Infer prerequisites (A before B) among topics from syllabus phrasing, concept prerequisites, and performance data.
- **Why:** A correct dependency order is what makes roadmaps and "what to study next" trustworthy.
- **Approach:** Seed from LLM analysis of syllabus; refine with `DEPENDS_ON` edges from `kb_edges`; adjust weights from quiz mastery (studying B before A hurts scores).
- **Dependencies:** Ideas 16, 44.
- **Priority:** High | **Complexity:** M

### Idea 47 🟡 — Learning roadmap generation
- **Objective:** Produce an ordered, time-boxed roadmap per subject: topics in dependency order, split into weekly sessions, respecting deadlines.
- **Why:** Turns a subject outline into an executable plan the student can follow day by day.
- **Approach:** Topological sort over topic graph → weekly bucketing by time estimates → conflicts checked against exam/assignment dates; output versioned in `roadmaps`.
- **Dependencies:** Ideas 44, 46, 49, 50.
- **Priority:** High | **Complexity:** M

### Idea 48 🔴 — Difficulty estimation
- **Objective:** Per-topic difficulty (Easy/Medium/Hard) from syllabus wording, note density, and the user's own quiz history.
- **Why:** Difficulty drives pacing: hard topics get more sessions and earlier starts.
- **Approach:** LLM rubric + overlap with known-difficult concepts; update with observed mastery slope from quiz attempts.
- **Dependencies:** Ideas 44, 61.
- **Priority:** Medium | **Complexity:** M

### Idea 49 🟡 — Time estimation
- **Objective:** Estimate minutes needed per topic (first pass, review, mastery) from content volume, difficulty, and past pacing.
- **Why:** Realistic time budgets make daily plans achievable rather than aspirational.
- **Approach:** Volume (chunk count) × difficulty factor × user pacing multiplier (learned from `learning_events`); UI slider to calibrate.
- **Dependencies:** Ideas 44, 48, 51.
- **Priority:** Medium | **Complexity:** M

### Idea 50 🔴 — Learning-outcome extraction
- **Objective:** Extract measurable learning outcomes per topic ("can derive X", "can solve Y") and track them as checkable goals.
- **Why:** Outcomes turn abstract mastery into verifiable checkboxes, making "am I done?" answerable.
- **Approach:** Syllabus outcome lines + LLM expansion; stored on `topics`; UI checkboxes linked to mastery events and to the existing Goals model.
- **Dependencies:** Ideas 42, 44.
- **Priority:** Medium | **Complexity:** S

### Phase 6 — Study Planning & Execution (Ideas 51–60)

### Idea 51 🟡 — Personalized study plans (AI-driven)
- **Objective:** Upgrade the existing `study-plans` router: plans generated from the roadmap, vault coverage, and user availability, not just syllabus text.
- **Why:** Plans grounded in the user's own notes and pace are far more likely to be followed.
- **Approach:** Extend `StudyPlanWeek` to reference topics/chunks; generation consumes roadmap + gaps; regenerate on demand or schedule change.
- **Dependencies:** Ideas 47, 49; existing study-plans router.
- **Priority:** High | **Complexity:** M

### Idea 52 🟡 — Revision scheduling (spaced repetition)
- **Objective:** Per-topic review scheduler (SM-2 style) with due dates pushed into `daily_schedule`/tasks/reminders.
- **Why:** Reviews at the right intervals are what make knowledge durable; the app already has the scheduling surfaces.
- **Approach:** `revision_schedule` table; quiz/recall outcomes update interval + ease; daily job materializes due reviews into the user's day.
- **Dependencies:** Ideas 44, 61, 68; existing daily-schedule + reminders.
- **Priority:** High | **Complexity:** M

### Idea 53 🔴 — Exam preparation mode
- **Objective:** A countdown-driven exam mode: auto-builds a revision plan from exam date, topic weights (from syllabus grading scheme), and gaps.
- **Why:** Exams concentrate stakes; a dedicated mode converts panic into a step-by-step plan.
- **Approach:** `POST /api/subjects-ai/{id}/exam-prep?exam_id=...` generates a reverse-scheduled plan; dashboard widget shows daily tasks until exam.
- **Dependencies:** Ideas 42, 47, 52; existing exams/assignments.
- **Priority:** High | **Complexity:** M

### Idea 54 🟡 — Assignment intelligence
- **Objective:** Auto-suggest assignment plans (break into subtasks, estimate hours, set reminders) and link assignments to covered topics.
- **Why:** Assignments are where subject knowledge is applied; planning them reduces last-minute pressure.
- **Approach:** For each assignment: LLM subtask breakdown + time estimate → tasks/reminders; link `topic_materials`/coverage for hints.
- **Dependencies:** Ideas 42, 49; existing assignments router.
- **Priority:** Medium | **Complexity:** M

### Idea 55 🔴 — Lab tracking
- **Objective:** Track lab sessions (experiments/drills) per subject: schedule, pre-requisite topics, submission, and reflection notes.
- **Why:** Labs are a distinct activity type that today has no home in the app.
- **Approach:** `labs` table + router; lab prep pulls relevant vault chunks as "read before lab"; completion links to learning events.
- **Dependencies:** Ideas 44, 51.
- **Priority:** Low | **Complexity:** S

### Idea 56 🔴 — Attendance monitoring
- **Objective:** Optional attendance logging per subject/class with streak and warning analytics.
- **Why:** Attendance is a leading indicator of performance; tracking it surfaces risk early.
- **Approach:** `attendance` table (date, subject, present); quick-tap UI; analytics view + alerts on falling patterns.
- **Dependencies:** Existing courses/assignments structure.
- **Priority:** Low | **Complexity:** S

### Idea 57 🟡 — Subject progress analytics
- **Objective:** Per-subject dashboard: topics mastered, hours logged, coverage %, quiz trend, roadmap completion, vs. semester timeline.
- **Why:** Visible progress motivates and flags subjects that are slipping before exams.
- **Approach:** Aggregate `learning_events`, quiz attempts, revision completions; frontend charts (extend existing Analytics/StudyHeatmap visuals); weekly summary notification.
- **Dependencies:** Ideas 44, 51, 61; existing analytics service.
- **Priority:** High | **Complexity:** M

### Idea 58 🟡 — Weak & strong topic detection
- **Objective:** Classify each topic as weak/strong from quiz accuracy, recall latency, and review outcomes; expose in dashboards.
- **Why:** Targeted practice beats uniform review; knowing precisely *where* the weakness is saves hours.
- **Approach:** Bayesian-ish mastery score per topic updated by each `learning_event`; thresholds + confidence; `GET /api/subjects-ai/weak-topics`.
- **Dependencies:** Ideas 44, 61, 66.
- **Priority:** High | **Complexity:** M

### Idea 59 🔴 — Recommended study order
- **Objective:** "What should I study right now?" — a ranked recommendation combining dependency readiness, weakness, due reviews, and exam proximity.
- **Why:** Decision fatigue is real; one clear next-action beats a list of options.
- **Approach:** Scoring function over the topic graph (ready = prerequisites mastered) + urgency; surfaced on dashboard and daily schedule.
- **Dependencies:** Ideas 46, 52, 58.
- **Priority:** High | **Complexity:** M

### Idea 60 🟡 — Micro-session & focus integration
- **Objective:** Generate 15–45 min micro-sessions (topic + specific chunk + practice task) and push them into the Pomodoro/daily schedule flows.
- **Why:** Small concrete sessions convert plans into completed work; the app already has Pomodoro and daily schedules.
- **Approach:** Session factory from roadmap + recommendations; one-tap "start pomodoro" launches with session context; completion logs a learning event.
- **Dependencies:** Ideas 51, 59; existing pomodoro + dailyschedule.
- **Priority:** Medium | **Complexity:** M

### Phase 7 — AI Tutor & Assessment (Ideas 61–70)

### Idea 61 🟡 — RAG-grounded AI tutor
- **Objective:** A chat tutor (extending the existing `AIChat`) that answers from the user's vault + subject materials, always citing sources.
- **Why:** A tutor grounded in the user's own knowledge answers in their context — and refuses to invent knowledge the vault lacks.
- **Approach:** Query → retrieval (Idea 23) → context assembly with user memory → `ai_client` chat; answer includes `[source: path]` markers; empty-retrieval → "not found in your Second Brain" with capture prompt.
- **Dependencies:** Ideas 23, 25, 79; existing `AIChat.tsx`.
- **Priority:** Critical | **Complexity:** L

### Idea 62 🔴 — AI doubt solving
- **Objective:** A focused doubt-ask flow: student pastes a question/step where stuck; the tutor identifies the blocking concept and re-explains from their notes.
- **Why:** Doubts usually sit at specific prerequisite gaps; fixing the gap fixes the doubt.
- **Approach:** Analyze doubt → find candidate blocking concepts via graph + retrieval → explain gap + re-walk the problem; logs to `learning_events`.
- **Dependencies:** Ideas 46, 61.
- **Priority:** High | **Complexity:** M

### Idea 63 🟡 — AI-generated practice questions
- **Objective:** On-demand practice sets per topic with difficulty tiers and worked solutions, stored for reuse.
- **Why:** Practice is the highest-yield study activity; auto-generation removes the biggest friction.
- **Approach:** Topic context → `generate_json` question bank (schema: q, options, answer, explanation, bloom level); UI review + save; dedupe by question hash.
- **Dependencies:** Ideas 33, 44.
- **Priority:** High | **Complexity:** M

### Idea 64 🔴 — Mock tests & exam simulations
- **Objective:** Timed full-subject mock tests assembled from practice banks with a weighted paper structure from the syllabus grading scheme.
- **Why:** Simulations train pacing and reveal whole-subject gaps that per-topic practice misses.
- **Approach:** Paper generator (structure from grading scheme, questions by topic weight); timer + results analytics; history view.
- **Dependencies:** Ideas 42, 63.
- **Priority:** Medium | **Complexity:** M

### Idea 65 🔴 — Interview preparation
- **Objective:** Subject-aware interview mode: generates interview questions (conceptual + problem) and scores answers against the vault.
- **Why:** For job/placement goals, the app should double as a mock interviewer.
- **Approach:** Skill map (Idea 70) → question generation; answer grading via existing `grade-answer` service; feedback with cited corrections.
- **Dependencies:** Ideas 61, 70; existing `ai/grade-answer`.
- **Priority:** Low | **Complexity:** M

### Idea 66 🟡 — Answer grading & feedback (advanced)
- **Objective:** Grade free-text answers with partial credit, misconception detection, and next-steps, beyond today's correct/incorrect.
- **Why:** Formative feedback is where learning actually happens; binary grading misses it.
- **Approach:** Rubric prompt (bloom level, key points from chunks) → score + strengths + misconceptions + action items; persists to `learning_events`.
- **Dependencies:** Ideas 61, 63; existing grade-answer service.
- **Priority:** High | **Complexity:** M

### Idea 67 🔴 — Adaptive question difficulty
- **Objective:** Choose next question difficulty from the student's running mastery per topic (item-response style).
- **Why:** Adaptive practice keeps challenge in the sweet spot — neither boring nor demoralizing.
- **Approach:** Mastery estimate gates difficulty selection; track correctness per difficulty; simple IRT-lite update rule.
- **Dependencies:** Ideas 58, 63.
- **Priority:** Medium | **Complexity:** M

### Idea 68 🔴 — Explain-my-mistake analysis
- **Objective:** After a wrong answer, generate a walkthrough: where the reasoning diverged, which note to re-read, which concept to review.
- **Why:** Mistake analysis converts every error into a targeted study action.
- **Approach:** Compare student answer vs model solution; pinpoint divergence; recommend retrieval from vault; logs review task to revision schedule.
- **Dependencies:** Ideas 52, 61, 66.
- **Priority:** High | **Complexity:** M

### Idea 69 🟡 — Knowledge capture & revision XP (replaces original)
- **Objective:** Reward *knowledge capture* (new notes, filing brain dumps, daily-note creation) and *revision completion* through the existing XP/habit/quest mechanics.
- **Why:** Quiz-attempt XP already exists (`xp_awarded`); the missing motivation is the capture-and-review loop itself — rewarding it keeps users returning daily.
- **Approach:** Emit XP on revision completions, daily-note creation, and brain-dump filing; surface in habit tracker/quest centre; reuse the existing `habit_xp`, quest, and character services — no new gamification system.
- **Dependencies:** Existing `habit_xp`, quest, character services; Ideas 35, 40, 90.
- **Priority:** Medium | **Complexity:** S

### Idea 70 🔴 — Skill mapping
- **Objective:** Map subjects/topics to a skill taxonomy (e.g., CS/ML/DSA skills); derive a user skill profile with levels per skill.
- **Why:** Skill profiles enable interview prep, portfolio clarity, and cross-subject recommendations.
- **Approach:** Taxonomy seed + LLM mapping from topics/outcomes; levels from mastery; profile view + export.
- **Dependencies:** Ideas 44, 58.
- **Priority:** Low | **Complexity:** M

### Phase 8 — Personalization & Learning Memory (Ideas 71–80)

### Idea 71 🔴 — Learning preference profile
- **Objective:** Explicit + inferred preferences (depth, examples vs. theory, visual vs. textual, session length, explanation style).
- **Why:** Personalization without a profile is guesswork; even a small explicit survey sharply improves relevance.
- **Approach:** `user_preferences` table + onboarding survey; prompts inject preferences; inferred adjustments from behavior (session length, explanation depth toggles).
- **Dependencies:** Idea 1.
- **Priority:** High | **Complexity:** S

### Idea 72 🔴 — Knowledge-gap detection (concept level)
- **Objective:** Concept-level gaps from combining quiz errors, retrieval misses, and missing vault coverage (beyond topic-level Idea 28).
- **Why:** Topic-level gaps hide concept-level holes; concept granularity drives precise recommendations.
- **Approach:** Map quiz errors to `kb_concepts`; gap = low mastery + low exposure; report with suggested source chunks to capture.
- **Dependencies:** Ideas 15, 28, 58.
- **Priority:** High | **Complexity:** M

### Idea 73 🔴 — Personalized explanations
- **Objective:** Explanations adapt to the user: start from concepts they already know (from `user_memory`), use their preferred style, at the right depth.
- **Why:** Explanations that build on known anchors are dramatically easier to understand.
- **Approach:** Retrieval includes known-adjacent concepts; prompt template renders "link to what you know" + style; track follow-up acceptance implicitly.
- **Dependencies:** Ideas 32, 71, 79.
- **Priority:** High | **Complexity:** M

### Idea 74 🔴 — Remember previously learned concepts
- **Objective:** The tutor references what the user has already studied/mastered when answering ("as you saw in your notes on X…").
- **Why:** Continuity makes the assistant feel like it knows the student, which is the whole point of a learning memory.
- **Approach:** `user_memory` (concept, strength, last_seen) updated on every interaction; injected into tutor system prompt as "known context".
- **Dependencies:** Ideas 61, 79.
- **Priority:** High | **Complexity:** M

### Idea 75 🔴 — Recommend what to study next
- **Objective:** "Next up" recommendations across subjects: readiness (deps mastered), due reviews, weakness, and upcoming exams.
- **Why:** The app should tell the student the single best next action every day.
- **Approach:** Composite scoring over graph + schedule (similar to Idea 59 but cross-subject); rendered on dashboard + daily schedule; explainable reasons shown.
- **Dependencies:** Ideas 46, 52, 58, 59.
- **Priority:** High | **Complexity:** M

### Idea 76 🔴 — Connect new concepts to existing notes
- **Objective:** When a new document is ingested, suggest links to existing notes/concepts it extends or contradicts.
- **Why:** New knowledge lands better when wired into what's already known; it also enriches the graph automatically.
- **Approach:** After ingestion, retrieve top similar docs + shared concepts; present "connect?" suggestions; user accepts → edges with provenance.
- **Dependencies:** Ideas 16, 17.
- **Priority:** Medium | **Complexity:** M

### Idea 77 🔴 — Suggest missing notes
- **Objective:** Propose notes the user should create ("you study X but have no note on it; your recent quiz exposed a gap").
- **Why:** Turns detected gaps into actionable capture, closing the know/capture loop.
- **Approach:** Gap list (Idea 72) + topic coverage (Idea 28) → ranked suggestions with outline template + linked materials; one-tap create draft note.
- **Dependencies:** Ideas 28, 40, 72.
- **Priority:** Medium | **Complexity:** M

### Idea 78 🔴 — Detect outdated notes
- **Objective:** Flag notes that contradict newer notes, are stale, or whose referenced materials changed.
- **Why:** Outdated knowledge actively misleads study plans and answers; detection keeps the vault honest.
- **Approach:** Contradiction scan (LLM, budget-capped) on pairs flagged by similarity + recency; stale = no updates/hits in N days; UI review queue.
- **Dependencies:** Ideas 9, 27, 39.
- **Priority:** Medium | **Complexity:** M

### Idea 79 🔴 — Long-term learning memory store
- **Objective:** A durable `user_memory` layer: concepts known, strengths, exposure counts, preferences, and interaction history, per user.
- **Why:** This is the substrate for personalization, adaptation, and trajectory forecasting (Idea 99).
- **Approach:** Normalized memory tables updated by event handlers (quiz, tutor, revision, notes); read side injected into prompts and recommendations.
- **Dependencies:** Ideas 1, 58, 74.
- **Priority:** High | **Complexity:** M

### Idea 80 🔴 — Adaptive learning paths
- **Objective:** Roadmaps and daily plans adapt continuously: as mastery rises, paths shorten/skip mastered topics; as gaps appear, they insert reviews.
- **Why:** A static plan decays; an adaptive plan stays aligned with reality.
- **Approach:** Versioned `roadmaps` + recompute triggers on mastery/due-date events; UI shows "plan updated: +2 reviews, -1 topic" diffs.
- **Dependencies:** Ideas 47, 58, 79.
- **Priority:** Medium | **Complexity:** L

### Phase 9 — Automation (Ideas 81–90)

### Idea 81 🔴 — Auto-categorize new notes
- **Objective:** On ingest, assign each document a folder/category (by source, subject, tag) with user review.
- **Why:** Vaults grow chaotic; automatic filing keeps them navigable with minimal user effort.
- **Approach:** Rules (folder patterns, existing taxonomy) + LLM category proposal; batch UI approve; moves logged to version history.
- **Dependencies:** Ideas 3, 4, 14.
- **Priority:** Medium | **Complexity:** M

### Idea 82 🔴 — Auto-tag documents (scheduled)
- **Objective:** Background job tags new/untagged documents nightly within the daily generation budget.
- **Why:** Tags power filtering and search facets; doing it automatically keeps tag coverage high.
- **Approach:** Nightly job over `status=untagged` docs; tag proposals stored as `kb_tags` with provenance; UI diff-review.
- **Dependencies:** Ideas 10, 14.
- **Priority:** Medium | **Complexity:** S

### Idea 83 🟡 — Auto-link related notes (scheduled)
- **Objective:** Periodic background pass suggests/creates `RELATED`/`BACKLINK` edges between similar notes.
- **Why:** Link quality improves with corpus size; scheduled passes keep the graph current without user effort.
- **Approach:** Cluster-by-embedding job; within cluster, propose edges above threshold; auto-create low-confidence-pending review.
- **Dependencies:** Ideas 10, 17.
- **Priority:** Medium | **Complexity:** M

### Idea 84 🔴 — Auto-detect duplicates (scheduled)
- **Objective:** Nightly duplicate scan flags exact and near-duplicate documents for merge.
- **Why:** Duplicates accumulate silently; periodic scanning keeps the KB clean without per-upload friction.
- **Approach:** Hash index scan (exact) + sampled embedding pairs (near); merge workflow moves content and re-points edges.
- **Dependencies:** Ideas 8, 19.
- **Priority:** Medium | **Complexity:** M

### Idea 85 🟡 — Auto-create flashcards from new notes
- **Objective:** New concept-bearing notes automatically get candidate flashcards queued for approval.
- **Why:** Keeps flashcard decks growing in lockstep with the vault, where learning actually happens.
- **Approach:** Hook after concept extraction (Idea 15); candidates → review queue → decks; dedupe by card hash.
- **Dependencies:** Ideas 15, 34.
- **Priority:** Medium | **Complexity:** M

### Idea 86 🟡 — Auto-create summaries (scheduled)
- **Objective:** Nightly summaries for changed/important documents within the daily generation budget.
- **Why:** Pre-built summaries mean instant answers later and cheaper on-demand generation.
- **Approach:** Job over docs with `dirty_summary` flag; respect `KB_DAILY_GEN_LIMIT`; cache invalidation on content change.
- **Dependencies:** Ideas 10, 31.
- **Priority:** Medium | **Complexity:** S

### Idea 87 🔴 — Auto-generate mind maps (scheduled)
- **Objective:** Background generation of mind-map outlines for documents with rich structure; stored and rendered on demand.
- **Why:** Visual previews make the vault browsable at a glance; pre-generation avoids render-time latency.
- **Approach:** Same pipeline as Idea 38, run as batch job; cache outline in document row.
- **Dependencies:** Ideas 10, 38.
- **Priority:** Low | **Complexity:** M

### Idea 88 🔴 — Auto-update study plans on new materials
- **Objective:** When a new material/vault chunk covers a topic, the roadmap and plans re-sync (coverage improves → estimated time shrinks).
- **Why:** Plans that ignore new resources are stale within days.
- **Approach:** Coverage-mapper rerun on material ingest; plan revision only when deltas exceed thresholds; notify via existing notifications system.
- **Dependencies:** Ideas 38, 47, 51.
- **Priority:** Medium | **Complexity:** M

### Idea 89 🔴 — Auto-sync external repositories
- **Objective:** Sync from Git repos, Google Drive, and web clippings; detect changed files via cursor/diff and import only deltas.
- **Why:** Knowledge lives in many places; the Second Brain should mirror them without manual export.
- **Approach:** Source adapters (git clone/pull, Drive API, clip service) behind the `kb_sources` registry; per-source sync cursors; conflict policy (newest wins, versioned).
- **Dependencies:** Ideas 2, 3, 10.
- **Priority:** Low | **Complexity:** L

### Idea 90 🔴 — Auto-create revision tasks
- **Objective:** Due reviews and gap-based reviews are automatically materialized as tasks/reminders on the user's calendar.
- **Why:** Plans only work when they land on the calendar; automatic materialization removes the last manual step.
- **Approach:** Daily job: due `revision_schedule` rows → tasks (with topic, link, estimated time); completed tasks feed back into scheduling.
- **Dependencies:** Ideas 52, 60; existing tasks/reminders.
- **Priority:** High | **Complexity:** M

### Phase 10 — Advanced AI, Analytics & Platform (Ideas 91–100)

### Idea 91 🔴 — Multi-agent architecture
- **Objective:** An orchestrator agent delegating to specialist sub-agents: retriever, summarizer, quizzer, tutor, scheduler, health-checker.
- **Why:** Complex requests ("prepare me for Thursday's exam using my weakest topics") need coordinated sub-tasks that one prompt handles poorly.
- **Approach:** Lightweight agent protocol: task objects with inputs/outputs; orchestrator plans → spawns sequential/parallel steps → composes; every agent uses the shared `ai_client` + budget guardrails.
- **Dependencies:** Ideas 23, 31, 33, 47, 58, 61.
- **Priority:** Medium | **Complexity:** L

### Idea 92 🔴 — Long-term memory system
- **Objective:** Persistent cross-session memory: facts about the user's studies, preferences, recurring confusions, and goals; memory summarization over time.
- **Why:** A tutor that forgets the user is a search engine; memory is what makes it a *personal* assistant.
- **Approach:** `user_memory` + episodic memory journal; periodic consolidation job (summarize old events into durable facts); memory injected into prompts.
- **Dependencies:** Ideas 79, 91.
- **Priority:** Medium | **Complexity:** L

### Idea 93 🟡 — Full RAG pipeline hardening
- **Objective:** Production-grade retrieval pipeline: query rewrite, multi-stage retrieval, rerank, citation verification, answer faithfulness checks.
- **Why:** Retrieval errors silently degrade every AI feature; hardening it is the highest-leverage investment.
- **Approach:** Pipeline stages as composable functions; faithfulness check post-generation (groundedness score); fallback to "not found" when ungrounded.
- **Dependencies:** Ideas 23, 26, 61.
- **Priority:** High | **Complexity:** L

### Idea 94 🔴 — Knowledge-graph + vector fusion
- **Objective:** Graph-aware retrieval: expand a vector hit via graph neighbors (prerequisites, related concepts) before answering.
- **Why:** Graph context adds relational knowledge pure vectors miss (e.g., prerequisite chains for explanation).
- **Approach:** Two-stage: vector top-k → graph expansion (1–2 hops) → dedupe/rerank; graph-aware prompts for tutor/explanations.
- **Dependencies:** Ideas 16, 23, 61.
- **Priority:** Medium | **Complexity:** L

### Idea 95 🟡 — Context-aware responses
- **Objective:** The assistant adapts responses to current context: active subject, upcoming exam, recent activity, and question history.
- **Why:** Same question means different things in exam week vs. mid-semester; context makes answers relevant.
- **Approach:** Context bundle (active subject, deadlines, recent topics) attached to requests; prompt injection + UI context chips; user can override context.
- **Dependencies:** Ideas 61, 79.
- **Priority:** Medium | **Complexity:** M

### Idea 96 🟡 — Research assistant
- **Objective:** Paper ingestion → summary, key-contribution extraction, related-paper suggestions from the user's own library, and citation-aware synthesis answers.
- **Why:** Research reading is time-heavy; an assistant that summarizes and connects papers to the user's existing notes pays off immediately.
- **Approach:** arXiv metadata (Idea 5) + summary pipeline (Idea 31) + citation registry (Idea 36); "explain this paper to me given my notes" flow.
- **Dependencies:** Ideas 5, 31, 36, 61.
- **Priority:** Medium | **Complexity:** M

### Idea 97 🔴 — Intelligent recommendation engine
- **Objective:** Cross-domain recommendations: what to study, which notes to revisit, which papers to read, which practice sets to take — ranked and explainable.
- **Why:** Recommendations tie all subsystems together into one coherent assistant behavior.
- **Approach:** Candidate generation from graph + memory + schedule; ranking by urgency × weakness × readiness; explanations ("because X is due and you missed it last week").
- **Dependencies:** Ideas 59, 75, 79, 94.
- **Priority:** Medium | **Complexity:** L

### Idea 98 🟡 — Goal planning & reflection system
- **Objective:** Term/quarter goals derived from subjects (e.g., "master DSA") with progress, weekly reflection prompts, and plan adjustments.
- **Why:** Goals without reflection drift; the app already has Goals — this adds AI-driven planning and periodic reflection.
- **Approach:** Goals ↔ roadmap alignment; weekly reflection (what worked/what didn't) generated from `learning_events`; insights pushed to user.
- **Dependencies:** Ideas 51, 57, 79; existing goals router.
- **Priority:** Medium | **Complexity:** M

### Idea 99 🟡 — Predictive analytics & learning-trajectory forecasting
- **Objective:** Forecast per-subject trajectory (mastery over time, exam-readiness score) from historical events; flag at-risk subjects early.
- **Why:** Early warning beats post-hoc analysis; "you're on track for a 72%" changes behavior before the exam.
- **Approach:** Time-series model over mastery/exposure events (simple regression/EWMA first); readiness score = weighted forecast vs. exam date; alerts via notifications.
- **Dependencies:** Ideas 57, 79, 98.
- **Priority:** Low | **Complexity:** L

### Idea 100 🟡 — Self-improving assistant + observability
- **Objective:** Closed-loop improvement: log every AI interaction, score quality (user feedback, faithfulness checks, retrieval metrics), and feed scores into prompt/retrieval tuning.
- **Why:** The system improves only if it measures itself; this is the meta-feature that compounds all others.
- **Approach:** `ai_logs` table (request, retrieval, response, latency, cost, feedback); weekly report; A/B-able prompt versions; automated regression suite from golden sets.
- **Dependencies:** Ideas 26, 93.
- **Priority:** Medium | **Complexity:** L

---

## 12. Risks and Challenges

| Risk | Impact | Mitigation |
|---|---|---|
| Embedding/LLM cost overruns | High | Per-feature daily budgets (extend `SUMMARY_DAILY_LIMIT` pattern), content-hash caching, batch embedding, deterministic local fallbacks when AI is off, cost telemetry (Idea 100). |
| Vault scale & performance | High | Chunked background jobs, incremental indexing with dirty flags, paginated graph queries, Postgres/pgvector when volume demands; keep the numpy/FAISS backend for small vaults. |
| Retrieval quality / hallucination | High | Mandatory citations, faithfulness checks, "not found in Second Brain" default, retrieval evaluation harness (Idea 26), golden sets in CI. |
| Schema & migration complexity | Medium | Follow the existing `COLUMN_MIGRATIONS` pattern; new tables via `create_all`; introduce Alembic only when Postgres lands. |
| Private vault data exposure | High | Per-user scoping enforced in SQL (never in prompts), role-based access, no cross-user retrieval; vault path validation against path traversal (pattern exists in uploads security). |
| Obsidian/format churn | Medium | Normalizer isolates format details; parser versioned; unknown frontmatter keys preserved losslessly. |
| Syllabus parsing variance | Medium | Strict JSON schema + human review UI; heuristic fallback when AI disabled; per-parse confidence stored. |
| Model/provider flakiness | Medium | Existing model fallback chain; retries; degraded mode falls back to deterministic generators (existing convention). |
| Scope creep in automation | Medium | Every automation has a review queue and a master switch per feature; nothing moves/deletes user files without confirmation. |
| User trust in recommendations | Medium | Explainable recommendations (reasons shown); easy "ignore/undo"; feedback loop (Idea 29) tunes rather than hard-codes. |
| Repo hygiene | Low | The 111 MB `Obsidian Vault/` is untracked but not gitignored — add it to `.gitignore` before the watcher indexes it. |
| Obsidian Copilot overlap | Medium | The vault already runs in-vault AI; app-side features complement it (server-side index, app-integrated tutor) instead of duplicating. |

---

## 13. Future Enhancements

- **Collaborative vaults** — shared subject libraries with teacher/classroom publishing into the knowledge base (builds on the existing teacher role).
- **Mobile & offline** — PWA/desktop capture widget that syncs clips into the vault; offline embedding via local models (e.g., ONNX).
- **Voice interaction** — spoken questions/notes via STT; hands-free capture into daily notes.
- **Multimodal notes** — images/diagrams in notes indexed with vision embeddings; diagram-to-text explanation.
- **Anki/other-deck export** — bidirectional sync with Anki for advanced spaced-repetition workflows.
- **Public knowledge packs** — community-contributed subject packs (parsed syllabi, question banks) users can import.
- **Federated/local LLM mode** — run embeddings + generation fully locally (Ollama/llama.cpp) for privacy-first users.
- **Proactive tutor** — scheduled check-ins that quiz from due reviews without being asked.
- **Insight reports** — weekly/monthly knowledge-health and learning reports emailed/in-app.

---

## 14. Implementation Timeline

Estimated 14–18 months for a small team (1–2 backend, 1 frontend, part-time AI/QA), built on the existing codebase. Timeline assumes the app's current sprint conventions (phased delivery with regression tests per phase).

| Phase | Scope | Suggested duration |
|---|---|---|
| Phase 0 | Fast win: wire the existing unused `VectorStore` + embeddings client into a vault-search endpoint (Ideas 11–12 subset) | Week 0–1 |
| Phase 1 | Knowledge Core + ingestion (Ideas 1–10) | Weeks 1–6 |
| Phase 2 | Embeddings, persistent vectors, knowledge graph (11–20) | Weeks 5–12 |
| Phase 3 | Search & retrieval (21–30) | Weeks 10–16 |
| Phase 4 | Note intelligence & content generation (31–40) | Weeks 14–20 |
| Phase 5 | Subject management core (41–50) | Weeks 18–26 |
| Phase 6 | Study planning & execution (51–60) | Weeks 24–32 |
| Phase 7 | AI tutor & assessment (61–70) | Weeks 30–38 |
| Phase 8 | Personalization & learning memory (71–80) | Weeks 36–44 |
| Phase 9 | Automation (81–90) | Weeks 42–52 |
| Phase 10 | Advanced AI, analytics & platform (91–100) | Weeks 50–70+ |

Phases overlap deliberately: a feature is shippable as soon as its dependencies (not its whole phase) are done. The first three phases are prerequisites for most AI features; phases 4–8 can run partly in parallel after Phase 3. Idea 100 (observability) starts early in lightweight form and is completed last. Because the audit (§2) shows ~43 ideas extend existing code, several phases are shorter than their idea counts suggest — treat the durations as upper bounds.

---

## 15. Milestones

| Milestone | Definition of done | Target |
|---|---|---|
| **M1 — Vault wired in** | User registers an Obsidian vault/folder; documents indexed with hash dedupe; `GET /api/kb/search` returns full-text hits. (Ideas 1–4, 7–10, 21) | End of Phase 1–2 |
| **M2 — Semantic knowledge base** | Embeddings + persistent vector store; hybrid search returns ranked, cited chunks; graph shows concepts and links. (Ideas 11–18, 22–23, 25) | End of Phase 3 |
| **M3 — Notes become study material** | AI summaries, quizzes, and flashcards generated from vault notes; brain-dump drafts file into the vault. (Ideas 31–34, 40) | End of Phase 4 |
| **M4 — Auto-managed subjects** | Syllabus → subject/units/topics with dependency graph and coverage map; first roadmap generated. (Ideas 41–47, 38) | End of Phase 5 |
| **M5 — Daily learning loop** | Revision scheduler + recommended next action materialize on the daily schedule; weak topics detected from quizzes. (Ideas 52, 58–60, 90) | End of Phase 6 |
| **M6 — Personal AI tutor** | RAG tutor answers with citations, explains from known concepts, adapts difficulty; doubt-solving and mistake analysis live. (Ideas 61–68, 73–74) | End of Phase 7–8 |
| **M7 — Autonomous assistant** | Automation jobs run nightly (tags, links, flashcards, summaries); multi-agent orchestration for compound requests; forecasts and reflection shipped. (Ideas 82–88, 91–99) | End of Phase 9–10 |
| **M8 — Self-improving system** | Evaluation harness in CI, faithfulness checks, feedback loops, cost dashboards; tuning cadence established. (Ideas 26, 93, 100) | End of Phase 10 |

---

## 16. Success Metrics

### Product metrics
- **Vault coverage:** % of indexed files that are searchable within 24h of change (target ≥ 95%).
- **Retrieval quality:** recall@5 and MRR ≥ 0.75 on the golden set; answer faithfulness ≥ 90% (groundedness checks).
- **Usage:** ≥ 3 tutor sessions / week / active user; ≥ 60% of generated study plans started; ≥ 40% revision tasks completed on time.
- **Gap-to-capture:** ≥ 25% of flagged knowledge gaps result in a new note within 7 days.
- **Subject automation:** ≥ 80% of imported syllabi parse to a confirmed subject profile without manual rework.

### Learning outcomes (proxy, 1 semester)
- Grade/exam readiness score correlation with final performance (target |r| ≥ 0.5).
- Practice-to-retention: users completing ≥ 70% of due revisions show measurable mastery growth on re-tests.

### Engineering metrics
- Zero unauthenticated cross-user data access (security regression suite, extended `test_ownership.py` patterns).
- AI-disabled mode keeps every feature functional (deterministic fallbacks) — full test suite green with `AI_ENABLED=false`.
- P95 API latency for search/tutor ≤ 3s; ingestion keeps pace with vault growth (index rate ≥ 2× new-file rate).
- Cost per active user/month for AI within budget; daily-limit breaches reported by Idea 100 telemetry.

---

*End of plan. This document is a blueprint: features are additive, build on the existing FastAPI/React architecture, and preserve the app's existing AI, curriculum, gamification, and study features.*
