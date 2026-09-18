---
type: community
cohesion: 0.40
members: 6
---

# Community 311

**Cohesion:** 0.40 - moderately connected
**Members:** 6 nodes

## Members
- [[Auto-detect course subjects and tag documents.          Args         dry_run I]] - rationale - backend/app/routers/kb_auto_subjects.py
- [[Preview what subjects would be detected from your documents.          This does]] - rationale - backend/app/routers/kb_auto_subjects.py
- [[Session_29]] - code
- [[User_14]] - code
- [[detect_and_tag_subjects()]] - code - backend/app/routers/kb_auto_subjects.py
- [[preview_subjects()]] - code - backend/app/routers/kb_auto_subjects.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_311
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 43]]

## Top bridge nodes
- [[detect_and_tag_subjects()]] - degree 5, connects to 2 communities
- [[preview_subjects()]] - degree 5, connects to 2 communities