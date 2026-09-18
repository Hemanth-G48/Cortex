---
type: community
cohesion: 0.21
members: 17
---

# Community 201

**Cohesion:** 0.21 - loosely connected
**Members:** 17 nodes

## Members
- [[GET variant of the search endpoint (simple curl  linkable results).]] - rationale - backend/app/routers/kb_search.py
- [[KbSearchItem]] - code - backend/app/schemas/kb.py
- [[KbSearchRequest]] - code - backend/app/schemas/kb.py
- [[KbSearchResponse]] - code - backend/app/schemas/kb.py
- [[Per-user search history + feedback (Idea 29, phrase 89).      The same list back]] - rationale - backend/app/routers/kb_search.py
- [[Privacy delete this user's search events (phrase 89).]] - rationale - backend/app/routers/kb_search.py
- [[Record explicit thumbs updown (or implicit click) on a search result.      Body]] - rationale - backend/app/routers/kb_search.py
- [[Run retrieval in the requested mode (keywordsemantichybrid).      Records the]] - rationale - backend/app/routers/kb_search.py
- [[Search endpoints (Phase 3, Ideas 21–25).  ``GET apikbsearch``  ``POST apik]] - rationale - backend/app/routers/kb_search.py
- [[Session_65]] - code
- [[User_50]] - code
- [[kb_search.py]] - code - backend/app/routers/kb_search.py
- [[purge_search_events()]] - code - backend/app/routers/kb_search.py
- [[search()]] - code - backend/app/routers/kb_search.py
- [[search_events()]] - code - backend/app/routers/kb_search.py
- [[search_feedback()]] - code - backend/app/routers/kb_search.py
- [[search_get()]] - code - backend/app/routers/kb_search.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_201
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Community 5]]
- 7 edges to [[_COMMUNITY_Community 21]]
- 5 edges to [[_COMMUNITY_Community 232]]
- 3 edges to [[_COMMUNITY_Community 135]]
- 2 edges to [[_COMMUNITY_Community 1]]
- 2 edges to [[_COMMUNITY_Community 81]]
- 2 edges to [[_COMMUNITY_Community 74]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 64]]

## Top bridge nodes
- [[kb_search.py]] - degree 27, connects to 8 communities
- [[search()]] - degree 13, connects to 5 communities
- [[purge_search_events()]] - degree 5, connects to 1 community
- [[search_events()]] - degree 5, connects to 1 community
- [[search_feedback()]] - degree 5, connects to 1 community