---
type: community
cohesion: 0.08
members: 51
---

# Community 47

**Cohesion:** 0.08 - loosely connected
**Members:** 51 nodes

## Members
- [[Base_87]] - code
- [[BaseModel_61]] - code
- [[Count summaries generated in the current UTC day.      Global (not per-user) th]] - rationale - backend/app/routers/summaries.py
- [[Gather extracted text for all active materials in the given units.]] - rationale - backend/app/services/ingestion.py
- [[Generate or retrieve a cached summary for the given unit IDs.]] - rationale - backend/app/services/summaries.py
- [[Material_1]] - code
- [[Prompt for a multi-unit summary. Returns strict JSON only.]] - rationale - backend/app/services/prompts.py
- [[Prompt for a single-unit summary. Returns strict JSON only.]] - rationale - backend/app/services/prompts.py
- [[Pydantic schemas for summaries.]] - rationale - backend/app/schemas/summary.py
- [[Return cached ``extracted_text`` or extract from disk and cache it.]] - rationale - backend/app/services/ingestion.py
- [[Session_95]] - code
- [[Session_115]] - code
- [[Session_215]] - code
- [[Summary]] - code - backend/app/models/summary.py
- [[Summary_1]] - code
- [[Summary generation and retrieval router.]] - rationale - backend/app/routers/summaries.py
- [[Summary generation service with caching and fallback.]] - rationale - backend/app/services/summaries.py
- [[SummaryGenerateRequest]] - code - backend/app/schemas/summary.py
- [[SummaryListItem]] - code - backend/app/schemas/summary.py
- [[SummaryResponse]] - code - backend/app/schemas/summary.py
- [[Tests that all new routersmodelsschemasservices import cleanly.]] - rationale - backend/tests/test_imports.py
- [[User_66]] - code
- [[_daily_generation_count()]] - code - backend/app/routers/summaries.py
- [[_demo_key_points()]] - code - backend/app/services/summaries.py
- [[_demo_summary()]] - code - backend/app/services/summaries.py
- [[_unit_key()]] - code - backend/app/services/summaries.py
- [[create_summary()]] - code - backend/app/routers/summaries.py
- [[delete_summary()]] - code - backend/app/services/summaries.py
- [[extract_text_for_units()]] - code - backend/app/services/ingestion.py
- [[find_cached()]] - code - backend/app/services/summaries.py
- [[generate_summary()]] - code - backend/app/services/summaries.py
- [[get_summaries()]] - code - backend/app/routers/summaries.py
- [[list_summaries()]] - code - backend/app/services/summaries.py
- [[multi_unit_summary_prompt()]] - code - backend/app/services/prompts.py
- [[remove_summary()]] - code - backend/app/routers/summaries.py
- [[routerssummaries.py]] - code - backend/app/routers/summaries.py
- [[schemassummary.py]] - code - backend/app/schemas/summary.py
- [[servicessummaries.py]] - code - backend/app/services/summaries.py
- [[summary_prompt()]] - code - backend/app/services/prompts.py
- [[test_import_auth_router()]] - code - backend/tests/test_imports.py
- [[test_import_curriculum_course_model()]] - code - backend/tests/test_imports.py
- [[test_import_ingestion()]] - code - backend/tests/test_imports.py
- [[test_import_institution_model()]] - code - backend/tests/test_imports.py
- [[test_import_quiz_stats_service()]] - code - backend/tests/test_imports.py
- [[test_import_summaries_service()]] - code - backend/tests/test_imports.py
- [[test_import_user_model()]] - code - backend/tests/test_imports.py
- [[test_import_user_schemas()]] - code - backend/tests/test_imports.py
- [[test_imports.py]] - code - backend/tests/test_imports.py
- [[test_text_for_material_returns_empty_on_unsupported_type()]] - code - backend/tests/test_ingestion_errors.py
- [[text_for_material returns empty string when extraction fails.]] - rationale - backend/tests/test_ingestion_errors.py
- [[text_for_material()]] - code - backend/app/services/ingestion.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_47
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 5]]
- 6 edges to [[_COMMUNITY_Community 20]]
- 5 edges to [[_COMMUNITY_Community 42]]
- 5 edges to [[_COMMUNITY_Community 71]]
- 4 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 10]]
- 3 edges to [[_COMMUNITY_Community 74]]
- 3 edges to [[_COMMUNITY_Community 305]]
- 2 edges to [[_COMMUNITY_Community 69]]
- 2 edges to [[_COMMUNITY_Community 154]]
- 2 edges to [[_COMMUNITY_Community 51]]
- 2 edges to [[_COMMUNITY_Community 103]]
- 2 edges to [[_COMMUNITY_Community 57]]
- 1 edge to [[_COMMUNITY_Community 122]]

## Top bridge nodes
- [[test_imports.py]] - degree 33, connects to 8 communities
- [[servicessummaries.py]] - degree 17, connects to 4 communities
- [[routerssummaries.py]] - degree 25, connects to 3 communities
- [[extract_text_for_units()]] - degree 11, connects to 3 communities
- [[generate_summary()]] - degree 17, connects to 2 communities