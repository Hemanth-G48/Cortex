---
source_file: "backend/app/models/kb/user_memory.py"
type: "code"
community: "Community 29"
location: "L24"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_29
---

# UserMemory

## Connections
- [[.test_accept_creates_draft_note()]] - `calls` [EXTRACTED]
- [[.test_accept_twice_400()]] - `calls` [EXTRACTED]
- [[.test_anchors_are_per_user()]] - `calls` [EXTRACTED]
- [[.test_anchors_come_from_memory_only()]] - `calls` [EXTRACTED]
- [[.test_bump_clamps_strength()]] - `indirect_call` [INFERRED]
- [[.test_bump_creates_and_accumulates()]] - `indirect_call` [INFERRED]
- [[.test_bump_from_topic_matches_concepts()]] - `indirect_call` [INFERRED]
- [[.test_bump_negative_delta_is_noop()]] - `indirect_call` [INFERRED]
- [[.test_covered_concept_not_suggested()]] - `calls` [EXTRACTED]
- [[.test_dismiss_prevents_resuggestion()]] - `calls` [EXTRACTED]
- [[.test_durable_facts_block()]] - `calls` [EXTRACTED]
- [[.test_fold_creates_memory_rows()]] - `indirect_call` [INFERRED]
- [[.test_get_memory_returns_snapshot()]] - `calls` [EXTRACTED]
- [[.test_half_life_math()]] - `indirect_call` [INFERRED]
- [[.test_known_context_from_memory()]] - `calls` [EXTRACTED]
- [[.test_known_strong_concept_scores_low()]] - `calls` [EXTRACTED]
- [[.test_list_returns_suggested()]] - `calls` [EXTRACTED]
- [[.test_memory_endpoints_are_per_user()]] - `calls` [EXTRACTED]
- [[.test_memory_is_per_user()]] - `calls` [EXTRACTED]
- [[.test_prompt_contains_anchors_and_profile()]] - `calls` [EXTRACTED]
- [[.test_reason_mentions_errors()]] - `calls` [EXTRACTED]
- [[.test_recall_events_logged()]] - `calls` [EXTRACTED]
- [[.test_strengths_weaknesses_and_anchors()]] - `calls` [EXTRACTED]
- [[.test_studied_uncovered_concept_suggested()]] - `calls` [EXTRACTED]
- [[.test_suggestions_are_per_user()]] - `calls` [EXTRACTED]
- [[.test_tutor_answer_keeps_known_reference()]] - `calls` [EXTRACTED]
- [[.test_tutor_turn_bumps_concepts()]] - `indirect_call` [INFERRED]
- [[.test_zero_strength_stays_zero()]] - `calls` [EXTRACTED]
- [[Base_68]] - `inherits` [EXTRACTED]
- [[_evidence()]] - `indirect_call` [INFERRED]
- [[_memory_summary()]] - `indirect_call` [INFERRED]
- [[_revisit_candidates()]] - `indirect_call` [INFERRED]
- [[_studied_concepts()]] - `indirect_call` [INFERRED]
- [[bump()]] - `calls` [EXTRACTED]
- [[concept_gaps()]] - `indirect_call` [INFERRED]
- [[context.py]] - `imports` [EXTRACTED]
- [[decay()]] - `indirect_call` [INFERRED]
- [[gap_engine.py]] - `imports` [EXTRACTED]
- [[gaps.py]] - `imports` [EXTRACTED]
- [[get_memory()_1]] - `indirect_call` [INFERRED]
- [[memory.py]] - `imports` [EXTRACTED]
- [[models__init__.py]] - `imports` [EXTRACTED]
- [[modelskb__init__.py]] - `imports` [EXTRACTED]
- [[recommendations.py]] - `imports` [EXTRACTED]
- [[suggestions.py]] - `imports` [EXTRACTED]
- [[test_kb_concept_gaps.py]] - `imports` [EXTRACTED]
- [[test_kb_gap_engine.py]] - `imports` [EXTRACTED]
- [[test_kb_longterm_memory.py]] - `imports` [EXTRACTED]
- [[test_kb_memory.py]] - `imports` [EXTRACTED]
- [[test_kb_missing_notes.py]] - `imports` [EXTRACTED]
- [[test_kb_personalized_explain.py]] - `imports` [EXTRACTED]
- [[test_kb_tutor_memory.py]] - `imports` [EXTRACTED]
- [[test_strong_memory_marks_mastered()]] - `calls` [EXTRACTED]
- [[user_memory.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_29