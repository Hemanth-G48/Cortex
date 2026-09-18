# Brainstorm: Additional Features for Cortex

Date: 2026-09-18
Author: brainstorming skill (obra/superpowers)
Context: Cortex — a "Student Life OS" / Second Brain app. FastAPI backend + React 19/TS/Vite frontend.
Purpose: Generate a menu of meaningful feature additions beyond the current Second Brain, gamification, academic, fitness, and wellness domains.

---

## Existing System Snapshot

Cortex already covers a very broad surface. Key existing domains:

- **Knowledge Base / Second Brain vault** — Markdown + PDF ingestion (local + Obsidian), chunk + fastembed (offline) embeddings, FTS5 + vector store, hybrid search (RRF fusion), knowledge graph (concepts, typed edges, mindmaps), de-dup, triage queue, backup/restore, health audit, weekly review.
- **Curriculum & Courses** — SyllabusAI import, topic DAG, roadmaps, study plans, exam-prep reverse scheduling, materials, enrollments.
- **Study Planning & Execution** — FSRS revision scheduling, weak-topic detection, next-action recommender, micro-sessions + pomodoro, labs, attendance, skill mapping.
- **AI Tutoring & Assessment** — RAG tutor, grounded explanations, auto quizzes/flashcards, adaptive practice, mock tests, interview prep, mistake analysis.
- **Personalization & Learning Memory** — preferences, gap detection, episodic→long-term memory consolidation (half-life decay), next-recommendation, outdated/missing-note suggestions.
- **Gamification / RPG** — quests, daily quests, missions, rewards, character sheet + XP/stats, life areas, quest centre, leaderboard, eisenhower matrix.
- **Fitness Hub** — workouts, goals, exercises, muscle groups, splits, PRs, diet plans, weight/membership, expenses.
- **Wellness** — mood + analytics/insights, sleep tracking + bedtime recommendations.
- **Tasks & Productivity** — todos, reminders, schedule, projects, notes, pomodoro, daily logs, brain dumps, calendar, Eisenhower matrix, notifications, analytics heatmap.
- **Integrations** — Google OAuth (Classroom/Gmail/Calendar read-only, test-shim auth), syllabus/course sync.

### Identified Gaps (from audit)
- Auth is a single-user test shim — no real multi-user auth, roles, or data isolation beyond the `current_user` filter.
- KB automation jobs (auto-categorize, auto-tag, auto-link, auto-dupes, auto-flashcards, auto-summary, auto-mindmap, auto-local-sync, auto-revision) ship default-OFF.
- Embeddings are local-only — no provider fallback path in production.
- No real-time/websocket — job progress and vault changes rely on polling.
- Global `search` router is thin (1 route) vs. rich `kb_search`.
- Books router is minimal (6 routes) while KB book-gap analyzer is rich.
- No mobile/PWA offline story, no native companion.
- No collaborative features — explicitly single-user.
- Google integration UIs (Classroom/Gmail/Calendar) and auth pages are missing in the frontend.

---

## Feature Ideas, Grouped by Domain

### 1. Deepen Second Brain (Collaboration, Mobility, Voice)

1. **Collaborative multi-user vault** — shared notes, inline comments / @mentions, presence (live cursors), permission scopes (view / comment / edit). Extends the existing KB document + edge model with ownership + ACL fields.
2. **Cross-vault linking** — import/sync a second vault (external Obsidian, Notion, Logseq) and create bidirectional links beyond the current "Copy Recent Notes" local adapter. Feeds into the existing knowledge graph + `kb_edges`.
3. **Two-way calendar sync** — currently read-only Google Calendar; add write-back of tasks, deadlines, and scheduled events. Extends `calendar` router + `daily_schedule`/`reminders` services.
4. **Voice journal / audio notes** — record audio → speech-to-text → transcript ingested as a KB document (OCR exists; STT does not). Taps the existing `text_extractor` + `pipeline` ingestion path.
5. **Weekly sprint planning** — turn the weekly review into an executable sprint: promote reflection-derived goals into quests/tasks with a start/end cadence and progress rollup. Extends `weekly_review` + `quests`/`tasks`.
6. **Local-first conflict-safe sync (CRDT-lite)** — make the vault work fully offline then merge on reconnect, using last-writer-wins + vector clocks for the document/chunk tables. Extends `kb_documents`/`pipeline` with merge semantics.

### 2. Academic Superpowers (LMS, ML, Cohorts)

7. **LMS integrations** — Canvas/Blackboard ingest (in addition to Google Classroom) for assignments, grades, and syllabi. New `lms_<provider>` router + `classroom_sync`-style adapter.
8. **Cohort / shared analytics dashboards** — class-wide performance, ranking, and insight sharing (grades is currently per-user). New cohort model + shared `analytics` view.
9. **Predictive GPA / exam-score modeling (ML)** — `forecast` is EWMA/linear; add regression over historical grades, attendance, mood, and study minutes to predict final grades and recommend target scores ("needed on final"). Extends `forecast` + `grade_calc` + `study_stats`.
10. **Automated assignment sourcing** — when an assignment is created from a linked book/course, auto-pull relevant KB documents, flashcards, and practice questions. Extends `courses`/`kb_subjects`/`flashcards`/`quizzes`.
11. **Plagiarism / quality check for submissions** — run brain-dump / summary outputs through the existing quality scoring + citation registry before they're treated as "final" notes. Extends `kb_quality` + `citation_registry`.

### 3. Mobile / Offline-First

12. **Progressive Web App (PWA) with offline** — existing app is desktop browser; add service worker, offline caching of the vault index + flashcards, and background sync. Extends `vite.config.ts` + `frontend/src/`.
13. **Native mobile wrapper** — Capacitor/Cordova shell for iOS/Android with push notifications for streaks, review due, sleep/mood reminders. New mobile target.
14. **Push + local notifications** — fire review-due, habit-streak, sleep-window, and quest-deadline reminders from the backend. Extends `notifications` + `reminders` + `sleep`/`habit` services.
15. **Offline flashcard/practice mode** — cache a user's due flashcards and practice queue locally so study works without network. Extends `kb_study` + `kb_practice` + service worker.

### 4. Social Learning

16. **Peer study groups** — create/join groups, group study plans, shared quest campaigns, group leaderboards. New `groups` model + extends `quests`/`missions`/`leaderboard`.
17. **Collaborative mocks & peer review** — group-created mock tests, peer answer review, and group mistake-analysis feeds. Extends `kb_practice` (mocks/interview).
18. **Skill showcase / portfolio export** — render a shareable "learning portfolio" (topics mastered, XP, quests, reflections) as a PDF/Markdown doc. Extends `kb_skills` + `reflections` + `character`.
19. **Mentorship / tutoring marketplace (in-product)** — connect stronger students with those struggling on specific topics; queue + reputation. Extends `topics` mastery + `quests` rewards.

### 5. Accessibility & Experience

20. **Full keyboard-first navigation + screen-reader labels** — extend existing shortcut modal with a11y focus management and ARIA labels across components.
21. **Dark / light / high-contrast theme toggle** — `ThemeSwitcher` exists but no themes/ dir; add real theme tokens.
22. **Visual preference for "calm" mode** — reduce gamification UI for deep-focus study (disable XP pop-ups, animated quest cards). Extends `quest_centre`/`rewards` with a focus flag.
23. **Dashboard widgets marketplace** — let users pick/extend dashboard widgets (habit heat, upcoming deadlines, weak topics) beyond the fixed set. Extends `dashboard/` + `widgets/`.

### 6. Content Creation & Publishing

24. **Publish KB documents to a personal site / blog** — export selected notes/flashcards as Markdown/HTML with the knowledge graph embedded. Extends `kb_documents` + `kb_backup`.
25. **Book → interactive syllabus** — when importing a book, auto-generate a study syllabus (chapters → topics → spaced schedule + quizzes). Extends `books` + `kb_subjects` + `kb_study`.
26. **AI-generated lecture companion** — for a course, produce a per-topic mini-lecture script + glossary from documents. Extends `kb_tutor` + `kb_content` summary/explain.

### 7. Data & Integrations

27. **Anki export/import** — sync FSRS flashcards to Anki for review on other devices. Extends `kb_practice`/flashcard review + `kb_backup`.
28. **Notion-style database views in the vault** — Kanban / calendar / table views over KB documents or tasks, saved as views. Extends `kb_documents`/`tasks` + `daily_notes`.
29. **Web clipper / browser extension** — one-click save the current page → KB document + auto-tag/categorize. Extends `uploads`/`scanner` to ingest URLs.
30. **Obsidian-style graph view polish** — the knowledge graph is already built; add themed styling, node collapse/expand by concept, and focus-mode highlighting (extends existing `KnowledgeGraphCanvas`/`MindMapView`).

### 8. Observability & Quality

31. **Automated A/B harness for prompts** — `observability`/`prompts` CRUD exist but no routing harness; let the AI tutor serve variant prompts and log win rates. Extends `ai`/`kb_observability`.
32. **Data-quality dashboard** — surface stale/outdated notes, missing backlinks, orphan documents, and broken edges in one pane. Extends `health_audit` + `kb_edges` + `neardup`.
33. **Usage heatmaps per surface** — extend existing `analytics`/heatmap from study to all screens (where do users linger / drop off).

---

## Shortlist (Prioritized, Quick Wins First)

| Priority | Feature ID | Name | Why now / value |
|---|---|---|---|
| P0 | #5 | Weekly sprint planning | Ties existing weekly review + quests/tasks into an executable cycle — low backend lift, high behavior-change value. |
| P0 | #20 | Full keyboard-first nav + a11y | Extends existing shortcuts; makes the dense RPG/dashboard usable by power users. |
| P1 | #2 | Cross-vault linking (Obsidian/Notion) | Users already keep second vaults; bidirectional sync into the graph is a killer combo. |
| P1 | #13 | Push/local notifications | Leverages existing `notifications`/`reminders`; huge retention/usage lift for reviews + streaks. |
| P1 | #25 | Book → interactive syllabus | Uses existing book analyzer + curriculum DAG + study planner; turns passive books into active study plans. |
| P2 | #1 | Collaborative multi-user vault | Biggest lift (auth/role rework) but unlocks team study + shared knowledge. Do after auth refactor. |
| P2 | #7 | LMS integrations (Canvas/Blackboard) | Extends the working Classroom sync pattern; high academic-value. |
| P2 | #14 | Offline flashcard mode | Extends existing PWA/service worker + FSRS; strong mobile story enabler. |
| P3 | #9 | Predictive GPA/ML modeling | Extends `forecast`; useful but needs clean historical data first. |
| P3 | #16 | Peer study groups | Rich social layer; best paired with the collaborative vault. |

---

## Implementation Notes & Interop

- **Auth refactor is a gating dependency** for multi-user (#1), cohort analytics (#8), and mentorship (#19). The current `current_user` filter + test shim must become real auth with roles before shared data is safe.
- **Most ideas plug into existing services** — `pipeline`, `jobs`, `embedder`, `graph`, `fsrs`, `weekly_review`, `quests`, `notifications`. Few need brand-new tables; most extend existing models.
- **Offline-first (#6, #12, #14) needs a sync-strategy decision** before coding: CRDT-lite vs. server-is-authority with background sync.
- **Social features (#1, #16, #17) imply a new `groups`/shared-entity ownership model** and per-resource ACLs — design the permission model before any group UI.
- **Content-publishing (#24) and cross-vault linking (#2) both produce "exports"** — keep these behind feature flags and reuse `kb_backup`'s zip/export plumbing.

---

## Next Step

Pick the P0/P1 items you want to tackle next and route through the writing-plans skill for an implementation plan. Suggested starter sequence:

1. **#5 Weekly sprint planning** (wired to quests/tasks) — short design + plan.
2. **#13 Push/local notifications** — extends `notifications` + `reminders`.
3. **#25 Book → interactive syllabus** — extends `books` + `kb_subjects` + `kb_study`.

Co-authored-by: CommandCodeBot <noreply@commandcode.ai>
