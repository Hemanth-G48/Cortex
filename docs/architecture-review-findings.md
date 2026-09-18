# Architecture Review — Cortex Productivity App

**Scope**: Full codebase (backend + frontend)
**Date**: 2026-09-11
**Reviewer**: review-architecture skill (ai-cortex)
**Source**: graphify graph (9,758 nodes, 26,010 edges) + direct file inspection

---

## Remediation Status (2026-09-13)

| # | Finding | Status | What was done |
|---|---|---|---|
| F1 | KbDocument god object | **Accepted by design** | Facet groups documented in `models/kb/document.py` module docstring (identity / content / metadata / processing-state / versioning-dedupe). Schema split rejected: no alembic, SQLite + `create_all` only, and 225+ importers depend on the flat surface. Revisit if a migration tool is adopted. |
| F2 | services/kb flat 70-file dir | **Partially done — deferred** | `metadata/` sub-package extracted (core.py, frontmatter.py) as the template. Full reorg (core/pipeline/learning/automation/retrieval/metadata/shared) deferred by owner decision 2026-09-13 to avoid conflicting with concurrent in-flight work in `services/kb/`. Layout below is the approved target — apply incrementally, one group per feature touch. |
| F3 | routers/kb_* 1:1 mirror | **Deferred (low)** | Pattern is idiomatic FastAPI; router `__init__.py` now uses PEP 562 lazy imports (audit F2) so the imports block is no longer a sync burden. Merging kb_graph/kb_edges remains optional cleanup. |
| F4 | course monoliths | **Fixed** | Frontmatter parsing → `services/kb/metadata/frontmatter.py` (pure functions). Topic tree + document resolution → `services/course_content_topics.py` with shared `resolve_course_document_ids()`; `course_documents()` and `course_document_count()` no longer duplicate the 3-path resolution. `course_content.py` is a 210-line aggregate. |
| F5 | pipeline.py inline feature calls | **Fixed** | Event-driven post-ingest hook registry: `register_post_ingest()` + `run_post_ingest_hooks()` in `pipeline.py`; daily-note tag, citation parse, and quality recompute self-register via idempotent `register_hook_once()` in their own modules. Fixed the duplicated `run_post_ingest_hooks` / `tag_daily_note` definitions that shadowed the registry (hooks never ran; registration duplicated on every call). |
| F6 | No domain layer | **Accepted as-is** | Per the review itself: defensible at current scale. Revisit when KB subsystem rules scatter further. |
| F7 | Frontend flat pages dir | **Deferred (low)** | 65 page components; grouping (kb/, courses/, rpg/, habits/) deferred with F2's backend reorg so both land together. |
| F8 | api.ts 3000+ line monolith | **Fixed** | True barrel: `services/api.ts` is now 43 lines re-exporting from `services/api/core.ts`, `api/types/` (27 domain modules, 3294 lines of types), and `api/endpoints/` (profile, upload, kb, index, book, task). All 92 legacy `import ... from '../services/api'` call sites unchanged. |
| F9 | No boundary enforcement | **Fixed** | `[tool.importlinter]` contracts in v2 `forbidden` schema (original config used a nonexistent `boundaries` schema — parsed as 0 contracts). Run from `backend/`: `lint-imports --config ../pyproject.toml` → **4 kept, 0 broken**. |

**Verification (2026-09-13, final)**: backend 1612 passed / 1 skipped (sleep — pre-existing intentional skip); frontend vitest 164 passed / 39 files; `tsc -b` fully clean (0 errors — the earlier Dashboard.tsx / KnowledgeBase.tsx / MiniTodoList.tsx errors from in-flight edits were resolved); `lint-imports` 4 contracts kept, 0 broken.

**Incidental fixes during remediation**:
- `routers/__init__.py` + `main.py`: the lazy-import refactor imported `app.routers.global_search`, which does not exist (the module is `search.py`) — the app did not boot and pytest collection failed. Fixed with an alias registry (`_ALIASES = {"global_search": "search"}`).
- `MiniTodoList.tsx` (`taskmanager/`): type-narrowing error on `task.id: number | string` inside a Set-callback closure — narrowed to a local `const { id }` binding.
- `settings.test.tsx`: stale mock — added `profileApi.getPrefs`/`updatePrefs` mocks and updated the model-dropdown test for the new staged-save UX (select stages a draft; Save persists via `updatePrefs`).

**Deferred-work contract (F2/F7)**: when moving a `services/kb/<mod>.py` into a sub-package, leave a one-line shim (`from app.services.kb.<group>.<mod> import *  # moved (F2)`) so the 180+ `app.services.kb` import sites keep working; delete shims only after all importers are migrated.

---

## Findings

### F1 — KbDocument is a god object spanning 3 layers

| | |
|---|---|
| **Location** | `backend/app/models/kb/document.py:24` |
| **Category** | cognitive-architecture |
| **Severity** | high |
| **Title** | KbDocument is imported by 225+ service files, 40+ routers, and 20+ test modules — it has become the de facto hub of the entire KB subsystem |

**Description**:
`KbDocument` (a single SQLAlchemy model, ~100 lines) is the most-imported symbol in the backend. Graph analysis confirms it bridges 78 of 362 communities. Every KB service imports it directly: `graph.py`, `connect.py`, `scanner.py`, `pipeline.py`, `embedder.py`, `tagger.py`, `concepts.py`, `gap_engine.py`, `course_derivation.py`, `course_content.py`, `reindex.py`, `auto_sync.py`, and 30+ more.

This violates single responsibility at the module-coupling level. `KbDocument` carries:
- Raw content fields (`extracted_text`, `frontmatter_json`, `metadata_json`, `outline_json`)
- Pipeline orchestration flags (`embedding_dirty`, `graph_dirty`, `tags_dirty`, `summary_dirty`)
- Quality scoring state (`quality_score`, `quality_detail`)
- Source/organization identity (`source_id`, `path_rel`, `file_path`, `doc_type`)
- Versioning relationship (`versions`)
- Dedup identity (`content_hash` unique index)

That's at least 5 distinct responsibilities stuffed into one model. When a change to quality scoring logic ripples through the graph builder, the course derivation, and the gap engine simultaneously, you're paying a coupling tax across the entire subsystem.

**Suggestion**: Split `KbDocument` into a thin identity/ownership core (id, user_id, source_id, path, status, timestamps) and move domain-specific concerns into separate aggregates:
- `DocumentContent` — extracted_text, char_count, ocr flags, content_hash
- `DocumentMetadata` — frontmatter_json, outline_json, metadata_json, author, language, reading_time
- `DocumentProcessingState` — the dirty flags, indexed_at, quality_score
- Keep `KbDocument` as the aggregate root that owns these by composition, not by column inflation.

Alternatively, accept the god model but enforce it intentionally: add a `kb_document/` package with feature-specific facets that import the model but never let two facets import each other.

---

### F2 — services/kb/ is a flat 70-file directory with no internal boundaries

| | |
|---|---|
| **Location** | `backend/app/services/kb/` (70 modules, one flat directory) |
| **Category** | cognitive-architecture |
| **Severity** | medium |
| **Title** | The KB service layer has no sub-package structure — all 70 modules sit at the same level |

**Description**:
`backend/app/services/kb/` contains 70 modules with no subdirectory organization: `graph.py`, `connect.py`, `gap_engine.py`, `book_gaps.py`, `course_derivation.py`, `course_content.py`, `automation.py`, `agents.py`, `budget.py`, `mastery.py`, `memory.py`, `tutor.py`, `rag.py`, `search.py`, `flashcards.py`, `revision.py`, `roadmap.py`, `adapt.py`, `plans.py`, `next_action.py`, `topics.py`, `dependencies.py`, `suggestions.py`, `recommendations.py`, `reflections.py`, `weekly_review.py`, `daily_notes.py`, `braindump_draft.py`, `triage.py`, `auto_subject_detect.py`, `auto_tag.py`, `auto_link.py`, `auto_categorize.py`, `auto_flashcards.py`, `auto_summary.py`, `auto_mindmap.py`, `auto_duplicates.py`, `auto_revision.py`, `auto_plan_sync.py`, `auto_sync.py`, `course_sync.py`, `embeddings.py`, `reindex.py`, `migrate.py`, `scanner.py`, `pipeline.py`, `ocr.py`, `chunker.py`, `markdown_parser.py`, `text_extractor.py`, `embedder.py`, `fusion.py`, `fts.py`, `search.py`, `context.py`, `preferences.py`, `skills.py`, `syllabus.py`, `subjects.py`, `units.py`, `grading.py`, `questions.py`, `interview.py`, `mocks.py`, `mistakes.py`, `sessions.py`, `adaptive.py`, `tutor.py`, `memory.py`, `memory_longterm.py`, `capt
ure_xp.py`, `budget.py`, `mastery.py`, `dependencies.py`, `gap_domains.py`, `gap_history.py`, `health.py`, `health_audit.py`, `outdated.py`, `quality.py`, `related.py`, `summarize.py`, `citations.py`, `citation_registry.py`, `concepts.py`, `graph.py`, `connect.py`, `mindmap.py`, `sync.py`

There is no subdirectory structure reflecting functional boundaries. A new developer cannot tell at a glance which modules are:
- **Core graph/ontology** (graph, connect, concepts, edge)
- **Content processing pipeline** (scanner, pipeline, embedder, chunker, ocr, markdown_parser, text_extractor)
- **Learning operations** (gap_engine, book_gaps, mastery, revision, flashcards, tutor, adaptive, interview, grading, questions, sessions, mistakes, explain)
- **Automation/jobs** (automation, jobs, auto_*, watcher)
- **Search & retrieval** (search, fusion, rag, fts)
- **Organization/metadata** (tagger, domain_service, subjects, topics, dependencies, syllabus, preferences, context, skills)

The graph confirms this: the flat structure means import relationships are dense and indiscriminate. `budget.py` (a 50-line rate-limiter) is imported by 30+ modules — it's the most-cross-cutting service dependency after `KbDocument` itself.

**Suggestion**: Reorganize into sub-packages:

```
backend/app/services/kb/
  __init__.py          # re-exports only the public API
  core/               # graph, connect, concepts, edge, domain_service
  pipeline/           # scanner, pipeline, embedder, chunker, ocr, text_extractor, markdown_parser
  learning/           # gap_engine, book_gaps, mastery, revision, tutor, adaptive, interview, grading, questions, sessions, mistakes, explain, flashcards
  automation/         # automation, jobs, all auto_*, watcher, triage
  retrieval/          # search, fusion, rag, fts, reindex
  metadata/           # tagger, subjects, topics, dependencies, syllabus, preferences, context, skills, citations, citation_registry
  shared/             # budget, utcnow, KbService base, corpus helpers
```

This makes the dependency graph readable and makes it possible to enforce layer boundaries with import-linter or a simple CI check.

---

### F3 — routers/kb_* duplication: router modules mirror service modules 1:1 with thin wrappers

| | |
|---|---|
| **Location** | `backend/app/routers/` (60+ kb_*.py files) |
| **Category** | cognitive-architecture |
| **Severity** | low |
| **Title** | Router modules are a 1:1 mirror of service modules, creating a maintenance surface with no additive value |

**Description**:
`routers/kb_documents.py` ↔ `services/kb/pipeline.py` + `services/kb/scanner.py`
`routers/kb_graph.py` ↔ `services/kb/graph.py`
`routers/kb_edges.py` ↔ `services/kb/graph.py` (same service, two routers)
`routers/kb_concepts.py` ↔ `services/kb/concepts.py`
`routers/kb_tags.py` ↔ `services/kb/tagger.py`
`routers/kb_search.py` ↔ `services/kb/search.py`
`routers/kb_mindmap.py` ↔ `services/kb/mindmap.py`
`routers/kb_quality.py` ↔ `services/kb/quality.py`
`routers/kb_reindex.py` ↔ `services/kb/reindex.py`
`routers/kb_duplicates.py` ↔ `services/kb/neardup.py`
`routers/kb_related.py` ↔ `services/kb/related.py`
`routers/kb_citations.py` ↔ `services/kb/citation_registry.py`
`routers/kb_subjects.py` ↔ `services/kb/subjects.py`
`routers/kb_study.py` ↔ `services/kb/mastery.py`
`routers/kb_tutor.py` ↔ `services/kb/tutor.py`
`routers/kb_papers.py` ↔ `services/kb/pipeline.py`
`routers/kb_daily_notes.py` ↔ `services/kb/daily_notes.py`
`routers/kb_personal.py` ↔ `services/kb/` (multiple)
`routers/kb_automation.py` ↔ `services/kb/automation.py`

There are 40+ kb_* router files, each one typically 15-50 lines of FastAPI route wiring that delegates to a single service module. This is a legitimate pattern when the router adds meaningful API composition (auth, validation, response shaping). Here, most routers do exactly one thing: accept a request, call one service function, return the result. The router layer adds almost no composition.

The problem: when you add a new KB feature, you now touch **two** files (service + router), and the router `__init__.py` has a 100-line imports block with phase-comment annotations that must be kept in sync. The router `__init__.py` also uses conditional imports (Phase comments) which creates a latent dependency-ordering constraint.

**Suggestion**: Consolidate. Two options:

**Option A (radical)**: Put FastAPI route definitions directly in the service modules using `APIRouter` instances, and have a single `routers/kb.py` that includes them all:
```python
# routers/kb.py
from app.services.kb import documents, graph, edges, concepts  # each exports its own router
router = APIRouter(prefix="/api/kb", tags=["kb"])
router.include_router(documents.router)
router.include_router(graph.router)
# ...
```

**Option B (moderate)**: Keep routers but group related ones — e.g. `routers/kb_documents.py` handles upload/list/chunks/versions (already does), but `routers/kb_graph.py` + `routers/kb_edges.py` could merge since they share the same service and model surface.

---

### F4 — course_derivation.py and course_content.py are 3000+ line monoliths

| | |
|---|---|
| **Location** | `backend/app/services/course_derivation.py` (396+ functions, ~1500 lines), `backend/app/services/course_content.py` (~800 lines) |
| **Category** | cognitive-architecture |
| **Severity** | medium |
| **Title** | Two service modules have grown into monoliths that mix derivation, sync, metadata parsing, folder logic, and content assembly |

**Description**:

**`course_derivation.py`** does too much:
- Tag→course derivation (`derive_courses_from_tags`, ~80 lines)
- Folder→course derivation (`_derive_courses_from_folders`, ~100 lines)
- Folder metadata parsing (`_folder_index_frontmatter`, `_folder_metadata`, `_normalize_status`, `_normalize_color`, `_meta_description` — ~100 lines of frontmatter parsing)
- Course sync status (`course_sync_status`, ~30 lines)
- Resource listing (`list_course_resources`, ~25 lines)
- Sync log persistence (`_write_sync_log`, ~20 lines)
- Helper utilities (`_folder_key`, `_folder_title`, `_like_escape`, `_course_for_tag`, `_course_for_folder`, `_delete_courses`, `_tag_doc_count`)

The frontmatter parsing helpers (`_STATUS_MAP`, `_NAMED_COLORS`, `_DESCRIPTION_KEYS`, `_STATUS_KEYS`, `_COLOR_KEYS`, `_normalize_status`, `_normalize_color`) are pure functions that have nothing to do with course derivation — they're a generic frontmatter normalization library trapped inside a course-specific module.

**`course_content.py`** does too much:
- Document resolution (3 resolution paths: folder, tag, legacy fuzzy tag-name match) — duplicated between `course_documents` and `course_document_count`
- Topic tree building (`build_topic_tree`, `_foldered_outline`, `_folder_segments`, `_normalize_heading`, `_sort` — ~200 lines)
- Concept aggregation (`course_concepts`, ~40 lines)
- Graph scoping (`course_graph`, ~15 lines)
- Gap analysis orchestration (`course_gaps`, ~80 lines — this function delegates to `gap_engine.analyze_subject` but also computes topic coverage gaps, concept gaps, and assembles the legacy + new gap payload)
- Content assembly (`course_content`, ~50 lines)
- Duplicate document-resolution logic (`_course_folder_data` appears in both this file and `course_derivation.py`)

The duplication between `course_documents()` and `course_document_count()` is the clearest smell: they have the same 3-path resolution logic, one returns payloads and the other returns a count. They should share a single `resolve_course_document_ids()` function.

**Suggestion**:

1. Extract frontmatter parsing from `course_derivation.py` into a generic `backend/app/services/kb/metadata/frontmatter.py`:
   ```python
   # frontmatter.py
   def normalize_status(value) -> str
   def normalize_color(value) -> str | None
   def extract_description(meta, keys) -> str | None
   ```

2. Extract the course document resolution logic into a shared helper:
   ```python
   # course_resolution.py
   def resolve_course_document_ids(db, user_id, course) -> set[int]
   def resolve_course_folder_roots(db, user_id, course_title) -> tuple[list[str], set[int]]
   ```

3. Split `course_content.py`:
   - `course_content/topics.py` — `build_topic_tree` and helpers
   - `course_content/gaps.py` — `course_gaps` orchestration
   - `course_content/content.py` — `course_content` aggregate + document resolution

4. Split `course_derivation.py`:
   - `course_derivation/tag.py` — tag→course
   - `course_derivation/folder.py` — folder→course
   - `course_derivation/sync.py` — sync status + log + resources

---

### F5 — pipeline.py is a 300+ line ingestion monolith with inline feature calls

| | |
|---|---|
| **Location** | `backend/app/services/kb/pipeline.py` |
| **Category** | cognitive-architecture |
| **Severity** | medium |
| **Title** | The ingest pipeline function `ingest_document()` calls 8+ downstream services inline, making it a hidden orchestrator |

**Description**:
`pipeline.py:ingest_document()` (the core ingestion function called by `kb_documents.py`, `jobs.py`, `scanner.py`, `auto_sync.py`, `braindump_draft.py`) inline-calls:
- `re_chunk()` (line 253)
- `tag_daily_note()` from `daily_notes` (line 253)
- `award_capture_xp()` from `capture_xp` (line 258)
- `extract_for_document()` from `citation_registry` (line 269)
- `recompute_for_document()` from `quality` (line 277)

These are lazy imports (inside the function body), which mitigates the import-time coupling, but the pipeline function is still an orchestrator that knows about 5 downstream features. When you add a new post-ingest feature (e.g. "auto-generate flashcards on ingest"), the natural place to add it is inside `ingest_document()` — which makes the function grow unbounded.

The graph confirms this: `pipeline.py` has edges to `daily_notes.py`, `capture_xp.py`, `citation_registry.py`, `quality.py`, `re_chunk` (itself in pipeline.py).

**Suggestion**: Make ingestion event-driven. Replace the inline calls with a post-ingest hook system:

```python
# services/kb/pipeline.py
POST_INGEST_HOOKS = []

def register_post_ingest(hook):
    POST_INGEST_HOOKS.append(hook)

def ingest_document(db, doc, ...):
    # ... extract, chunk, etc ...
    for hook in POST_INGEST_HOOKS:
        hook(db, doc)
```

Then each feature registers itself:
```python
# services/kb/citations/__init__.py
from app.services.kb.pipeline import register_post_ingest
register_post_ingest(extract_for_document)
```

This keeps `pipeline.py` stable and lets features opt into the ingestion lifecycle without modifying the pipeline code.

---

### F6 — No domain layer: business logic lives in services, models are pure SQLAlchemy

| | |
|---|---|
| **Location** | `backend/app/services/` (all business logic) + `backend/app/models/` (pure ORM) |
| **Category** | cognitive-architecture |
| **Severity** | medium |
| **Title** | The codebase has no domain layer — business rules live in service functions, not in domain objects |

**Description**:
The architecture is currently: **routers → services → models** (ORM).

There is no domain layer between services and models. Business rules are expressed as service functions:
- `add_edge()` in `graph.py` knows the edge dedup key, relation vocab, weight threshold, and upsert logic
- `connect_suggestions()` in `connect.py` knows the strong/weak relation thresholds (STRONG_SHARED=2, MIN_SHARED=1)
- `build_topic_tree()` in `course_content.py` knows the heading merge rules and folder-breadcrumb logic
- `_classify()` in `book_gaps.py` knows the KNOWN/PARTIAL/UNKNOWN classification rules and historical-term detection

These are domain rules expressed as function logic rather than as domain object behavior. The benefit of this approach is simplicity — it works, it's testable, it's straightforward. The cost is that as the system grows, the domain rules become scattered across 70 service modules with no single place to look for "how does the KB model learning?".

For a project at this scale (single-user app, 1-2 developers), this is a defensible choice. The risk is that `services/kb/` becomes the place where every rule accumulates, and the lack of a domain layer makes it harder to reason about invariants.

**Suggestion**: This is acceptable as-is for the current scale. If the KB subsystem continues growing, introduce a thin domain layer **only for the core KB aggregate**:

```
backend/app/domain/kb/
  document.py       # KbDocument domain object (not ORM) with invariants
  concept.py        # KbConcept domain object
  edge.py           # KbEdge domain rules (relation vocab, weight semantics)
  learning_state.py # mastery classification, gap classification
```

The service layer would then translate: router → service → domain object → ORM model. Don't do this prematurely — wait until you feel the pain of scattered rules.

---

### F7 — Frontend has 70+ page components with no apparent feature grouping

| | |
|---|---|
| **Location** | `frontend/src/pages/` (70+ .tsx files, flat) |
| **Category** | cognitive-architecture |
| **Severity** | low |
| **Title** | 70+ page components in a flat directory with no feature-based grouping |

**Description**:
`frontend/src/pages/` contains 70+ components in a flat directory:
`Dashboard.tsx`, `KnowledgeBase.tsx`, `KnowledgeGraph.tsx`, `Courses.tsx`, `CourseDetail.tsx`, `Subjects.tsx`, `SubjectWorkspace.tsx`, `GapAnalysis.tsx`, `BookGapReader.tsx`, `Today.tsx`, `WeeklyReview.tsx`, `LearningPlanner.tsx`, `DomainDetail.tsx`, `Notes.tsx`, `Flashcards.tsx`, `FlashcardReview.tsx`, `Quiz.tsx`, `Practice.tsx`, `Tutor.tsx`, `Mocks.tsx`, `Interview.tsx`, `Skills.tsx`, `Leaderboard.tsx`, `Assignments.tsx`, `Grades.tsx`, `StudyPlans.tsx`, `SyllabusImport.tsx`, `Settings.tsx`, `Admin.tsx`, `Missions.tsx`, `Rewards.tsx`, `Quests.tsx`, `QuestCentreDashboard.tsx`, `RPGDashboard.tsx`, `Character.tsx`, `HabitTracker.tsx`, `HabitReport.tsx`, `ArchiveHabits.tsx`, `HabitLogs.tsx`, `GamifiedHabitTracker.tsx`, `Goals.tsx`, `GoalsSetting.tsx`, `LifePlannerDashboard.tsx`, `LifeAreas.tsx`, `Tasks.tsx`, `Projects.tsx`, `Schedule.tsx`, `Calendar.tsx`, `Journal.tsx`, `Reading.tsx`, `Pomodoro.tsx`, `Fitness.tsx`, `FitnessHubDashboard.tsx`, `VaultDashboard.tsx`, `VaultDatabase.tsx`, `VaultSearch.tsx`, `KbInsights.tsx`, `Browse.tsx`, `Exams.tsx`, `Workflows.tsx`, `Analytics.tsx`, `DomainDetail.tsx`, ...

There's no grouping by feature area. A KB feature might span `KnowledgeBase.tsx`, `KnowledgeGraph.tsx`, `KbInsights.tsx`, `KbSearch.tsx`, `BookGapReader.tsx`, `GapAnalysis.tsx`, `Flashcards.tsx`, `Quiz.tsx`, `Practice.tsx`, `Tutor.tsx`, `Mocks.tsx`, `Interview.tsx` — and they're scattered alphabetically across the directory.

The frontend components directory is similarly flat (`frontend/src/components/`), though at least there are some subdirectories (`components/rpg/`, `components/settings/`, `components/taskmanager/`, `components/shared/`, `components/layout/`).

**Suggestion**: Group pages by feature area:

```
frontend/src/pages/
  kb/                  # Knowledge Base feature
    KnowledgeBase.tsx
    KnowledgeGraph.tsx
    KbInsights.tsx
    BookGapReader.tsx
    GapAnalysis.tsx
    Flashcards.tsx
    ...
  courses/             # Courses/Subjects feature
    Courses.tsx
    CourseDetail.tsx
    Subjects.tsx
    ...
  rpg/                 # Gamification (some already in components/rpg/)
    RPGDashboard.tsx
    Quests.tsx
    ...
  habits/              # Habits feature
    HabitTracker.tsx
    ...
```

This mirrors the backend service sub-package suggestion (F2) and makes it easier to reason about feature boundaries.

---

### F8 — frontend/src/services/api.ts is a 3000+ line API client monolith

| | |
|---|---|
| **Location** | `frontend/src/services/api.ts` (2908+ lines per graph analysis) |
| **Category** | cognitive-architecture |
| **Severity** | medium |
| **Title** | The API client is a single 3000+ line file containing every endpoint call |

**Description**:
`api.ts` at 2908+ lines is the frontend's equivalent of the backend's service monoliths. It contains every API call the frontend makes — KB endpoints, course endpoints, habit endpoints, RPG endpoints, auth, uploads, search, analytics, etc.

The graph shows `api.ts` as a high-degree node reaching into many communities (it's in Community 0 and Community 3 per the graph analysis). Every page component that makes an API call depends on this file.

This is a common pattern in small-to-medium React apps (a single api.ts with axios/fetch wrappers), but at 3000+ lines it becomes hard to navigate, hard to split, and a merge-conflict hotspot when multiple features add endpoints simultaneously.

**Suggestion**:
1. Split by feature:
   ```
   frontend/src/services/api/
     index.ts          # re-exports
     kb.ts            # all /api/kb/* calls
     courses.ts       # all /api/courses/* calls
     habits.ts        # all habit endpoints
     rpg.ts           # quests, missions, rewards, characters
     auth.ts          # login, logout, profile
     uploads.ts       # file upload
     search.ts        # search endpoints
   ```

2. Use a small wrapper so existing call sites don't need to change:
   ```ts
   // api/index.ts
   export { getDocuments, uploadDocument } from './kb'
   export { getCourses } from './courses'
   // ... etc
   ```

---

### F9 — import-linter or boundary enforcement is absent

| | |
|---|---|
| **Location** | Project-wide (no tool configuration found) |
| **Category** | cognitive-architecture |
| **Severity** | low |
| **Title** | There is no automated enforcement of architectural boundaries |

**Description**:
The codebase currently relies on convention alone to maintain boundaries. There is no evidence of:
- `import-linter` configuration
- `layer-linter` or similar
- pylint/private-naming conventions to enforce `_` prefixed internal functions
- CI checks that prevent services from importing routers (currently OK, but not enforced)
- CI checks that prevent models from importing services (currently OK, but not enforced)

The good news: the current dependency direction is healthy:
- models ← services ← routers (correct)
- frontend components ← frontend services (correct)
- No reverse imports detected in the scan

The risk: without enforcement, the next developer (or future you) can silently introduce a reverse dependency. `services/kb/` already has 141 internal cross-imports — it's easy for one more to go the wrong direction.

**Suggestion**: Add lightweight boundary enforcement:

```ini
# pyproject.toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.boundaries]]
name = "models-must-not-import-services"
from = "app.models"
to = "app.services"
kind = "cannot-use"

[[tool.importlinter.boundaries]]
name = "models-must-not-import-routers"
from = "app.models"
to = "app.routers"
kind = "cannot-use"

[[tool.importlinter.boundaries]]
name = "routers-should-not-import-other-routers"
from = "app.routers"
to = "app.routers"
kind = "may-not-use"  # or cannot-use, depending on preference

[[tool.importlinter.boundaries]]
name = "kb-services-can-import-other-kb-services"
from = "app.services.kb"
to = "app.services.kb"
kind = "may-use"
```

Run `import-linter` in CI. Start strict and relax as needed.

---

## Summary

| # | Severity | Title |
|---|---|---|
| F1 | high | KbDocument is a god object spanning 3 layers |
| F2 | medium | services/kb/ is a flat 70-file directory with no internal boundaries |
| F3 | low | routers/kb_* duplication: router modules mirror service modules 1:1 |
| F4 | medium | course_derivation.py and course_content.py are 3000+ line monoliths |
| F5 | medium | pipeline.py is a 300+ line ingestion monolith with inline feature calls |
| F6 | medium | No domain layer: business logic lives in services, models are pure SQLAlchemy |
| F7 | low | Frontend has 70+ page components with no feature grouping |
| F8 | medium | frontend/src/services/api.ts is a 3000+ line API client monolith |
| F9 | low | No automated boundary enforcement |

**Overall assessment**: The architecture is coherent for a single-developer fullstack app. Dependency direction is healthy (models ← services ← routers, frontend components ← services). The primary risks are scale-driven: as the KB subsystem grows from "functional" to "large", the flat service directory (F2), the god model (F1), and the pipeline orchestrator (F5) will become harder to navigate. The suggestions above are incremental — none require a rewrite, all can be done piecemeal as part of regular feature work.
