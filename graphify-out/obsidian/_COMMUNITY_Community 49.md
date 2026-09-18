---
type: community
cohesion: 0.13
members: 50
---

# Community 49

**Cohesion:** 0.13 - loosely connected
**Members:** 50 nodes

## Members
- [[A course derived from a ``course`` tag ALSO shows documents that live     unde]] - rationale - backend/tests/test_course_content.py
- [[A resync drops the saved analysis so the next gaps request recomputes.]] - rationale - backend/tests/test_course_content.py
- [[A subject with no KB docs must not score the user's whole concept vault.      Re]] - rationale - backend/tests/test_course_content.py
- [[A topic that exists BOTH as a root heading and as a vault folder is     treated]] - rationale - backend/tests/test_course_content.py
- [[CourseGapAnalysis]] - code - backend/app/models/course.py
- [[Deleting a course (or having it removed by a sync) also removes its     saved an]] - rationale - backend/tests/test_course_content.py
- [[Docs directly in the subject root without headings stay unorganized;     folder-]] - rationale - backend/tests/test_course_content.py
- [[Each course (and user) keeps its own saved analysis.]] - rationale - backend/tests/test_course_content.py
- [[Folder-derived subjects reflect their vault structure nested folders     become]] - rationale - backend/tests/test_course_content.py
- [[Folder-derived subjects surface their vault folders as gap-analysis     knowledg]] - rationale - backend/tests/test_course_content.py
- [[KbConcept_6]] - code
- [[KbDocument_32]] - code
- [[KbSource_7]] - code
- [[Paths equal to the root, trailing slashes, and backslash separators are     hand]] - rationale - backend/tests/test_course_content.py
- [[Saved Gap Analysis for one course (one row per user + course).      Gap Analysis]] - rationale - backend/app/models/course.py
- [[Seed a kb_folder course with nested folder docs (no tagging needed).]] - rationale - backend/tests/test_course_content.py
- [[Seed a kb_tag course with 2 docs (shared + unique headings) and a concept.]] - rationale - backend/tests/test_course_content.py
- [[Session_219]] - code
- [[TestClient_1]] - code
- [[Tests for the Subject Details content pipeline  - ``GET apicourses{id}conte]] - rationale - backend/tests/test_course_content.py
- [[The analysis is computed once, saved, and reused on later GETs;     only the exp]] - rationale - backend/tests/test_course_content.py
- [[_build_course()]] - code - backend/tests/test_course_content.py
- [[_build_folder_course()]] - code - backend/tests/test_course_content.py
- [[_link()_1]] - code - backend/tests/test_course_content.py
- [[_make_concept()]] - code - backend/tests/test_course_content.py
- [[_make_doc()_1]] - code - backend/tests/test_course_content.py
- [[_make_source()_1]] - code - backend/tests/test_course_content.py
- [[_make_tag()_1]] - code - backend/tests/test_course_content.py
- [[_mention()_1]] - code - backend/tests/test_course_content.py
- [[_signup()_4]] - code - backend/tests/test_course_content.py
- [[_uid()_3]] - code - backend/tests/test_course_content.py
- [[test_content_graph_is_scoped_to_subject_documents()]] - code - backend/tests/test_course_content.py
- [[test_content_related_concepts_from_mentions()]] - code - backend/tests/test_course_content.py
- [[test_content_returns_documents_with_outline_and_metadata()]] - code - backend/tests/test_course_content.py
- [[test_content_topics_are_nested_and_carry_their_documents()]] - code - backend/tests/test_course_content.py
- [[test_course_content.py]] - code - backend/tests/test_course_content.py
- [[test_folder_segments_edge_cases()]] - code - backend/tests/test_course_content.py
- [[test_folder_subject_gap_topics_include_folder_topics()]] - code - backend/tests/test_course_content.py
- [[test_folder_subject_nested_folders_become_topics()]] - code - backend/tests/test_course_content.py
- [[test_folder_subject_root_docs_without_folders_remain_unorganized()]] - code - backend/tests/test_course_content.py
- [[test_folder_topic_wins_over_same_named_root_heading()]] - code - backend/tests/test_course_content.py
- [[test_gaps_are_saved_and_reused_until_explicit_reanalyze()]] - code - backend/tests/test_course_content.py
- [[test_gaps_cache_cleaned_up_when_course_deleted()]] - code - backend/tests/test_course_content.py
- [[test_gaps_cache_invalidated_by_resync()]] - code - backend/tests/test_course_content.py
- [[test_gaps_on_subject_with_no_documents_returns_no_global_concept_gaps()]] - code - backend/tests/test_course_content.py
- [[test_gaps_report_topic_and_concept_gaps()]] - code - backend/tests/test_course_content.py
- [[test_gaps_saved_per_course_and_per_user()]] - code - backend/tests/test_course_content.py
- [[test_resync_classroom_course_merges_by_google_id()]] - code - backend/tests/test_course_content.py
- [[test_resync_is_idempotent_and_returns_content()]] - code - backend/tests/test_course_content.py
- [[test_tag_course_includes_docs_from_matching_folder()]] - code - backend/tests/test_course_content.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_49
SORT file.name ASC
```

## Connections to other communities
- 12 edges to [[_COMMUNITY_Community 9]]
- 4 edges to [[_COMMUNITY_Community 60]]
- 4 edges to [[_COMMUNITY_Community 2]]
- 4 edges to [[_COMMUNITY_Community 43]]
- 3 edges to [[_COMMUNITY_Community 75]]
- 3 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 30]]
- 2 edges to [[_COMMUNITY_Community 29]]
- 2 edges to [[_COMMUNITY_Community 92]]
- 2 edges to [[_COMMUNITY_Community 54]]
- 2 edges to [[_COMMUNITY_Community 70]]

## Top bridge nodes
- [[test_course_content.py]] - degree 40, connects to 9 communities
- [[CourseGapAnalysis]] - degree 17, connects to 5 communities
- [[test_gaps_cache_cleaned_up_when_course_deleted()]] - degree 14, connects to 2 communities
- [[test_gaps_saved_per_course_and_per_user()]] - degree 14, connects to 2 communities
- [[_link()_1]] - degree 9, connects to 2 communities