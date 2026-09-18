---
type: community
cohesion: 0.19
members: 15
---

# Community 225

**Cohesion:** 0.19 - loosely connected
**Members:** 15 nodes

## Members
- [[Append one snapshot for a scope, pruning to the newest ``HISTORY_CAP``.      Cal]] - rationale - backend/app/services/kb/gap_history.py
- [[Base_39]] - code
- [[Drop a course's history when the course is deleted (no orphaned rows).]] - rationale - backend/app/services/kb/gap_history.py
- [[Gap Analysis history — a compact log of analyses per scope over time.  Every tim]] - rationale - backend/app/services/kb/gap_history.py
- [[GapAnalysisHistory]] - code - backend/app/models/kb/gap_history.py
- [[GapAnalysisHistory model — snapshot log of gap analyses over time.  One row per]] - rationale - backend/app/models/kb/gap_history.py
- [[Reduce a full analysis payload to the diffable snapshot shape.]] - rationale - backend/app/services/kb/gap_history.py
- [[Session_156]] - code
- [[Snapshots for a scope, oldest → newest (chronological for diffing).]] - rationale - backend/app/services/kb/gap_history.py
- [[_compact_snapshot()]] - code - backend/app/services/kb/gap_history.py
- [[delete_course_history()]] - code - backend/app/services/kb/gap_history.py
- [[list_gap_history()]] - code - backend/app/services/kb/gap_history.py
- [[modelskbgap_history.py]] - code - backend/app/models/kb/gap_history.py
- [[record_gap_history()]] - code - backend/app/services/kb/gap_history.py
- [[serviceskbgap_history.py]] - code - backend/app/services/kb/gap_history.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_225
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_Community 60]]
- 3 edges to [[_COMMUNITY_Community 31]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 38]]
- 2 edges to [[_COMMUNITY_Community 30]]
- 2 edges to [[_COMMUNITY_Community 61]]
- 1 edge to [[_COMMUNITY_Community 5]]

## Top bridge nodes
- [[serviceskbgap_history.py]] - degree 10, connects to 4 communities
- [[GapAnalysisHistory]] - degree 10, connects to 3 communities
- [[record_gap_history()]] - degree 9, connects to 2 communities
- [[list_gap_history()]] - degree 7, connects to 2 communities
- [[modelskbgap_history.py]] - degree 4, connects to 2 communities