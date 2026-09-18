---
source_file: "backend/app/models/course.py"
type: "code"
community: "Community 49"
location: "L72"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_49
---

# CourseGapAnalysis

## Connections
- [[Base_5]] - `inherits` [EXTRACTED]
- [[Saved Gap Analysis for one course (one row per user + course).      Gap Analysis]] - `rationale_for` [EXTRACTED]
- [[_delete_courses()]] - `indirect_call` [INFERRED]
- [[_invalidate_saved_gaps()]] - `indirect_call` [INFERRED]
- [[_load_saved_gaps()]] - `indirect_call` [INFERRED]
- [[_save_gaps()]] - `calls` [EXTRACTED]
- [[course_derivation.py]] - `imports` [EXTRACTED]
- [[courses.py]] - `imports` [EXTRACTED]
- [[models__init__.py]] - `imports` [EXTRACTED]
- [[modelscourse.py]] - `contains` [EXTRACTED]
- [[test_course_content.py]] - `imports` [EXTRACTED]
- [[test_course_history_capped_at_25()]] - `indirect_call` [INFERRED]
- [[test_gaps_are_saved_and_reused_until_explicit_reanalyze()]] - `indirect_call` [INFERRED]
- [[test_gaps_cache_cleaned_up_when_course_deleted()]] - `indirect_call` [INFERRED]
- [[test_gaps_cache_invalidated_by_resync()]] - `indirect_call` [INFERRED]
- [[test_gaps_saved_per_course_and_per_user()]] - `indirect_call` [INFERRED]
- [[test_kb_gap_history.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_49