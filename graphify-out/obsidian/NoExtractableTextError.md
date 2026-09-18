---
source_file: "backend/app/services/text_extractor.py"
type: "code"
community: "Community 71"
location: "L14"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_71
---

# NoExtractableTextError

## Connections
- [[Exception_1]] - `inherits` [EXTRACTED]
- [[Raised when a file has no extractable text or an unsupported type.]] - `rationale_for` [EXTRACTED]
- [[SetStatusRequest]] - `uses` [INFERRED]
- [[_book_file_path()]] - `calls` [EXTRACTED]
- [[analyze_book()]] - `calls` [EXTRACTED]
- [[analyze_pages()]] - `calls` [EXTRACTED]
- [[analyze_toc()]] - `calls` [EXTRACTED]
- [[book_gaps.py]] - `imports` [EXTRACTED]
- [[extract()]] - `calls` [EXTRACTED]
- [[ingestion.py]] - `imports` [EXTRACTED]
- [[kb_book_gaps.py]] - `imports` [EXTRACTED]
- [[materials.py]] - `imports` [EXTRACTED]
- [[pipeline.py]] - `imports` [EXTRACTED]
- [[test_extract_docx_empty_raises()]] - `indirect_call` [INFERRED]
- [[test_extract_no_text_raises()]] - `indirect_call` [INFERRED]
- [[test_extract_pdf_empty_raises()]] - `indirect_call` [INFERRED]
- [[test_extract_unsupported_type_raises()]] - `indirect_call` [INFERRED]
- [[test_ingestion_errors.py]] - `imports` [EXTRACTED]
- [[test_no_extractable_text_error_for_empty_txt()]] - `indirect_call` [INFERRED]
- [[test_no_extractable_text_error_for_unsupported_type()]] - `indirect_call` [INFERRED]
- [[test_text_extractor.py]] - `imports` [EXTRACTED]
- [[text_extractor.py]] - `contains` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_71