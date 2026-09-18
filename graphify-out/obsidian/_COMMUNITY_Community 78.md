---
type: community
cohesion: 0.16
members: 37
---

# Community 78

**Cohesion:** 0.16 - loosely connected
**Members:** 37 nodes

## Members
- [[.test_accept_all_files_every_detected_subject()]] - code - backend/tests/test_kb_workflows.py
- [[.test_accept_all_leaves_no_subject_docs_queued()]] - code - backend/tests/test_kb_workflows.py
- [[.test_apply_subjects_tags_and_leaves_queue()]] - code - backend/tests/test_kb_workflows.py
- [[.test_confirm_derived_goal()]] - code - backend/tests/test_kb_workflows.py
- [[.test_dismiss_all_clears_queue_without_tagging()]] - code - backend/tests/test_kb_workflows.py
- [[.test_dismiss_all_idempotent_and_window_scoped()]] - code - backend/tests/test_kb_workflows.py
- [[.test_dismiss_leaves_queue_without_tagging()]] - code - backend/tests/test_kb_workflows.py
- [[.test_export_returns_zip_with_manifest()]] - code - backend/tests/test_kb_workflows.py
- [[.test_generate_reflection_creates_row()]] - code - backend/tests/test_kb_workflows.py
- [[.test_manual_tag()]] - code - backend/tests/test_kb_workflows.py
- [[.test_queue_lists_untriaged_documents_with_subjects()]] - code - backend/tests/test_kb_workflows.py
- [[.test_restore_rejects_non_backup()]] - code - backend/tests/test_kb_workflows.py
- [[.test_restore_rejects_path_traversal()]] - code - backend/tests/test_kb_workflows.py
- [[.test_restore_writes_vault_files_but_skips_db_by_default()]] - code - backend/tests/test_kb_workflows.py
- [[.test_stats_endpoint_lightweight_counts()]] - code - backend/tests/test_kb_workflows.py
- [[.test_today_accepts_date_param()]] - code - backend/tests/test_kb_workflows.py
- [[.test_today_deadlines_include_assignments()]] - code - backend/tests/test_kb_workflows.py
- [[.test_today_overview_shape()]] - code - backend/tests/test_kb_workflows.py
- [[.test_triage_stats_pending_scoped_to_window()]] - code - backend/tests/test_kb_workflows.py
- [[.test_weekly_review_payload()]] - code - backend/tests/test_kb_workflows.py
- [[Bulk accept applies course tags + leaves the queue for all docs.]] - rationale - backend/tests/test_kb_workflows.py
- [[Dashboard reminder source counts only, no document payload.]] - rationale - backend/tests/test_kb_workflows.py
- [[Docs with no detected subjects stay in the queue (skipped).]] - rationale - backend/tests/test_kb_workflows.py
- [[Old triaged docs (outside the window) must not shrink ``pending``.]] - rationale - backend/tests/test_kb_workflows.py
- [[TestBackup]] - code - backend/tests/test_kb_workflows.py
- [[TestToday]] - code - backend/tests/test_kb_workflows.py
- [[TestTriage]] - code - backend/tests/test_kb_workflows.py
- [[TestWeeklyReview]] - code - backend/tests/test_kb_workflows.py
- [[Workflow-glue tests Today command center, new-note triage, vault backup, and th]] - rationale - backend/tests/test_kb_workflows.py
- [[_auth()_56]] - code - backend/tests/test_kb_workflows.py
- [[_make_source()_7]] - code - backend/tests/test_kb_workflows.py
- [[_scan()_10]] - code - backend/tests/test_kb_workflows.py
- [[_seed_subject_profile()]] - code - backend/tests/test_kb_workflows.py
- [[_seed_topic()_1]] - code - backend/tests/test_kb_workflows.py
- [[_signup()_103]] - code - backend/tests/test_kb_workflows.py
- [[_uid()_24]] - code - backend/tests/test_kb_workflows.py
- [[test_kb_workflows.py]] - code - backend/tests/test_kb_workflows.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_78
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Community 2]]
- 7 edges to [[_COMMUNITY_Community 92]]
- 6 edges to [[_COMMUNITY_Community 43]]
- 5 edges to [[_COMMUNITY_Community 127]]
- 4 edges to [[_COMMUNITY_Community 9]]
- 3 edges to [[_COMMUNITY_Community 5]]
- 3 edges to [[_COMMUNITY_Community 14]]
- 2 edges to [[_COMMUNITY_Community 120]]
- 2 edges to [[_COMMUNITY_Community 40]]
- 2 edges to [[_COMMUNITY_Community 12]]
- 2 edges to [[_COMMUNITY_Community 35]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 121]]

## Top bridge nodes
- [[test_kb_workflows.py]] - degree 27, connects to 12 communities
- [[.test_triage_stats_pending_scoped_to_window()]] - degree 10, connects to 5 communities
- [[.test_dismiss_all_idempotent_and_window_scoped()]] - degree 8, connects to 4 communities
- [[.test_accept_all_files_every_detected_subject()]] - degree 9, connects to 3 communities
- [[.test_apply_subjects_tags_and_leaves_queue()]] - degree 8, connects to 3 communities