---
type: community
cohesion: 0.07
members: 39
---

# Community 74

**Cohesion:** 0.07 - loosely connected
**Members:** 39 nodes

## Members
- [[Extract a JSON value (object or array) from model output.      Handles ```json f]] - rationale - backend/app/services/ai_client.py
- [[Flatten kb_concepts aliases → {alias canonical_name} (phrase 33).      Returns]] - rationale - backend/app/services/kb/query.py
- [[Full expansion pipeline applied before retrieval (phrase 31).]] - rationale - backend/app/services/kb/query.py
- [[Lowercase + strip punctuation, keep word boundaries (phrase 32).]] - rationale - backend/app/services/kb/query.py
- [[Map tokens to canonical names and OR them into the expansion.]] - rationale - backend/app/services/kb/query.py
- [[Optional LLM query rewrite (phrase 36).      Budget-capped via ``KB_INFER_DAILY_]] - rationale - backend/app/services/kb/query.py
- [[Point the module registry at a temp file + a mock transport.]] - rationale - backend/tests/test_ai.py
- [[Query normalization + expansion (Idea 24).  ``expand`` runs before every retriev]] - rationale - backend/app/services/kb/query.py
- [[Return True when expansion didn't change anything (zero-hit risk).]] - rationale - backend/app/services/kb/query.py
- [[Send a request to the active provider and return text, or None on failure.]] - rationale - backend/app/services/ai_client.py
- [[Session_182]] - code
- [[Tests for the AI foundation (Group 1).  Hermetic every test monkeypatches ``ai_]] - rationale - backend/tests/test_ai.py
- [[_expand_tokens()]] - code - backend/app/services/kb/query.py
- [[_llm_rewrite()]] - code - backend/app/services/kb/query.py
- [[_load_aliases()]] - code - backend/app/services/kb/query.py
- [[_normalize()_1]] - code - backend/app/services/kb/query.py
- [[_registry_with_transport()]] - code - backend/tests/test_ai.py
- [[expand()]] - code - backend/app/services/kb/query.py
- [[extract_json()]] - code - backend/app/services/ai_client.py
- [[generate()]] - code - backend/app/services/ai_client.py
- [[query.py]] - code - backend/app/services/kb/query.py
- [[should_llm_rewrite()]] - code - backend/app/services/kb/query.py
- [[test_ai.py]] - code - backend/tests/test_ai.py
- [[test_ai_chat_fallback_uses_db_context()]] - code - backend/tests/test_ai.py
- [[test_ai_complete_fallback()]] - code - backend/tests/test_ai.py
- [[test_ai_flashcards_demo_fallback()]] - code - backend/tests/test_ai.py
- [[test_ai_grade_answer_exact_match()]] - code - backend/tests/test_ai.py
- [[test_ai_health()]] - code - backend/tests/test_ai.py
- [[test_ai_models()]] - code - backend/tests/test_ai.py
- [[test_ai_quiz_demo_fallback()]] - code - backend/tests/test_ai.py
- [[test_ai_study_plan_demo_fallback()]] - code - backend/tests/test_ai.py
- [[test_ai_syllabus_demo_fallback()]] - code - backend/tests/test_ai.py
- [[test_extract_json()]] - code - backend/tests/test_ai.py
- [[test_extract_json_invalid()]] - code - backend/tests/test_ai.py
- [[test_generate_disabled()]] - code - backend/tests/test_ai.py
- [[test_generate_returns_none_on_connection_error()]] - code - backend/tests/test_ai.py
- [[test_generate_success()]] - code - backend/tests/test_ai.py
- [[test_generate_uses_configured_model()]] - code - backend/tests/test_ai.py
- [[test_import_ai_client()]] - code - backend/tests/test_imports.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_74
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Community 1]]
- 6 edges to [[_COMMUNITY_Community 20]]
- 3 edges to [[_COMMUNITY_Community 47]]
- 3 edges to [[_COMMUNITY_Community 81]]
- 3 edges to [[_COMMUNITY_Community 38]]
- 2 edges to [[_COMMUNITY_Community 29]]
- 2 edges to [[_COMMUNITY_Community 201]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 187]]
- 1 edge to [[_COMMUNITY_Community 233]]
- 1 edge to [[_COMMUNITY_Community 175]]
- 1 edge to [[_COMMUNITY_Community 140]]
- 1 edge to [[_COMMUNITY_Community 252]]

## Top bridge nodes
- [[query.py]] - degree 15, connects to 7 communities
- [[generate()]] - degree 18, connects to 6 communities
- [[test_ai.py]] - degree 23, connects to 3 communities
- [[expand()]] - degree 9, connects to 3 communities
- [[test_import_ai_client()]] - degree 5, connects to 3 communities