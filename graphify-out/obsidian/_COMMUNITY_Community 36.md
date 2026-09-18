---
type: community
cohesion: 0.07
members: 56
---

# Community 36

**Cohesion:** 0.07 - loosely connected
**Members:** 56 nodes

## Members
- [[A learning path discovered on an external platform (Layer 1).]] - rationale - backend/app/models/kb/learning_path.py
- [[Attempt a lightweight URL verification for one resource.      ``include_body=Fal]] - rationale - backend/app/services/kb/source_crawler.py
- [[Base_46]] - code
- [[Best-effort generic card extraction for non-PortSwigger platforms.      Looks fo]] - rationale - backend/app/services/kb/source_crawler.py
- [[Create-or-refresh one ``LearningPath`` from a discovery card + crawl it.      Us]] - rationale - backend/app/services/kb/source_crawler.py
- [[Dedup key host + path, lowercase, queryfragment stripped.]] - rationale - backend/app/services/kb/source_crawler.py
- [[Discover + persist Layer-1 (paths + resources) for the submitted URLs.      URLs]] - rationale - backend/app/services/kb/learning_planner.py
- [[Discover learning paths from a source URL (Layer 1, index level).      Returns `]] - rationale - backend/app/services/kb/source_crawler.py
- [[Extract a path page's structure summary + sections with resources.      PortSwi]] - rationale - backend/app/services/kb/source_crawler.py
- [[Fetch ``url`` and return an honest verification record.      Returns a dict with]] - rationale - backend/app/services/kb/source_crawler.py
- [[Fetch one path page and return its resources (Layer 1, path level).      Returns]] - rationale - backend/app/services/kb/source_crawler.py
- [[Flatten the persisted Layer-1 hierarchy into one resource list.      Each entry]] - rationale - backend/app/services/kb/learning_planner.py
- [[Junction which learning paths contain which (deduplicated) resources.]] - rationale - backend/app/models/kb/learning_path.py
- [[Layer-1 fallback for generic sites one resource row per submitted URL.      Whe]] - rationale - backend/app/services/kb/learning_planner.py
- [[Layer-1 snapshot for the UI platform → paths → resources + report.]] - rationale - backend/app/services/kb/source_crawler.py
- [[Learning Path Planner — source-hierarchy models (Layer 1 the real platform).  T]] - rationale - backend/app/models/kb/learning_path.py
- [[LearningDependency]] - code - backend/app/models/kb/learning_path.py
- [[LearningPath]] - code - backend/app/models/kb/learning_path.py
- [[LearningPathResource]] - code - backend/app/models/kb/learning_path.py
- [[LearningResource]] - code - backend/app/models/kb/learning_path.py
- [[LearningResource_1]] - code
- [[One resource (reading page or lab) inside a learning path.      Deduplicated per]] - rationale - backend/app/models/kb/learning_path.py
- [[Parse ``progress-cards`` blocks → learning path dicts.      Each card carries t]] - rationale - backend/app/services/kb/source_crawler.py
- [[Prerequisite edge with provenance (platform-stated vs AI-inferred).]] - rationale - backend/app/models/kb/learning_path.py
- [[Re-crawl the plan's paths + re-verify its resources with a live session.      Th]] - rationale - backend/app/services/kb/portswigger_session.py
- [[Re-crawl the plan's stored source URL(s) and refresh Layer 1 in place.      Plan]] - rationale - backend/app/services/kb/learning_planner.py
- [[Reproduce the page's own ``POST apiwidgets`` call → merged card HTML.]] - rationale - backend/app/services/kb/source_crawler.py
- [[Resolve + normalise a URL (drop fragments; keep query).]] - rationale - backend/app/services/kb/source_crawler.py
- [[Rough HTML→text extraction (no external parser dependency).]] - rationale - backend/app/services/kb/source_crawler.py
- [[Run Layer-1 discovery for the plan's submitted URLs.      For each submitted URL]] - rationale - backend/app/services/kb/source_crawler.py
- [[Session_197]] - code
- [[Source crawler — Layer 1 discover and persist the REAL platform structure.  The]] - rationale - backend/app/services/kb/source_crawler.py
- [[_flatten_sources()]] - code - backend/app/services/kb/learning_planner.py
- [[_generic_parse_path_cards()]] - code - backend/app/services/kb/source_crawler.py
- [[_generic_resources_from_submission()]] - code - backend/app/services/kb/learning_planner.py
- [[_is_skippable()]] - code - backend/app/services/kb/source_crawler.py
- [[_normalise_url()]] - code - backend/app/services/kb/source_crawler.py
- [[_parse_path_page()]] - code - backend/app/services/kb/source_crawler.py
- [[_ps_fetch_widgets()]] - code - backend/app/services/kb/source_crawler.py
- [[_ps_parse_path_cards()]] - code - backend/app/services/kb/source_crawler.py
- [[_ps_widget_ids()]] - code - backend/app/services/kb/source_crawler.py
- [[_run_layer1()]] - code - backend/app/services/kb/learning_planner.py
- [[_strip_html()]] - code - backend/app/services/kb/source_crawler.py
- [[_url_key()]] - code - backend/app/services/kb/source_crawler.py
- [[_verify_resource()]] - code - backend/app/services/kb/source_crawler.py
- [[build_source_payload()]] - code - backend/app/services/kb/source_crawler.py
- [[crawl_learning_path()]] - code - backend/app/services/kb/source_crawler.py
- [[delete_plan()]] - code - backend/app/routers/kb_learning_plans.py
- [[discover_learning_paths()]] - code - backend/app/services/kb/source_crawler.py
- [[fetch_verified()]] - code - backend/app/services/kb/source_crawler.py
- [[learning_path.py]] - code - backend/app/models/kb/learning_path.py
- [[resync_plan()_1]] - code - backend/app/services/kb/learning_planner.py
- [[reverify_plan()]] - code - backend/app/services/kb/portswigger_session.py
- [[run_discovery()]] - code - backend/app/services/kb/source_crawler.py
- [[source_crawler.py]] - code - backend/app/services/kb/source_crawler.py
- [[upsert_path_crawl()]] - code - backend/app/services/kb/source_crawler.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_36
SORT file.name ASC
```

## Connections to other communities
- 19 edges to [[_COMMUNITY_Community 87]]
- 11 edges to [[_COMMUNITY_Community 55]]
- 11 edges to [[_COMMUNITY_Community 95]]
- 9 edges to [[_COMMUNITY_Community 65]]
- 5 edges to [[_COMMUNITY_Community 10]]
- 5 edges to [[_COMMUNITY_Community 38]]
- 5 edges to [[_COMMUNITY_Community 58]]
- 4 edges to [[_COMMUNITY_Community 113]]
- 4 edges to [[_COMMUNITY_Community 98]]
- 3 edges to [[_COMMUNITY_Community 127]]
- 2 edges to [[_COMMUNITY_Community 5]]
- 2 edges to [[_COMMUNITY_Community 121]]
- 1 edge to [[_COMMUNITY_Community 16]]
- 1 edge to [[_COMMUNITY_Community 96]]

## Top bridge nodes
- [[source_crawler.py]] - degree 30, connects to 9 communities
- [[LearningPath]] - degree 24, connects to 7 communities
- [[LearningResource]] - degree 20, connects to 7 communities
- [[LearningPathResource]] - degree 18, connects to 6 communities
- [[LearningDependency]] - degree 12, connects to 5 communities