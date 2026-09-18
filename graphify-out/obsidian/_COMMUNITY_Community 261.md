---
type: community
cohesion: 0.20
members: 11
---

# Community 261

**Cohesion:** 0.20 - loosely connected
**Members:** 11 nodes

## Members
- [[Add missing columns to existing tables (safe to run every startup).]] - rationale - backend/app/database.py
- [[Idempotently create the ``kb_edges(target_concept_id)`` index.      Gap analysis]] - rationale - backend/app/database.py
- [[One-time Second Brain vault migration runner (notes + daily-life).  Moves top-]] - rationale - backend/scripts/migrate_vault.py
- [[Rebuild ``kb_edges`` with a nullable ``target_document_id``.      Knowledge-grap]] - rationale - backend/app/database.py
- [[Rebuild ``quizzes`` with a nullable ``unit_id`` (Idea 33 note quizzes).      Not]] - rationale - backend/app/database.py
- [[_ensure_kb_edges_concept_index()]] - code - backend/app/database.py
- [[_relax_kb_edges_target_document_id()]] - code - backend/app/database.py
- [[_relax_quizzes_unit_id()]] - code - backend/app/database.py
- [[main()_1]] - code - backend/scripts/migrate_vault.py
- [[migrate_schema()]] - code - backend/app/database.py
- [[migrate_vault.py]] - code - backend/scripts/migrate_vault.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_261
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 22]]
- 1 edge to [[_COMMUNITY_Community 111]]
- 1 edge to [[_COMMUNITY_Community 2]]

## Top bridge nodes
- [[migrate_vault.py]] - degree 6, connects to 3 communities
- [[migrate_schema()]] - degree 9, connects to 2 communities
- [[_ensure_kb_edges_concept_index()]] - degree 3, connects to 1 community
- [[_relax_kb_edges_target_document_id()]] - degree 3, connects to 1 community
- [[_relax_quizzes_unit_id()]] - degree 3, connects to 1 community