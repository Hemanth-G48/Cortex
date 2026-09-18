---
source_file: "backend/app/services/kb/tagger.py"
type: "code"
community: "Community 44"
location: "L232"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_44
---

# propose_tags()

## Connections
- [[.test_apply_idempotent()]] - `calls` [EXTRACTED]
- [[.test_apply_promotes_to_manual()]] - `calls` [EXTRACTED]
- [[.test_create_or_reuse_tags()]] - `calls` [EXTRACTED]
- [[.test_deterministic_fallback_when_ai_disabled()_1]] - `calls` [EXTRACTED]
- [[.test_get_document_tags_returns_200_when_manual_tags_exist()]] - `calls` [EXTRACTED]
- [[.test_reject_never_removes_rule_tags()]] - `calls` [EXTRACTED]
- [[.test_reject_removes_ai_tags()]] - `calls` [EXTRACTED]
- [[.test_reject_removes_manual_tags()]] - `calls` [EXTRACTED]
- [[.test_rule_tags_have_confidence_1()]] - `calls` [EXTRACTED]
- [[.token_estimate()]] - `calls` [EXTRACTED]
- [[KbChunk]] - `indirect_call` [INFERRED]
- [[KbDocument_27]] - `references` [EXTRACTED]
- [[KbDocumentTag]] - `indirect_call` [INFERRED]
- [[KbTag]] - `indirect_call` [INFERRED]
- [[Return a list of ``KbTagSuggestion`` dicts for doc.      Rule tags (provenance]] - `rationale_for` [EXTRACTED]
- [[Session_202]] - `references` [EXTRACTED]
- [[_create_or_reuse_tag()]] - `calls` [EXTRACTED]
- [[ai_available()]] - `calls` [EXTRACTED]
- [[auto_tag_document()]] - `calls` [EXTRACTED]
- [[embedding_budget()]] - `calls` [EXTRACTED]
- [[generate_json()]] - `calls` [EXTRACTED]
- [[persist_ai_suggestions()]] - `calls` [EXTRACTED]
- [[tagger.py]] - `contains` [EXTRACTED]
- [[test_kb_auto_tag.py]] - `imports` [EXTRACTED]
- [[tfidf_tag_candidates()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_44