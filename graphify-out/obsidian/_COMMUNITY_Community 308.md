---
type: community
cohesion: 0.40
members: 6
---

# Community 308

**Cohesion:** 0.40 - moderately connected
**Members:** 6 nodes

## Members
- [[Fetch Classroom courses; merge into the current user's Course rows.]] - rationale - backend/app/routers/classroom.py
- [[Fetch course work across all courses; merge into Assignment by google_id.]] - rationale - backend/app/routers/classroom.py
- [[Session_10]] - code
- [[User_7]] - code
- [[classroom_assignments()]] - code - backend/app/routers/classroom.py
- [[classroom_courses()]] - code - backend/app/routers/classroom.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_308
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 9]]

## Top bridge nodes
- [[classroom_assignments()]] - degree 5, connects to 2 communities
- [[classroom_courses()]] - degree 5, connects to 2 communities