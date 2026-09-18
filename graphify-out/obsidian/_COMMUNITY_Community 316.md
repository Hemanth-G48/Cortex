---
type: community
cohesion: 0.33
members: 6
---

# Community 316

**Cohesion:** 0.33 - loosely connected
**Members:** 6 nodes

## Members
- [[.test_health_surfaces_cache_stats()]] - code - backend/tests/test_ai_cache_insights.py
- [[.test_insights_cached_second_call()]] - code - backend/tests/test_ai_cache_insights.py
- [[.test_insights_fallback_with_seed_data()]] - code - backend/tests/test_ai_cache_insights.py
- [[.test_insights_persisted_survives_cache_clear()]] - code - backend/tests/test_ai_cache_insights.py
- [[TestInsightsEndpoint]] - code - backend/tests/test_ai_cache_insights.py
- [[The DB snapshot (not just the in-memory TTL cache) is reused — a         server]] - rationale - backend/tests/test_ai_cache_insights.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_316
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Community 274]]
- 1 edge to [[_COMMUNITY_Community 10]]

## Top bridge nodes
- [[TestInsightsEndpoint]] - degree 6, connects to 2 communities