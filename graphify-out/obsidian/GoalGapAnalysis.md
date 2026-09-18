---
source_file: "backend/app/models/kb/goal_gap.py"
type: "code"
community: "Community 30"
location: "L27"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_30
---

# GoalGapAnalysis

## Connections
- [[Base_41]] - `inherits` [EXTRACTED]
- [[gap_engine.py]] - `imports` [EXTRACTED]
- [[goal_gap.py]] - `contains` [EXTRACTED]
- [[invalidate_goal_gaps()]] - `indirect_call` [INFERRED]
- [[load_saved_goal_gaps()]] - `indirect_call` [INFERRED]
- [[models__init__.py]] - `imports` [EXTRACTED]
- [[modelskb__init__.py]] - `imports` [EXTRACTED]
- [[save_goal_gaps()]] - `calls` [EXTRACTED]
- [[test_goal_gap_cache_is_per_user()]] - `indirect_call` [INFERRED]
- [[test_goal_gaps_saved_and_reused_until_explicit_reanalyze()]] - `indirect_call` [INFERRED]
- [[test_kb_gap_engine.py]] - `imports` [EXTRACTED]
- [[test_kb_gap_history.py]] - `imports` [EXTRACTED]
- [[test_reindex_invalidates_cache_but_keeps_goal_history()]] - `indirect_call` [INFERRED]
- [[test_reindex_invalidates_goal_gap_cache()]] - `indirect_call` [INFERRED]
- [[test_saved_goal_payload_missing_fields_is_normalized_on_read()]] - `indirect_call` [INFERRED]

#graphify/code #graphify/EXTRACTED #community/Community_30