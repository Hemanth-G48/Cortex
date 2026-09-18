---
type: community
cohesion: 0.07
members: 51
---

# Community 48

**Cohesion:** 0.07 - loosely connected
**Members:** 51 nodes

## Members
- [[.convert_from_path()]] - code - backend/tests/test_kb_ocr.py
- [[.get_tesseract_version()]] - code - backend/tests/test_kb_ocr.py
- [[.image_to_string()]] - code - backend/tests/test_kb_ocr.py
- [[.test_graceful_degradation_when_ocr_unavailable()]] - code - backend/tests/test_kb_ocr.py
- [[.test_needs_ocr_flag_heuristic()]] - code - backend/tests/test_kb_ocr.py
- [[.test_ocr_disabled_leaves_doc_alone()]] - code - backend/tests/test_kb_ocr.py
- [[.test_ocr_runs_merges_and_flags()]] - code - backend/tests/test_kb_ocr.py
- [[Delete existing chunks and insert new ones in a single transaction (phrase 67).]] - rationale - backend/app/services/kb/pipeline.py
- [[FakeImg]] - code - backend/tests/test_kb_ocr.py
- [[FakePdf2Image]] - code - backend/tests/test_kb_ocr.py
- [[FakePytesseract]] - code - backend/tests/test_kb_ocr.py
- [[Flag a PDF when any page yields  ~50 chars (phrase 53).]] - rationale - backend/app/services/kb/ocr.py
- [[Idea 6 — OCR tests monkeypatched pytesseractpdf2image, merged output, ocr_used]] - rationale - backend/tests/test_kb_ocr.py
- [[KbDocument_22]] - code
- [[KbVersion_2]] - code
- [[Keep only the latest ``KB_MAX_VERSIONS`` snapshots (phrase 85).]] - rationale - backend/app/services/kb/pipeline.py
- [[OCR for scannedimage-only documents (Idea 6).  Fully import-guarded — when ``KB]] - rationale - backend/app/services/kb/ocr.py
- [[OcrUnavailableError]] - code - backend/app/services/kb/ocr.py
- [[Paste an arXiv ID (or URL) → fetch metadata → create a document.      Offline lo]] - rationale - backend/app/routers/kb_papers.py
- [[Per-document ingestion pipeline (Idea 10, phrase 96).  Order extract → OCR (if]] - rationale - backend/app/services/kb/pipeline.py
- [[Phase 4 best-effort hooks after a successful ingest (phrases 42, 56, 84).      P]] - rationale - backend/app/services/kb/pipeline.py
- [[Raised when OCR cannot run (disabled, missing deps, missing binary).]] - rationale - backend/app/services/kb/ocr.py
- [[Render PDF pages to images and run tesseract. Returns merged text.      Raises]] - rationale - backend/app/services/kb/ocr.py
- [[Run the per-document pipeline. Never raises for content errors.]] - rationale - backend/app/services/kb/pipeline.py
- [[RuntimeError]] - code
- [[Session_56]] - code
- [[Session_177]] - code
- [[Snapshot the document's current content unless it is unchanged.      Only snapsh]] - rationale - backend/app/services/kb/pipeline.py
- [[TestOcrPipeline]] - code - backend/tests/test_kb_ocr.py
- [[True only when OCR is enabled AND every dependency is present.]] - rationale - backend/app/services/kb/ocr.py
- [[User_41]] - code
- [[_current_hash()]] - code - backend/app/services/kb/pipeline.py
- [[_doc()_6]] - code - backend/tests/test_kb_ocr.py
- [[_enforce_version_cap()]] - code - backend/app/services/kb/pipeline.py
- [[_fake_ocr_deps()]] - code - backend/tests/test_kb_ocr.py
- [[_imports_ok()]] - code - backend/app/services/kb/ocr.py
- [[_inner]] - code - backend/tests/test_kb_ocr.py
- [[_parse_markdown_meta()]] - code - backend/app/services/kb/pipeline.py
- [[_snapshot_to_disk()]] - code - backend/app/services/kb/pipeline.py
- [[_tesseract_ok()]] - code - backend/app/services/kb/ocr.py
- [[import_paper()]] - code - backend/app/routers/kb_papers.py
- [[ingest_document()]] - code - backend/app/services/kb/pipeline.py
- [[needs_ocr()]] - code - backend/app/services/kb/ocr.py
- [[ocr.py]] - code - backend/app/services/kb/ocr.py
- [[ocr_available()]] - code - backend/app/services/kb/ocr.py
- [[ocr_pdf()]] - code - backend/app/services/kb/ocr.py
- [[pipeline.py]] - code - backend/app/services/kb/pipeline.py
- [[re_chunk()]] - code - backend/app/services/kb/pipeline.py
- [[run_post_ingest_hooks()]] - code - backend/app/services/kb/pipeline.py
- [[snapshot_version()]] - code - backend/app/services/kb/pipeline.py
- [[test_kb_ocr.py]] - code - backend/tests/test_kb_ocr.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_48
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Community 21]]
- 10 edges to [[_COMMUNITY_Community 5]]
- 8 edges to [[_COMMUNITY_Community 2]]
- 5 edges to [[_COMMUNITY_Community 71]]
- 5 edges to [[_COMMUNITY_Community 33]]
- 4 edges to [[_COMMUNITY_Community 1]]
- 4 edges to [[_COMMUNITY_Community 116]]
- 4 edges to [[_COMMUNITY_Community 203]]
- 3 edges to [[_COMMUNITY_Community 28]]
- 3 edges to [[_COMMUNITY_Community 127]]
- 3 edges to [[_COMMUNITY_Community 17]]
- 2 edges to [[_COMMUNITY_Community 10]]
- 2 edges to [[_COMMUNITY_Community 264]]
- 2 edges to [[_COMMUNITY_Community 12]]
- 2 edges to [[_COMMUNITY_Community 102]]
- 2 edges to [[_COMMUNITY_Community 226]]
- 2 edges to [[_COMMUNITY_Community 216]]
- 2 edges to [[_COMMUNITY_Community 31]]
- 2 edges to [[_COMMUNITY_Community 185]]
- 2 edges to [[_COMMUNITY_Community 16]]
- 2 edges to [[_COMMUNITY_Community 86]]
- 1 edge to [[_COMMUNITY_Community 109]]
- 1 edge to [[_COMMUNITY_Community 115]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 22]]

## Top bridge nodes
- [[pipeline.py]] - degree 38, connects to 18 communities
- [[ingest_document()]] - degree 26, connects to 8 communities
- [[import_paper()]] - degree 15, connects to 8 communities
- [[re_chunk()]] - degree 19, connects to 7 communities
- [[run_post_ingest_hooks()]] - degree 10, connects to 5 communities