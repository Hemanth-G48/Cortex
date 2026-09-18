---
type: community
cohesion: 0.09
members: 34
---

# Community 86

**Cohesion:** 0.09 - loosely connected
**Members:** 34 nodes

## Members
- [[.find_canonical()]] - code - backend/app/services/kb/__init__.py
- [[.record_duplicate()]] - code - backend/app/services/kb/__init__.py
- [[.test_scan_discovers_and_ingests_documents()]] - code - backend/tests/test_kb_scanner.py
- [[.test_scan_missing_root_returns_empty_summary()]] - code - backend/tests/test_kb_scanner.py
- [[.test_scan_respects_ownership()]] - code - backend/tests/test_kb_scanner.py
- [[.test_scan_subfolder_ingests_only_that_folder()]] - code - backend/tests/test_kb_scanner.py
- [[.test_scan_subfolder_rejects_bad_paths()]] - code - backend/tests/test_kb_scanner.py
- [[.test_status_transitions()]] - code - backend/tests/test_kb_scanner.py
- [[.test_subfolder_scan_escapes_like_wildcards_in_folder_name()]] - code - backend/tests/test_kb_scanner.py
- [[.test_subfolder_scan_scopes_removal_sweep()]] - code - backend/tests/test_kb_scanner.py
- [[A folder whose name contains LIKE wildcards (``%``  ``_``) is         matched l]] - rationale - backend/tests/test_kb_scanner.py
- [[A folder-scoped scan only marks files as deleted when they vanish         INSIDE]] - rationale - backend/tests/test_kb_scanner.py
- [[Earliest row for (user, hash) — the dedupe canonical document.]] - rationale - backend/app/services/kb/__init__.py
- [[Escape LIKE wildcards so a folder name is matched literally.      Vault folder n_1]] - rationale - backend/app/services/kb/scanner.py
- [[Folder watcher scanning (Idea 3).  ``scan_source`` is the core idempotent scan r]] - rationale - backend/app/services/kb/scanner.py
- [[Idempotently scan one source folder. Returns a summary dict.      ``subpath`` (o]] - rationale - backend/app/services/kb/scanner.py
- [[KbDocument_4]] - code
- [[KbDocument_49]] - code
- [[KbSource_5]] - code
- [[Session_116]] - code
- [[Session_193]] - code
- [[TestScanApi]] - code - backend/tests/test_kb_scanner.py
- [[TestScannerService]] - code - backend/tests/test_kb_scanner.py
- [[Update from folder scanning with ``path=`` walks only that         subtree —]] - rationale - backend/tests/test_kb_scanner.py
- [[Upsert the DUPLICATE_OF self-loop edge on the canonical document.          The e]] - rationale - backend/app/services/kb/__init__.py
- [[_doc()_8]] - code - backend/tests/test_kb_scanner.py
- [[_ext_of()_2]] - code - backend/app/services/kb/scanner.py
- [[_like_escape()_1]] - code - backend/app/services/kb/scanner.py
- [[_make_source()_5]] - code - backend/tests/test_kb_scanner.py
- [[_scan()_6]] - code - backend/tests/test_kb_scanner.py
- [[_signup()_86]] - code - backend/tests/test_kb_scanner.py
- [[_uid()_23]] - code - backend/tests/test_kb_scanner.py
- [[scan_source()_1]] - code - backend/app/services/kb/scanner.py
- [[scanner.py]] - code - backend/app/services/kb/scanner.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_86
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 10]]
- 7 edges to [[_COMMUNITY_Community 2]]
- 5 edges to [[_COMMUNITY_Community 22]]
- 4 edges to [[_COMMUNITY_Community 21]]
- 4 edges to [[_COMMUNITY_Community 115]]
- 3 edges to [[_COMMUNITY_Community 1]]
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 127]]
- 2 edges to [[_COMMUNITY_Community 64]]
- 2 edges to [[_COMMUNITY_Community 33]]
- 2 edges to [[_COMMUNITY_Community 48]]
- 1 edge to [[_COMMUNITY_Community 54]]
- 1 edge to [[_COMMUNITY_Community 116]]
- 1 edge to [[_COMMUNITY_Community 176]]
- 1 edge to [[_COMMUNITY_Community 45]]
- 1 edge to [[_COMMUNITY_Community 16]]
- 1 edge to [[_COMMUNITY_Community 72]]
- 1 edge to [[_COMMUNITY_Community 17]]
- 1 edge to [[_COMMUNITY_Community 71]]

## Top bridge nodes
- [[scanner.py]] - degree 19, connects to 11 communities
- [[scan_source()_1]] - degree 20, connects to 8 communities
- [[.record_duplicate()]] - degree 8, connects to 5 communities
- [[.find_canonical()]] - degree 7, connects to 3 communities
- [[.test_subfolder_scan_escapes_like_wildcards_in_folder_name()]] - degree 8, connects to 2 communities