---
type: community
cohesion: 0.07
members: 83
---

# Community 18

**Cohesion:** 0.07 - loosely connected
**Members:** 83 nodes

## Members
- [[._list()]] - code - backend/app/schemas/kb.py
- [[A single domain folder, breadcrumb, documents, subfolders.]] - rationale - backend/app/services/kb/domain_service.py
- [[All non-ignored folder paths strictly below ``root`` for one document.      ``Cy]] - rationale - backend/app/services/kb/domain_service.py
- [[Any_1]] - code
- [[Any_10]] - code
- [[Base_38]] - code
- [[Base_37]] - code
- [[Canonical domain tree for a course (or all domains when unscoped).]] - rationale - backend/app/routers/kb_folders.py
- [[Concept names mentioned (MENTIONS) by the folder's documents.]] - rationale - backend/app/services/kb/domain_service.py
- [[Course_5]] - code
- [[Deleting a folder removes its saved gap analysis (no orphaned rows).]] - rationale - backend/tests/test_kb_folders.py
- [[Documents inside a folder — direct children, or recursive when asked.]] - rationale - backend/app/services/kb/domain_service.py
- [[Domain service — the Second Brain folder hierarchy as the canonical model.  Fold]] - rationale - backend/app/services/kb/domain_service.py
- [[Drop the cached domain analyses (after reindexresync — data changed).      Pass]] - rationale - backend/app/services/kb/domain_service.py
- [[FolderGapAnalysis]] - code - backend/app/models/kb/folder_gap.py
- [[FolderGapAnalysis model — saved per-domaintopic Gap Analysis (one row per user]] - rationale - backend/app/models/kb/folder_gap.py
- [[Folders below a course root + per-folder direct document counts.]] - rationale - backend/app/services/kb/domain_service.py
- [[Force a fresh domain Gap Analysis and save it (the only recompute path).]] - rationale - backend/app/routers/kb_folders.py
- [[Gap analysis scoped to one folder's documents (recursive).      Uses the same ac]] - rationale - backend/app/services/kb/domain_service.py
- [[Guarantee the full gap-analysis response shape on every read.      Saved payload]] - rationale - backend/app/services/kb/gap_engine.py
- [[Heading names + heading→document-count hints for a set of documents.]] - rationale - backend/app/services/kb/domain_service.py
- [[Hierarchical domains for a course (top-level domains with children).]] - rationale - backend/app/services/kb/domain_service.py
- [[Humanize a folder name (same rules as course derivation).]] - rationale - backend/app/services/kb/domain_service.py
- [[KbDocument_42]] - code
- [[KbFolder]] - code - backend/app/models/kb/folder.py
- [[KbFolder model — canonical persisted folderdomain entity (Idea folder = source]] - rationale - backend/app/models/kb/folder.py
- [[KbSource_9]] - code
- [[One domain breadcrumb, its documents (direct children), subfolders.]] - rationale - backend/app/routers/kb_folders.py
- [[Return a previously saved domain analysis, or None (mirrors course gaps).]] - rationale - backend/app/services/kb/domain_service.py
- [[Saved domain Gap Analysis, or computed once on the first request.      Persisted]] - rationale - backend/app/routers/kb_folders.py
- [[Second Brain folderdomain endpoints — the folder hierarchy as source of truth.]] - rationale - backend/app/routers/kb_folders.py
- [[Session_43]] - code
- [[Session_147]] - code
- [[Session_231]] - code
- [[TestClient_13]] - code
- [[Tests for the folder-hierarchy-as-source-of-truth model.  The Second Brain folde]] - rationale - backend/tests/test_kb_folders.py
- [[The course's root vault folder, or None.      Folder-derived courses carry ``kb_]] - rationale - backend/app/services/kb/domain_service.py
- [[Upsert ``KbFolder`` rows for every course's child folders; drop stale.      Idem]] - rationale - backend/app/services/kb/domain_service.py
- [[Upsert the analysis payload for a user + folder (one row).]] - rationale - backend/app/services/kb/domain_service.py
- [[User_28]] - code
- [[_domain_concept_names()]] - code - backend/app/services/kb/domain_service.py
- [[_domain_heading_names()]] - code - backend/app/services/kb/domain_service.py
- [[_domain_row()]] - code - backend/tests/test_kb_folders.py
- [[_folder_or_404()]] - code - backend/app/routers/kb_folders.py
- [[_folder_paths_below()]] - code - backend/app/services/kb/domain_service.py
- [[_folder_payload()]] - code - backend/app/services/kb/domain_service.py
- [[_folder_title()_1]] - code - backend/app/services/kb/domain_service.py
- [[_make_doc()_13]] - code - backend/tests/test_kb_folders.py
- [[_make_source()_3]] - code - backend/tests/test_kb_folders.py
- [[_root_for_course()]] - code - backend/app/services/kb/domain_service.py
- [[_scan_course_folders()]] - code - backend/app/services/kb/domain_service.py
- [[_signup()_39]] - code - backend/tests/test_kb_folders.py
- [[_sync()]] - code - backend/tests/test_kb_folders.py
- [[_uid()_13]] - code - backend/tests/test_kb_folders.py
- [[``CybersecurityWeb SecuritySQL Injection.md`` → Course Cybersecurity,     doma]] - rationale - backend/tests/test_kb_folders.py
- [[domain_detail()]] - code - backend/app/services/kb/domain_service.py
- [[domain_gaps()]] - code - backend/app/services/kb/domain_service.py
- [[domain_gaps_endpoint()]] - code - backend/app/routers/kb_folders.py
- [[domain_gaps_reanalyze()]] - code - backend/app/routers/kb_folders.py
- [[domain_service.py]] - code - backend/app/services/kb/domain_service.py
- [[domain_tree()]] - code - backend/app/services/kb/domain_service.py
- [[folder.py]] - code - backend/app/models/kb/folder.py
- [[folder_documents()]] - code - backend/app/services/kb/domain_service.py
- [[folder_gap.py]] - code - backend/app/models/kb/folder_gap.py
- [[get_domain()]] - code - backend/app/routers/kb_folders.py
- [[invalidate_domain_gaps()]] - code - backend/app/services/kb/domain_service.py
- [[kb_folders.py]] - code - backend/app/routers/kb_folders.py
- [[list_domains()]] - code - backend/app/routers/kb_folders.py
- [[load_saved_domain_gaps()]] - code - backend/app/services/kb/domain_service.py
- [[normalize_gap_payload()]] - code - backend/app/services/kb/gap_engine.py
- [[save_domain_gaps()]] - code - backend/app/services/kb/domain_service.py
- [[sync_all_folders()]] - code - backend/app/services/kb/domain_service.py
- [[test_course_content_includes_domains_grid()]] - code - backend/tests/test_kb_folders.py
- [[test_domain_detail_404_for_unknown()]] - code - backend/tests/test_kb_folders.py
- [[test_domain_detail_returns_documents_and_subfolders()]] - code - backend/tests/test_kb_folders.py
- [[test_domain_gaps_compute_once_then_reuse()]] - code - backend/tests/test_kb_folders.py
- [[test_domain_gaps_reanalyze_is_explicit()]] - code - backend/tests/test_kb_folders.py
- [[test_domain_tree_endpoint_returns_hierarchy()]] - code - backend/tests/test_kb_folders.py
- [[test_kb_folders.py]] - code - backend/tests/test_kb_folders.py
- [[test_sync_cleans_domain_gaps_with_stale_folder()]] - code - backend/tests/test_kb_folders.py
- [[test_sync_derives_domain_folders_from_course_folders()]] - code - backend/tests/test_kb_folders.py
- [[test_sync_is_idempotent_and_counts_direct_children()]] - code - backend/tests/test_kb_folders.py
- [[test_sync_removes_stale_domain_when_folder_deleted()]] - code - backend/tests/test_kb_folders.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_18
SORT file.name ASC
```

## Connections to other communities
- 14 edges to [[_COMMUNITY_Community 5]]
- 12 edges to [[_COMMUNITY_Community 2]]
- 7 edges to [[_COMMUNITY_Community 9]]
- 6 edges to [[_COMMUNITY_Community 31]]
- 5 edges to [[_COMMUNITY_Community 10]]
- 4 edges to [[_COMMUNITY_Community 38]]
- 4 edges to [[_COMMUNITY_Community 70]]
- 2 edges to [[_COMMUNITY_Community 29]]
- 2 edges to [[_COMMUNITY_Community 17]]
- 2 edges to [[_COMMUNITY_Community 75]]
- 1 edge to [[_COMMUNITY_Community 54]]
- 1 edge to [[_COMMUNITY_Community 21]]
- 1 edge to [[_COMMUNITY_Community 109]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 99]]

## Top bridge nodes
- [[domain_service.py]] - degree 30, connects to 8 communities
- [[test_kb_folders.py]] - degree 25, connects to 5 communities
- [[KbFolder]] - degree 21, connects to 3 communities
- [[FolderGapAnalysis]] - degree 13, connects to 3 communities
- [[sync_all_folders()]] - degree 13, connects to 3 communities