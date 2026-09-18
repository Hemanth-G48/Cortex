# Brainstorm: Single-User Self-Hosted Features for Cortex

Date: 2026-09-18
Author: brainstorming skill (obra/superpowers)
Context: Cortex — a "Student Life OS" / Second Brain app (FastAPI backend + React 19/TS/Vite frontend).
Constraint: Designed for a **single user running their own instance locally/offline** (self-hosted). No collaboration, no multi-tenancy, no cloud-only features. Everything must work without internet where feasible, and respect local privacy.

---

## Lens: What "Single-User, Self-Hosted, Local" Changes

The existing Cortex is already almost single-user (single-user auth test shim). Framing it explicitly as "I am the only user, I run this on my machine, my data stays local" unlocks a different feature set than the collaborative/Mobile/PWA ideas from the prior brainstorm. The focus shifts to:

- **Privacy-first defaults** — no telemetry, no phone-home, no third-party deps that phone data.
- **Offline-first everywhere** — works on a plane, in a cave, on a train.
- **Self-administration** — backups, migrations, upgrades, and introspection are part of the UX, not afterthoughts.
- **Deep personalization without consent** — since there's only one user, optimize aggressively for *this* person's habits, attention, and workflows.
- **Local compute** — run local LLMs / embed models directly; no reliance on paid APIs.

---

## Existing Self-Host-Ready Pieces (already in Cortex)

- **Local embeddings** — `fastembed` (BAAI/bge-small-en-v1.5, ONNX) runs fully offline.
- **Local file ingestion** — Markdown + PDF + Obsidian sources scanned from local filesystem.
- **SQLite database** — single local DB, easy to back up/migrate.
- **Folder watcher** — detects vault changes live.
- **Backup/restore** — zip export/import of the vault.
- **Auto-sync** — local sync job for course data.
- **Knowledge graph** — built and rendered client-side (sigma.js).

Gaps relative to "truly self-hosted, offline, privacy-first":
- No built-in **backup scheduling / rotation** (manual export only).
- No **local LLM provider** option (only provider registry + fallbacks; default path still leans on a configured provider for some gen tasks).
- No **offline mode toggle** — the app assumes it can reach services.
- No **self-host admin dashboard** (logs, resources, DB health, upgrade status).
- No **migration/versioning** tooling for the schema between upgrades (relies on `COLUMN_MIGRATIONS` idempotent runner but no user-facing migration UI).
- **Auth is a test shim** — fine for one user, but no clean "I am me" single-user identity (no profile avatar/name persistence tied to a real account, no per-user config file).

---

## Feature Ideas — Single-User, Self-Hosted, Local

### 1. Local LLM / Compute

1. **Local LLM provider** — plug `llama.cpp` / `onnxruntime-genai` / `ollama` into the existing `ai_providers` registry so chat, tutoring, summaries, and flashcard generation run without any third-party API key. Falls back to CPU/GPU on the host.
2. **Model downloader + manager** — browse and pull GGUF/ONNX models from the internet once, cache locally, list/switch between them, auto-pick based on size budget. Reuses `embedder`/`ai_cache` plumbing.
3. **Compute scheduling** — queue heavy jobs (reindex, bulk summary, bulk flashcards) to run during off-hours or when the laptop is idle; show progress in a local jobs UI (extends `kb_jobs`).
4. **Cost guard for local compute** — show token/time cost estimates of a local run *before* starting, so the user can decide whether to use local LLM vs. a provider.

### 2. Offline-First & Resilient

5. **Offline mode toggle** — a switch that forces the app to use only local models, local search, and cached data; surface a clear "offline" banner.
6. **Local-first sync for the frontend** — cache the vault index, due flashcards, and pending edits in IndexedDB so the UI works (read + write) with no backend, then merges when the server returns. Extends the existing PWA surface.
7. **Periodic full sync to a second disk** — auto-export the DB + vault to a second path (USB/network mount) on a schedule. Extends `backup` + `auto_sync`.
8. **Network health dashboard** — show which features are online/offline/local-only at a glance.

### 3. Privacy & Security

9. **No-telemetry / privacy report** — a page listing every outbound dependency and why, with a one-click "disable all external calls."
10. **End-to-end encrypted notes** — optional per-document encryption (a passphrase the server never stores) for the most sensitive notes. Extends `kb_documents` with an encrypted blob field.
11. **Local-only auth** — replace the test shim with a single local password / biometrics gate stored in the local DB (no OAuth, no third-party). Single-user by design.
12. **Audit log of your own activity** — every read/search/edit of your vault, queryable, so you can see what the AI "read" and when. Extends `ai_log`/`observability`.

### 4. Self-Administration & Ops

13. **Self-host admin dashboard** — system stats (CPU/mem/disk), DB size + bloat, model cache size, job queue, log tail, "restart server" / "reindex all" buttons.
14. **Schema migration UI** — show pending migrations, run them, show a diff of the schema, with one-click rollback snapshot. Extends `COLUMN_MIGRATIONS`.
15. **Automated backup scheduler + retention** — daily/weekly snapshots, keep N, restore picker. Extends `backup`.
16. **Upgrade checklist** — when you pull a new version, a page walks you through: read changelog, run migrations, reindex if prompted, verify health.

### 5. Deep Personal Automation (only safe for one user)

17. **Attention-aware scheduler** — integrate with a local webcam/mic idle detector (or manual focus state) to auto-schedule heavy jobs only when you're away, and to dim/pause notifications while you study.
18. **Habit loop automation** — define "if this, then that" rules locally: e.g., "when sleep log shows <6h, auto-schedule a lighter study plan and add a caffeine reminder." Extends `habit`/`sleep`/`kb_study`.
19. **Personal model tuning** — let the local LLM fine-tune on your own notes (text-generation fine-tune) so tutoring/chat match *your* voice and knowledge. Local-only, opt-in.
20. **Context profiles** — multiple local "profiles" (e.g., "exam week", "vacation", "deep work") that flip feature flags, notification urgency, and review density together.

### 6. Data Ownership & Portability

21. **Portable vault export** — export any slice (a course, a topic, a notebook) as a portable, re-importable archive with its graph edges, tags, and reviews intact. Extends `kb_backup`/export.
22. **SQLite CLI companion** — ship a tiny helper you can run to `cortex db export|import|stats|defrag` from the shell.
23. **Open format for KB content** — keep the raw Markdown + sidecar JSON (tags, edges, schedule) so the vault is usable outside Cortex in Obsidian/VS Code. Reuses the existing frontmatter + `kb_metadata`.
24. **Daily data snapshot** — a single "data pack" (DB + vault) you can `rsync` anywhere; versioned, restorable.

### 7. Local Intelligence & Insight

25. **Local AI insights about *you*** — weekly "you this week" report: mood/sleep/study correlation, most-procrastinated topics, review backlog aging. Extends `mood`/`sleep`/`study_stats`/`analytics`.
26. **Local recommendation engine without network** — next-review, next-quest, and daily-plan recommendations computed from your local FSRS + graph data (already mostly local).
27. **Spelling/grammar linter over the vault** — run a local model (or `tree-sitter`-based) check over Markdown notes and batch-fix. Extends `kb_quality`.
28. **Unused knowledge finder** — flag documents you haven't touched in 6 months so you can archive/prune them. Extends `kb_health`/`health_audit`.

### 8. Hardware Integration (still local)

29. **e-Ink / Kindle sync** — pull your Kindle highlights and clippings file into the vault as notes + auto-flashcards. Extends `scanner`/ingestion + `flashcards`.
30. **Local USB device import** — plug in a camera/phone, auto-import photos/receipts as dated notes with OCR. Extends `uploads`/`ocr`.
31. **Terminal companion CLI** — a `cortex` CLI to query due flashcards, log mood, add quick notes, or trigger a sync — all offline, all local. First-class terminal UX alongside the GUI.
31. **Local calendar file sync** — read/write CalDAV or a plain `calcurse`/ics file on disk instead of Google Calendar. Extends `daily_schedule`/events.

### 9. Focus & Flow Tools

33. **"Deep work" lock** — a mode that blocks distracting domains (via `/etc/hosts` write on the host, or just a local blocklist enforced by a local proxy you run), logs the session to a quest, and rewards streaks.
34. **Ambient dashboard** — a screensaver/secondary display showing today's plan, upcoming reviews, and a live knowledge-graph visualization of recent connections. Extends `KnowledgeGraphCanvas` + `QuestCentre`.
35. **Time-budget enforcement** — a Pomodoro/duration limiter per topic derived from your roadmap pacing; gently hard-stops you when the budget is used. Extends `pomodoro`/`kb_study`/pacing.

### 10. Knowledge Hygiene & Growth

36. **Automated pruning suggestion** — propose archiving/duplicating/removing stale notes after a configurable TTL of no interaction. Extends `health_audit`/`neardup`.
37. **Mastery gap "lab"** — for weak topics, auto-generate a focused 15-min lab (flashcards + a practice set + an explanation) and schedule it. Extends `kb_labs`/`kb_study`/`kb_practice`.
38. **Reading velocity tracker** — track words-per-minute over ingested books/PDFs and predict completion dates, nudging pacing. Extends `books`/`reading`.
39. **Personal glossary evolution** — extract a definition per concept, show how its explanation evolved as you wrote more about it. Extends `kb_concepts`/`explain`.

---

## Shortlist (Prioritized for the Single-User Self-Hosted Vision)

| Priority | Feature ID | Name | Effort |
|---|---|---|---|
| P0 | #11 | Local-only auth (drop the test shim) | Low |
| P0 | #1 | Local LLM provider via the existing registry | Medium |
| P0 | #15 | Backup scheduler + retention | Medium |
| P0 | #5 | Offline mode toggle | Medium |
| P1 | #13 | Self-host admin dashboard | Medium-High |
| P1 | #10 | Audit log of your own vault activity | Medium |
| P1 | #2 | Model downloader + local manager | Medium-High |
| P1 | #25 | Local "you this week" insight report | Medium |
| P1 | #31 | Terminal companion CLI | Medium |
| P2 | #19 | Personal fine-tuning on your notes | High |
| P2 | #9 | No-telemetry / privacy report page | Medium |
| P2 | #17 | Attention-aware job scheduling | High |
| P2 | #29 | Kindle highlights import | Medium |

---

## Implementation Notes & Interop

- **Local LLM (#1, #2)** slots into the existing `ai_providers`/`ai_client` registry — the cleanest win with the highest leverage (unlocks offline chat/tutor/summary/flashcard generation).
- **#11 (auth)** removes the test shim; for a single self-hosted user this is mostly a local password gate — minimal schema work, high "feel of real product" return.
- **#15, #13, #9, #10** are all "ops/UX polish" that only make sense for self-hosting — bundle them into a single "self-host admin" milestone.
- **#31 (terminal CLI)** pairs well with the existing `backend/main.py` FastAPI app — a thin `typer`/`click` CLI that talks to the local DB directly for offline use.
- **Avoid** any feature that assumes network identity, shared data, or a "platform" — that's the line between self-hosted and collaborative. Cross off anything that needs server-side multi-user state.

---

## Next Step

Pick a P0 cluster to spec next (recommended starter: **Local LLM provider (#1)** — it unlocks most other offline features). Route it through the writing-plans skill for an implementation plan.

Co-authored-by: CommandCodeBot <noreply@commandcode.ai>
