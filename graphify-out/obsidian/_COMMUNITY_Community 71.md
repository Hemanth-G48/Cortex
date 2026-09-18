---
type: community
cohesion: 0.11
members: 40
---

# Community 71

**Cohesion:** 0.11 - loosely connected
**Members:** 40 nodes

## Members
- [[A garbage PDF file should raise NoExtractableTextError, not crash.]] - rationale - backend/tests/test_text_extractor.py
- [[A minimal hand-written PDF that pypdf can parse (or raises NoExtractableTextErro]] - rationale - backend/tests/test_text_extractor.py
- [[Exception_1]] - code
- [[Extract text from multiple files, joining with headers.      Each element is ``(]] - rationale - backend/app/services/text_extractor.py
- [[Ingestion helpers for SyllabusAI materials.]] - rationale - backend/app/services/ingestion.py
- [[NoExtractableTextError]] - code - backend/app/services/text_extractor.py
- [[NoExtractableTextError is raised for empty txt content.]] - rationale - backend/tests/test_ingestion_errors.py
- [[NoExtractableTextError is raised for unsupported file types.]] - rationale - backend/tests/test_ingestion_errors.py
- [[Raised when a file has no extractable text or an unsupported type.]] - rationale - backend/app/services/text_extractor.py
- [[Return the plain text of the file at ``file_path``.      Parameters     --------]] - rationale - backend/app/services/text_extractor.py
- [[Tests for extract_multiple in text_extractor service.]] - rationale - backend/tests/test_text_extractor_multi.py
- [[Tests for ingestion error handling (emptyunsupported content).]] - rationale - backend/tests/test_ingestion_errors.py
- [[Tests for text_extractor service.]] - rationale - backend/tests/test_text_extractor.py
- [[Text extraction from uploaded study documents (SyllabusAI materials).  Supports]] - rationale - backend/app/services/text_extractor.py
- [[Write content to a temp file and return its path.]] - rationale - backend/tests/test_text_extractor.py
- [[_write_tmp()_1]] - code - backend/tests/test_text_extractor_multi.py
- [[_write_tmp()]] - code - backend/tests/test_text_extractor.py
- [[extract()]] - code - backend/app/services/text_extractor.py
- [[extract_multiple()]] - code - backend/app/services/text_extractor.py
- [[ingestion.py]] - code - backend/app/services/ingestion.py
- [[test_extract_docx_empty_raises()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_docx_returns_paragraph_text()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_md_returns_text()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_multiple_empty_result()]] - code - backend/tests/test_text_extractor_multi.py
- [[test_extract_multiple_joins_with_headers()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_multiple_skips_unsupported()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_multiple_skips_unsupported_file()]] - code - backend/tests/test_text_extractor_multi.py
- [[test_extract_multiple_two_txt_files()]] - code - backend/tests/test_text_extractor_multi.py
- [[test_extract_multiple_with_docx()]] - code - backend/tests/test_text_extractor_multi.py
- [[test_extract_no_text_raises()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_pdf_empty_raises()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_pdf_graceful()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_txt_returns_text()]] - code - backend/tests/test_text_extractor.py
- [[test_extract_unsupported_type_raises()]] - code - backend/tests/test_text_extractor.py
- [[test_ingestion_errors.py]] - code - backend/tests/test_ingestion_errors.py
- [[test_no_extractable_text_error_for_empty_txt()]] - code - backend/tests/test_ingestion_errors.py
- [[test_no_extractable_text_error_for_unsupported_type()]] - code - backend/tests/test_ingestion_errors.py
- [[test_text_extractor.py]] - code - backend/tests/test_text_extractor.py
- [[test_text_extractor_multi.py]] - code - backend/tests/test_text_extractor_multi.py
- [[text_extractor.py]] - code - backend/app/services/text_extractor.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_71
SORT file.name ASC
```

## Connections to other communities
- 7 edges to [[_COMMUNITY_Community 16]]
- 5 edges to [[_COMMUNITY_Community 47]]
- 5 edges to [[_COMMUNITY_Community 48]]
- 3 edges to [[_COMMUNITY_Community 153]]
- 3 edges to [[_COMMUNITY_Community 154]]
- 2 edges to [[_COMMUNITY_Community 63]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 122]]
- 1 edge to [[_COMMUNITY_Community 21]]
- 1 edge to [[_COMMUNITY_Community 33]]
- 1 edge to [[_COMMUNITY_Community 116]]
- 1 edge to [[_COMMUNITY_Community 2]]
- 1 edge to [[_COMMUNITY_Community 86]]
- 1 edge to [[_COMMUNITY_Community 5]]

## Top bridge nodes
- [[ingestion.py]] - degree 13, connects to 8 communities
- [[text_extractor.py]] - degree 16, connects to 7 communities
- [[NoExtractableTextError]] - degree 22, connects to 4 communities
- [[extract()]] - degree 22, connects to 3 communities
- [[test_ingestion_errors.py]] - degree 9, connects to 2 communities