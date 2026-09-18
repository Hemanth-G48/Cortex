---
type: community
cohesion: 0.11
members: 44
---

# Community 60

**Cohesion:** 0.11 - loosely connected
**Members:** 44 nodes

## Members
- [[NOTE registered before {course_id} so resources is not parsed as an id.]] - rationale - backend/app/routers/courses.py
- [[NOTE registered before {course_id} so resourcessync-status are not pa]] - rationale - backend/app/routers/courses.py
- [[Any]] - code
- [[BaseModel_35]] - code
- [[Course_1]] - code
- [[CourseBase]] - code - backend/app/schemas/course.py
- [[CourseCreate]] - code - backend/app/schemas/course.py
- [[CourseResponse]] - code - backend/app/schemas/course.py
- [[Deriverefresh one Course per Second Brain ``course`` tag.]] - rationale - backend/app/routers/courses.py
- [[Drop the cached analysis (used after a resync, since data changed).]] - rationale - backend/app/routers/courses.py
- [[Force a fresh Gap Analysis for the subject and save the result.      The only pa]] - rationale - backend/app/routers/courses.py
- [[Gap analysis for the subject, computed from its actual data.      Results are sa]] - rationale - backend/app/routers/courses.py
- [[Get Second Brain documents tagged with this course's subject.]] - rationale - backend/app/routers/courses.py
- [[Health payload explaining why a KB sync may be empty (sourcesdocstags     coun]] - rationale - backend/app/routers/courses.py
- [[Resource cards for the Academic Resources grid (KB folders + Classroom).]] - rationale - backend/app/routers/courses.py
- [[Resync the course with its data sources (Second Brain tags + Google     Classroo]] - rationale - backend/app/routers/courses.py
- [[Return a previously saved analysis payload, or None.      When the saved copy ex]] - rationale - backend/app/routers/courses.py
- [[Session_11]] - code
- [[Set transient progress_percentage from assignment completion.      Progress is c]] - rationale - backend/app/routers/courses.py
- [[Snapshot log of this subject's gap analyses (oldest → newest).      Each entry i]] - rationale - backend/app/routers/courses.py
- [[Subject Details payload Second Brain (documents, nested topics,     related con]] - rationale - backend/app/routers/courses.py
- [[Upsert the analysis payload for a user + course (one row).      The stored ``ana]] - rationale - backend/app/routers/courses.py
- [[User_8]] - code
- [[_attach_progress()]] - code - backend/app/routers/courses.py
- [[_course_or_404()]] - code - backend/app/routers/courses.py
- [[_invalidate_saved_gaps()]] - code - backend/app/routers/courses.py
- [[_load_saved_gaps()]] - code - backend/app/routers/courses.py
- [[_save_gaps()]] - code - backend/app/routers/courses.py
- [[course_content_endpoint()]] - code - backend/app/routers/courses.py
- [[course_documents_endpoint()]] - code - backend/app/routers/courses.py
- [[course_gaps_endpoint()]] - code - backend/app/routers/courses.py
- [[course_gaps_history()]] - code - backend/app/routers/courses.py
- [[course_gaps_reanalyze()]] - code - backend/app/routers/courses.py
- [[course_resources()]] - code - backend/app/routers/courses.py
- [[courses.py]] - code - backend/app/routers/courses.py
- [[courses_sync_status()]] - code - backend/app/routers/courses.py
- [[create_course()]] - code - backend/app/routers/courses.py
- [[delete_course()]] - code - backend/app/routers/courses.py
- [[get_course()]] - code - backend/app/routers/courses.py
- [[list_courses()]] - code - backend/app/routers/courses.py
- [[resync_course()]] - code - backend/app/routers/courses.py
- [[schemascourse.py]] - code - backend/app/schemas/course.py
- [[sync_courses_from_kb()]] - code - backend/app/routers/courses.py
- [[update_course()]] - code - backend/app/routers/courses.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_60
SORT file.name ASC
```

## Connections to other communities
- 13 edges to [[_COMMUNITY_Community 70]]
- 11 edges to [[_COMMUNITY_Community 9]]
- 9 edges to [[_COMMUNITY_Community 5]]
- 8 edges to [[_COMMUNITY_Community 75]]
- 7 edges to [[_COMMUNITY_Community 225]]
- 4 edges to [[_COMMUNITY_Community 49]]
- 4 edges to [[_COMMUNITY_Community 7]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 1]]

## Top bridge nodes
- [[courses.py]] - degree 51, connects to 8 communities
- [[resync_course()]] - degree 12, connects to 3 communities
- [[_load_saved_gaps()]] - degree 8, connects to 2 communities
- [[_save_gaps()]] - degree 8, connects to 2 communities
- [[delete_course()]] - degree 6, connects to 2 communities