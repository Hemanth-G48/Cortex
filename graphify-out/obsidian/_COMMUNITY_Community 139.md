---
type: community
cohesion: 0.13
members: 23
---

# Community 139

**Cohesion:** 0.13 - loosely connected
**Members:** 23 nodes

## Members
- [[.__init__()_9]] - code - backend/app/services/kb/backup.py
- [[Build and download the full vault backup zip.]] - rationale - backend/app/routers/kb_backup.py
- [[Build the full vault backup archive as bytes (in-memory zip).]] - rationale - backend/app/services/kb/backup.py
- [[Normalise a zip member to a safe relative path, or None if unsafe.]] - rationale - backend/app/services/kb/backup.py
- [[Path_2]] - code
- [[Resolve the SQLite file path from ``settings.DATABASE_URL``.      Returns ``None]] - rationale - backend/app/services/kb/backup.py
- [[Response]] - code
- [[Restore a vault backup zip.      Vault files are restored into their original so]] - rationale - backend/app/routers/kb_backup.py
- [[Restore an exported backup archive.      Safe by default ``replace_db`` must be]] - rationale - backend/app/services/kb/backup.py
- [[RestoreResult]] - code - backend/app/services/kb/backup.py
- [[Session_31]] - code
- [[Session_135]] - code
- [[UploadFile_2]] - code
- [[User_16]] - code
- [[Workflow glue — vault backup & restore.  ``build_backup_zip`` — one-click snapsh]] - rationale - backend/app/services/kb/backup.py
- [[_db_file_path()]] - code - backend/app/services/kb/backup.py
- [[_safe_member()]] - code - backend/app/services/kb/backup.py
- [[_walk_files()]] - code - backend/app/services/kb/backup.py
- [[backup.py]] - code - backend/app/services/kb/backup.py
- [[build_backup_zip()]] - code - backend/app/services/kb/backup.py
- [[export_backup()]] - code - backend/app/routers/kb_backup.py
- [[restore_backup()]] - code - backend/app/routers/kb_backup.py
- [[restore_zip()]] - code - backend/app/services/kb/backup.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_139
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 2]]
- 3 edges to [[_COMMUNITY_Community 5]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 10]]

## Top bridge nodes
- [[backup.py]] - degree 11, connects to 4 communities
- [[restore_zip()]] - degree 9, connects to 1 community
- [[build_backup_zip()]] - degree 8, connects to 1 community
- [[export_backup()]] - degree 6, connects to 1 community
- [[restore_backup()]] - degree 6, connects to 1 community