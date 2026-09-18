---
type: community
cohesion: 0.15
members: 15
---

# Community 226

**Cohesion:** 0.15 - loosely connected
**Members:** 15 nodes

## Members
- [[.test_make_cite_key_with_year()]] - code - backend/tests/test_kb_citations_registry.py
- [[.test_parse_inline_citations()]] - code - backend/tests/test_kb_citations_registry.py
- [[.test_parse_reference_lines()]] - code - backend/tests/test_kb_citations_registry.py
- [[Best-effort field extraction from one reference line.]] - rationale - backend/app/services/kb/citation_registry.py
- [[Deterministic cite key first-alnum-token of the author + year, else slug.]] - rationale - backend/app/services/kb/citation_registry.py
- [[Extract inline citation keys (``@citekey``  ``citekey``) (phrase 54).]] - rationale - backend/app/services/kb/citation_registry.py
- [[Ingest-stage extraction PDF reference lists + md inline ``@cite`` (phrase 56).]] - rationale - backend/app/services/kb/citation_registry.py
- [[KbDocument_12]] - code
- [[Split a document's reference list into citation lines (phrase 53).      Heuristi]] - rationale - backend/app/services/kb/citation_registry.py
- [[TestParsing]] - code - backend/tests/test_kb_citations_registry.py
- [[_parse_meta()]] - code - backend/app/services/kb/citation_registry.py
- [[extract_for_document()]] - code - backend/app/services/kb/citation_registry.py
- [[make_cite_key()]] - code - backend/app/services/kb/citation_registry.py
- [[parse_inline_citations()]] - code - backend/app/services/kb/citation_registry.py
- [[parse_reference_lines()]] - code - backend/app/services/kb/citation_registry.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_226
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Community 224]]
- 5 edges to [[_COMMUNITY_Community 244]]
- 2 edges to [[_COMMUNITY_Community 48]]
- 1 edge to [[_COMMUNITY_Community 116]]
- 1 edge to [[_COMMUNITY_Community 264]]

## Top bridge nodes
- [[extract_for_document()]] - degree 12, connects to 4 communities
- [[make_cite_key()]] - degree 6, connects to 3 communities
- [[parse_inline_citations()]] - degree 5, connects to 2 communities
- [[parse_reference_lines()]] - degree 5, connects to 2 communities
- [[TestParsing]] - degree 4, connects to 1 community