---
source_file: "backend/app/routers/grades.py"
type: "code"
community: "Community 35"
location: "L154"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_35
---

# cumulative_gpa()

## Connections
- [[Course]] - `indirect_call` [INFERRED]
- [[CourseWeight]] - `indirect_call` [INFERRED]
- [[GPACourse]] - `calls` [EXTRACTED]
- [[GPAResponse]] - `calls` [EXTRACTED]
- [[Grade]] - `indirect_call` [INFERRED]
- [[Session_23]] - `references` [EXTRACTED]
- [[calculate_course_grade()]] - `calls` [EXTRACTED]
- [[grades.py]] - `contains` [EXTRACTED]
- [[pct_to_gpa()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_35