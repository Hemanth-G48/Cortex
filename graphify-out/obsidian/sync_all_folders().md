---
source_file: "backend/app/services/kb/domain_service.py"
type: "code"
community: "Community 18"
location: "L146"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_18
---

# sync_all_folders()

## Connections
- [[Any_10]] - `references` [EXTRACTED]
- [[Course]] - `indirect_call` [INFERRED]
- [[FolderGapAnalysis]] - `indirect_call` [INFERRED]
- [[KbFolder]] - `calls` [EXTRACTED]
- [[Session_147]] - `references` [EXTRACTED]
- [[Upsert ``KbFolder`` rows for every course's child folders; drop stale.      Idem]] - `rationale_for` [EXTRACTED]
- [[_root_for_course()]] - `calls` [EXTRACTED]
- [[_scan_course_folders()]] - `calls` [EXTRACTED]
- [[course_content()]] - `calls` [EXTRACTED]
- [[course_content.py]] - `imports` [EXTRACTED]
- [[course_derivation.py]] - `imports` [EXTRACTED]
- [[derive_courses_from_tags()]] - `calls` [EXTRACTED]
- [[domain_service.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_18