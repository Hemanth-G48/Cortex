---
type: community
cohesion: 0.14
members: 23
---

# Community 140

**Cohesion:** 0.14 - loosely connected
**Members:** 23 nodes

## Members
- [[._as_bool()]] - code - backend/app/services/ai_providers.py
- [[._coerce()]] - code - backend/app/services/ai_providers.py
- [[._load()]] - code - backend/app/services/ai_providers.py
- [[._save()]] - code - backend/app/services/ai_providers.py
- [[._to_dict()]] - code - backend/app/services/ai_providers.py
- [[.all()]] - code - backend/app/services/ai_providers.py
- [[.api_key_preview()]] - code - backend/app/services/ai_providers.py
- [[.create()]] - code - backend/app/services/ai_providers.py
- [[.refresh_models()]] - code - backend/app/services/ai_providers.py
- [[.remove()]] - code - backend/app/services/ai_providers.py
- [[.set_default()]] - code - backend/app/services/ai_providers.py
- [[.update()]] - code - backend/app/services/ai_providers.py
- [[Enabled-but-incomplete providers must not report AI as available.]] - rationale - backend/tests/test_ai_providers.py
- [[Fetch the live model list from the provider and persist it.]] - rationale - backend/app/services/ai_providers.py
- [[Hand-edited JSON with truefalse strings must parse correctly.]] - rationale - backend/tests/test_ai_providers.py
- [[Lenient bool parse — hand-edited JSON may store truefalse strings.]] - rationale - backend/app/services/ai_providers.py
- [[Loads providers from JSON, exposes CRUD, and resolves the active one.      The l]] - rationale - backend/app/services/ai_providers.py
- [[ProviderConfig]] - code - backend/app/services/ai_providers.py
- [[ProviderRegistry]] - code - backend/app/services/ai_providers.py
- [[test_ai_available_requires_base_url_and_model()]] - code - backend/tests/test_ai_providers.py
- [[test_coerce_handles_string_bools()]] - code - backend/tests/test_ai_providers.py
- [[test_health_reports_active_provider()]] - code - backend/tests/test_ai_providers.py
- [[test_providers_api_404()]] - code - backend/tests/test_ai_providers.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_140
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Community 175]]
- 7 edges to [[_COMMUNITY_Community 258]]
- 7 edges to [[_COMMUNITY_Community 128]]
- 6 edges to [[_COMMUNITY_Community 233]]
- 3 edges to [[_COMMUNITY_Community 20]]
- 1 edge to [[_COMMUNITY_Community 74]]

## Top bridge nodes
- [[ProviderRegistry]] - degree 30, connects to 6 communities
- [[ProviderConfig]] - degree 18, connects to 4 communities
- [[.refresh_models()]] - degree 7, connects to 2 communities
- [[._load()]] - degree 4, connects to 2 communities
- [[test_ai_available_requires_base_url_and_model()]] - degree 4, connects to 2 communities