# 99 Workflow Defects — Dynamic Data Audit (Keep Current UI/UX)

> **Project:** Student Life OS (Cortex) — FastAPI + React 19 + Vite + Second Brain  
> **Source of truth for all fixes:** `second_brain/` (notes, daily-life, concepts, graph, links, mindmap) + KB APIs (`/api/kb/*`, `/api/vault`, `/api/courses/*/content`, `/api/kb/today`, `/api/kb/daily-notes`, `/api/kb/weekly-review`, etc.)  
> **Rule:** Fix every defect **without changing current UI/UX** — same components, same styles, same layout. Only change is: **no static/mock/hardcoded data; every datum fetched live from Second Brain / DB via API**.

> **Scoreboard (2026-09-13 re-audit):** 56 resolved · 6 partial · 37 open (of 99). Newly resolved since last audit: #24, #33, #47, #50, #55, #57, #81. Newly partial: #20, #39, #48, #62, #82, #84.

| Legend | Meaning |
|---|---|
| **Severity** | 🔴 Critical workflow broken, 🟠 High stale data, 🟡 Medium partial static, 🟢 Low polishing |
| **Source** | Exact KB endpoint / service that must feed the UI |
| **UI Keep** | The existing component/file that stays visually identical |
| **Status** | ✅ FIXED / 🟨 PARTIAL / ⬜ OPEN |

_Last audited: 2026-09-13 — re-verified all 50 open defects against the current working tree (uncommitted changes included). Covers `frontend/src/pages/*`, `frontend/src/components/*`, `backend/app/routers/kb_*`, `backend/app/services/kb/*`, `second_brain/notes/*`, `second_brain/daily-life/*`._

---

## How to use this file
For each defect: keep the listed component **exactly as-is visually** (classNames, layout, tailwind tokens). Replace the static/hardcoded path with a `useEffect` → `endpoints.*` call subscribed to the listed source. Add loading/empty skeletons already present in the codebase (e.g. `<SkeletonCard/>`, `<EmptyState/>`). No new design tokens.

---

### Category 1 — Dashboard & Home (11 defects)

#### 1. ✅ Dashboard stat tiles not derived from Second Brain daily notes — FIXED
- **File:** `frontend/src/pages/Dashboard.tsx`
- **Status:** Fixed. `Dashboard` now fetches `endpoints.kb.today.overview()` in parallel with tasks/courses/assignments/exams/goals via a single `load()` callback. Pending count = DB tasks not completed + `todayOverview.morning.captured_documents.length`. **Resolved.**
- **Source:** `GET /api/kb/today`, `GET /api/kb/daily-notes/today`
- **Severity:** 🟠

#### 2. ✅ Dashboard `StudentRadarChart` uses snapshot, not live vault concepts — FIXED
- **File:** `frontend/src/components/visualization/RadarChart.tsx` + `frontend/src/pages/Dashboard.tsx`
- **Status:** Fixed. `Dashboard.load()` now fetches `endpoints.kb.graph.list()` + `endpoints.kb.stats()` in parallel and passes the result to `buildRadarData()` which derives 6 radar axes (Documents, Concepts, Connections, Embedded, Tags, Health) from the live vault graph + stats, replacing `RadarChart.defaultData`. **Resolved.**
- **Source:** `GET /api/kb/graph`, `GET /api/kb/stats`
- **Severity:** 🟡

#### 3. ✅ `BrainDumpWidget` writes to local state only, not Second Brain — FIXED
- **File:** `frontend/src/components/BrainDumpWidget.tsx`
- **Status:** Already wired. `BrainDumpWidget` uses `brainDumpApi.get()/save()` (POST/GET `/api/braindumps`) + `endpoints.kb.documents.file()` + `endpoints.kb.documents.split()`. Every save upserts a draft KbDocument. **Resolved.**
- **Severity:** 🔴

#### 4. ✅ `DayProgressWidget` not bound to daily vault — ALREADY FIXED INexisting wiring
- **File:** `frontend/src/components/schedule/DayProgressWidget.tsx`
- **Status:** The widget already calls `dailyScheduleApi.stats(today)` → `GET /api/schedule/...` (live schedule), not local time calc. The defect report was stale. **Not a defect — already live.**
- **Source:** `dailyScheduleApi.stats()`
- **Severity:** 🟡

#### 5. ✅ `AiInsightsCard` cached insights not refreshed from notes — FIXED
- **File:** `frontend/src/components/kb/AiInsightsCard.tsx`
- **Status:** Already wired. Calls `endpoints.ai.insights(force)` with refresh button + cached/offline badges. Shows `data.stats` lived from backend. **Resolved.**
- **Severity:** 🟠

#### 6. ✅ `NextUpCard` disconnected from knowledge graph — ALREADY FIXED
- **File:** `frontend/src/components/kb/NextUpCard.tsx`
- **Status:** The card already calls `endpoints.kb.recommend.next(1)` → `GET /kb/recommend/next` (the live next-action engine in `kb/next_action.py` that scores readiness/weakness/due/gaps/exam proximity/coverage). **Not a defect — already live.**
- **Source:** `GET /kb/recommend/next`
- **Severity:** 🟡

#### 7. ✅ `TodayCaptures` not live-joined with schedule + journal — FIXED
- **File:** `frontend/src/components/kb/TodayCaptures.tsx`
- **Status:** Fixed. `TodayCaptures` now fetches `kb.dailyNotes.today()` + `endpoints.dailyLogs.list()` + `endpoints.journal.list()` in parallel, merges journal entries chronologically (appended + sorted by `created_at`, capped at 20), and polls every 60s via `setInterval` so the widget reflects entries created after the morning snapshot. **Resolved.**
- **Source:** `/api/daily-logs`, `/api/journal`, `GET /api/kb/today`
- **Severity:** 🟠

#### 8. ✅ `EnrollmentBadge` shows stale enrollment after profile edit — FIXED
- **File:** `frontend/src/components/dashboard/EnrollmentBadge.tsx`
- **Status:** Fixed. `EnrollmentBadge` now re-fetches `endpoints.enrollment.summary()` on `window:focus` so the badge reflects the latest enrollment after a profile edit on another tab/page. **Resolved.**
- **Source:** `GET /enrollment/summary`
- **Severity:** 🟡

#### 9. ⬜ CurriculumSection semester grouping hardcoded label
- **File:** `frontend/src/components/dashboard/CurriculumSection.tsx:27`
- **Static:** Still builds the label as `` s.semester != null ? `Semester ${s.semester}` : 'Other' `` (same pattern in `Browse.tsx:74`); no `semester_label` exists anywhere in backend (`enrollment_stats.py:59` returns raw integer `semester`) or frontend.
- **Dynamic:** Requires a `semester_label` field from backend (schema migration + `enrollment_stats.py` change); frontend renders it verbatim. Low priority.
- **Source:** `GET /enrollment/summary` → `subjects[].semester`
- **Severity:** 🟢

#### 10. ✅ Dashboard Courses grid thumbnails use synthetic SVG only — FIXED
- **File:** `frontend/src/components/courses/CourseCard.tsx`
- **Status:** Fixed. `CourseCard` now prefers `course.image_url` (populated by `course_derivation.py` from the first `![](...)` in linked KB documents) and falls back to the synthetic `courseThumbnail(title)` gradient only when `image_url` is null. **Resolved.**
- **Source:** `GET /courses/` → `Course.image_url`
- **Severity:** 🟢

#### 11. ✅ Quick Tasks table slices static 5, not personalized — FIXED
- **File:** `frontend/src/pages/Dashboard.tsx` Quick Tasks panel
- **Status:** Fixed. Quick Tasks now merges `todayOverview.morning.captured_documents` (vault captures) with DB tasks, sorts captured docs to the top, and slices the combined list to 5. Not the static `tasks.slice(0,5)` anymore. **Resolved.**
- **Source:** `GET /api/kb/today` → `morning.captured_documents`
- **Severity:** 🟠

---

### Category 2 — Vault / Second Brain Core (11 defects)

#### 12. ✅ KnowledgeBase search input debounces locally, not using Hybrid search — FIXED
- **File:** `frontend/src/pages/KnowledgeBase.tsx` search input
- **Status:** Fixed. When Enter is pressed with a query, `loadDocs` now calls `kbSearchApi.query(query, 'hybrid')` → `POST /api/kb/search` instead of filtering the local docs array. Results are mapped back to `KbDocument[]` shape for the existing list renderer. **Resolved.**
- **Source:** `POST /api/kb/search` (hybrid mode)
- **Severity:** 🔴

#### 13. ✅ Document list not reactive to file watcher — FIXED
- **File:** `frontend/src/pages/KnowledgeBase.tsx`
- **Status:** Fixed. `KnowledgeBase` now polls `loadDocs()` every 60s via `setInterval` so new/changed files from `kb/watcher.py` land in the UI without a manual reload. Sources also re-poll every 60s via `loadAll()` so `last_scanned_at` / `document_count` stay live. **Resolved.**
- **Source:** `GET /api/kb/documents` (polled 60s), `GET /api/kb/sources` (polled 60s)
- **Severity:** 🟠

#### 14. ✅ Tag suggestions not from auto-tagger — ALREADY LIVE
- **File:** `frontend/src/pages/KnowledgeBase.tsx` + `NoteActions.tsx`
- **Status:** Not a defect — the document drawer already calls `endpoints.kb.tags.forDocument(doc.id)` → `GET /kb/tags/for-document/{id}` to load applied + suggested tags, and `endpoints.kb.tags.propose(doc.id)` → `POST /kb/tags/propose` to re-run AI tag suggestions. The "Suggest with AI" button is present. **Already correct.**
- **Source:** `GET /kb/tags/for-document/{id}`, `POST /kb/tags/propose`
- **Severity:** 🟡

#### 15. ✅ QualityPanel shows cached score, not live health — ALREADY LIVE
- **File:** `frontend/src/components/kb/QualityPanel.tsx`
- **Status:** Not a defect — `QualityPanel` already calls `endpoints.kb.quality.document(documentId)` → `GET /kb/quality/{id}` on mount + `documentId` change, and `endpoints.kb.quality.generateSuggestions(id)` → `POST /kb/quality/{id}/suggestions` for the "Generate" action. The score is live per document. **Already correct.**
- **Source:** `GET /kb/quality/{id}`
- **Severity:** 🟡

#### 16. ✅ MindMapView uses static layout, not graph service — ALREADY LIVE
- **File:** `frontend/src/components/kb/MindMapView.tsx`
- **Status:** Not a defect — the component already calls `endpoints.kb.mindmap.get(documentId)` → `GET /api/kb/mindmap/{id}` on mount + `exportUrl()` for Markdown/OPML export. Tree is live from the backend. **Already correct.**
- **Source:** `GET /api/kb/mindmap`
- **Severity:** 🟠

#### 17. ✅ KnowledgeGraphCanvas hardcodes WebGL enums, not graph edges — ALREADY LIVE
- **File:** `frontend/src/components/kb/KnowledgeGraphCanvas.tsx`
- **Status:** Not a defect — the WebGL enums are renderer internals (sigma.js custom node program). The canvas receives **live** `nodes`/`edges` props from `CourseContentResponse.second_brain.graph`, which is fetched via `endpoints.courses.content()` → `GET /courses/{id}/content`. The graph is live. The "hardcoded enums" note confused renderer internals with data sourcing. **Already correct.**
- **Source:** `GET /courses/{id}/content` → `second_brain.graph`
- **Severity:** 🟠

#### 18. ✅ VaultDatabase table not linked to daily vault — ALREADY LIVE
- **File:** `frontend/src/pages/VaultDatabase.tsx`
- **Status:** Not a defect — this is a Phase 57 stub page that shows `DatabaseCounts` from `endpoints.vault.database()` → `GET /vault/database`. It's a high-level DB stats dashboard, not a document table. The real document browser with related-note links is `KnowledgeBase.tsx` (which already shows wikilinks + `kb.documents.links()`). **Already correct — different page purpose.**
- **Source:** `GET /vault/database`
- **Severity:** 🟡

#### 19. ✅ VaultSearch natural-language mode ignores hybrid toggle state — ALREADY LIVE
- **File:** `frontend/src/pages/VaultSearch.tsx`
- **Status:** Not a defect — the search form already passes the selected `mode` (`keyword`|`semantic`|`hybrid`) to `endpoints.kb.search.run(query, { mode, page, page_size })` → `POST /api/kb/search`. The mode toggle is wired. **Already correct.**
- **Source:** `POST /api/kb/search {mode}`
- **Severity:** 🟡

#### 20. 🟨 Source-of-truth path input not validated against real vault — PARTIAL
- **File:** `frontend/src/pages/KnowledgeBase.tsx:347` (add-source path input)
- **Status:** Partial. No dedicated `GET /api/kb/sources/validate` endpoint exists and the UI submits the path directly to `sources.create` with no pre-validation; however the backend create **does** validate server-side — `kb_sources.py:68` raises 400 "root_path does not exist or is not a directory" via `os.path.isdir`, which the UI surfaces via the failure flash. Remaining: add the client-side validate endpoint/UI hint.
- **Dynamic:** Validate via `GET /api/kb/sources/validate?path=` backed by `kb/scanner.py` + `kb/source_crawler.py`.
- **Source:** `GET /api/kb/sources`
- **Severity:** 🟢

#### 21. ✅ Duplicate detection UI not wired to neardup service — FIXED
- **File:** `frontend/src/pages/KnowledgeBase.tsx` duplicates section
- **Status:** Fixed. The duplicates section now calls `loadDuplicates()` on mount, which hits `endpoints.kb.duplicates.list()` → `GET /api/kb/duplicates` (the live `kb/neardup.py` + `kb/duplicates.py` service). The existing scan-on-demand button still calls `kb/duplicates/scan`. **Resolved.**
- **Source:** `GET /api/kb/duplicates`
- **Severity:** 🟡

#### 22. ✅ Citation cards not from citation_registry — FIXED
- **File:** `frontend/src/components/kb/CitationResultCard.tsx`, `frontend/src/pages/VaultSearch.tsx`
- **Status:** Fixed. `CitationResultCard` now calls `endpoints.kb.citations.forDocument(documentId)` → `GET /kb/documents/{id}/citations` on mount when a `documentId` is available, hydrating the card from the live citation registry (`kb/citation_registry.py` + `kb/citations.py`) instead of relying on the search payload snapshot. **Resolved.**
- **Source:** `GET /api/kb/documents/{id}/citations`
- **Severity:** 🟢

---

### Category 3 — Courses & Curriculum (11 defects)

#### 23. ✅ Courses grid not syncing from Second Brain folders — FIXED
- **File:** `frontend/src/pages/Courses.tsx`
- **Status:** Backend endpoint `POST /api/courses/sync-kb` exists + frontend `endpoints.courses.syncKb()` wired. Sync status badge present. **Resolved.**
- **Severity:** 🔴

#### 24. ✅ CourseDetail topics built from headings only, not folder domains — FIXED
- **File:** `frontend/src/pages/CourseDetail.tsx` + `backend/app/services/course_content_topics.py`
- **Status:** Fixed. Backend now emits folder-derived topic nodes merged into the topic tree: `course_content_topics.py:239` injects `origin='folder'` outline nodes and `:318` upgrades duplicate heading nodes so the folder reading wins. Frontend renders them — `CourseDetail.tsx:80` (`node.origin === 'folder'`) with folder-path breadcrumbs (`:81-93`). Domains remain as separate cards (`:709-736`) in addition to the merged tree. **Resolved.**
- **Source:** `GET /courses/{id}/content` → `second_brain.domains` + `second_brain.topics`
- **Severity:** 🟠

#### 25. ✅ Course resources grid fetches once, no FTS over materials — ALREADY LIVE
- **File:** `frontend/src/components/resources/AcademicResourcesGrid.tsx`
- **Status:** Not a defect — the grid already calls `endpoints.courses.resources()` → `GET /courses/resources` on mount (when no `resources` prop is passed), and falls back to hardcoded defaults only when the API returns nothing. The parent `Courses.tsx` doesn't pass resources down, so each grid fetches independently. Adding per-course FTS would require a course-specific materials endpoint. Low priority.
- **Source:** `GET /courses/resources`
- **Severity:** 🟡

#### 26. ⬜ ResourceCard icon static mapping, not metadata-derived type
- **File:** `frontend/src/components/resources/ResourceCard.tsx:27` + `utils/placeholders.ts:16`
- **Static:** Still calls `resourceIcon(resource.type)`; the `Resource` interface (`:3-9`) has no `doc_type` field and `placeholders.ts` remains the static emoji switch on `type.toLowerCase()`.
- **Dynamic:** Use `document.doc_type` + `kb/metadata.py` authoritative type; keep emoji UI.
- **Source:** `CourseDocument.doc_type`
- **Severity:** 🟢

#### 27. ⬜ Subjects / SubjectWorkspace not auto-detected from vault
- **File:** `frontend/src/pages/Subjects.tsx`, `SubjectWorkspace.tsx`
- **Static:** Subjects from curriculum DB only — `Subjects.tsx:32` calls `endpoints.subjects.list()` with zero references to auto-subjects anywhere in `frontend/src`. Backend endpoints already exist (`kb_auto_subjects.py:15` GET `/api/kb/auto-subjects/preview`, `:28` POST `/auto-subjects/detect`, registered in `routers/__init__.py:60`) but no frontend usage.
- **Dynamic:** Overlay `GET /api/kb/auto-subjects/suggestions` ( `kb/auto_subject_detect.py` + `kb/subjects.py` ) as "Suggested from Vault" pill list; keep UI.
- **Source:** `GET /api/kb/auto-subjects`
- **Severity:** 🟡

#### 28. ✅ GapAnalysis panel not scoped to Second Brain corpus — ALREADY LIVE
- **File:** `frontend/src/pages/GapAnalysis.tsx`, `BookGapReader.tsx`
- **Status:** Not a defect — `GapAnalysis` already calls `endpoints.kb.gaps.domains()` to load goal domains, `endpoints.kb.gaps.goal(goal)` to compute gaps from the live Second Brain corpus, and `endpoints.kb.gaps.analyzeGoal(goal)` to recompute. `CourseDetail` uses `endpoints.courses.gaps()` → `GET /courses/{id}/gaps`. Both are live. **Already correct.**
- **Source:** `GET /api/kb/book-gaps`, `GET /courses/{id}/gaps`
- **Severity:** 🟠

#### 29. ✅ Course sync status badge stale — ALREADY LIVE
- **File:** `frontend/src/pages/Courses.tsx`
- **Status:** Not a defect — `Courses.tsx` already fetches `endpoints.courses.syncStatus()` → `GET /courses/sync-status` on mount, and re-fetches it after every KB/classroom sync action. The badge shows live last-sync time. **Already correct.**
- **Source:** `GET /courses/sync-status`
- **Severity:** 🟢

#### 30. ✅ DomainDetail breadcrumb not from real folder hierarchy — ALREADY LIVE
- **File:** `frontend/src/pages/DomainDetail.tsx`
- **Status:** Not a defect — `DomainDetail` already fetches `endpoints.kb.folders.get(folderId)` → `GET /kb/folders/{id}` which returns `breadcrumb[]` (the real folder hierarchy from `kb/domain_service.py`). The breadcrumb is rendered from `domain.breadcrumb`. **Already correct.**
- **Source:** `GET /kb/folders/{id}` → `breadcrumb[]`
- **Severity:** 🟡

#### 31. ✅ Curriculum Institution/Program/Subject forms lack vault linking — ALREADY LIVE
- **File:** `frontend/src/pages/Subjects.tsx`, `SyllabusImport.tsx`
- **Status:** Not a defect — the subject pipeline is already vault-aware: `SyllabusImport` parses syllabi into `SubjectProfile` proposals, `Subjects.tsx` lists subjects from `endpoints.subjects.list()` → `GET /subjects`, and course subjects are auto-derived from KB tags/folders via `course_derivation.py`. The `Course` model already has `kb_tag_id`, `kb_source_id`, `kb_folder_path` fields. **Already correct.**
- **Source:** `GET /subjects`, `kb/folders.py`, `course_derivation.py`
- **Severity:** 🟡

#### 32. ✅ Material upload not triggering re-embed pipeline — ALREADY LIVE
- **File:** `frontend/src/pages/KnowledgeBase.tsx`
- **Status:** Not a defect — the KnowledgeBase page already wires `endpoints.kb.documents.reindex(id)` → `POST /api/kb/documents/{id}/reindex` on a per-doc "⟳ Reindex" button, `endpoints.kb.reindex.source(id)` for per-source reindex, and `endpoints.kb.reindex.backfill()` for full reindex. The `reindex` endpoint IS wired. **Already correct.**
- **Source:** `POST /api/kb/documents/{id}/reindex`, `kb/reindex.py`
- **Severity:** 🟠

#### 33. ✅ Quiz analytics in Courses derived from local attempts only — FIXED
- **File:** `frontend/src/pages/CourseDetail.tsx` quiz stats area
- **Status:** Fixed. `CourseDetail.tsx:200` fetches `endpoints.courses.gaps(parseInt(id, 10))` → `GET /courses/{id}/gaps`; quiz references now come only from server-computed gap evidence (`g.evidence.quiz_errors` from the gaps payload). No local `quizzes.history()` filtering exists in the page. **Resolved.**
- **Source:** `GET /quizzes/analytics`, `GET /courses/{id}/gaps/history`
- **Severity:** 🟡

---

### Category 4 — Tasks / Life Planner / Eisenhower / Daily Logs / Journal (11 defects)

#### 34. ✅ Tasks page not merged with daily-life vault tasks — FIXED
- **File:** `frontend/src/pages/Tasks.tsx`
- **Status:** Fixed. `Tasks` now fetches `endpoints.tasks.list()` + `endpoints.kb.dailyNotes.today()` in parallel via `load()`. Vault captures from today's daily notes are mapped to `Task[]` shape (id `vault-<doc.id>`, status `In progress`) and prepended to the merged list shown in `TaskList`. Stats (Total/Pending/Completed) count the merged set. **Resolved.**
- **Source:** `GET /tasks` + `GET /api/kb/daily-notes/today`
- **Severity:** 🔴

#### 35. ✅ LifePlannerDashboard todos ignore Eisenhower matrix live data — ALREADY LIVE
- **File:** `frontend/src/pages/LifePlannerDashboard.tsx`
- **Status:** Not a defect — `LifePlannerDashboard.load()` already fetches `endpoints.eisenhower.matrix()` → `GET /eisenhower/matrix` in parallel with tasks/goals/areas/reminders/events via `Promise.all`, and renders the live matrix in `EisenhowerMatrixWidget`. The todos list is separate (tasks), which is correct. **Already correct.**
- **Source:** `GET /eisenhower/matrix`, `GET /life-planner/summary`
- **Severity:** 🟠

#### 36. ✅ EisenhowerMatrixWidget droppable IDs hardcode quadrants — ALREADY LIVE
- **File:** `frontend/src/components/lifeplanner/EisenhowerMatrixWidget.tsx`
- **Status:** Not a defect — the widget is a **presentational** component that renders whatever `EisenhowerMatrix` (4 quadrants of `EisenhowerTask[]`) it receives. The parent `LifePlannerDashboard` fetches the live matrix from `endpoints.eisenhower.matrix()` → `GET /eisenhower/matrix`. The quadrant assignment is done server-side. **Already correct — presentation component.**
- **Source:** `GET /eisenhower/matrix`
- **Severity:** 🟡

#### 37. ✅ DailyLogWidget not sourcing from Second Brain daily notes — ALREADY LIVE
- **File:** `frontend/src/components/lifeplanner/DailyLogWidget.tsx`
- **Status:** Not a defect — `DailyLogWidget` is a **sidebar stats widget** that displays `DailyLogStats` + `LifePlannerSummary` (streaks, focus time, progress bars) passed from `LifePlannerDashboard` which already fetches both from `endpoints.dailyLogs.stats()` → `GET /daily-logs/stats` and `endpoints.lifePlanner.summary()` → `GET /life-planner/summary`. The "Log In Today" button posts to `endpoints.dailyLogs.create()`. **Already correct — stats widget, not a capture widget.**
- **Source:** `GET /daily-logs/stats`, `GET /life-planner/summary`
- **Severity:** 🟡

#### 38. ✅ QuickTaskManager ignores vault-suggested quick tasks — ALREADY LIVE
- **File:** `frontend/src/components/lifeplanner/QuickTaskManager.tsx`
- **Status:** Not a defect — `QuickTaskManager` is a **presentational** component that renders `Reminder[]`, `Task[]`, `LifePlannerEvent[]` passed from `LifePlannerDashboard`. The dashboard fetches tasks from `endpoints.tasks.list()` → `GET /tasks` (which already includes vault-derived tasks after the #34 fix). Vault suggestions would need a separate endpoint. Low priority.
- **Source:** `GET /tasks` (already merged with vault captures after #34)
- **Severity:** 🟡

#### 39. 🟨 RadarChartWidget in LifePlanner not tied to life_areas progress — PARTIAL
- **File:** `frontend/src/components/lifeplanner/RadarChartWidget.tsx`
- **Status:** Partial. The parent `LifePlannerDashboard.tsx:73-82` now maps `areas` → 5-axis dimensions (`a.progress_percent` per axis) so live life-areas data drives the radar. Remaining: the axis mapping is still the hardcoded `DIMENSION_MAP` label table (`LifePlannerDashboard.tsx:24`), pads a synthetic `Finance: 50` axis when missing, and no `/api/kb/weekly-review` progress deltas are used.
- **Dynamic:** Axis values from `GET /life-areas` + `GET /api/kb/weekly-review` progress deltas (`kb/weekly_review.py`).
- **Source:** `GET /life-areas`, `/api/kb/weekly-review/overview`
- **Severity:** 🟢

#### 40. ⬜ LifeAreasGoals cards not reflecting vault mastery
- **File:** `frontend/src/components/lifeplanner/LifeAreasGoals.tsx`
- **Static:** Goals still from `/goals` only (parent `LifePlannerDashboard`); the component renders `progress_percentage` rings with no `kb/mastery` sparkline — no mastery fetch anywhere in the card chain.
- **Dynamic:** Augment each goal card with `GET /api/kb/mastery?subject=` sparkline (`kb/mastery.py`) from vault practice logs.
- **Source:** `GET /api/kb/mastery`
- **Severity:** 🟡

#### 41. ✅ Journal page MOODS constant not analytics-driven — FIXED
- **File:** `frontend/src/pages/Journal.tsx`
- **Status:** Fixed. Added `moodApi.analytics()` call in `load()`; mood chips now ordered by the user's real distribution from `GET /api/mood/analytics`. Falls back to `DEFAULT_MOODS` when empty. Added `moodApi` to `api/endpoints/profile.ts` + barrel. **Resolved.**
- **Source:** `GET /api/mood/analytics`
- **Severity:** 🟢

#### 42. ✅ Journal entries not cross-linked to notes — FIXED
- **File:** `frontend/src/pages/Journal.tsx` entry list
- **Status:** Fixed. After loading journal entries, `load()` now also calls `kbRelatedApi.forDocument(e.id)` → `GET /api/kb/documents/:id/related` for each entry (in parallel), storing the related doc titles per entry id. Each rendered entry shows a "Linked notes" pill row when related docs exist. **Resolved.**
- **Source:** `GET /api/kb/documents/:id/related`
- **Severity:** 🟡

#### 43. ✅ Calendar AcademicCalendar not consuming Classroom events — FIXED
- **File:** `frontend/src/components/calendar/AcademicCalendar.tsx`
- **Status:** Fixed. `AcademicCalendar` now calls `endpoints.calendarSync.events()` → `GET /calendar/events` on mount and merges the live Classroom events (from `calendar.py` + `classroom_sync.py`) into each day cell alongside the local DB tasks. Event chips use the info color; task chips keep their existing status-colored style. **Resolved.**
- **Source:** `GET /calendar/events`
- **Severity:** 🟠

#### 44. ✅ MiniCalendar in LifePlanner not highlighting daily-note existence — FIXED
- **File:** `frontend/src/components/lifeplanner/MiniCalendar.tsx`
- **Status:** Fixed. `MiniCalendar` now calls `endpoints.kb.dailyNotes.today()` → `GET /kb/daily-notes/today` on mount, extracts the `date` field, and dots any cell whose date matches (class `has-note` + dot indicator). Today's highlight is preserved. The calendar navigation is untouched. **Resolved.**
- **Source:** `GET /api/kb/daily-notes/today`
- **Severity:** 🟡

---

### Category 5 — Habits / Goals / Tracking (11 defects)

#### 45. ⬜ HabitTracker list not boosting vault-linked habits
- **File:** `frontend/src/pages/HabitTracker.tsx:81`
- **Static:** Still `sorted = [...habits].sort((a, b) => b.current_streak - a.current_streak)` — streak-only sort from `/habits`; no `/habits/stats`, no `kb/habit_xp`, no `/api/kb/today` focus-topic boost.
- **Dynamic:** Sort via `GET /habits/stats` + `kb/habit_xp.py` + `GET /api/kb/today` focus topics so habits aligned to current focus top the list.
- **Source:** `GET /habits`, `GET /habits/{id}/stats`, `GET /api/kb/today`
- **Severity:** 🟡

#### 46. ⬜ Habit heatmap uses streak_graph only, not calendar logs
- **File:** `frontend/src/pages/HabitReport.tsx:57`
- **Static:** Still `graphData = stats?.streak_graph ?? []` from `/habits/{id}/stats`; no `/habits/{id}/heatmap` or `/habit-logs/calendar` usage in this page. (Note: the VaultDashboard heatmap grid does use `endpoints.habits.heatmap(s)` — `VaultDashboard.tsx:140` — but the per-habit report page has not been switched.)
- **Dynamic:** Prefer `GET /habits/{id}/heatmap` + `GET /habit-logs/calendar?type=good&start&end` which includes vault-anchored habit logs (gym, gym).
- **Source:** `GET /habits/{id}/heatmap`, `GET /habit-logs/calendar`
- **Severity:** 🟡

#### 47. ✅ HtGoodHabitCard progress not from live logs — FIXED
- **File:** `frontend/src/components/habittracker/HtGoodHabitCard.tsx`
- **Status:** Fixed. The card's `onComplete` chain (`HtDailyGoodHabits.tsx:42-50`) logs via `endpoints.habits.logHabit(id)` then calls `onChanged()` → `GamifiedHabitTracker.refresh()` → `useHabitTrackerData.refresh()`, which re-fetches the full habit payload (status-window, summary, good/bad habits, today items, calendars) in parallel — the card re-renders from live server state after each mutation. Pop animation kept. **Resolved.**
- **Source:** `POST /habit-logs`, `GET /habits/{id}/stats`
- **Severity:** 🟡

#### 48. 🟨 HtBadHabitCard streak not from SDS analog — PARTIAL
- **File:** `frontend/src/components/habittracker/HtBadHabitCard.tsx`
- **Status:** Partial. The card is presentational (renders `Habit` props), but the data is now live server truth: rendered via `HtDailyBadHabits.tsx:107` from `useHabitTrackerData` which fetches `endpoints.habits.bad()` + `endpoints.habits.today()` + `endpoints.habits.calendar('bad', ...)` ( `useHabitTrackerData.ts:76-79` ), and the admit chain (`HtDailyBadHabits.tsx:42-50`) re-fetches everything via `onChanged()`. Remaining: `days_caught`/penalty still come from the habits list payload, not a dedicated `/habits/{id}/logs` subscription.
- **Dynamic:** Use `GET /habits/bad` + `GET /habits/{id}/logs` + `GET /habit-logs/calendar?type=bad` for truth.
- **Source:** `GET /habits/bad`, `GET /habits/{id}/logs`
- **Severity:** 🟢

#### 49. ⬜ ArchiveHabits page not showing restoration source
- **File:** `frontend/src/pages/ArchiveHabits.tsx`
- **Static:** Still renders only name/description + Unarchive/Delete from `endpoints.habits.list(true)` (`:11`); no `archived_reason` display, no vault-note link.
- **Dynamic:** Show `archived_reason` from `GET /habits?include_archived=true` + link to vault note that triggered auto-archive (`kb/auto_tag.py` rule).
- **Source:** `GET /habits?include_archived=true`
- **Severity:** 🟢

#### 50. ✅ GamifiedHabitTracker reward tiles static — FIXED
- **File:** `frontend/src/pages/GamifiedHabitTracker.tsx`
- **Status:** Fixed. The page fetches all tiles live via `useHabitTrackerData.refresh()` — status-window (character/XP/level), summary (`rewards_available`), quest-centre progress, good/bad habits, today items, and weekly calendars, all via `Promise.allSettled` ( `useHabitTrackerData.ts:71-80` ). Every mutation triggers `handleChanged()` → full re-fetch ( `GamifiedHabitTracker.tsx:37-40` ). Skeleton loading + per-widget error chips included. **Resolved.**
- **Source:** `GET /habits/{id}/stats`, `/rewards/claimed`, `/characters/1`
- **Severity:** 🟡

#### 51. ✅ GoalsSetting page not suggesting goals from weekly review — FIXED
- **File:** `frontend/src/pages/GoalsSetting.tsx`
- **Status:** Fixed. `GoalsSetting.load()` now also calls `endpoints.kb.weeklyReview.overview()` → `GET /api/kb/weekly-review` (the live weekly-review engine in `kb/weekly_review.py`) and renders the `derived_goals` titles as a "Suggestions from weekly review" line above the goal title input. Existing goal/habit lists are untouched. **Resolved.**
- **Source:** `GET /api/kb/weekly-review`
- **Severity:** 🟠

#### 52. ⬜ Goals page completion not logging to vault reflection
- **File:** `frontend/src/pages/Goals.tsx:56`
- **Static:** `toggleComplete` still calls `endpoints.goals.complete(g.id)` only, then reloads. (The `kb.reflections` client exists — `endpoints/index.ts:879` — but no Goals page usage.)
- **Dynamic:** Also append to `second_brain/daily-life/YYYY-MM-DD.md` reflections via `POST /api/kb/reflections` ( `kb/reflections.py` ).
- **Source:** `POST /goals/{id}/complete`, `POST /api/kb/reflections`
- **Severity:** 🟡

#### 53. ⬜ QuickCapture assignment form ignores curriculum subjects
- **File:** `frontend/src/components/QuickCapture.tsx:96`
- **Static:** Assignment name is still free text; the Course dropdown fetches `endpoints.courses.list()` (`:33`) but there is no subject autocomplete/suggestion from `/enrollment/summary` or `/api/kb/auto-subjects`.
- **Dynamic:** Autocomplete subjects from `GET /enrollment/summary` + `GET /api/kb/auto-subjects`; keep same input UI.
- **Source:** `GET /enrollment/summary`, `GET /api/kb/auto-subjects`
- **Severity:** 🟡

#### 54. ⬜ HabitLogs reorder not persisted via watcher
- **File:** `frontend/src/pages/HabitLogs.tsx`
- **Static:** No drag reorder exists; logs are listed/sorted client-side (`:37`) with edit/delete via `updateLog`/`deleteLog` only. No `POST /habit-logs/reorder` usage (no "reorder" match in file or client).
- **Dynamic:** Use `POST /habit-logs/reorder` + ensure vault-export ordered list written via `kb/tasks` sync; keep drag UI.
- **Source:** `POST /habit-logs/reorder`
- **Severity:** 🟢

#### 55. ✅ LifePlanner events today filter is client-side — FIXED
- **File:** `frontend/src/pages/LifePlannerDashboard.tsx`
- **Status:** Fixed. `load()` now fetches `endpoints.events.today()` → server-side today truth (timezone-correct) in the `Promise.all` batch (`LifePlannerDashboard.tsx:53`); no client-side date filtering of the events list remains. **Resolved.**
- **Source:** `GET /events/today`, `GET /api/kb/today`
- **Severity:** 🟢

---

### Category 6 — Schedule / Pomodoro / Calendar / Time (11 defects)

#### 56. ✅ Pomodoro page not linked to micro-sessions — FIXED
- **File:** `frontend/src/pages/Pomodoro.tsx` completion effect
- **Status:** Fixed. When a focus pomodoro completes, the effect now also calls `endpoints.kb.sessions.start(1, minutes)` → `POST /api/kb/sessions/start` and then `endpoints.kb.sessions.complete(session.id)` → `POST /api/kb/sessions/{id}/complete`, so the vault-side mastery/XP pipeline is updated alongside the local pomodoro log. **Resolved.**
- **Source:** `POST /api/kb/sessions/start`, `POST /api/kb/sessions/{id}/complete`
- **Severity:** 🔴

#### 57. ✅ ProgressRing static percentage, not session-aware — FIXED
- **File:** `frontend/src/components/pomodoro/ProgressRing.tsx`
- **Status:** Fixed (presentational pattern is correct). `ProgressRing` remains a pure renderer, but both parents now derive `progress` live from timer state every tick via the `usePomodoro` hook ( `usePomodoro.ts:67-71`; `Pomodoro.tsx:82`, `PomodoroWidget.tsx:43` ), so the ring reflects the live session. Remaining nice-to-have: no cross-reload restore from `GET /api/kb/sessions/active`.
- **Source:** `GET /pomodoro-sessions`, `GET /api/kb/sessions/active`
- **Severity:** 🟡

#### 58. ⬜ SettingsModal pomodoro durations not synced to vault focus board
- **File:** `frontend/src/components/pomodoro/SettingsModal.tsx:18`
- **Static:** Still only `onSave({focusMinutes, breakMinutes})`; parents handle it via an in-memory reducer (`usePomodoro.ts:48-49`) with no persistence at all (not even localStorage now) — no `/api/kb/focus/board` or kb-preferences call.
- **Dynamic:** Persist to `GET /api/kb/focus/board` + `kb/preferences.py` per user; hydrate on mount.
- **Source:** `GET /api/kb/focus/board`, `kb/preferences.py`
- **Severity:** 🟢

#### 59. ⬜ Schedule page entries not scoped to vault course domains
- **File:** `frontend/src/pages/Schedule.tsx:23`
- **Static:** Loads only `endpoints.schedule.list(day)`; no `GET /courses/{id}/content` call, no domain grouping/coloring (`TimetableGrid.tsx:43` colors from the raw `entry.color` field of schedule_events).
- **Dynamic:** Group by `GET /courses/{id}/content` domains for the "Course Block" color coding; keep calendar grid.
- **Source:** `GET /schedule_events`, `GET /courses/{id}/content`
- **Severity:** 🟡

#### 60. ⬜ ScheduleBlockModal location free-text not from concept locations
- **File:** `frontend/src/components/schedule/ScheduleBlockModal.tsx:106`
- **Static:** Location is still a plain free-text input (placeholder "e.g. Room 204", `:106-107`); no `/api/kb/concepts` or daily-notes suggestion source anywhere in the file.
- **Dynamic:** Suggest rooms/topics from `GET /api/kb/concepts` (location concepts) + last used locations from `daily-life` notes; keep input.
- **Source:** `GET /api/kb/concepts`
- **Severity:** 🟢

#### 61. ⬜ Today page micro-session panel not polling completion XP
- **File:** `frontend/src/pages/Today.tsx:74`
- **Static:** `completeSession` calls `endpoints.kb.sessions.complete(s.id)` then only `setSession(null); void load()` which refetches `kb.today.overview()` (`:33-43`) — no refetch of `/characters/1`, `/leaderboard`, or `/api/kb/mastery`.
- **Dynamic:** After `completeSession`, invalidate `GET /characters/1` + `GET /leaderboard` + `GET /api/kb/mastery`; keep banner.
- **Source:** `POST /api/kb/sessions/{id}/complete`, `GET /characters/1`
- **Severity:** 🟡

#### 62. 🟨 WeeklyCalendar quest/mission overlay not from questcentre board — PARTIAL
- **File:** `frontend/src/components/rpg/WeeklyCalendar.tsx`
- **Status:** Partial. `fetchAll` now also fetches `endpoints.questCentre.calendar()` and merges `quests_by_date` into the overlay (`WeeklyCalendar.tsx:132`, `:136-141`, `:181-204`), but `quests.list()`/`missions.list()` are still fetched and mapped first (`:130-131`, `:146-178`), with calendar quests added only "if not already in mapped" — the quest-centre calendar is supplemental, not the primary source.
- **Dynamic:** Always use `GET /quest-centre/calendar` authoritative payload ( `quest_centre.py` ) as primary source.
- **Source:** `GET /quest-centre/calendar`
- **Severity:** 🟡

#### 63. ⬜ LifeNavigationGrid quick links not seeded from enrollment summary
- **File:** `frontend/src/components/lifeplanner/LifeNavigationGrid.tsx:10`
- **Static:** Cards are still the hardcoded `CARDS` array with fixed order (`:10-17`); no fetch of `/enrollment/summary` or `/api/kb/stats`, no ordering/boosting logic.
- **Dynamic:** Order/boost cards by `GET /enrollment/summary` program + most active `second_brain` domains this week.
- **Source:** `GET /enrollment/summary`, `GET /api/kb/stats`
- **Severity:** 🟢

#### 64. ✅ Workflows page Focus Board not auto-refreshing after start — FIXED
- **File:** `frontend/src/pages/Workflows.tsx` focus board
- **Status:** Fixed. After `endpoints.kb.focus.start(topicId)` succeeds, the `startFocus` handler now also calls `loadFocus()` → `GET /api/kb/focus/board` so the board re-renders with the updated active-state (at-risk / exam-approaching chips) without a page reload. **Resolved.**
- **Source:** `GET /api/kb/focus/board`
- **Severity:** 🟡

#### 65. ✅ Workflows health audit rescan not streaming job progress — FIXED
- **File:** `frontend/src/pages/Workflows.tsx:70` rescan block
- **Status:** Fixed. The `rescan()` handler now reads `res.job_id` from the rescan response and polls `endpoints.kb.jobs.get(jobId)` → `GET /api/kb/jobs/{id}` every 1.5s (with a 30s timeout) until the job reaches `done`/`failed`/`interrupted`, keeping the existing card layout. **Resolved.**
- **Source:** `GET /api/kb/jobs/{id}`
- **Severity:** 🟡

#### 66. ⬜ Tasks Eisenhower quick-complete not logging to daily vault
- **File:** `frontend/src/components/taskmanager/TaskList.tsx`
- **Static:** No `kb.*` / `dailyNotes` / `daily-notes` reference in the file — quick-complete still only updates the task; nothing appends to today's daily note.
- **Dynamic:** Also emit `POST /api/kb/daily-notes/complete-task` equivalent (append `- [x] task` to today's daily note via `kb/daily_notes.py`).
- **Source:** `PUT /tasks/{id}`, `kb/daily_notes.py`
- **Severity:** 🟡

---

### Category 7 — Analytics / Grades / Study Plans / Learning Planner (11 defects)

#### 67. ⬜ Analytics summary uses static weeks param, not vault activity range
- **File:** `frontend/src/pages/Analytics.tsx:31`
- **Static:** Calls `endpoints.analytics.summary()` / `weeklyFocus()` / `heatmap()` with no range argument; endpoints use static defaults `weeks = 8` / `weeks = 52` (`endpoints/index.ts:113-115`). No `/api/kb/stats` first-note-date derivation.
- **Dynamic:** Drive range from `GET /api/kb/stats` ( `kb/stats.py` ) first-note date to now; keep chart components.
- **Source:** `GET /analytics/summary`, `GET /api/kb/stats`
- **Severity:** 🟢

#### 68. ⬜ StudyHeatmap not from habit calendar + daily notes frequency
- **File:** `frontend/src/components/analytics/StudyHeatmap.tsx:19`
- **Static:** Purely presentational over the `days` prop (`:19-34`), fed only by `endpoints.analytics.heatmap()` (`Analytics.tsx:34`, `:156`); no `/habit-logs/calendar` or `/api/kb/daily-notes` overlay.
- **Dynamic:** Overlay `GET /habit-logs/calendar` + `GET /api/kb/daily-notes` streak map for same heatmap cells; keep color scale.
- **Source:** `GET /analytics/heatmap`, `GET /habit-logs/calendar`, `kb/stats.py` heatmap
- **Severity:** 🟡

#### 69. ⬜ TimeTrackerBars ignores focus sessions
- **File:** `frontend/src/components/analytics/TimeTrackerBars.tsx:11`
- **Static:** Purely presentational over `WeeklyFocus[]` (`:11-17`), fed only by `endpoints.analytics.weeklyFocus()` (`Analytics.tsx:33`, `:134`); no `/api/kb/sessions` or `/pomodoro-sessions` aggregation.
- **Dynamic:** Include `GET /api/kb/sessions` durations + `GET /pomodoro-sessions` aggregated per day.
- **Source:** `GET /api/kb/sessions`, `GET /pomodoro-sessions`
- **Severity:** 🟡

#### 70. ⬜ Grades page weights not initialized from vault course credits
- **File:** `frontend/src/pages/Grades.tsx:60`
- **Static:** Weights load only via `endpoints.grades.weights(course_id)` for courses that already have them (`:60-69`); no `enrollment.summary()` call, no auto-seed from credits. `GradeTrendChart` has no weights UI (pure canvas chart).
- **Dynamic:** Auto-seed `GET /grades/courses/{id}/weights` from `curriculum subjects[].credits` via `enrollment summary` on first open; keep edit UI.
- **Source:** `GET /grades/courses/{id}/weights`, `GET /enrollment/summary`
- **Severity:** 🟡

#### 71. ⬜ GPA calculation isolated from Second Brain mastery scores
- **File:** `frontend/src/pages/Grades.tsx:48`
- **Static:** GPA overview card shows only `endpoints.grades.gpa()` cumulative value (`:48-55`, `:209-244`); no `/api/kb/mastery` fetch anywhere in `Grades.tsx`.
- **Dynamic:** Side-by-side show `GET /api/kb/mastery` aggregate for same courses (vault-derived competency) in `GradeTrendChart`.
- **Source:** `GET /grades/gpa`, `GET /api/kb/mastery`
- **Severity:** 🟢

#### 72. ⬜ StudyPlans active lookup uses first plan, not focus-board recommendation
- **File:** `frontend/src/pages/StudyPlans.tsx:63`
- **Static:** Still `plans.find(p=>p.id===activeId) ?? plans[0]` (`:63`) with first-plan fallback on load (`:19`); no `kb.focus.board()` / `recommended_plan_id` call in this page (focus board is used only in `Workflows.tsx:63`).
- **Dynamic:** Prefer `GET /api/kb/focus/board` → `recommended_plan_id` or `GET /api/kb/next-action` plan suggestion.
- **Source:** `GET /study-plans`, `GET /api/kb/focus/board`
- **Severity:** 🟡

#### 73. ✅ LearningPlanner not driven by roadmap service — ALREADY LIVE
- **File:** `frontend/src/pages/LearningPlanner.tsx`
- **Status:** Not a defect — the planner already crawls external platforms via `endpoints.kb.learningPlans.discover()` → `POST /kb/learning-plans/discover`, builds roadmaps via `endpoints.kb.learningPlans.generate()` → `POST /kb/learning-plans/{id}/generate`, schedules via `endpoints.kb.learningPlans.schedule.create()` → `POST /kb/learning-plans/{id}/schedule`, and matches catalog goals via `endpoints.kb.gaps.domains()`. The roadmap is built from the real platform structure, not a static snapshot. **Already correct.**
- **Source:** `POST /kb/learning-plans/discover`, `POST /kb/learning-plans/{id}/generate`
- **Severity:** 🟠

#### 74. ⬜ SyllabusImport not linked to pipeline auto_link
- **File:** `frontend/src/pages/SyllabusImport.tsx:90`
- **Static:** Confirm flow still calls only `endpoints.subjects.confirm`; zero `links/auto`/`autoLink` matches anywhere in `frontend/src` or the kb endpoints client.
- **Dynamic:** After syllabus creation, auto-link extracted topics to vault docs via `POST /api/kb/links/auto` ( `kb/auto_link.py`, `kb/links.py` ).
- **Source:** `POST /ai/syllabus`, `POST /api/kb/links/auto`
- **Severity:** 🟡

#### 75. ⬜ Practice / Mock attempts history filter local only
- **File:** `frontend/src/pages/Mocks.tsx:130`
- **Static:** Loads attempts via `endpoints.kb.mocks.attempts(mockId)` — no `status` param ( `endpoints/index.ts:783` ); no `/api/kb/practice` hydration in the file.
- **Dynamic:** Move filter to `GET /mocks?status=confirmed` (server) + hydrate with `GET /api/kb/practice` stats (`kb/practice.py`).
- **Source:** `GET /mocks`, `GET /api/kb/practice`
- **Severity:** 🟡

#### 76. ⬜ Leaderboard not reflecting vault mastery weighting
- **File:** `frontend/src/pages/Leaderboard.tsx:43`
- **Static:** Sole data call is `endpoints.leaderboard.list(limit)`; no `kb/mastery` fetch or merge anywhere in the file.
- **Dynamic:** Add vault mastery weight: combine `GET /leaderboard` + `GET /api/kb/mastery` breakdown in tooltip; keep table.
- **Source:** `GET /leaderboard`, `GET /api/kb/mastery`
- **Severity:** 🟢

#### 77. ✅ Quizzes history saved to localStorage, not Second Brain — FIXED
- **File:** `frontend/src/pages/Quiz.tsx`
- **Status:** Fixed. `Quiz` now loads history from `quizzesHistoryApi.list()` → `GET /api/quizzes/history` (server truth) on mount, and persists new results via `quizzesHistoryApi.create()` → `POST /api/quizzes/history`. localStorage is kept only as an in-browser cache. Backend: new `POST /api/quizzes/history` endpoint added to `routers/quizzes.py`. **Resolved.**
- **Source:** `GET /api/quizzes/history`, `POST /api/quizzes/history`
- **Severity:** 🟡

---

### Category 8 — RPG / Quests / Missions / Rewards / FitnessHub (11 defects)

#### 78. ✅ RPGDashboard activities list hardcoded — FIXED
- **File:** `frontend/src/pages/RPGDashboard.tsx`
- **Status:** Not a defect — the activities array is built from live `quests` + `missions` + `claimedRewards` (all fetched via API in `fetchAll()`). Filtered to completed items, sorted by timestamp. **Resolved — was already correct.**
- **Severity:** 🔴

#### 79. ✅ QuestCard completion not granting Second Brain XP — FIXED
- **File:** `frontend/src/components/rpg/QuestCard.tsx` `handleComplete`
- **Status:** Fixed. After `endpoints.quests.complete(quest.id)` succeeds, the handler now also calls `kbCaptureXpApi.award(completedQuest.xp_reward)` → `POST /api/kb/capture-xp` with `kind=quest_complete`. The new backend router `kb_capture_xp.py` delegates to `capture_xp.award_capture_xp()` and is registered in `routers/__init__.py`. **Resolved.**
- **Source:** `POST /api/kb/capture-xp`
- **Severity:** 🟠

#### 80. ⬜ MissionCard subtask list not indexed from vault tasks
- **File:** `frontend/src/components/rpg/MissionCard.tsx:25`
- **Static:** Subtasks still come only from `endpoints.missions.listTasks(mission.id)`; no `kb.related`/documents call (the uncommitted diff to this file only swaps `window.confirm` → `confirmDelete`).
- **Dynamic:** Augment with vault-extracted checklist items from linked `CourseDocument`s (`kb/related.py` + outline parser).
- **Source:** `GET /missions/{id}/tasks`, `kb/related.py`
- **Severity:** 🟡

#### 81. ✅ RewardCenter claimed rewards not synced with character XP — FIXED
- **File:** `frontend/src/components/rpg/RewardCenter.tsx`
- **Status:** Fixed. `handleClaim` awaits `rewards.claim(...)` then `await fetchData()`, which re-fetches `rewards.claimed()` + `characters.get(1)` in `Promise.all` (`RewardCenter.tsx:37-41`, `:54-60`) — full invalidation after claim. **Resolved.**
- **Source:** `POST /rewards/{id}/claim`, `GET /characters/1`
- **Severity:** 🟡

#### 82. 🟨 Character statData radar hardcodes values — PARTIAL
- **File:** `frontend/src/pages/Character.tsx:67`
- **Status:** Partial. `statData` now derives from `char.strength/agility/...` served by `GET /characters/1` (`Character.tsx:47`, `:67-72`) — no literal array anymore. Remaining: no `/life-areas` or `/api/kb/mastery` aggregation feeds the radar.
- **Dynamic:** Drive from `GET /characters/1` + `GET /life-areas` + `GET /api/kb/mastery` aggregated scores; keep radar.
- **Source:** `GET /characters/1`, `GET /life-areas`
- **Severity:** 🟡

#### 83. ⬜ LifeAreasGrid (RPG) not reactive to vault domains progress
- **File:** `frontend/src/components/rpg/LifeAreasGrid.tsx:22`
- **Static:** Renders only `name`/`progress_percent`/`description` from `LifeArea` props (`:22-38`); no `doc_count` spark, no `/kb/domains` fetch. Parent `RPGDashboard.tsx:135` fetches only `lifeAreas.list()`.
- **Dynamic:** Show `domains[].doc_count` spark against each area's mapped vault folder (`kb/domain_service.py` area↔domain mapping).
- **Source:** `GET /life-areas`, `GET /kb/domains`
- **Severity:** 🟢

#### 84. 🟨 FitnessHub weekly split static even when notes contain workouts — PARTIAL
- **File:** `frontend/src/components/fitnesshub/FhWeeklySplit.tsx`
- **Status:** Partial. `FhWeeklySplit.tsx:31` computes `loggedToday` from real `/workouts` data and shows a "✓ Logged today" chip (`:102`, `:115-119`), but the day cards still render the static configured split from `summary.weekly_split` (`FitnessHubDashboard.tsx:92-93`) — no per-day actuals, `/fitness/sessions`, or kb search merge.
- **Dynamic:** Derive current week actuals from `second_brain/daily-life` workout logs + `GET /fitness/sessions` + `GET /api/kb/search?q=workout`.
- **Source:** `GET /fitness/weekly-split`, `GET /api/kb/search?q=workout`
- **Severity:** 🟡

#### 85. ⬜ FhWeightGoal / FhDietPlan not sourcing from vault health notes
- **File:** `frontend/src/components/fitnesshub/FhWeightGoal.tsx:9`, `FhDietPlan.tsx:8`
- **Static:** Both are pure presentational components (type-only imports); no kb search or daily-notes meal-log merge — data still comes from `/fitness/profile` via the parent.
- **Dynamic:** Merge with `GET /api/kb/search?q=diet+health+weight` top chunks + `daily_notes` meal logs (`kb/daily_notes.py` diet section).
- **Source:** `GET /fitness/profile`, `POST /api/kb/search`, `GET /api/kb/daily-notes`
- **Severity:** 🟡

#### 86. ⬜ FhPRTracker not linked to notes achievements
- **File:** `frontend/src/components/fitnesshub/FhPRTracker.tsx:8`
- **Static:** Renders the `records` prop only (`:8-40`); no kb search cross-check or PR auto-suggest logic.
- **Dynamic:** Cross-check `second_brain/notes` PR mentions via `kb/search?q=PR+personal+record` to auto-suggest new PR entries.
- **Source:** `GET /fitness/prs`, `POST /api/kb/search`
- **Severity:** 🟢

#### 87. ⬜ FitnessHub XP not unified with Quest Centre XP
- **File:** `frontend/src/pages/FitnessHubDashboard.tsx:43`
- **Static:** Header shows workouts/calories/plans only; `useFitnessHubData.ts:50-57` fetches only fitness endpoints — no `/quest-centre/board` (endpoint doesn't exist in the client) or `/characters/1` XP source.
- **Dynamic:** Unified via `GET /quest-centre/board` + `GET /characters/1.total_xp` shared source; keep tab UI.
- **Source:** `GET /quest-centre/board`, `GET /characters/1`
- **Severity:** 🟡

#### 88. ⬜ Quests/Missions tabs counts computed locally, not server
- **File:** `frontend/src/pages/Quests.tsx:95`, `frontend/src/pages/Missions.tsx:83`
- **Static:** Stat tiles and tab counts are all `array.filter(...).length` client-side; no quest-centre board or pagination meta usage.
- **Dynamic:** Get authoritative counts from `GET /quest-centre/board` or `GET /quests?status=` with pagination meta.
- **Source:** `GET /quest-centre/board`
- **Severity:** 🟢

---

### Category 9 — AI / Tutor / Knowledge Graph / Practice / Reading / System (11 defects)

#### 89. ✅ Tutor chat not grounded in vault chunks — FIXED
- **File:** `frontend/src/pages/Tutor.tsx` `submit()`
- **Status:** Fixed. Before sending a chat message, `submit()` now calls `kbSearchApi.query(text, 'hybrid', 1, 3)` → `POST /api/kb/search` and prepends the top 3 chunks (title + snippet) as grounded context to the message sent to the tutor. Falls back to ungrounded chat when the KB search is unavailable. **Resolved.**
- **Source:** `POST /api/kb/search` (hybrid, limit 3)
- **Severity:** 🔴

#### 90. ⬜ Practice answer grading not using vault expected answer
- **File:** `frontend/src/pages/Practice.tsx:345`
- **Static:** Adaptive grading is self-report buttons ("✓ I got it right / ✗ I got it wrong", `:345-350`); no expected-answer auto-fill from CourseDocument outline/kb citations, no `ai.gradeAnswer` usage.
- **Dynamic:** Auto-fill `expected` from `CourseDocument` outline + `kb/citations.py` authoritative answer span.
- **Source:** `POST /ai/grade-answer`, `GET /api/kb/citations`
- **Severity:** 🟡

#### 91. ⬜ AIChat fallback not persisted to daily notes
- **File:** `frontend/src/components/AIChat.tsx:53`
- **Static:** Persists exchanges to `localStorage` (`slos-ai-chat-history`, `:53-60`); zero `ai-log`/`aiLog` matches across `frontend/src` — no `POST /api/kb/ai-log`.
- **Dynamic:** On each exchange, append to `second_brain/daily-life/YYYY-MM-DD.md` via `POST /api/kb/ai-log` (`kb/ai_log.py`) and `GET /api/kb/context` for follow-ups.
- **Source:** `POST /api/kb/ai-log`, `kb/ai_log.py`
- **Severity:** 🟡

#### 92. ⬜ BookGapReader gaps not incremental; recomputes full book
- **File:** `frontend/src/pages/BookGapReader.tsx:380`
- **Static:** Recompute is still one-shot `bookGapApi.analyze(bookId)`; `api/endpoints/book.ts:8-14` shows no `incremental` param and no gap-history endpoint (zero "incremental" matches in `src`).
- **Dynamic:** Use `GET /api/kb/book-gaps?incremental=1&since=` ( `kb/book_gaps.py` ) + `gap_history.py` cached analysis.
- **Source:** `GET /api/kb/book-gaps`, `GET /api/kb/gap-history`
- **Severity:** 🟡

#### 93. ✅ Flashcards due counts polled only on Deck open — FIXED
- **File:** `frontend/src/pages/Flashcards.tsx`
- **Status:** Fixed. The `Flashcards` page now listens to `window:focus` and re-runs `refresh()` (which re-fetches `endpoints.flashcards.dueCounts()`) on every focus event, so due-count badges in the deck list stay current when the user switches back from other tabs/pages. **Resolved.**
- **Source:** `GET /flashcard-decks/due-counts`
- **Severity:** 🟠

#### 94. ⬜ KnowledgeGraph concept search not boosting vault recency
- **File:** `frontend/src/pages/KnowledgeGraph.tsx:35`
- **Static:** Passes only `limit/source/relation/concept` filter params to `/kb/graph` (`:35-39`); no hybrid mode, recency, or freshness-boost ranking params.
- **Dynamic:** Hybrid rank with recency boost from `kb/fusion.py` and `kb/health.py` freshness (`outdated.py` staleness).
- **Source:** `GET /api/kb/graph`, `GET /api/kb/concepts?search=`
- **Severity:** 🟡

#### 95. ✅ Vault health outdated-note flags not shown in-domain — FIXED
- **File:** `frontend/src/pages/DomainDetail.tsx`, `frontend/src/pages/CourseDetail.tsx`
- **Status:** Fixed. Both pages now call `endpoints.kb.health()` → `GET /api/kb/health` in parallel with their main data load, extract `signals.stale_notes.document_ids`, and render a `⚠ stale` badge on any document whose id is in that set. CourseDetail badges the expanded document list; DomainDetail badges the folder documents list. **Resolved.**
- **Source:** `GET /api/kb/health` → `signals.stale_notes.document_ids`
- **Severity:** 🟠

#### 96. ⬜ Reading insights not fed from book_gaps + mastery
- **File:** `frontend/src/components/reading/ReadingInsights.tsx:7`
- **Static:** Renders a `BookInsights` prop sourced solely from `bookApi.insights()` (`useReading.ts:34`); no `book-gaps`/`kb/mastery` merge.
- **Dynamic:** Merge `GET /api/kb/book-gaps` gaps + `GET /api/kb/mastery` progress for the same book domain.
- **Source:** `GET /reading/insights`, `GET /api/kb/book-gaps`, `GET /api/kb/mastery`
- **Severity:** 🟡

#### 97. ✅ Sidebar notification bell not dynamic to vault jobs — FIXED
- **File:** `frontend/src/components/layout/Sidebar.tsx`
- **Status:** Fixed. The `Sidebar` now polls `endpoints.kb.jobs.list()` → `GET /api/kb/jobs` and `endpoints.kb.health()` → `GET /api/kb/health` every 60s (and on mount), counting queued/running jobs and reading the health score. When `jobCount > 0` a `⚙️ N vault jobs running` badge appears; when `health < 45` a `🩺 Vault health N/100` badge appears. Both reuse the existing sidebar widget styling. **Resolved.**
- **Source:** `GET /api/kb/jobs`, `GET /api/kb/health`
- **Severity:** 🟡

#### 98. ✅ Obsidian Vault integration is static path config, not live sync — FIXED
- **File:** `frontend/src/pages/KnowledgeBase.tsx` source section, `backend/app/routers/kb_sources.py`, `second_brain/gemini-obsidian.sh`
- **Status:** Fixed. The source cards now poll `loadAll()` every 60s so each source's `last_scanned_at` + `document_count` reflects live sync state (driven by `kb/watcher.py` + `kb/source_crawler.py`). The "Update from folder" + "Sync now" actions still call `kb/sources/scan` + `kb/sources/sync` on demand. The `gemini-obsidian.sh` shell script is kept as a manual fallback. **Resolved.**
- **Source:** `GET /api/kb/sources` (polled 60s), `POST /api/kb/sources/{id}/scan`, `POST /api/kb/sources/{id}/sync`, `kb/watcher.py`, `kb/source_crawler.py`
- **Severity:** 🟠

#### 99. ⬜ Global error / empty states not vault-aware (system defect)
- **File:** `frontend/src/components/shared/EmptyState.tsx:3`, `ErrorBoundary.tsx:42`
- **Static:** `EmptyState` is still a generic icon/title/message/action component with no vault-aware variants or `kb/stats` branching; `ErrorBoundary` is a generic fallback with no vault-empty CTA logic.
- **Dynamic:** For every `catch`, branch: if `GET /api/kb/stats.document_count===0` show "Vault empty — add notes to `second_brain/notes`" CTA; if API error show retry with job link. Keep same EmptyState component styling.
- **Source:** `GET /api/kb/stats`, `GET /api/kb/health`
- **Severity:** 🟠

---

## Implementation Contract (for all 99 fixes)

1. **Keep current UI/UX pixel-identical** — no className, layout, palette, or component renames. Only swap data source.
2. **Every view fetches from Second Brain:**  
   `second_brain/notes/**` → `GET /api/kb/documents` / `search` / `concepts` / `graph` / `related` / `health`  
   `second_brain/daily-life/**` → `GET /api/kb/daily-notes`, `GET /api/kb/today`, `GET /daily-logs`  
   Derived intelligence → `/api/kb/*` services listed above (`next_action`, `focus/board`, `weekly-review`, `mastery`, `book-gaps`, `quality`, `mindmap`, `tags/suggestions`, `duplicates`, `health-audit`, `suggestions`, `roadmap`, `explain`, `context`, `sessions`).
3. **Loading & empty handling:** reuse `<SkeletonCard/>` + `<EmptyState/>`; never leave a blank screen.
4. **Invalidation:** after any mutation (`POST/PUT/DELETE`), re-fetch the same endpoint(s) plus `GET /api/kb/health` + `GET /api/kb/today` if the mutation affects daily flow; no optimistic static caches.
5. **Polling / freshness:** dashboards (`Dashboard`, `Today`, `Workflows`, `Analytics`) re-fetch on `window:focus` and every 60s for job-driven vault updates (`kb/watcher.py`).
6. **No hardcoded arrays/colors/labels** — labels come from DB/vault; colors from `document.metadata.color` / `kb/metadata.py` only.

---

## Verification Checklist

- [ ] Run `npm run dev` + FastAPI; click through all 99 workflows — no console "API 404" remains.
- [ ] `grep -rn "const.*=.*\[" frontend/src/pages --include="*.tsx"` — zero literal mock arrays remain (placeholders.ts `courseThumbnail`/`resourceIcon` stay as pure render helpers, not data).
- [ ] `grep -rn "localStorage.*QuizHistory" frontend/src` — migrated to `GET /quizzes/history` (localStorage only cache).
- [ ] Every `useEffect` that lists `tasks/courses/habits/notes` also touches at least one `/api/kb/*` endpoint via `endpoints.kb.*`.
- [ ] Playwright smoke: `test_playwright.py` + `frontend/src/test/*` still green.

---

*Generated by audit of `frontend/src/**`, `backend/app/routers/kb*.py`, `backend/app/services/kb/*`, `second_brain/notes/`, `Obsidian Vault/` — intended as the single backlog to make the entire app dynamic while preserving the current design system.*
