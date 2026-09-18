---
source_file: "backend/app/services/kb/neardup.py"
type: "code"
community: "Community 45"
location: "L341"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_45
---

# list_duplicates()

## Connections
- [[.test_list_duplicates()]] - `calls` [EXTRACTED]
- [[.test_per_user_isolation()_7]] - `calls` [EXTRACTED]
- [[KbEdge]] - `indirect_call` [INFERRED]
- [[Return all ``DUPLICATE_OF`` edges for user_id as KbDuplicateItem dicts.      `]] - `rationale_for` [EXTRACTED]
- [[Session_173]] - `references` [EXTRACTED]
- [[audit()]] - `calls` [EXTRACTED]
- [[get_duplicates()]] - `calls` [EXTRACTED]
- [[kb_duplicates.py]] - `imports` [EXTRACTED]
- [[neardup.py]] - `contains` [EXTRACTED]
- [[test_kb_neardup.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_45