---
type: community
cohesion: 0.09
members: 63
---

# Community 28

**Cohesion:** 0.09 - loosely connected
**Members:** 63 nodes

## Members
- [[.test_accept_is_user_scoped()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_accept_moves_and_logs_version()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_category_from_frontmatter()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_cross_user_restore_returns_404()]] - code - backend/tests/test_kb_versions.py
- [[.test_diff_between_versions()]] - code - backend/tests/test_kb_versions.py
- [[.test_ignores_pathlike_or_missing()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_never_reproposes_settled_doc()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_proposes_pending_suggestions()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_queue_and_accept_flow()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_reject_keeps_path()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_respects_limit()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_restore_ownership()]] - code - backend/tests/test_kb_versions.py
- [[.test_restore_rolls_back_and_versions_itself()]] - code - backend/tests/test_kb_versions.py
- [[.test_skips_already_folded()]] - code - backend/tests/test_kb_auto_categorize.py
- [[.test_snapshot_on_change_and_noop_on_unchanged()]] - code - backend/tests/test_kb_versions.py
- [[.test_version_cap_enforced()]] - code - backend/tests/test_kb_versions.py
- [[Any prior proposal settles the doc — idempotency across nightly runs.]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Apply approved moves update ``path_rel`` + log the move in version history.]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Auto-categorize tests (Phase 9, Idea 81, phrases 1-10).]] - rationale - backend/tests/test_kb_auto_categorize.py
- [[Base_25]] - code
- [[Base_71]] - code
- [[CategorizeSuggestion]] - code - backend/app/models/kb/categorize_suggestion.py
- [[CategorizeSuggestion model — auto-categorization review queue (Idea 81).  One ro]] - rationale - backend/app/models/kb/categorize_suggestion.py
- [[Deterministic folder signal from frontmatter, or None.      Returns a single-seg]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Idea 81 — auto-categorize new notes into folders (Phase 9 Automation).  The nigh]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Idea 9 — version history & diff tests snapshot-on-change, restore, diff, cap en]] - rationale - backend/tests/test_kb_versions.py
- [[KbDocument_5]] - code
- [[KbDocument_34]] - code
- [[KbVersion]] - code - backend/app/models/kb/version.py
- [[KbVersion model — content snapshots for version history & diff (Idea 9).]] - rationale - backend/app/models/kb/version.py
- [[Pending proposals for the user's review queue (newest first).]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Reject proposals — the doc stays put and is never re-proposed.]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Scan newest-first for categorizeable docs and queue proposals.]] - rationale - backend/app/services/kb/auto_categorize.py
- [[Session_122]] - code
- [[Session_221]] - code
- [[TestAcceptReject]] - code - backend/tests/test_kb_auto_categorize.py
- [[TestCategorySignal]] - code - backend/tests/test_kb_auto_categorize.py
- [[TestClient_3]] - code
- [[TestEndpoints_2]] - code - backend/tests/test_kb_auto_categorize.py
- [[TestRun]] - code - backend/tests/test_kb_auto_categorize.py
- [[TestVersioning_2]] - code - backend/tests/test_kb_versions.py
- [[_current_folder()]] - code - backend/app/services/kb/auto_categorize.py
- [[_doc_id()]] - code - backend/tests/test_kb_versions.py
- [[_has_proposal()]] - code - backend/app/services/kb/auto_categorize.py
- [[_loads()]] - code - backend/app/services/kb/auto_categorize.py
- [[_make_doc()_3]] - code - backend/tests/test_kb_auto_categorize.py
- [[_proposed_path()]] - code - backend/app/services/kb/auto_categorize.py
- [[_scan()_9]] - code - backend/tests/test_kb_versions.py
- [[_serialize()]] - code - backend/app/services/kb/auto_categorize.py
- [[_signup()_13]] - code - backend/tests/test_kb_auto_categorize.py
- [[_signup()_101]] - code - backend/tests/test_kb_versions.py
- [[_source()_4]] - code - backend/tests/test_kb_versions.py
- [[_uid()_5]] - code - backend/tests/test_kb_auto_categorize.py
- [[accept()_2]] - code - backend/app/services/kb/auto_categorize.py
- [[auto_categorize.py]] - code - backend/app/services/kb/auto_categorize.py
- [[categorize_suggestion.py]] - code - backend/app/models/kb/categorize_suggestion.py
- [[category_for_document()]] - code - backend/app/services/kb/auto_categorize.py
- [[queue()_1]] - code - backend/app/services/kb/auto_categorize.py
- [[reject()_2]] - code - backend/app/services/kb/auto_categorize.py
- [[run()_1]] - code - backend/app/services/kb/auto_categorize.py
- [[test_kb_auto_categorize.py]] - code - backend/tests/test_kb_auto_categorize.py
- [[test_kb_versions.py]] - code - backend/tests/test_kb_versions.py
- [[version.py]] - code - backend/app/models/kb/version.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_28
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 2]]
- 7 edges to [[_COMMUNITY_Community 5]]
- 5 edges to [[_COMMUNITY_Community 10]]
- 4 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 38]]
- 4 edges to [[_COMMUNITY_Community 21]]
- 3 edges to [[_COMMUNITY_Community 48]]
- 2 edges to [[_COMMUNITY_Community 43]]
- 2 edges to [[_COMMUNITY_Community 45]]
- 2 edges to [[_COMMUNITY_Community 144]]
- 1 edge to [[_COMMUNITY_Community 271]]
- 1 edge to [[_COMMUNITY_Community 17]]

## Top bridge nodes
- [[KbVersion]] - degree 24, connects to 7 communities
- [[auto_categorize.py]] - degree 20, connects to 5 communities
- [[CategorizeSuggestion]] - degree 17, connects to 4 communities
- [[test_kb_versions.py]] - degree 13, connects to 4 communities
- [[test_kb_auto_categorize.py]] - degree 19, connects to 3 communities