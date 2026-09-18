---
type: community
cohesion: 0.09
members: 48
---

# Community 56

**Cohesion:** 0.09 - loosely connected
**Members:** 48 nodes

## Members
- [[.test_all_unknown_when_no_evidence()]] - code - backend/tests/test_kb_mastery.py
- [[.test_classify_needs_min_evidence()]] - code - backend/tests/test_kb_mastery.py
- [[.test_classify_thresholds()]] - code - backend/tests/test_kb_mastery.py
- [[.test_filter_by_subject()]] - code - backend/tests/test_kb_mastery.py
- [[.test_no_events_zero()]] - code - backend/tests/test_kb_mastery.py
- [[.test_quiz_accuracy_raises_score()]] - code - backend/tests/test_kb_mastery.py
- [[.test_strong_topics_excluded()]] - code - backend/tests/test_kb_mastery.py
- [[.test_weak_topics_is_per_user()]] - code - backend/tests/test_kb_mastery.py
- [[Append a learning event and recompute the topic's mastery (phrase 72).]] - rationale - backend/app/services/kb/mastery.py
- [[Bayesian-ish 0–1 score from attempts, accuracy, and recency.      - ``quiz`` eve]] - rationale - backend/app/services/kb/mastery.py
- [[Day-granularity, deterministic FSRS scheduler (empty learnrelearn steps).]] - rationale - backend/app/services/srs.py
- [[FSRS scheduler bounded by the configured max interval (deterministic).]] - rationale - backend/app/services/kb/revision.py
- [[FSRS update for a topic review (phrases 13–14). Grade is 0–5.]] - rationale - backend/app/services/kb/revision.py
- [[Idea 58 — mastery engine + weak-topics endpoint tests.  ``log_event`` recomputes]] - rationale - backend/tests/test_kb_mastery.py
- [[Map a 0–5 review grade to an FSRS 1–4 rating.]] - rationale - backend/app/services/srs.py
- [[Per-day average quiz accuracy for the sparkline (Idea 57).]] - rationale - backend/app/services/kb/mastery.py
- [[Per-subject dashboard payload (Idea 57, phrase 65).]] - rationale - backend/app/services/kb/mastery.py
- [[Phase 6 mastery + learning-event spine (Ideas 57–58).  ``log_event`` is the sing]] - rationale - backend/app/services/kb/mastery.py
- [[Phase 6 revision scheduling — FSRS (Idea 52).  ``apply_review`` runs the Free Sp]] - rationale - backend/app/services/kb/revision.py
- [[Recalculate a topic's mastery score from its events (phrase 71).]] - rationale - backend/app/services/kb/mastery.py
- [[Session_165]] - code
- [[Sum of ``session````study`` minutes ÷ 60 (Idea 57 hours logged).]] - rationale - backend/app/services/kb/mastery.py
- [[TestEngine]] - code - backend/tests/test_kb_mastery.py
- [[TestWeakTopics]] - code - backend/tests/test_kb_mastery.py
- [[Weak  strong  unknown with a minimum-evidence guard (phrase 73).]] - rationale - backend/app/services/kb/mastery.py
- [[_auth()_24]] - code - backend/tests/test_kb_mastery.py
- [[_confirmed()_12]] - code - backend/tests/test_kb_mastery.py
- [[_disable_ai()_24]] - code - backend/tests/test_kb_mastery.py
- [[_mastery_from_events()]] - code - backend/app/services/kb/mastery.py
- [[_scheduler()]] - code - backend/app/services/kb/revision.py
- [[_signup()_57]] - code - backend/tests/test_kb_mastery.py
- [[``{topic_id {score, classification, evidence}}`` for many topics.]] - rationale - backend/app/services/kb/mastery.py
- [[apply_review()]] - code - backend/app/services/kb/revision.py
- [[classify()]] - code - backend/app/services/kb/mastery.py
- [[datetime_5]] - code
- [[grade_to_rating()]] - code - backend/app/services/srs.py
- [[hours_logged()]] - code - backend/app/services/kb/mastery.py
- [[log_event()_1]] - code - backend/app/services/kb/mastery.py
- [[make_scheduler()]] - code - backend/app/services/srs.py
- [[mastery.py]] - code - backend/app/services/kb/mastery.py
- [[mastery_by_topic()]] - code - backend/app/services/kb/mastery.py
- [[progress_payload()]] - code - backend/app/services/kb/mastery.py
- [[quiz_trend()]] - code - backend/app/services/kb/mastery.py
- [[recompute_mastery()]] - code - backend/app/services/kb/mastery.py
- [[revision.py]] - code - backend/app/services/kb/revision.py
- [[subject_events()]] - code - backend/app/services/kb/mastery.py
- [[test_kb_mastery.py]] - code - backend/tests/test_kb_mastery.py
- [[topic_events()]] - code - backend/app/services/kb/mastery.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_56
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Community 100]]
- 12 edges to [[_COMMUNITY_Community 12]]
- 10 edges to [[_COMMUNITY_Community 1]]
- 10 edges to [[_COMMUNITY_Community 32]]
- 9 edges to [[_COMMUNITY_Community 10]]
- 6 edges to [[_COMMUNITY_Community 40]]
- 5 edges to [[_COMMUNITY_Community 120]]
- 5 edges to [[_COMMUNITY_Community 127]]
- 4 edges to [[_COMMUNITY_Community 79]]
- 4 edges to [[_COMMUNITY_Community 189]]
- 4 edges to [[_COMMUNITY_Community 38]]
- 4 edges to [[_COMMUNITY_Community 145]]
- 3 edges to [[_COMMUNITY_Community 162]]
- 3 edges to [[_COMMUNITY_Community 198]]
- 3 edges to [[_COMMUNITY_Community 134]]
- 3 edges to [[_COMMUNITY_Community 144]]
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 273]]
- 2 edges to [[_COMMUNITY_Community 121]]
- 2 edges to [[_COMMUNITY_Community 178]]
- 2 edges to [[_COMMUNITY_Community 179]]
- 2 edges to [[_COMMUNITY_Community 239]]
- 2 edges to [[_COMMUNITY_Community 251]]
- 2 edges to [[_COMMUNITY_Community 181]]
- 1 edge to [[_COMMUNITY_Community 46]]
- 1 edge to [[_COMMUNITY_Community 168]]
- 1 edge to [[_COMMUNITY_Community 106]]
- 1 edge to [[_COMMUNITY_Community 20]]
- 1 edge to [[_COMMUNITY_Community 52]]
- 1 edge to [[_COMMUNITY_Community 9]]

## Top bridge nodes
- [[log_event()_1]] - degree 41, connects to 16 communities
- [[mastery.py]] - degree 34, connects to 14 communities
- [[revision.py]] - degree 29, connects to 12 communities
- [[mastery_by_topic()]] - degree 24, connects to 7 communities
- [[apply_review()]] - degree 13, connects to 5 communities