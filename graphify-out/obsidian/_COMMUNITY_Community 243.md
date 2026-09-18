---
type: community
cohesion: 0.22
members: 13
---

# Community 243

**Cohesion:** 0.22 - loosely connected
**Members:** 13 nodes

## Members
- [[Mark everything dirty and run a full reindex (phrase 9299).]] - rationale - backend/app/cli/kb.py
- [[Print per-user Knowledge Core statistics (phrase 20).]] - rationale - backend/app/cli/kb.py
- [[Rebuild the FTS5 index from kb_chunks (Idea 21, phrase 10).]] - rationale - backend/app/cli/kb.py
- [[Run retrieval evaluation over the golden sets (Idea 26, phrase 53).]] - rationale - backend/app/cli/kb.py
- [[Run the Phase 2 incremental reindex coordinator (phrase 91).]] - rationale - backend/app/cli/kb.py
- [[Second Brain CLI (Phase 2 + Phase 3).  Usage     python -m app.cli.kb reindex]] - rationale - backend/app/cli/kb.py
- [[clikb.py]] - code - backend/app/cli/kb.py
- [[cmd_backfill()]] - code - backend/app/cli/kb.py
- [[cmd_reindex()]] - code - backend/app/cli/kb.py
- [[cmd_stats()]] - code - backend/app/cli/kb.py
- [[main()]] - code - backend/app/cli/kb.py
- [[rebuild_fts()]] - code - backend/app/cli/kb.py
- [[run_eval()]] - code - backend/app/cli/kb.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_243
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 2]]
- 3 edges to [[_COMMUNITY_Community 97]]
- 3 edges to [[_COMMUNITY_Community 72]]
- 2 edges to [[_COMMUNITY_Community 17]]
- 1 edge to [[_COMMUNITY_Community 5]]

## Top bridge nodes
- [[clikb.py]] - degree 12, connects to 4 communities
- [[main()]] - degree 7, connects to 1 community
- [[rebuild_fts()]] - degree 5, connects to 1 community
- [[cmd_backfill()]] - degree 4, connects to 1 community
- [[cmd_reindex()]] - degree 4, connects to 1 community