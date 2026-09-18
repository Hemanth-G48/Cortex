---
type: community
cohesion: 0.05
members: 88
---

# Community 14

**Cohesion:** 0.05 - loosely connected
**Members:** 88 nodes

## Members
- [[Add ``habit.xp_reward`` to the user + character wallet; return xp_change.]] - rationale - backend/app/services/habit_xp.py
- [[Aggregate ``{total_xp, level, current_streak, good_today, bad_today, xp_to_next}]] - rationale - backend/app/services/habit_xp.py
- [[Aggregate counts, wallet, life-area totals and available rewards.]] - rationale - backend/app/routers/habit_tracker.py
- [[Alias only bad habits (spec URL surface).]] - rationale - backend/app/routers/habits.py
- [[Alias only good habits (spec URL surface).]] - rationale - backend/app/routers/habits.py
- [[Any_5]] - code
- [[Attribute a positive XP change to a life area's all-time total.]] - rationale - backend/app/services/habit_xp.py
- [[Base_16]] - code
- [[BaseModel_43]] - code
- [[Character_1]] - code
- [[Completed-habit calendar rows HabitLogs grouped by date.]] - rationale - backend/app/routers/habits.py
- [[Did-Today aggregation every habit with ``log_today`` + ``xp_today``.]] - rationale - backend/app/routers/habits.py
- [[Fitness Hub (Phase 84) edit only the habit's goal text.]] - rationale - backend/app/routers/habits.py
- [[Gamification engine for the Gamified Habit Tracker (Gold & Punishment).  Eac]] - rationale - backend/app/services/habit_xp.py
- [[Gamified Habit Tracker dashboard endpoints.  Composes the ``habit_xp`` service h]] - rationale - backend/app/routers/habit_tracker.py
- [[Gamified Habit Tracker seed data (99-phase plan, Phases 25-31).      Idempotent]] - rationale - backend/app/seed/__init__.py
- [[Good → ``current_streak += 1`` (+ longest); Bad → ``days_caught += 1``.]] - rationale - backend/app/services/habit_xp.py
- [[Habit]] - code - backend/app/models/habit.py
- [[Habit_2]] - code
- [[HabitBase]] - code - backend/app/schemas/habit.py
- [[HabitCreate]] - code - backend/app/schemas/habit.py
- [[HabitLog]] - code - backend/app/models/habit.py
- [[HabitLog_1]] - code
- [[HabitLogBase]] - code - backend/app/schemas/habit.py
- [[HabitLogCreate]] - code - backend/app/schemas/habit.py
- [[HabitLogReorder]] - code - backend/app/schemas/habit.py
- [[HabitLogResponse]] - code - backend/app/schemas/habit.py
- [[HabitLogUpdate]] - code - backend/app/schemas/habit.py
- [[HabitResponse]] - code - backend/app/schemas/habit.py
- [[LifeArea_1]] - code
- [[Log a completion; awardpenalize XP via the habit_xp engine.]] - rationale - backend/app/routers/habits.py
- [[New visual order of log ids within a calendar day (Phase 91).]] - rationale - backend/app/schemas/habit.py
- [[Partial updates for habit logs (all fields optional).      Editing a log (e.g. t]] - rationale - backend/app/schemas/habit.py
- [[Per-day arrays for the current week (Mon..Sun).      Combines Task.due_date, Sch]] - rationale - backend/app/routers/vault.py
- [[Persist a day column's visual order (Phase 91 drag-and-drop).      ``log_ids`` l]] - rationale - backend/app/routers/habits.py
- [[Persist a spec-consistent ``HabitLog`` and apply XP + streak side effects.]] - rationale - backend/app/services/habit_xp.py
- [[Row counts for the vault Quick Action 'Database' link.]] - rationale - backend/app/routers/vault.py
- [[Seed the 4 vault habits with color themes + sample logs. Idempotent  append-onl]] - rationale - backend/app/seed/__init__.py
- [[Session_24]] - code
- [[Session_25]] - code
- [[Session_98]] - code
- [[Session_114]] - code
- [[Sidebar Status-Window wizard card + habit Today's Stats list.]] - rationale - backend/app/routers/habit_tracker.py
- [[Subtract ``habit.xp_penalty`` from both wallets, floored at 0.]] - rationale - backend/app/services/habit_xp.py
- [[User_72]] - code
- [[_character_for()]] - code - backend/app/services/habit_xp.py
- [[archive_habit()]] - code - backend/app/routers/habits.py
- [[award_good_habit()]] - code - backend/app/services/habit_xp.py
- [[bump_streak()]] - code - backend/app/services/habit_xp.py
- [[create_habit()]] - code - backend/app/routers/habits.py
- [[create_habit_log()]] - code - backend/app/routers/habits.py
- [[credit_life_area()]] - code - backend/app/services/habit_xp.py
- [[date_1]] - code
- [[date_5]] - code
- [[delete_habit()]] - code - backend/app/routers/habits.py
- [[delete_habit_log()]] - code - backend/app/routers/habits.py
- [[get_habit()]] - code - backend/app/routers/habits.py
- [[habit_gamification_summary()]] - code - backend/app/services/habit_xp.py
- [[habit_heatmap()]] - code - backend/app/routers/habits.py
- [[habit_logs_calendar()]] - code - backend/app/routers/habits.py
- [[habit_stats()]] - code - backend/app/routers/habits.py
- [[habit_tracker.py]] - code - backend/app/routers/habit_tracker.py
- [[habit_tracker_status_window()]] - code - backend/app/routers/habit_tracker.py
- [[habit_tracker_summary()]] - code - backend/app/routers/habit_tracker.py
- [[habit_xp.py]] - code - backend/app/services/habit_xp.py
- [[habits.py]] - code - backend/app/routers/habits.py
- [[habits_today()]] - code - backend/app/routers/habits.py
- [[list_bad_habits()]] - code - backend/app/routers/habits.py
- [[list_good_habits()]] - code - backend/app/routers/habits.py
- [[list_habit_logs()]] - code - backend/app/routers/habits.py
- [[list_habits()]] - code - backend/app/routers/habits.py
- [[modelshabit.py]] - code - backend/app/models/habit.py
- [[penalize_bad_habit()]] - code - backend/app/services/habit_xp.py
- [[record_log()]] - code - backend/app/services/habit_xp.py
- [[reorder_habit_logs()]] - code - backend/app/routers/habits.py
- [[schemashabit.py]] - code - backend/app/schemas/habit.py
- [[seed_habit_tracker()]] - code - backend/app/seed/__init__.py
- [[seed_vault_habits()]] - code - backend/app/seed/__init__.py
- [[timedelta]] - code
- [[unarchive_habit()]] - code - backend/app/routers/habits.py
- [[update_habit()]] - code - backend/app/routers/habits.py
- [[update_habit_goal()]] - code - backend/app/routers/habits.py
- [[update_habit_log()]] - code - backend/app/routers/habits.py
- [[vault.py]] - code - backend/app/routers/vault.py
- [[vault_calendar()]] - code - backend/app/routers/vault.py
- [[vault_database_counts()]] - code - backend/app/routers/vault.py
- [[vault_summary()]] - code - backend/app/routers/vault.py
- [[vault_tasks()]] - code - backend/app/routers/vault.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_14
SORT file.name ASC
```

## Connections to other communities
- 26 edges to [[_COMMUNITY_Community 5]]
- 22 edges to [[_COMMUNITY_Community 10]]
- 18 edges to [[_COMMUNITY_Community 51]]
- 10 edges to [[_COMMUNITY_Community 7]]
- 9 edges to [[_COMMUNITY_Community 127]]
- 5 edges to [[_COMMUNITY_Community 126]]
- 4 edges to [[_COMMUNITY_Community 138]]
- 4 edges to [[_COMMUNITY_Community 35]]
- 4 edges to [[_COMMUNITY_Community 40]]
- 3 edges to [[_COMMUNITY_Community 123]]
- 3 edges to [[_COMMUNITY_Community 199]]
- 3 edges to [[_COMMUNITY_Community 9]]
- 3 edges to [[_COMMUNITY_Community 106]]
- 3 edges to [[_COMMUNITY_Community 27]]
- 3 edges to [[_COMMUNITY_Community 78]]
- 2 edges to [[_COMMUNITY_Community 187]]
- 2 edges to [[_COMMUNITY_Community 66]]
- 2 edges to [[_COMMUNITY_Community 125]]
- 2 edges to [[_COMMUNITY_Community 155]]
- 2 edges to [[_COMMUNITY_Community 41]]
- 2 edges to [[_COMMUNITY_Community 105]]
- 2 edges to [[_COMMUNITY_Community 134]]
- 2 edges to [[_COMMUNITY_Community 43]]
- 2 edges to [[_COMMUNITY_Community 171]]
- 2 edges to [[_COMMUNITY_Community 172]]
- 2 edges to [[_COMMUNITY_Community 29]]
- 2 edges to [[_COMMUNITY_Community 46]]
- 2 edges to [[_COMMUNITY_Community 144]]
- 1 edge to [[_COMMUNITY_Community 161]]
- 1 edge to [[_COMMUNITY_Community 326]]
- 1 edge to [[_COMMUNITY_Community 89]]
- 1 edge to [[_COMMUNITY_Community 204]]
- 1 edge to [[_COMMUNITY_Community 188]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 185]]
- 1 edge to [[_COMMUNITY_Community 98]]
- 1 edge to [[_COMMUNITY_Community 145]]
- 1 edge to [[_COMMUNITY_Community 237]]
- 1 edge to [[_COMMUNITY_Community 206]]
- 1 edge to [[_COMMUNITY_Community 219]]
- 1 edge to [[_COMMUNITY_Community 227]]
- 1 edge to [[_COMMUNITY_Community 297]]
- 1 edge to [[_COMMUNITY_Community 194]]
- 1 edge to [[_COMMUNITY_Community 107]]
- 1 edge to [[_COMMUNITY_Community 180]]
- 1 edge to [[_COMMUNITY_Community 152]]

## Top bridge nodes
- [[timedelta]] - degree 85, connects to 40 communities
- [[vault.py]] - degree 18, connects to 6 communities
- [[Habit]] - degree 39, connects to 5 communities
- [[seed_habit_tracker()]] - degree 11, connects to 5 communities
- [[HabitLog]] - degree 31, connects to 4 communities