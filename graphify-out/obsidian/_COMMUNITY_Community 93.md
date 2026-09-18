---
type: community
cohesion: 0.06
members: 31
---

# Community 93

**Cohesion:** 0.06 - loosely connected
**Members:** 31 nodes

## Members
- [[.ai_model_list()]] - code - backend/app/config.py
- [[.book_max_upload_bytes()]] - code - backend/app/config.py
- [[.kb_forecast_model()]] - code - backend/app/config.py
- [[.kb_forecast_risk_threshold()]] - code - backend/app/config.py
- [[.kb_memory_anchor_min()]] - code - backend/app/config.py
- [[.kb_memory_consolidation_days()]] - code - backend/app/config.py
- [[.kb_memory_half_life_days()]] - code - backend/app/config.py
- [[.kb_next_action_weights()]] - code - backend/app/config.py
- [[.kb_quality_weights()]] - code - backend/app/config.py
- [[.kb_rag_stages()]] - code - backend/app/config.py
- [[.kb_recommend_weights()]] - code - backend/app/config.py
- [[.kb_recommendation_weights()]] - code - backend/app/config.py
- [[.kb_tesseract_cmd()]] - code - backend/app/config.py
- [[.kb_xp_rewards()]] - code - backend/app/config.py
- [[.max_upload_bytes()]] - code - backend/app/config.py
- [[.revision_initial_interval()]] - code - backend/app/config.py
- [[.revision_min_ease()]] - code - backend/app/config.py
- [[.sleep_target_hours()]] - code - backend/app/config.py
- [[BaseSettings]] - code
- [[Configured tesseract binary path, or None to let pytesseract find it.]] - rationale - backend/app/config.py
- [[Maximum book (PDF) upload size in bytes.]] - rationale - backend/app/config.py
- [[Maximum upload size in bytes.]] - rationale - backend/app/config.py
- [[Primary model + comma-separated fallbacks (deduped, order preserved).]] - rationale - backend/app/config.py
- [[Sanitised Phase 8 recommender weights — clamp negatives, re-normalize.]] - rationale - backend/app/config.py
- [[Sanitised RAG stage switches — known keys, booleans only.]] - rationale - backend/app/config.py
- [[Sanitised capture-XP amounts — clamp to non-negative ints.]] - rationale - backend/app/config.py
- [[Sanitised quality weights — clamp negatives, keep known keys, re-normalize.]] - rationale - backend/app/config.py
- [[Sanitised recommendation weights — clamp negatives, re-normalize.]] - rationale - backend/app/config.py
- [[Sanitised recommender weights — clamp negatives, re-normalize.]] - rationale - backend/app/config.py
- [[Sanitised sleep target, clamped to a healthy 4–14h range.]] - rationale - backend/app/config.py
- [[Settings]] - code - backend/app/config.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_93
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 100]]

## Top bridge nodes
- [[Settings]] - degree 21, connects to 2 communities