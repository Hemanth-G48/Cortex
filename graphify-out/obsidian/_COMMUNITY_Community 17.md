---
type: community
cohesion: 0.04
members: 85
---

# Community 17

**Cohesion:** 0.04 - loosely connected
**Members:** 85 nodes

## Members
- [[.test_async_ingest_job_completes()]] - code - backend/tests/test_kb_jobs.py
- [[.test_error_capture_sets_failed_status()]] - code - backend/tests/test_kb_jobs.py
- [[.test_jobs_are_user_scoped()]] - code - backend/tests/test_kb_jobs.py
- [[.test_resume_interrupted_flips_stuck_jobs_and_redispatch()]] - code - backend/tests/test_kb_jobs.py
- [[.test_running_job_not_rerun()]] - code - backend/tests/test_kb_jobs.py
- [[.test_scan_job_runs_synchronously_and_is_pollable()]] - code - backend/tests/test_kb_jobs.py
- [[.tmp_db()]] - code - backend/tests/test_kb_jobs.py
- [[AutoJob]] - code - backend/app/services/kb/automation.py
- [[Base_43]] - code
- [[BaseModel_5]] - code
- [[Documents with any Phase 2 dirty flag set (phrase 93).]] - rationale - backend/app/services/kb/reindex.py
- [[Enqueue a Phase 2 reindex job (phrase 96).      Scoped to ``source_id`` when giv]] - rationale - backend/app/services/kb/jobs.py
- [[Enqueue a scan job (and return the KbJob row, phrase 92).      ``subpath`` optio]] - rationale - backend/app/services/kb/jobs.py
- [[Enqueue an ingestreindex job for the given documents.]] - rationale - backend/app/services/kb/jobs.py
- [[Execute a queued job using the provided session (caller owns the close).]] - rationale - backend/app/services/kb/jobs.py
- [[File-based SQLite so worker threads can share the database.]] - rationale - backend/tests/test_kb_jobs.py
- [[Idea 10 — ingestion job queue & status tests submit, await completion, status t]] - rationale - backend/tests/test_kb_jobs.py
- [[Import Phase 9 feature modules so their ``@auto_job`` registrations run.]] - rationale - backend/app/services/kb/automation.py
- [[Ingestion job queue & status (Idea 10).  An in-process ``ThreadPoolExecutor`` (m]] - rationale - backend/app/services/kb/jobs.py
- [[KbDocument_24]] - code
- [[KbJob]] - code - backend/app/models/kb/job.py
- [[KbJob_1]] - code
- [[KbJob_2]] - code
- [[KbJob model — ingestion job queue state (Idea 10).]] - rationale - backend/app/models/kb/job.py
- [[List registered jobs with their gatecap state (for the UI).]] - rationale - backend/app/services/kb/automation.py
- [[Mark every document dirty then run a full reindex (phrase 99).]] - rationale - backend/app/routers/kb_reindex.py
- [[Mark every document dirty, then run a full reindex (phrase 9299).]] - rationale - backend/app/services/kb/reindex.py
- [[One registered Phase 9 automation job.]] - rationale - backend/app/services/kb/automation.py
- [[Phase 9 automation registry + runner (Ideas 81–90).  The one unifying pattern fo]] - rationale - backend/app/services/kb/automation.py
- [[Process dirty documents in stage order (phrase 93-95).      Returns a summary di]] - rationale - backend/app/services/kb/reindex.py
- [[Registered Phase 9 jobs + enabledcap state (for a control UI).]] - rationale - backend/app/routers/kb_automation.py
- [[Run every enabled automation job once, in registry order.]] - rationale - backend/app/services/kb/automation.py
- [[Run one automation job (respecting its toggle unless ``force``).      Persists a]] - rationale - backend/app/services/kb/automation.py
- [[Run one job inline, mutating ``job`` in the caller's session.]] - rationale - backend/app/services/kb/automation.py
- [[Run one named job (``mode=one``) or all enabled jobs (``mode=all``).]] - rationale - backend/app/routers/kb_automation.py
- [[Run synchronously (hermetic) or enqueue on the executor.      In sync mode with]] - rationale - backend/app/services/kb/jobs.py
- [[Run the dirty stages for a single document (phrase 95).      Clears each flag on]] - rationale - backend/app/services/kb/reindex.py
- [[RunRequest]] - code - backend/app/routers/kb_automation.py
- [[Session_30]] - code
- [[Session_62]] - code
- [[Session_134]] - code
- [[Session_163]] - code
- [[Session_187]] - code
- [[Set the given dirty flags on all (optionally source-scoped) documents.      Used]] - rationale - backend/app/services/kb/reindex.py
- [[Startup recovery (phrase 95) flip stuck ``running`` → ``interrupted``,     then]] - rationale - backend/app/services/kb/jobs.py
- [[TestJobApi]] - code - backend/tests/test_kb_jobs.py
- [[TestJobEngine]] - code - backend/tests/test_kb_jobs.py
- [[ThreadPoolExecutor]] - code
- [[Trigger an incremental reindex (phrase 97).      ``source_id=`` scopes the rebu]] - rationale - backend/app/routers/kb_reindex.py
- [[True when jobs should run inline (hermetic CI  tiny vaults).]] - rationale - backend/app/services/kb/jobs.py
- [[User_15]] - code
- [[User_47]] - code
- [[Worker body load the job in a fresh session and execute it.]] - rationale - backend/app/services/kb/jobs.py
- [[Write the job's summary_json, merging caller-set metadata (e.g.     backfill's `]] - rationale - backend/app/services/kb/jobs.py
- [[_dispatch()]] - code - backend/app/services/kb/jobs.py
- [[_execute()]] - code - backend/app/services/kb/automation.py
- [[_load_features()]] - code - backend/app/services/kb/automation.py
- [[_merge_summary()]] - code - backend/app/services/kb/jobs.py
- [[_run_inline()]] - code - backend/app/services/kb/jobs.py
- [[_signup()_52]] - code - backend/tests/test_kb_jobs.py
- [[_source()_3]] - code - backend/tests/test_kb_jobs.py
- [[admin_backfill()]] - code - backend/app/routers/kb_reindex.py
- [[admin_reindex()]] - code - backend/app/routers/kb_reindex.py
- [[automation.py]] - code - backend/app/services/kb/automation.py
- [[backfill()]] - code - backend/app/services/kb/reindex.py
- [[dirty_documents()]] - code - backend/app/services/kb/reindex.py
- [[get_executor()]] - code - backend/app/services/kb/jobs.py
- [[job.py]] - code - backend/app/models/kb/job.py
- [[jobs.py]] - code - backend/app/services/kb/jobs.py
- [[list_automation_jobs()]] - code - backend/app/routers/kb_automation.py
- [[mark_dirty()]] - code - backend/app/services/kb/reindex.py
- [[registered_jobs()]] - code - backend/app/services/kb/automation.py
- [[reindex_documents()]] - code - backend/app/services/kb/reindex.py
- [[resume_interrupted_jobs()]] - code - backend/app/services/kb/jobs.py
- [[run_all()]] - code - backend/app/services/kb/automation.py
- [[run_automation()]] - code - backend/app/routers/kb_automation.py
- [[run_document_stages()]] - code - backend/app/services/kb/reindex.py
- [[run_job()]] - code - backend/app/services/kb/jobs.py
- [[run_one()]] - code - backend/app/services/kb/automation.py
- [[submit_ingest_job()]] - code - backend/app/services/kb/jobs.py
- [[submit_reindex_job()]] - code - backend/app/services/kb/jobs.py
- [[submit_scan_job()]] - code - backend/app/services/kb/jobs.py
- [[sync_mode()]] - code - backend/app/services/kb/jobs.py
- [[test_job_is_registered_and_gated()]] - code - backend/tests/test_auto_course_sync.py
- [[test_kb_jobs.py]] - code - backend/tests/test_kb_jobs.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_17
SORT file.name ASC
```

## Connections to other communities
- 21 edges to [[_COMMUNITY_Community 2]]
- 18 edges to [[_COMMUNITY_Community 5]]
- 6 edges to [[_COMMUNITY_Community 1]]
- 6 edges to [[_COMMUNITY_Community 21]]
- 5 edges to [[_COMMUNITY_Community 10]]
- 5 edges to [[_COMMUNITY_Community 22]]
- 5 edges to [[_COMMUNITY_Community 127]]
- 4 edges to [[_COMMUNITY_Community 169]]
- 3 edges to [[_COMMUNITY_Community 111]]
- 3 edges to [[_COMMUNITY_Community 48]]
- 2 edges to [[_COMMUNITY_Community 243]]
- 2 edges to [[_COMMUNITY_Community 38]]
- 2 edges to [[_COMMUNITY_Community 18]]
- 2 edges to [[_COMMUNITY_Community 31]]
- 2 edges to [[_COMMUNITY_Community 115]]
- 2 edges to [[_COMMUNITY_Community 75]]
- 2 edges to [[_COMMUNITY_Community 16]]
- 2 edges to [[_COMMUNITY_Community 13]]
- 1 edge to [[_COMMUNITY_Community 28]]
- 1 edge to [[_COMMUNITY_Community 90]]
- 1 edge to [[_COMMUNITY_Community 76]]
- 1 edge to [[_COMMUNITY_Community 12]]
- 1 edge to [[_COMMUNITY_Community 116]]
- 1 edge to [[_COMMUNITY_Community 117]]
- 1 edge to [[_COMMUNITY_Community 37]]
- 1 edge to [[_COMMUNITY_Community 86]]
- 1 edge to [[_COMMUNITY_Community 45]]
- 1 edge to [[_COMMUNITY_Community 92]]
- 1 edge to [[_COMMUNITY_Community 62]]

## Top bridge nodes
- [[automation.py]] - degree 31, connects to 13 communities
- [[jobs.py]] - degree 32, connects to 11 communities
- [[KbJob]] - degree 26, connects to 6 communities
- [[_run_inline()]] - degree 14, connects to 5 communities
- [[admin_backfill()]] - degree 11, connects to 5 communities