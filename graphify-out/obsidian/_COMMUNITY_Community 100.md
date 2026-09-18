---
type: community
cohesion: 0.12
members: 29
---

# Community 100

**Cohesion:** 0.12 - loosely connected
**Members:** 29 nodes

## Members
- [[.revision_max_interval()]] - code - backend/app/config.py
- [[API-friendly snapshot of a card's schedule after a review.]] - rationale - backend/app/services/flashcard_srs.py
- [[Cards due now or earlier (``state`` is None for never-reviewed cards).]] - rationale - backend/app/services/flashcard_srs.py
- [[Days until the next due date, for APIdisplay compatibility.]] - rationale - backend/app/services/srs.py
- [[Display ease updated with the SM-2 formula (see module docstring).]] - rationale - backend/app/services/srs.py
- [[FSRS-powered flashcard scheduling (Idea 52 — vendored py-fsrs).  The ``Flashcard]] - rationale - backend/app/services/flashcard_srs.py
- [[Flashcard_1]] - code
- [[Grade a flashcard 0–5, advance its FSRS schedule, persist and return it.]] - rationale - backend/app/services/flashcard_srs.py
- [[Rehydrate an FSRS Card from persisted columns (UTC naive → aware).]] - rationale - backend/app/services/srs.py
- [[Session_112]] - code
- [[Shared FSRS scheduling helpers (Idea 52 — spaced repetition).  Replaces the clas]] - rationale - backend/app/services/srs.py
- [[Treat naive stored datetimes as UTC (the app stores UTC).      Accepts plain ``d]] - rationale - backend/app/services/srs.py
- [[Whole days until due — rounded so sub-second drift never drops a day.]] - rationale - backend/app/services/flashcard_srs.py
- [[_as_utc()]] - code - backend/app/services/srs.py
- [[_ease_delta()]] - code - backend/app/services/srs.py
- [[_interval_from_next()]] - code - backend/app/services/flashcard_srs.py
- [[_now_utc()]] - code - backend/app/services/flashcard_srs.py
- [[card_from_state()]] - code - backend/app/services/srs.py
- [[datetime]] - code
- [[datetime_12]] - code
- [[deck_id → number of due cards (for deck-list badges).]] - rationale - backend/app/services/flashcard_srs.py
- [[due_cards()]] - code - backend/app/services/flashcard_srs.py
- [[due_count_by_deck()]] - code - backend/app/services/flashcard_srs.py
- [[flashcard_srs.py]] - code - backend/app/services/flashcard_srs.py
- [[interval_days()]] - code - backend/app/services/srs.py
- [[review_card()_1]] - code - backend/app/services/flashcard_srs.py
- [[review_payload()]] - code - backend/app/services/flashcard_srs.py
- [[srs.py]] - code - backend/app/services/srs.py
- [[update_legacy_ease()]] - code - backend/app/services/srs.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_100
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Community 56]]
- 7 edges to [[_COMMUNITY_Community 77]]
- 6 edges to [[_COMMUNITY_Community 104]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 93]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 168]]
- 1 edge to [[_COMMUNITY_Community 106]]

## Top bridge nodes
- [[flashcard_srs.py]] - degree 18, connects to 4 communities
- [[srs.py]] - degree 16, connects to 4 communities
- [[card_from_state()]] - degree 10, connects to 2 communities
- [[interval_days()]] - degree 7, connects to 2 communities
- [[review_card()_1]] - degree 9, connects to 1 community