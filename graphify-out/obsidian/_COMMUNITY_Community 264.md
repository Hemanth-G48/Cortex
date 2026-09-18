---
type: community
cohesion: 0.20
members: 11
---

# Community 264

**Cohesion:** 0.20 - loosely connected
**Members:** 11 nodes

## Members
- [[Best-effort arXiv metadata enrichment (phrase 55). Never raises.]] - rationale - backend/app/services/kb/citation_registry.py
- [[KbCitation_1]] - code
- [[Pull an arXiv ID out of a filename, URL, or first-page text.]] - rationale - backend/app/services/kb/arxiv.py
- [[Return ``{arxiv_id, title, authors, abstract}`` or None on any failure.]] - rationale - backend/app/services/kb/arxiv.py
- [[_citation_dict()]] - code - backend/app/services/kb/citation_registry.py
- [[_enrich_arxiv()]] - code - backend/app/services/kb/citation_registry.py
- [[_parse_atom()]] - code - backend/app/services/kb/arxiv.py
- [[arXiv metadata lookup (Idea 5, phrases 45–48).  Fetches titleauthorsabstract f]] - rationale - backend/app/services/kb/arxiv.py
- [[arxiv.py]] - code - backend/app/services/kb/arxiv.py
- [[extract_arxiv_id()]] - code - backend/app/services/kb/arxiv.py
- [[fetch_arxiv_metadata()]] - code - backend/app/services/kb/arxiv.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_264
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Community 244]]
- 2 edges to [[_COMMUNITY_Community 48]]
- 2 edges to [[_COMMUNITY_Community 224]]
- 1 edge to [[_COMMUNITY_Community 5]]
- 1 edge to [[_COMMUNITY_Community 12]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 190]]
- 1 edge to [[_COMMUNITY_Community 226]]

## Top bridge nodes
- [[_enrich_arxiv()]] - degree 6, connects to 3 communities
- [[_citation_dict()]] - degree 4, connects to 3 communities
- [[arxiv.py]] - degree 6, connects to 2 communities
- [[fetch_arxiv_metadata()]] - degree 6, connects to 2 communities
- [[extract_arxiv_id()]] - degree 3, connects to 1 community