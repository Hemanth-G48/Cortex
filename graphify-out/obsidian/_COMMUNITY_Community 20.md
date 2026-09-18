---
type: community
cohesion: 0.04
members: 80
---

# Community 20

**Cohesion:** 0.04 - loosely connected
**Members:** 80 nodes

## Members
- [[AI capability + generation endpoints.  Every feature endpoint 1. Tries the Open]] - rationale - backend/app/routers/ai.py
- [[Advanced partial-credit grading (phrases 53–55).]] - rationale - backend/app/services/kb/grading.py
- [[All configured providers with masked credentials (never raw API keys).]] - rationale - backend/app/routers/ai.py
- [[BaseModel]] - code
- [[ChatRequest]] - code - backend/app/routers/ai.py
- [[ChatResponse]] - code - backend/app/routers/ai.py
- [[CompleteRequest]] - code - backend/app/routers/ai.py
- [[CompleteResponse]] - code - backend/app/routers/ai.py
- [[Context-aware AI study companion (Phase 62).      Builds a system prompt from th]] - rationale - backend/app/routers/ai.py
- [[Deterministic 3-question MCQ quiz. Port of Shiori's ``DEMO_QUIZ``.      When con]] - rationale - backend/app/services/ai_fallback.py
- [[Deterministic 4-week plan. Port of Shiori's ``DEMO_PLAN``.]] - rationale - backend/app/services/ai_fallback.py
- [[Deterministic advanced-grading fallback (Idea 66, phrase 56).      Partial credi]] - rationale - backend/app/services/ai_fallback.py
- [[Deterministic card set. Port of Shiori's 5-difficulty prompt map.]] - rationale - backend/app/services/ai_fallback.py
- [[Deterministic extraction. Port of Shiori's ``DEMO_EXTRACTED``.]] - rationale - backend/app/services/ai_fallback.py
- [[Deterministic grading fallback — casewhitespace-insensitive exact match.]] - rationale - backend/app/services/ai_fallback.py
- [[Fetch the provider's current model list and persist it.]] - rationale - backend/app/routers/ai.py
- [[FlashcardsRequest]] - code - backend/app/routers/ai.py
- [[Generate a quiz for a curriculum unit, with fallback.]] - rationale - backend/app/services/quizzes.py
- [[GradeAnswerRequest]] - code - backend/app/routers/ai.py
- [[InsightsRequest]] - code - backend/app/routers/ai.py
- [[Key-point rubric from the topic's chunks (phrase 52).]] - rationale - backend/app/services/kb/grading.py
- [[Live connection test against the provider (short timeout).]] - rationale - backend/app/routers/ai.py
- [[Mark this provider as the activedefault one.]] - rationale - backend/app/routers/ai.py
- [[Ordered model list of the active provider (or env fallbacks).]] - rationale - backend/app/services/ai_client.py
- [[Persisted productivity insights from real user stats (QuestLog pattern).      Th]] - rationale - backend/app/routers/ai.py
- [[Prompt for quiz generation. Returns strict JSON only.]] - rationale - backend/app/services/prompts.py
- [[ProviderCreate]] - code - backend/app/routers/ai.py
- [[ProviderUpdate]] - code - backend/app/routers/ai.py
- [[Public API shape — never exposes the raw API key.]] - rationale - backend/app/services/ai_providers.py
- [[Public stats mirroring QuestLog's ``getAIStatus`` cacheSize block.]] - rationale - backend/app/services/ai_cache.py
- [[Quiz_2]] - code
- [[Quiz generation and scoring service.]] - rationale - backend/app/services/quizzes.py
- [[QuizRequest]] - code - backend/app/routers/ai.py
- [[Rule-based chat assistant response built from real DB context.      Port of Shio]] - rationale - backend/app/services/ai_fallback.py
- [[Score a quiz attempt and return detailed results.]] - rationale - backend/app/services/quizzes.py
- [[Session]] - code
- [[Session_158]] - code
- [[Session_212]] - code
- [[StudyPlanRequest]] - code - backend/app/routers/ai.py
- [[SyllabusRequest]] - code - backend/app/routers/ai.py
- [[True when an AI provider is configured, enabled, and reachable.      Preserves t]] - rationale - backend/app/services/ai_client.py
- [[User_1]] - code
- [[ai.py]] - code - backend/app/routers/ai.py
- [[ai_available()]] - code - backend/app/services/ai_client.py
- [[ai_chat()]] - code - backend/app/routers/ai.py
- [[ai_complete()]] - code - backend/app/routers/ai.py
- [[ai_flashcards()]] - code - backend/app/routers/ai.py
- [[ai_grade_answer()]] - code - backend/app/routers/ai.py
- [[ai_health()]] - code - backend/app/routers/ai.py
- [[ai_insights()]] - code - backend/app/routers/ai.py
- [[ai_models()]] - code - backend/app/routers/ai.py
- [[ai_models()_1]] - code - backend/app/services/ai_client.py
- [[ai_quiz()]] - code - backend/app/routers/ai.py
- [[ai_study_plan()]] - code - backend/app/routers/ai.py
- [[ai_syllabus()]] - code - backend/app/routers/ai.py
- [[build_rubric()]] - code - backend/app/services/kb/grading.py
- [[cache_stats()]] - code - backend/app/services/ai_cache.py
- [[create_provider()]] - code - backend/app/routers/ai.py
- [[delete_provider()]] - code - backend/app/routers/ai.py
- [[demo_flashcards()]] - code - backend/app/services/ai_fallback.py
- [[demo_grade_advanced()]] - code - backend/app/services/ai_fallback.py
- [[demo_grade_answer()]] - code - backend/app/services/ai_fallback.py
- [[demo_quiz()]] - code - backend/app/services/ai_fallback.py
- [[demo_study_plan()]] - code - backend/app/services/ai_fallback.py
- [[demo_syllabus()]] - code - backend/app/services/ai_fallback.py
- [[generate_quiz()]] - code - backend/app/services/quizzes.py
- [[get_registry()]] - code - backend/app/services/ai_providers.py
- [[grade_answer()]] - code - backend/app/services/kb/grading.py
- [[list_providers()]] - code - backend/app/routers/ai.py
- [[local_chat_response()]] - code - backend/app/services/ai_fallback.py
- [[mask_config()]] - code - backend/app/services/ai_providers.py
- [[quiz_prompt()]] - code - backend/app/services/prompts.py
- [[refresh_provider_models()]] - code - backend/app/routers/ai.py
- [[score_attempt()]] - code - backend/app/services/quizzes.py
- [[servicesquizzes.py]] - code - backend/app/services/quizzes.py
- [[set_default_provider()]] - code - backend/app/routers/ai.py
- [[test_fallback_shapes_are_stable()]] - code - backend/tests/test_ai.py
- [[test_import_quizzes_service()]] - code - backend/tests/test_imports.py
- [[test_provider()]] - code - backend/app/routers/ai.py
- [[update_provider()]] - code - backend/app/routers/ai.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_20
SORT file.name ASC
```

## Connections to other communities
- 46 edges to [[_COMMUNITY_Community 1]]
- 11 edges to [[_COMMUNITY_Community 5]]
- 7 edges to [[_COMMUNITY_Community 57]]
- 6 edges to [[_COMMUNITY_Community 74]]
- 6 edges to [[_COMMUNITY_Community 47]]
- 4 edges to [[_COMMUNITY_Community 9]]
- 4 edges to [[_COMMUNITY_Community 12]]
- 4 edges to [[_COMMUNITY_Community 233]]
- 3 edges to [[_COMMUNITY_Community 163]]
- 3 edges to [[_COMMUNITY_Community 103]]
- 3 edges to [[_COMMUNITY_Community 140]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 187]]
- 2 edges to [[_COMMUNITY_Community 2]]
- 2 edges to [[_COMMUNITY_Community 16]]
- 2 edges to [[_COMMUNITY_Community 203]]
- 2 edges to [[_COMMUNITY_Community 37]]
- 2 edges to [[_COMMUNITY_Community 87]]
- 2 edges to [[_COMMUNITY_Community 98]]
- 2 edges to [[_COMMUNITY_Community 38]]
- 1 edge to [[_COMMUNITY_Community 50]]
- 1 edge to [[_COMMUNITY_Community 204]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 273]]
- 1 edge to [[_COMMUNITY_Community 150]]
- 1 edge to [[_COMMUNITY_Community 81]]
- 1 edge to [[_COMMUNITY_Community 40]]
- 1 edge to [[_COMMUNITY_Community 92]]
- 1 edge to [[_COMMUNITY_Community 44]]
- 1 edge to [[_COMMUNITY_Community 128]]
- 1 edge to [[_COMMUNITY_Community 56]]
- 1 edge to [[_COMMUNITY_Community 52]]

## Top bridge nodes
- [[ai_available()]] - degree 55, connects to 20 communities
- [[ai.py]] - degree 50, connects to 8 communities
- [[servicesquizzes.py]] - degree 11, connects to 5 communities
- [[grade_answer()]] - degree 15, connects to 4 communities
- [[ai_chat()]] - degree 12, connects to 4 communities