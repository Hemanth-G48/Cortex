# REPOS REUSE ANALYSIS — What to Borrow From the 68 Cloned Reference Repos

**Generated:** 2026-08-05 · Companion to `SIMILAR_GITHUB_REPOS.md` · All repos cloned under `similar_repos/<owner>/<repo>`

## Purpose

For every one of the **68 cloned repos**, this file answers: *what is genuinely useful here, and which concrete components can be reused, adapted, or studied — mapped to the specific Phase / Idea of the Second Brain AI Integration plan?*

## How to read this file

- **Phase map (below):** fastest view — for each Phase 1–10 and each Idea, which repos supply a reusable component.
- **Repo detail groups:** per-repo write-ups with **exact file paths** inside `similar_repos/...` so you can open the component directly.
- **License flags:** ⚠️ = copyleft (AGPL/GPL/BUSL) — read the code, don't vendor it wholesale. ✅ = permissive (MIT/Apache/BSD).
- **Reuse mode:** `PORT` = copy/adapt the code; `INTEGRATE` = wrap the library as a dependency; `STUDY` = reference implementation worth reading; `INSPIRE` = UX/architecture ideas only.

## The 10 Phases (from SECOND_BRAIN_AI_INTEGRATION_PLAN.md)

| Phase | Title | Ideas |
|---|---|---|
| 1 | Second Brain Foundation & Ingestion | 1–10 (data model, source registry, watcher, markdown parser, PDF, OCR, chunking, dedupe, versioning, job queue) |
| 2 | Embeddings, Indexing & Knowledge Graph | 11–20 (embeddings, vector store, metadata, auto-tag, concepts, KG nodes/edges, backlinks, graph viz, dup detection, re-index) |
| 3 | Search & Retrieval | 21–30 (FTS5, semantic search, hybrid RRF, query expansion, citation cards, eval, health, missing knowledge, feedback, unified search) |
| 4 | Note Intelligence & Content Generation | 31–40 (summaries, ELI5 explanations, quizzes, flashcards, daily notes, citations, concept linking UI, mind maps, quality scoring, braindump→notes) |
| 5 | Subject Management Core | 41–50 (auto subjects, syllabus parsing, semester detection, topic extraction, unit segmentation, dependency graph, roadmaps, difficulty, time, outcomes) |
| 6 | Study Planning & Execution | 51–60 (personalized plans, spaced repetition, exam prep, assignments, labs, attendance, progress analytics, weak/strong topics, study order, micro-sessions) |
| 7 | AI Tutor & Assessment | 61–70 (RAG tutor, doubt solving, practice Qs, mock tests, interview prep, grading, adaptive difficulty, mistake analysis, XP, skill mapping) |
| 8 | Personalization & Learning Memory | 71–80 (preferences, gap detection, personalized explanations, remembered concepts, recommend-next, connect concepts, missing notes, outdated detection, memory store, adaptive paths) |
| 9 | Automation | 81–90 (auto-categorize, auto-tag, auto-link, auto-dupes, auto-flashcards, auto-summaries, auto-mindmaps, auto-plan-sync, repo sync, auto-revision tasks) |
| 10 | Advanced AI, Analytics & Platform | 91–100 (multi-agent, long-term memory, RAG hardening, graph+vector fusion, context-aware, research assistant, recommendations, goals/reflection, forecasting, observability) |

---

## ⭐ Phase-by-Phase Reuse Map

### Phase 1 — Foundation & Ingestion
- **Idea 1 data model:** `basic-memory` (entity/relation SQLAlchemy schema), `siyuan` (block/attribute model), `dendron` (note hierarchy), `engram` (SQLite store)
- **Idea 2 source registry:** `glean` (RSS sources), `khoj` (content-type configs), `obsidian-wiki` (session_sources.py)
- **Idea 3 folder watcher:** `obsidian-wiki` (sync.py), `glean`, `claude-obsidian` (vault_ops.py), `obsidian-second-brain` (adapters/)
- **Idea 4 markdown parser (frontmatter & wikilinks):** `basic-memory` (markdown/), `foam` (foam-core), `dendron` (engine-server), `llm_wiki` (commands/fs.ts), `claude-obsidian` (obsidian-markdown skill)
- **Idea 5 PDF ingestion:** `khoj` (processor/content/pdf), `syllabus-agent` (PyPDF2 extract), `memora` (processing.py), `PAIDEIA` (vision_ocr.py), `recalla` (flashcards/pdf route)
- **Idea 6 OCR:** `PAIDEIA` (vision_ocr.py + tesseract checks in doctor.py)
- **Idea 7 semantic chunking:** `khoj` (processor/content), `reor` (ChunkSizeSettings.tsx), `decodingai` (chunk_embed_load.py), `glean`
- **Idea 8 content-hash dedupe:** `hashcards` (content-addressable cards), `engram` (content hash), `basic-memory` (mtime/size columns)
- **Idea 9 version history:** `orbit` (store-fs/store-web), `engram` (store), `llm_wiki` (file-history-panel.tsx)
- **Idea 10 job queue:** `glean` (worker), `khoj` (background jobs), `decodingai` (pipelines/)

### Phase 2 — Embeddings, Indexing & Knowledge Graph
- **Idea 11 embeddings service:** `glean` (embedding_factory.py + provider classes), `reor` (lib/llm), `khoj` (bi-encoder config), `decodingai`
- **Idea 12 vector store:** `glean` (milvus_client.py), `reor` (local vector DB), `khoj` (pgvector), `dyresearch` (pgvector/lancedb)
- **Idea 13 metadata extraction:** `llm_wiki` (frontmatter-panel.tsx), `claude-obsidian`, `khoj`
- **Idea 14 auto-tagging:** `khoj` (tag/group processors), `basic-memory` (picoschema/), `llm_wiki`
- **Idea 15 concept extraction & canonicalization:** `obsidian-wiki` (ast_extractor.py, graph_analysis.py), `knowledge-nexus` (entity_extraction_agent.py), `llm_wiki`
- **Idea 16 KG nodes & edges:** `basic-memory` (models + index/), `nocturne_memory` (db/graph.py), `obsidian-wiki` (session_graph.py), `knowledge-nexus` (Neo4j)
- **Idea 17 backlink inference:** `foam` (foam-core backlinks), `dendron`, `llm_wiki` (page-links-panel.tsx)
- **Idea 18 graph visualization:** `llm_wiki` (graph-view.tsx + layout worker), `dendron` (dendron-viz), `obsidian-wiki` (session_viz.py), `mind-mentor` (insights/knowledge-graph page), `basic-memory`
- **Idea 19 duplicate detection:** `hashcards`, `engram`
- **Idea 20 backfill & re-index:** `PAIDEIA` (reindex.py), `obsidian-wiki` (batch.py, sync.py), `decodingai` (pipelines)

### Phase 3 — Search & Retrieval
- **Idea 21 FTS5:** `siyuan` (kernel/search + sql/), `engram` (SQLite FTS), `basic-memory` (search index)
- **Idea 22 semantic search:** `khoj` (search_type/), `reor` (SearchComponent.tsx), `glean`
- **Idea 23 hybrid RRF:** `khoj` (search_type/hybrid), `reor`
- **Idea 24 query expansion:** `khoj`, `dyresearch`
- **Idea 25 citation-aware cards:** `claude-obsidian` (ledgers.py, contracts.py), `khoj`
- **Idea 26 eval harness:** `khoj` (tests), `decodingai` (eval/dataset steps)
- **Idea 27 knowledge health:** `claude-obsidian` (lint_engine.py), `PAIDEIA` (doctor.py), `obsidian-wiki` (lint.py, trust.py)
- **Idea 28 missing knowledge detection:** `llm_wiki` (gap analysis), `obsidian-wiki` (graph_analysis.py)
- **Idea 29 search feedback & learning:** `QuestLog` (ai.controller.js caching + feedback), `khoj`
- **Idea 30 unified search box:** `siyuan`, `reor` (SearchComponent), `khoj` (web search UI)

### Phase 4 — Note Intelligence & Content Generation
- **Idea 31 AI summaries:** `memora` (generatorGPT.py), `StudyWise` (notes page), `khoj` (summarize), `EduAI` (chat app)
- **Idea 32 ELI5 explanations:** `StudyWise` (eli5 page), `mind-mentor`
- **Idea 33 AI quizzes:** `EduAI` (practice app), `StudyWise` (quiz), `studybuddy-ai`, `memora`, `Multi-Agent-Study-Assistant` (quiz gen), `infinition` (quiz modals)
- **Idea 34 flashcards:** `LearnKit` (engine/scheduler), `obsidian-spaced-repetition`, `hashcards`, `mimocard`, `memo`, `recalla`, `yt-flashcard-ai`, `studybuddy-ai`, `org-fc`
- **Idea 35 daily notes:** `obsidian-second-brain` (obsidian-daily command), `My-Brain-System`, `OrbitOS`, `obsidian-claude-pkm`
- **Idea 36 citation management:** `claude-obsidian` (contracts.py/ledgers.py), `obsidian-wiki`
- **Idea 37 concept linking UI:** `llm_wiki` (page-links-panel.tsx), `mind-mentor` (knowledge graph), `obsidian-wiki`
- **Idea 38 mind-map generation:** `second_brain_builder` (mermaid output), `StudyWise` (concept-map), `mind-mentor`, `obsidian-second-brain` (obsidian-architect)
- **Idea 39 note quality scoring:** `claude-obsidian` (lint_engine.py), `PAIDEIA` (doctor.py), `obsidian-wiki` (lint.py)
- **Idea 40 brain dump → notes:** `CortX` (cortx_extractor.py + agent), `second_brain_builder` (generation modals), `claude-obsidian` (capture.py), `obsidian-second-brain` (obsidian-capture)

### Phase 5 — Subject Management Core
- **Idea 41 auto subject creation:** `syllabo`, `study-planner-agent` (models.py Subject)
- **Idea 42 syllabus parsing:** `syllabus-agent` (utils.py extract_topics_from_text), `syllabo`, `PAIDEIA`, `study-planner-agent`, `Syllabify`, `EduAI` (syllabus app)
- **Idea 43 semester/calendar detection:** `syllabo`, `Student_Study_Planner`, `EduAI`
- **Idea 44 topic extraction & normalization:** `syllabus-agent`, `PAIDEIA`, `syllabo`, `StudyWise`
- **Idea 45 unit & lecture segmentation:** `PAIDEIA`, `syllabo`, `EduAI`
- **Idea 46 topic dependency graph:** `PAIDEIA` (learning graph), `mind-mentor` (knowledge graph), `knowledge-nexus` (Neo4j), `obsidian-wiki`
- **Idea 47 learning roadmap generation:** `Multi-Agent-Study-Assistant` (roadmaps), `study-planner-agent` (generate_plan), `syllabo`, `StudyWise`, `PAIDEIA`, `OrbitOS`
- **Idea 48 difficulty estimation:** `syllabo` (difficulty_analyzer.py), `studybuddy-ai`, `syllabus-agent`
- **Idea 49 time estimation:** `syllabus-agent` (build_study_plan), `study-planner-agent`, `syllabo`
- **Idea 50 learning-outcome extraction:** `syllabo`, `PAIDEIA`, `syllabus-agent`

### Phase 6 — Study Planning & Execution
- **Idea 51 personalized study plans:** `study-planner-agent` (generate_plan), `mind-mentor` (study-plan), `Multi-Agent-Study-Assistant`, `syllabo`, `StudyWise`
- **Idea 52 spaced repetition (FSRS/SM-2):** `py-fsrs`, `ts-fsrs`, `fsrs-rs`, `obsidian-spaced-repetition` (FSRS+SM-2), `LearnKit` (fsrs.ts/lkrs.ts), `infinition` (SM-2), `org-fc` (SM-2 + FSRS), `hashcards`, `memo`, `orbit`, `fsrs4anki`, `anki` (rslib scheduler)
- **Idea 53 exam prep mode:** `StudyWise` (exam page), `EduAI` (practice), `syllabo`, `Student_Study_Planner`
- **Idea 54 assignment intelligence:** `QuestLog` (tasks), `noodle` (modules), `EduAI`
- **Idea 55 lab tracking:** `QuestLog` (collaboration), `EduAI`
- **Idea 56 attendance monitoring:** `EduAI`, `habit_quest` (streak patterns)
- **Idea 57 progress analytics:** `QuestLog` (analytics.controller.js), `StudyWise` (progress), `mind-mentor` (insights), `HabitTrove`, `syllabo`
- **Idea 58 weak/strong topics:** `QuestLog` (AI insights), `StudyWise`, `syllabo`, `PAIDEIA`
- **Idea 59 recommended study order:** `syllabo` (content_recommender.py), `Multi-Agent-Study-Assistant`, `StudyWise`
- **Idea 60 micro-session/focus:** `mind-mentor` (timer), `habit_quest`, `HabitTrove`

### Phase 7 — AI Tutor & Assessment
- **Idea 61 RAG-grounded tutor:** `khoj` (chat + search), `reor` (Chat), `mind-mentor` (chat), `EduAI` (chat), `memora` (RetrievalQA_mod.py), `dyresearch`, `Multi-Agent-Study-Assistant`, `claude-obsidian` (grounded answers), `tutor-skills`, `obsidian-wiki`
- **Idea 62 doubt solving:** `EduAI` (chat), `mind-mentor`, `StudyWise`
- **Idea 63 practice questions:** `EduAI` (practice), `StudyWise` (quiz), `studybuddy-ai`, `syllabo` (adaptive_quiz_engine.py), `memora`
- **Idea 64 mock tests & simulations:** `StudyWise` (exam), `EduAI`, `LearnKit` (exam-tests-sqlite.ts), `syllabo`
- **Idea 65 interview prep:** `Multi-Agent-Study-Assistant`, `dyresearch` (research agents)
- **Idea 66 advanced grading:** `EduAI` (practice grading), `StudyWise` (quiz scoring)
- **Idea 67 adaptive difficulty:** `syllabo` (adaptive_quiz_engine.py), `StudyWise`
- **Idea 68 mistake analysis:** `PAIDEIA` (오답/wrong-answer tracking), `QuestLog` (analytics), `syllabo`
- **Idea 69 knowledge capture & XP:** `habit_quest`, `QuestLog` (XP), `Habit-Quest`, `HabitTrove`, `LearnKit` (exam-tests)
- **Idea 70 skill mapping:** `PAIDEIA` (subject learning graph), `mind-mentor` (knowledge graph), `syllabo`

### Phase 8 — Personalization & Learning Memory
- **Idea 71 preferences:** `mind-mentor` (profile/settings), `Multi-Agent-Study-Assistant` (profiling), `dyresearch` (config_manager.py), `glean` (preference.py schema)
- **Idea 72 knowledge-gap detection:** `llm_wiki` (gap analysis), `Multi-Agent-Study-Assistant` (gap analysis), `obsidian-wiki` (graph_analysis.py)
- **Idea 73 personalized explanations:** `mind-mentor`, `EduAI`, `StudyWise`
- **Idea 74 remember learned concepts:** `engram` (memory store), `nocturne_memory`, `basic-memory`, `claude-obsidian`
- **Idea 75 recommend next:** `QuestLog` (AI recommendations), `syllabo` (content_recommender.py), `StudyWise`
- **Idea 76 connect concepts to notes:** `llm_wiki` (graph), `claude-obsidian` (connect skill), `obsidian-second-brain` (obsidian-connect), `obsidian-wiki`
- **Idea 77 suggest missing notes:** `llm_wiki`, `obsidian-wiki` (graph_analysis), `My-Brain-Is-Full-Crew`
- **Idea 78 outdated-note detection:** `claude-obsidian` (lint_engine.py), `obsidian-wiki` (lint.py, trust.py)
- **Idea 79 long-term memory store:** `engram` (internal/store), `nocturne_memory` (db/), `basic-memory` (repository/), `memory-bank-mcp`, `token-savior`
- **Idea 80 adaptive learning paths:** `Multi-Agent-Study-Assistant`, `syllabo`, `StudyWise`

### Phase 9 — Automation
- **Idea 81 auto-categorize:** `CortX` (agent structuring), `obsidian-second-brain` (obsidian-board), `My-Brain-Is-Full-Crew` (sorter agent), `claude-obsidian` (wiki-fold skill)
- **Idea 82 scheduled auto-tag:** `My-Brain-Is-Full-Crew` (sorter/scribe), `khoj` (grouping)
- **Idea 83 auto-link:** `llm_wiki`, `claude-obsidian`, `obsidian-second-brain` (obsidian-connect), `My-Brain-Is-Full-Crew` (connector)
- **Idea 84 auto-dupes:** `hashcards`, `engram`
- **Idea 85 auto-flashcards:** `LearnKit`, `mimocard`, `yt-flashcard-ai`, `StudyWise`, `studybuddy-ai`
- **Idea 86 auto-summaries:** `memora`, `StudyWise`, `khoj`
- **Idea 87 auto mind maps:** `second_brain_builder`, `StudyWise` (concept-map), `mind-mentor`
- **Idea 88 auto-plan-sync:** `study-planner-agent`, `syllabo`, `OrbitOS`
- **Idea 89 repo sync:** `glean` (RSS), `khoj` (github_to_entries.py), `llm_wiki` (file-sync.ts), `obsidian-wiki` (sync.py)
- **Idea 90 auto-revision tasks:** `obsidian-spaced-repetition`, `LearnKit`, `py-fsrs` (due cards)

### Phase 10 — Advanced AI, Analytics & Platform
- **Idea 91 multi-agent:** `Multi-Agent-Study-Assistant` (study_agents.py), `My-Brain-Is-Full-Crew` (8 agents), `dyresearch` (ADK agents), `obsidian-second-brain` (46 commands), `mind-mentor` (mind-mentor-agents), `phantom`, `arscontexta`
- **Idea 92 long-term memory:** `engram`, `nocturne_memory`, `basic-memory`, `token-savior`, `memory-bank-mcp`
- **Idea 93 RAG hardening:** `khoj`, `decodingai`, `reor`, `obsidian-wiki` (graphrag.py)
- **Idea 94 graph+vector fusion:** `knowledge-nexus` (Neo4j GraphRAG), `llm_wiki`, `obsidian-wiki` (graphrag.py), `basic-memory`
- **Idea 95 context-aware responses:** `QuestLog` (AI controller w/ user stats), `mind-mentor`, `EduAI`
- **Idea 96 research assistant:** `dyresearch`, `knowledge-nexus` (notion/pocket providers), `decodingai`, `claude-obsidian` (autoresearch skill)
- **Idea 97 recommendation engine:** `syllabo` (content_recommender.py), `QuestLog`, `StudyWise`
- **Idea 98 goals & reflection:** `obsidian-claude-pkm` (3-year vision → daily), `OrbitOS`, `My-Brain-System`, `obsidian-second-brain` (obsidian-challenge)
- **Idea 99 trajectory forecasting:** `QuestLog` (analytics), `syllabo` (prediction), `StudyWise`
- **Idea 100 observability:** `claude-obsidian` (ledgers.py), `token-savior`, `QuestLog` (analytics), `decodingai` (Opik integration)

---

## Repo Detail Groups

### Group 1 — Spaced Repetition & Flashcards (17 repos) — Phase 6 Idea 52, Phase 4 Idea 34, Phase 7 63–64

**1. open-spaced-repetition/py-fsrs** ✅ MIT · `PORT`/`INTEGRATE`
- The official Python FSRS scheduler. **Reuse directly** as the engine behind Idea 52 (revision scheduling) and Idea 34 (flashcards).
- `fsrs/scheduler.py` — `Scheduler.review_card()`, `reschedule_card()`, `get_card_retrievability()` (lines 234/517/208); `_next_interval()`, `_initial_stability()`, `_next_difficulty()` (677/660/714) — the full DSR-model math.
- `fsrs/card.py`, `fsrs/review_log.py`, `fsrs/state.py`, `fsrs/rating.py` — the card/state/review-log data model to mirror in our DB schema.
- `fsrs/optimizer.py` — parameter optimization from review logs (Idea 29/52 "self-tuning scheduler").

**2. open-spaced-repetition/ts-fsrs** ✅ MIT · `PORT`/`INTEGRATE`
- TypeScript FSRS (monorepo). If we ever run scheduling client-side, this is the port. Same algorithm as py-fsrs.

**3. open-spaced-repetition/fsrs-rs** ✅ MIT · `STUDY`
- Rust reference implementation with benches. The fastest engine; only needed if performance becomes an issue.

**4. open-spaced-repetition/fsrs4anki** ✅ MIT · `STUDY`
- `fsrs4anki_scheduler.js` — standalone JS FSRS scheduler (Anki's production scheduler). Simpler than ts-fsrs to read.
- `.ipynb` notebooks: `fsrs4anki_optimizer.ipynb` (parameter optimization), `fsrs4anki_simulator.ipynb` (simulate retention) — great for testing retention-rate configs.

**5. open-spaced-repetition/free-spaced-repetition-scheduler** ✅ MIT · `STUDY`
- Spec/paper repo only (READMEs). Read to understand DSR model before wiring py-fsrs.

**6. open-spaced-repetition/awesome-fsrs** ✅ MIT · `INSPIRE`
- Curated list of all FSRS implementations (Python/Rust/TS/JS) — pick the right port.

**7. st3v3nmw/obsidian-spaced-repetition** ✅ MIT · `STUDY` + `PORT` (scheduler math)
- The most battle-tested open-source SRS plugin. **FSRS + SM-2 dual algorithm**.
- `src/data/data-store/notes-data-store/note-data-store-algorithm-osr.ts` — FSRS integration over markdown notes.
- `src/data/data-structures/card/card.ts`, `deck/deck.ts`, `deck/deck-tree-stats-calculator.ts` — card/deck/stat models.
- `src/data/data-manager.ts`, `src/data/plugin-data.ts` — persistence pattern for review state.
- Reuse for: Idea 52 scheduler storage, Idea 34 flashcard parsing from markdown, deck stats UI (Idea 57).

**8. infinition/obsidian-flash-quizz** ✅ MIT · `PORT`
- Minimal, clean. `main.ts` — SM-2 algorithm inline (line 48 comment "SRS LOGIC"), vault-wide flashcard/quiz block scanning, Library modal, QuizModal (809), FlashcardModal (929).
- Reuse: SM-2 as fallback scheduler; the "scan markdown blocks → build deck" parser for Idea 34; quiz modal UX for Idea 33.

**9. ctrlaltwill/LearnKit** ✅ (LICENSE.md) · `PORT` + `STUDY`
- The most complete "study inside your vault" tool — flashcards + note review + tests + AI, FSRS-based.
- `src/engine/scheduler/scheduler.ts` + `fsrs-optimizer.ts` — FSRS scheduling + optimizer.
- `src/engine/note-review/fsrs.ts` + `lkrs.ts` — two review algorithms.
- `src/engine/indexing/group-index.ts`, `group-normalization.ts` — how notes auto-group into decks (Idea 44/85).
- `src/platform/core/exam-tests-sqlite.ts` — exam mode with SQLite persistence (Idea 64).
- `src/platform/core/coach-plan-sqlite.ts` — spaced study plan scheduling (Idea 51/52).
- `src/engine/parser/parser.ts` — markdown → card parsing.

**10. l3kn/org-fc** ✅ MIT · `STUDY` (Emacs/elisp)
- `org-fc-algo-sm2.el` and `org-fc-algo-fsrs.el` — clean reference implementations of SM-2 and FSRS.
- `org-fc-scheduler.el`, `org-fc-dashboard.el` — scheduling + review dashboard patterns.
- `org-fc-type-cloze.el`, `org-fc-type-double.el`, `org-fc-type-normal.el` — card-type models (cloze/double/normal) worth mirroring in Idea 34.

**11. eudoxia0/hashcards** ✅ MIT (check) · `PORT` (concept)
- **Content-addressable cards**: card ID = hash of text; editing a card resets progress. Directly reusable for **Idea 8 (content-hash dedupe)** and **Idea 19 (duplicate detection)**.
- `src/cmd/due.rs`, `src/cmd/drill/` (heatmap.rs, retention.rs, state.rs) — review drill UI + retention heatmap (Idea 57).
- `src/cmd/export.rs` — export formats.

**12. bmmunga/recalla** ✅ MIT · `INSPIRE` (Next.js SRS)
- `src/app/api/flashcards/generate/route.ts` — AI flashcard generation endpoint (Idea 85).
- `src/app/flashcards/study/page.js` + `progress/page.js` — study + progress UI patterns.

**13. olmps/memo** ✅ MIT · `STUDY` (Flutter)
- Mobile flashcard app. `lib/application/pages/home/progress/`, `lib/application/pages/execution/` — mobile study UX reference if we ever ship mobile.

**14. andymatuschak/orbit** ⚠️ BUSL+AGPL · `STUDY` only
- "Mnemonic medium" SRS platform. `packages/core`, `packages/interpreter`, `packages/ingester` — prompt interpretation + ingestion pipeline concepts.
- `packages/anki-import` — Anki import (Idea 89). Research-grade architecture to read, not vendor.

**15. gyoomei/mimocard** ✅ (no license → STUDY) · `INSPIRE`
- Single-HTML AI flashcard generator: URL → Jina reader → SM-2 scheduler → Anki export. `app.js` — the whole loop in one file. Great end-to-end reference for Idea 34 + Idea 85.

**16. KeyulJain/yt-flashcard-ai** ✅ MIT · `PORT` (concept)
- `content.js` + `background.js` + `server.js` — YouTube transcript extraction → AI flashcards. Reuse for Idea 89 (auto-sync external repos) + Idea 85 (auto-flashcards from lectures).

**17. ankitects/anki** ⚠️ AGPL · `STUDY` only
- The reference SRS implementation. `rslib/src/scheduler/fsrs/` (rescheduler.rs), `rslib/src/scheduler/states/` — production-grade scheduler state machine.
- SQL schema in `pylib` + `.sql` files — deck/card/review schema worth mirroring (inspired, not copied) for our `flashcard` + `revision_schedule` tables.
### Group 2 — RAG & Second Brain Engines (14 repos) — Phases 1–3, 7, 10

**18. khoj-ai/khoj** ⚠️ AGPL · `STUDY` (deep) + `INTEGRATE` (as separate service if AGPL acceptable)
- The flagship open-source "AI second brain". The best architecture reference for Phases 1–3 and 10.
- `src/khoj/processor/content/` — per-content-type ingestion: `markdown/`, `pdf/`, `github/github_to_entries.py`, `images/` (Idea 4/5/89).
- `src/khoj/search_type/` — semantic + keyword + hybrid search; RRF fusion reference for **Idea 23**.
- `src/khoj/search_filter/` — date/file-type/folder filters (Idea 30).
- `src/khoj/database/` — embeddings storage + `searchmodelconfig` (bi-encoder/cross-encoder config) for **Idea 11/12/93**.
- `src/khoj/routers/` — chat + search API endpoints (Idea 61 shell).
- `src/khoj/processor/` — chunking + embedding pipeline (Idea 7).
- Frontend `src/interface/web` + `src/interface/obsidian` — search UI patterns (Idea 30).

**19. reorproject/reor** ⚠️ AGPL · `STUDY` (deep)
- Local-first AI PKM (RAG + embeddings fully local). Best reference for local embeddings + chunking.
- `src/components/Settings/ChunkSizeSettings.tsx` — chunk-size UX (Idea 7).
- `src/components/Settings/EmbeddingSettings/EmbeddingModelSelect.tsx`, `EmbeddingSettings.tsx`, `modals/NewRemoteEmbeddingModel.tsx` — model config UI (Idea 11).
- `src/lib/llm/chat.ts`, `client.ts`, `tools/` — local LLM chat + tool calls (Idea 61/91).
- `src/components/Chat/ChatConfigComponents/DBSearchFilters.tsx` — retrieval filters in chat (Idea 93).
- `src/components/Sidebars/SearchComponent.tsx` — unified search sidebar (Idea 30).
- `node/` — the Node embedding server; check its `.ts` sources for chunking/embedding implementation.

**20. basicmachines-co/basic-memory** ⚠️ AGPL · `STUDY` (deep) + `PORT` (schema ideas)
- Knowledge-graph-over-markdown MCP server. The cleanest entity/relation graph implementation.
- `src/basic_memory/markdown/` — markdown parser with frontmatter + wikilinks (Idea 4).
- `src/basic_memory/models/` — Entity/Relation/SearchIndex SQLAlchemy models (Idea 1/16).
- `src/basic_memory/index/`, `indexing/` — graph indexing pipeline (Idea 15/16).
- `src/basic_memory/repository/` — storage layer.
- `src/basic_memory/picoschema/` — lightweight schema/validation (Idea 13/14).
- `alembic/versions/...` — migrations incl. `add_postgres_full_text_search_support_` (Idea 21 FTS) and `add_scan_watermark_tracking_to_project` (Idea 3 watcher cursor).
- `NOTE-FORMAT.md` — the note format spec for graph entities — read before designing our kb format.

**21. nashsu/llm_wiki** ✅ MIT · `STUDY` + `PORT`
- "Knowledge base that builds itself" — Tauri + React. Graph-driven note generation.
- `src/components/graph/graph-view.tsx` + `graph-layout-worker.ts` — graph visualization (Idea 18).
- `src/components/editor/page-links-panel.tsx` — backlinks/concept-linking UI (Idea 17/37).
- `src/components/editor/frontmatter-panel.tsx` — metadata editing (Idea 13).
- `src/components/editor/file-history-panel.tsx` — version history UI (Idea 9).
- `src/commands/fs.ts`, `file-sync.ts` — file scanning/sync (Idea 3/89).
- `mcp-server/` — MCP interface; `src-tauri/` — desktop shell.
- Gap analysis + graph-relevance ranking are documented in `plans/` and `llm-wiki.md` — reference for **Idea 28 (missing knowledge) and Idea 94 (graph+vector fusion)**.

**22. Jallermax/knowledge-nexus** ✅ MIT (check) · `STUDY` + `PORT`
- Neo4j GraphRAG engine — the closest reference for **Idea 94 (graph+vector fusion)**.
- `graph_rag/ai_agent/entity_extraction_agent.py`, `insight_generation_agent.py`, `summarization_agent.py` — agent-based graph building (Idea 15/31/91).
- `graph_rag/controller/query_controller.py` — GraphRAG query path.
- `graph_rag/data_source/` — notion_api.py, pocket_api.py, web_scraper.py, to_markdown_parser.py — external repo sync (Idea 89).
- `graph_rag/data_model/graph_data_classes.py` — graph schema models.
- Note: depends on Neo4j — heavy; borrow the *design*, keep our SQLite graph.

**23. gcorman/CortX** ✅ MIT (check) · `STUDY` + `PORT` (prompt/agent flows)
- "AI second brain" desktop app — natural-language capture → structured markdown. The **propose-then-execute** review pattern.
- `python-sidecar/cortx_extractor.py` — extraction sidecar (Idea 40 brain-dump → notes).
- `src/renderer/` — Electron UI; `docs/` — agent prompts defining the filing/structuring workflow (Idea 81 auto-categorize).
- Reference for how an agent decides "where to file" a note with human approval.

**24. Ar9av/obsidian-wiki** ✅ MIT · `STUDY` + `PORT`
- Python package: "digital brain that connects and answers".
- `obsidian_wiki/ast_extractor.py` — parse markdown into AST (Idea 4).
- `obsidian_wiki/graph_analysis.py` + `graphrag.py` — graph + RAG combo (Idea 94).
- `obsidian_wiki/session_index.py`, `session_sources.py`, `session_query.py` — indexing + retrieval sessions (Idea 2/22).
- `obsidian_wiki/sync.py` — vault sync (Idea 3/89).
- `obsidian_wiki/lint.py`, `trust.py` — note quality + trust scoring (Idea 27/39/78).
- `obsidian_wiki/cache.py` — caching.

**25. AgriciDaniel/claude-obsidian** ✅ MIT · `STUDY` + `PORT`
- The most disciplined Obsidian agent toolkit — citation ledgers, linting, vault health.
- `claude_obsidian/ledgers.py` — **citation/provenance ledger** — directly reusable pattern for **Idea 25 (citation-aware cards) and Idea 36 (citation management)**.
- `claude_obsidian/lint_engine.py` — vault health checks (Idea 27/39).
- `claude_obsidian/capture.py` — capture → note flow (Idea 40).
- `claude_obsidian/vault_ops.py` — safe vault file ops (Idea 3).
- `claude_obsidian/contracts.py` — response contract validation (guards against hallucination) for Idea 61.
- `skills/wiki-ingest`, `wiki-query`, `wiki-lint`, `wiki-connect` — agent skill definitions.

**26. decodingai-magazine/second-brain-ai-assistant-course** ✅ (check) · `STUDY`
- Production-grade RAG course code (ZenML pipelines + MongoDB + Comet/Opik observability).
- `apps/second-brain-offline/steps/compute_rag_vector_index/chunk_embed_load.py` — chunk → embed → load pipeline (Idea 7/11/12).
- `apps/second-brain-offline/steps/etl/` (crawl.py, add_quality_score.py) — ETL with quality scoring (Idea 5/39).
- `apps/second-brain-offline/steps/generate_dataset/` — eval dataset generation (Idea 26).
- `apps/second-brain-online/` — serving + observability (Idea 100).

**27. tejgor/memora** ✅ MIT (check) · `PORT` (concept)
- NotebookLM alternative: upload notes → Q&A + flashcard generation, grounded in your content.
- `src/RetrievalQA_mod.py` — retrieval QA pipeline (Idea 61).
- `src/el_professor.py`, `src/generatorGPT.py` — quiz/flashcard generation prompts (Idea 33/34/85).
- `src/processing.py` — document processing/chunking (Idea 5/7).
- `src/async_generator.py` — streaming.

**28. karthikkasirajan/studybuddy-ai** ✅ (no license → STUDY) · `INSPIRE`
- `study_buddy.py` — single-file Streamlit app: PDF → quizzes/flashcards/summaries via Groq. Compact reference for Idea 31/33/34 + grading UI.

**29. LeslieLeung/glean** ✅ (check) · `STUDY` + `PORT`
- Self-hosted RSS + PKM with embeddings. Best reference for **Idea 89 (auto-sync external repos) and Idea 12 (vector store client)**.
- `backend/packages/vector/glean_vector/clients/` — `embedding_factory.py`, `providers/openai_provider.py`, `providers/sentence_transformer_provider.py`, `milvus_client.py`, `rate_limiter.py` — pluggable embedding/vector backends (Idea 11/12).
- `backend/packages/rss/glean_rss/` — `parser.py`, `opml.py`, `extractor.py`, `discoverer.py` — RSS ingestion (Idea 89).
- `backend/apps/worker/` — background job worker (Idea 10).

**30. DylanTartarini1996/dyresearch** ✅ MIT (check) · `STUDY`
- Multi-agent study/research (Google ADK + FastAPI + pgvector/lancedb).
- `dyresearch/app/routers/chat.py`, `documents.py` — FastAPI chat/documents endpoints (Idea 61/96).
- `dyresearch/app/settings/config_manager.py` — config (Idea 71).
- Multi-agent note-writing workflows documented in README — reference for **Idea 91 (multi-agent)**.

**31. mohsinkhadim59/youtube-obsidian-mcp** ✅ MIT · `PORT` (concept)
- `server.py` — single-file MCP server: YouTube → structured study notes. Reuse for Idea 89 (lecture capture) + Idea 5.

### Group 3 — Subject Management & Study Planners (13 repos) — Phases 5–6, 7

**32. PixelCode01/syllabo** ✅ MIT · `STUDY` + `PORT`
- "Upload syllabus → complete learning plan" AI companion. The densest Phase 5 reference.
- `src/syllabus/` — syllabus parsing pipeline (Idea 42).
- `src/adaptive_quiz_engine.py` — adaptive difficulty quiz engine (Idea 67).
- `src/difficulty_analyzer.py` — difficulty estimation (Idea 48).
- `src/content_recommender.py` — recommended resources (Idea 59/75/97).
- `src/ai_learning_engine.py` — learning plan generation (Idea 47/51).
- `src/achievement_system.py` — gamification (Idea 69).
- `src/enhanced_video_search.py` — YouTube resource search (Idea 47).
- `src/calendar_sync.py` — calendar integration (Idea 43).
- `src/database.py` — storage.

**33. vxk8058/syllabus-agent** ✅ (no license → STUDY) · `PORT`
- Small and focused: syllabus PDF → topics → study plan + YouTube.
- `utils.py` — `extract_text_from_pdf()`, `extract_topics_from_text()` (Idea 42/44), `find_youtube_videos()` (Idea 47), `build_study_plan(topics_resources, total_minutes)` (Idea 49 time estimation).
- `main.py` — CrewAI orchestration (Idea 91).

**34. SAHIL-creator-Dev/study-planner-agent** ✅ MIT (check) · `STUDY` + `PORT`
- Django + Gemini study planner with real working flows.
- `planner/models.py` — Subject/Syllabus/StudyPlan models (Idea 41/42/51 schema reference).
- `planner/agent.py` — Gemini agent prompt logic (Idea 51).
- `planner/views.py` — `generate_plan()`, `today_focus()` (Idea 59/95), `quiz_me()`/`take_quiz()`/`quiz_result()` (Idea 33/63/66), `mark_complete()` (Idea 54), `ask_agent()`.
- Best end-to-end reference for the "study planner agent" flows we already have partially (`/api/ai/study-plan`).

**35. OPTIMETA/PAIDEIA** ✅ MIT (check) · `STUDY` + `PORT`
- "One subject, one persistent learning graph" Claude plugin — syllabus → topics → graph → wrong-answer tracking → cheat sheet.
- `plugins/paideia/scripts/paideia_lib.py` — core library.
- `plugins/paideia/scripts/vision_ocr.py` — OCR (Idea 6).
- `plugins/paideia/scripts/reindex.py` — re-index tooling (Idea 20).
- `plugins/paideia/scripts/doctor.py` — environment health checks (Idea 27).
- `docs/` — the learning-graph methodology (Idea 46/70): read the docs before designing our `kb_concepts` + `kb_edges`.

**36. shafisma/StudyWise** ✅ MIT · `STUDY` + `INSPIRE`
- Next.js AI study assistant — broad feature surface.
- `src/app/notes/`, `eli5/` (Idea 31/32), `flashcards/` (Idea 34/85), `quiz/` (Idea 33/63), `exam/` (Idea 53/64), `concept-map/` (Idea 38/87), `progress/` (Idea 57), `achievements/` (Idea 69), `history/`.
- `page-client.tsx` pattern — client components per feature. UI/UX reference for our study pages.

**37. KartikLabhshetwar/mind-mentor** ✅ MIT (check) · `STUDY` + `INSPIRE`
- Next.js multi-agent study assistant (tutoring + spaced repetition + PDF analysis + analytics).
- `src/app/(dashboard)/chat/` (Idea 61/62), `pdf/` (Idea 5), `study-plan/` (Idea 51/52), `insights/knowledge-graph/` (Idea 18/46), `insights/` (Idea 57), `timer/` (Idea 60), `settings/reminders/` (Idea 90).
- `mind-mentor-agents/` — the multi-agent layer (Idea 91).
- `server/` — API. Great dashboard UI reference.

**38. ajay160380/ai-tutor (EduAI)** ✅ MIT · `STUDY` + `INSPIRE`
- Django AI tutor (chat, practice, dashboard, syllabus).
- `chat/` (Idea 61/62), `practice/` (Idea 33/63/66), `syllabus/` (Idea 42/45), `dashboard/` (Idea 57), `core/` — the backend service modules.
- `requirements.txt` — useful AI stack list.

**39. ramya0715/Student_Study_Planner** ✅ (no license → STUDY) · `INSPIRE`
- Single-HTML study planner: subjects + exam dates + auto-timetable + daily checklist (localStorage). `script.js` — lightweight timetable generation algorithm reference (Idea 43/51).

**40. mhss1/AIStudyAssistant** ⚠️ GPL-3.0 · `STUDY` only
- Android Kotlin study assistant: chatbot, lecture summarizer, essay writer, question generator. UI patterns only (different platform); GPL blocks porting.

**41. A-R007/Multi-Agent-Study-Assistant** ✅ MIT (check) · `STUDY` + `PORT`
- Multi-agent learning platform — student profiling → roadmap → quizzes → RAG Q&A.
- `study_agents.py` — the agent definitions (Idea 91/47).
- `rag_helper.py` — RAG helper (Idea 61).
- `agent_handler.py`, `prompts.yaml` — agent orchestration + prompts (Idea 91).
- `ARCHITECTURE.md`, `FILE_GUIDE.md` — design docs worth reading.

**42. MansiPatil21/Syllabify** ✅ (no license → STUDY) · `STUDY`
- Full-stack syllabus → schedule (no README). `backend/` + `frontend/` — parse a syllabus PDF into a calendar. Reference for Idea 42/43 pipeline design.

**43. Yuvazyli/StudentAI-Assistant** ✅ (no license → STUDY) · `INSPIRE`
- ML notebooks (`src/`, `notebooks/`) for notes → practice → exam planning. Lightweight algorithms reference.

**44. MarsWang42/OrbitOS** ✅ MIT · `INSPIRE`
- "AI-orchestrated knowledge + task system" — a vault template where AI coordinates knowledge management and daily planning. `EN/` + `CN/` markdown structures: PARALLELS for Idea 35 (daily notes) and Idea 98 (goals & reflection). Borrow the folder/knowledge workflow, not code.
### Group 4 — PKM / Obsidian Ecosystems (11 repos) — Phases 1–4, 8–9

**45. foambubble/foam** ✅ MIT · `STUDY` + `PORT`
- VS Code markdown PKM (wikilinks, backlinks, graph).
- `packages/foam-core/` — core note graph logic: wikilink parsing, backlink inference (Idea 4/17).
- `packages/foam-graph/` — graph viz (Idea 18).
- `packages/foam-mcp/` — MCP server exposing notes (Idea 30/61 context).
- `packages/foam-vscode/` — editor integration.
- The cleanest small reference for **wikilink/backlink mechanics** (Idea 17) without the Obsidian dependency.

**46. dendronhq/dendron** ✅ MIT · `STUDY` (big)
- Hierarchical markdown PKM (maintenance mode).
- `packages/engine-server/` — note engine: lookup, refs, backlinks (Idea 4/17).
- `packages/dendron-viz/` — graph visualization (Idea 18).
- `packages/common-all/` — shared types/constants.
- `packages/dendron-cli/` — CLI ingestion.
- Reference for hierarchical note schemas (hierarchy = auto-categorization basis, Idea 81).

**47. siyuan-note/siyuan** ⚠️ AGPL · `STUDY` only
- The largest local PKM (Go kernel + TS app).
- `kernel/search/` — **production FTS + hybrid search** over blocks (Idea 21/23) — the best FTS5 reference.
- `kernel/sql/` — SQL layer.
- `kernel/api/search.go`, `kernel/model/search.go` — search API/models.
- `kernel/mcp/tools/` — MCP integration.
- `kernel/model/` — block/attribute data model (Idea 1).
- Too big/AGPL to vendor; study the search architecture for Idea 21/23.

**48. algometrix/second_brain_builder** ✅ MIT · `PORT` (concept) + `INSPIRE`
- Obsidian plugin: topic → interlinked deep-dive notes + **mermaid concept maps** + wikilinks, via CLI/Ollama backends.
- `src/main.ts`, `src/cli.ts` — the note-generation driver (Idea 40/47).
- `src/modals/generation.ts`, `analysis.ts`, `system-design.ts` — generation UX (Idea 38/40).
- `src/output-rules.ts` — output formatting rules.
- Mermaid mind-map generation is the direct reference for **Idea 38/87 (mind-map generation)**.

**49. eugeniughelbur/obsidian-second-brain** ✅ MIT · `STUDY` + `PORT`
- "One brain, seven platforms, 46 commands" — huge skill/command library for Obsidian.
- `commands/` — 46 markdown command specs: `obsidian-capture.md` (Idea 40), `obsidian-connect.md` (Idea 76/83), `obsidian-daily.md` (Idea 35), `obsidian-distill.md`, `obsidian-architect.md` (Idea 38), `obsidian-board.md`/`obsidian-board-hygiene.md` (Idea 81), `obsidian-challenge.md` (Idea 98), `notebooklm.md`.
- `adapters/` — cross-CLI adapters (Idea 91).
- `hooks/` — automation hooks (Idea 9/82).
- Read the command specs as a feature checklist for Phases 8–9.

**50. Timeverse/My-Brain-System** ✅ (no license → STUDY) · `INSPIRE`
- Obsidian vault + Claude system: `00_Inbox / 10_Garden / 30_Lab / 99_Archives` — the **PARA-style folder structure** + Claude workflow (Idea 81 auto-categorize basis). `CLAUDE.md` — the system prompt.

**51. ballred/obsidian-claude-pkm** ✅ MIT · `INSPIRE`
- "3-Year Vision → Yearly Goals → Projects → Weekly Review → Daily Tasks" accountability system (markdown only). Direct inspiration for **Idea 98 (goals & reflection)** + Idea 35.

**52. uan-iel/obsidian-museum-desk** ✅ (no license → STUDY) · `INSPIRE`
- Obsidian theme/plugin hybrid: dark "museum desk" dashboard for study/health/mood tracking. UI theme reference.

**53. bevibing/tutor-skills** ✅ MIT · `INSPIRE`
- Claude Code skills: `/tutor-setup` (docs → StudyVault) + `/tutor` (quiz rounds with concept tracking).
- `skills/tutor/references/quiz-rules.md` — quiz rules reference (Idea 33/63).
- `skills/tutor-setup/references/templates.md`, `codebase-templates.md` — note templates (Idea 4/47).

**54. gnekt/My-Brain-Is-Full-Crew** ✅ MIT (check) · `STUDY` + `PORT`
- **8 specialized agents + 14 skills** managing an Obsidian vault — the best multi-agent division-of-labor reference.
- `agents/` — architect.md, connector.md (Idea 83), librarian.md (Idea 22), seeker.md (Idea 22/28), sorter.md (Idea 81/82), scribe.md (Idea 40), postman.md, transcriber.md (Idea 6/89).
- `skills/` — 14 skill defs; `hooks/` — automation triggers; `mcp/` — MCP integration.
- Read the agent prompts — they are the spec for **Idea 91 (multi-agent)** task decomposition.

**55. agenticnotetaking/arscontexta** ✅ MIT · `STUDY`
- "Second brain for your agent" — Claude Code plugin that generates a cognitive architecture (folder structure, pipeline, hooks, nav maps) from conversation. `generators/`, `hooks/`, `methodology/`, `presets/` — interesting for Idea 81/91, mostly meta/plugin content.
### Group 5 — Memory & MCP Servers (8 repos) — Phase 8 Idea 79, Phase 10 Idea 92

**56. Gentleman-Programming/engram** ✅ MIT (check) · `STUDY` + `PORT` (design)
- "Persistent memory for AI coding agents" — single Go binary, SQLite-backed.
- `internal/store/` — the memory store: content-addressed notes + FTS (Idea 8/21/79).
- `internal/obsidian/` — Obsidian vault sync (Idea 3/89).
- `internal/sync/`, `internal/cloud/` — sync layer.
- `internal/llm/` — LLM interface.
- `internal/mcp/` — MCP server.
- `docs/ARCHITECTURE.md` — read before building our `user_memory` (Idea 79) or `ai_logs` (Idea 100).

**57. Dataojitori/nocturne_memory** ✅ MIT · `STUDY` + `PORT`
- Long-term memory server for MCP agents (SQLite/Postgres + graph).
- `backend/db/database.py`, `backend/db/graph.py` — memory + graph storage (Idea 79/92).
- `backend/db/glossary.py` — entity glossary (Idea 15).
- `backend/api/browse.py`, `review.py`, `maintenance.py` — memory review/maintenance endpoints (Idea 92 consolidation).
- `backend/db/migrations/` — schema evolution examples.
- `docs/` — the memory model (episodic memory patterns).

**58. alioshr/memory-bank-mcp** ✅ MIT · `STUDY` (TS architecture)
- Clean TypeScript clean-architecture (usecases/repositories/protocols) MCP server for memory-bank files.
- `src/data/usecases/` (list-projects, read-file, write-file, update-file), `src/domain/entities/` — the layered pattern is a good template for our own services layer. Not core-feature relevant.

**59. Mibayy/token-savior** ✅ MIT (check) · `STUDY`
- MCP server: code navigation + persistent memory + output compaction (97.9% tsbench). `src/` — memory compaction ideas for **Idea 92 (long-term memory) and Idea 100 (observability)**. Mostly coding-agent focused.

**60. DeusData/codebase-memory-mcp** ✅ MIT · `STUDY` (C)
- Pure-C code intelligence engine (LSP index, 1.4 GB clone). Not related to our student domain — skim only. No reusable components for the phases.

**61. agentset-ai/agentset** ✅ MIT (check) · `STUDY`
- "RAG optimized for max performance" (TypeScript monorepo: apps, packages, 45 SQL files). `docs/` — RAG performance patterns for **Idea 93 (RAG hardening)**. Reference only.

**62. ghostwright/phantom** ✅ Apache-2.0 · `STUDY`
- AI coworker platform (TypeScript). `prompts/`, `skills-builtin/`, `config/`, `chat-ui/` — agent orchestration + chat UI reference for **Idea 91 (multi-agent)**.

**63. moltis-org/moltis** ✅ (check) · `STUDY`
- AI-native issue tracking in Rust. Not student-domain related — skim only.
### Group 6 — Gamification & Habit Trackers (4 repos) — Idea 69, gamified UX

**64. 4RGUS/habit_quest** ✅ MIT · `PORT` + `INSPIRE`
- React gamified habit tracker: XP, 6-tier levels (Seedling→Ancient Oak), badges, streaks, 60-day calendar heatmap.
- `src/lib/db.js`, `src/hooks/useHabits.js` — habit + XP data logic (Idea 69).
- `src/components/CalendarView.jsx` — **calendar heatmap component** (reusable for Idea 57 progress viz + heatmap-style vault dashboards).
- `src/components/LevelPanel.jsx`, `HabitCard.jsx`, `HabitModal.jsx` — gamified habit UI.
- `src/lib/AuthContext.jsx` — Google auth (reference only).

**65. dohsimpson/HabitTrove** ✅ MIT · `STUDY` + `INSPIRE`
- Next.js gamified habits: coins → rewards (with TaskTrove sibling).
- `app/actions/data.ts` — coins/habits/wishlist data actions (Idea 69 reward economy).
- `app/calendar/page.tsx`, `app/coins/page.tsx`, `app/habits/page.tsx` — UI.
- `app/actions/push.ts`, `app/api/user/delete/route.ts` — data safety patterns.
- Coin-reward economy is a nice alternative to pure XP (Idea 69).

**66. hussaino03/QuestLog** ✅ MIT · `STUDY` + `PORT`
- Full MERN gamified productivity: XP, achievements, leaderboard, AI insights, collaboration.
- `server/controllers/ai/ai.controller.js` — **AI insights controller with response caching (NodeCache) + daily stat reset + user-stat-context prompts** — the best reference for **Idea 95 (context-aware responses) and Idea 29 (search/insight feedback)**.
- `server/controllers/analytics/analytics.controller.js` — analytics (Idea 57/99).
- `server/controllers/leaderboard/`, `collaboration/` — gamified social (Idea 69).
- `server/middleware/ai-rate-limit.js` — AI rate limiting (Idea 100 budget guard).
- `client/` — React UI.

**67. Karthik998byte/Habit-Quest** ✅ (no license → STUDY) · `INSPIRE`
- Flask + SQLite gamified habits (XP/streaks/levels/leaderboard) in ~1 file + HTML. `app.py` + `habit_quest.db` — minimal schema reference (Idea 69).
### Group 7 — Miscellaneous (1 repo)

**68. noodle-run/noodle** ✅ MIT · `INSPIRE`
- "Rethinking student productivity" — the closest existing Student-OS-style product (Next.js + Drizzle, in-progress).
- `src/app/(dashboard)/app/_components/module-card.tsx`, `create-module-popover.tsx`, `recent-modules.tsx`, `side-menu.tsx` — student dashboard UI reference.
- `drizzle/` — DB schema (modules/tasks) for inspiration on our own tables.
- Warning: mostly a design mockup (README states UI is aspirational) — use for UX inspiration only.

---

## License & Reuse Rules

- **✅ Safe to PORT** (permissive): khoj (AGPL ⚠️ — actually AGPL!), anki (AGPL ⚠️), basic-memory (AGPL ⚠️), siyuan (AGPL ⚠️), orbit (BUSL+Apache ⚠️) — **all the big PKM engines are AGPL; use them as STUDY references, never vendor code into a closed app.**
- **MIT/Apache/BSD (PORT-friendly):** py-fsrs, ts-fsrs, fsrs-rs, fsrs4anki, awesome-fsrs, free-spaced-repetition-scheduler, obsidian-spaced-repetition, infinition, LearnKit (see its LICENSE.md), org-fc, hashcards, recalla, memo, mimocard, yt-flashcard-ai, habit_quest, HabitTrove, QuestLog, engram, glean, llm_wiki, reor (AGPL ⚠️ — check), claude-obsidian (MIT), obsidian-wiki, syllabo, StudyWise, mind-mentor, PAIDEIA, study-planner-agent, syllabus-agent, memora, dyresearch, noodle, OrbitOS, My-Brain-Is-Full-Crew, second_brain_builder, memory-bank-mcp, nocturne_memory, token-savior, eduai (MIT), multi-agent-study-assistant, ai-tutor, recalla
- **⚠️ Copyleft — STUDY only:** khoj (AGPL), anki (AGPL), basic-memory (AGPL), siyuan (AGPL), reor (AGPL), orbit (BUSL-1.1 + AGPL), dendron, foam (MIT ✅)
- **🔍 No license file** (treat as all-rights-reserved, STUDY only): ai-tutor(eduai has MIT badge), StudentAI-Assistant, Student_Study_Planner, Syllabify, mimocard, Habit-Quest, studybuddy-ai, codebase-memory-mcp (MIT ✅), moltis (LICENSE.md — check), Phantom (Apache 2.0 ✅), arscontexta (MIT ✅)
