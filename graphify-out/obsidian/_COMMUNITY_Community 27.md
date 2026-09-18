---
type: community
cohesion: 0.05
members: 64
---

# Community 27

**Cohesion:** 0.05 - loosely connected
**Members:** 64 nodes

## Members
- [[Aggregate mood history total, avg energy, dominant mood, distribution,     and]] - rationale - backend/app/services/mood.py
- [[Aggregate one day's vault documents, schedule blocks, and journal entries.]] - rationale - backend/app/services/kb/daily_notes.py
- [[Base_9]] - code
- [[Base_18]] - code
- [[Base_75]] - code
- [[BaseModel_37]] - code
- [[Daily-note integration (Phase 4, Idea 35).  - ``tag_daily_note`` — auto-tag ``YY]] - rationale - backend/app/services/kb/daily_notes.py
- [[DailyLog]] - code - backend/app/models/daily_log.py
- [[DailyLogBase]] - code - backend/app/schemas/daily_log.py
- [[DailyLogCreate]] - code - backend/app/schemas/daily_log.py
- [[DailyLogResponse]] - code - backend/app/schemas/daily_log.py
- [[DailyLogUpdate]] - code - backend/app/schemas/daily_log.py
- [[JournalEntry]] - code - backend/app/models/journal.py
- [[Mood-driven session design + mood analytics.  Zenith-Study-Planner G2 (Phases 10]] - rationale - backend/app/services/mood.py
- [[MoodLog]] - code - backend/app/models/mood_log.py
- [[Pair each day's mood with a journal snippet + daily-log focus minutes.]] - rationale - backend/app/services/mood.py
- [[Return a day series ending today (zero-filled for missing days).]] - rationale - backend/app/services/mood.py
- [[Server-date convenience wrapper (phrase 45).]] - rationale - backend/app/services/kb/daily_notes.py
- [[Session_13]] - code
- [[Session_26]] - code
- [[Session_38]] - code
- [[Session_145]] - code
- [[Session_209]] - code
- [[Tests for the mood tracking domain (Zenith-Study-Planner G2, Phases 8-14).]] - rationale - backend/tests/test_mood.py
- [[User_23]] - code
- [[_clear_moods()]] - code - backend/tests/test_mood.py
- [[analytics()]] - code - backend/app/services/mood.py
- [[create_daily_log()]] - code - backend/app/routers/daily_logs.py
- [[create_entry()]] - code - backend/app/routers/journal.py
- [[daily_log_stats()]] - code - backend/app/routers/daily_logs.py
- [[daily_logs.py]] - code - backend/app/routers/daily_logs.py
- [[daily_notes()]] - code - backend/app/routers/kb_daily_notes.py
- [[daily_notes.py]] - code - backend/app/services/kb/daily_notes.py
- [[daily_notes_today()]] - code - backend/app/routers/kb_daily_notes.py
- [[date_2]] - code
- [[date_8]] - code
- [[delete_daily_log()]] - code - backend/app/routers/daily_logs.py
- [[delete_journal_entry()]] - code - backend/app/routers/journal.py
- [[get_daily_notes()]] - code - backend/app/services/kb/daily_notes.py
- [[get_today()]] - code - backend/app/services/kb/daily_notes.py
- [[insights()]] - code - backend/app/services/mood.py
- [[list_daily_logs()]] - code - backend/app/routers/daily_logs.py
- [[list_entries()]] - code - backend/app/routers/journal.py
- [[modelsdaily_log.py]] - code - backend/app/models/daily_log.py
- [[modelsjournal.py]] - code - backend/app/models/journal.py
- [[mood_log.py]] - code - backend/app/models/mood_log.py
- [[schemasdaily_log.py]] - code - backend/app/schemas/daily_log.py
- [[servicesmood.py]] - code - backend/app/services/mood.py
- [[test_analytics_aggregates()]] - code - backend/tests/test_mood.py
- [[test_analytics_empty()]] - code - backend/tests/test_mood.py
- [[test_create_mood()]] - code - backend/tests/test_mood.py
- [[test_create_mood_rejects_invalid_mood()]] - code - backend/tests/test_mood.py
- [[test_create_mood_validates_energy_range()]] - code - backend/tests/test_mood.py
- [[test_delete_mood()]] - code - backend/tests/test_mood.py
- [[test_delete_mood_missing_returns_404()]] - code - backend/tests/test_mood.py
- [[test_insights_pairs_journal_snippet()]] - code - backend/tests/test_mood.py
- [[test_list_moods()]] - code - backend/tests/test_mood.py
- [[test_mood.py]] - code - backend/tests/test_mood.py
- [[test_mood_model_import()]] - code - backend/tests/test_mood.py
- [[test_session_params_endpoint()]] - code - backend/tests/test_mood.py
- [[test_weekly_returns_seven_days()]] - code - backend/tests/test_mood.py
- [[test_weekly_zero_fills_missing_days()]] - code - backend/tests/test_mood.py
- [[update_daily_log()]] - code - backend/app/routers/daily_logs.py
- [[weekly()]] - code - backend/app/services/mood.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_27
SORT file.name ASC
```

## Connections to other communities
- 18 edges to [[_COMMUNITY_Community 5]]
- 12 edges to [[_COMMUNITY_Community 10]]
- 10 edges to [[_COMMUNITY_Community 110]]
- 7 edges to [[_COMMUNITY_Community 51]]
- 6 edges to [[_COMMUNITY_Community 7]]
- 5 edges to [[_COMMUNITY_Community 9]]
- 5 edges to [[_COMMUNITY_Community 216]]
- 3 edges to [[_COMMUNITY_Community 14]]
- 2 edges to [[_COMMUNITY_Community 46]]
- 2 edges to [[_COMMUNITY_Community 2]]
- 1 edge to [[_COMMUNITY_Community 92]]
- 1 edge to [[_COMMUNITY_Community 43]]
- 1 edge to [[_COMMUNITY_Community 1]]

## Top bridge nodes
- [[daily_notes.py]] - degree 13, connects to 8 communities
- [[JournalEntry]] - degree 19, connects to 5 communities
- [[test_mood.py]] - degree 23, connects to 4 communities
- [[MoodLog]] - degree 16, connects to 3 communities
- [[get_daily_notes()]] - degree 10, connects to 3 communities