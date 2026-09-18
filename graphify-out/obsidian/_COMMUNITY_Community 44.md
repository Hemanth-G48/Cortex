---
type: community
cohesion: 0.12
members: 52
---

# Community 44

**Cohesion:** 0.12 - loosely connected
**Members:** 52 nodes

## Members
- [[._upload()_1]] - code - backend/tests/test_kb_auto_tag.py
- [[._upload()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_apply_idempotent()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_apply_promotes_to_manual()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_create_blank_name_rejected()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_create_course_tag_derives_course()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_create_or_reuse_tags()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_create_plain_tag_appears_in_applied()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_deterministic_fallback_when_ai_disabled()_1]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_get_document_tags_returns_200_when_manual_tags_exist()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_get_tags_never_calls_llm()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_idempotent()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_propose_endpoint_persists_and_get_reuses()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_reject_never_removes_rule_tags()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_reject_removes_ai_tags()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_reject_removes_manual_tags()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_rule_tags_have_confidence_1()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_rule_tags_never_suggested_for_deletion()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_rule_tags_still_listed_in_applied()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_seeds_from_frontmatter()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_seeds_from_inline_hashes()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_user_cannot_apply_tags_to_other_users_doc()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_user_cannot_reject_tags_on_other_users_doc()]] - code - backend/tests/test_kb_auto_tag.py
- [[.test_user_cannot_see_other_users_tags()]] - code - backend/tests/test_kb_auto_tag.py
- [[Auto-tagging tests (Phase 2, Idea 14, phrase 38).]] - rationale - backend/tests/test_kb_auto_tag.py
- [[Browsing a document must never call the LLM for tag suggestions.      The GET en]] - rationale - backend/tests/test_kb_auto_tag.py
- [[Extract inline ``tag`` tokens andor a ``tags`` list from     ``doc.frontmatte]] - rationale - backend/app/services/kb/tagger.py
- [[GET documents{id}tags works without any LLM call — the read         path uses]] - rationale - backend/tests/test_kb_auto_tag.py
- [[KbApplyTags]] - code - backend/app/schemas/kb.py
- [[KbDocument_40]] - code
- [[KbRejectTags]] - code - backend/app/schemas/kb.py
- [[POST apikbdocuments{id}tagscreate (Second Brain tag editor).]] - rationale - backend/tests/test_kb_auto_tag.py
- [[POST documents{id}tagspropose (explicit action) runs the AI         proposal]] - rationale - backend/tests/test_kb_auto_tag.py
- [[Regression GET apikbdocuments{id}tags returned 500 with         ``Attribut]] - rationale - backend/tests/test_kb_auto_tag.py
- [[Return a list of ``KbTagSuggestion`` dicts for doc.      Rule tags (provenance]] - rationale - backend/app/services/kb/tagger.py
- [[Rule (inline) tags surface in ``applied`` alongside manual ones.]] - rationale - backend/tests/test_kb_auto_tag.py
- [[Rule provenance tags must not be removable by reject_tags.]] - rationale - backend/tests/test_kb_auto_tag.py
- [[Session_229]] - code
- [[TestApplyAndReject]] - code - backend/tests/test_kb_auto_tag.py
- [[TestClient_11]] - code
- [[TestCreateTagEndpoint]] - code - backend/tests/test_kb_auto_tag.py
- [[TestDocumentTagsEndpoint]] - code - backend/tests/test_kb_auto_tag.py
- [[TestNoLLMOnGet]] - code - backend/tests/test_kb_auto_tag.py
- [[TestPerUserIsolation]] - code - backend/tests/test_kb_auto_tag.py
- [[TestProposeTags]] - code - backend/tests/test_kb_auto_tag.py
- [[TestSeedInlineTags]] - code - backend/tests/test_kb_auto_tag.py
- [[_make_doc()_9]] - code - backend/tests/test_kb_auto_tag.py
- [[_make_doc_no_tags()]] - code - backend/tests/test_kb_auto_tag.py
- [[_signup()_21]] - code - backend/tests/test_kb_auto_tag.py
- [[propose_tags()]] - code - backend/app/services/kb/tagger.py
- [[seed_inline_tags()]] - code - backend/app/services/kb/tagger.py
- [[test_kb_auto_tag.py]] - code - backend/tests/test_kb_auto_tag.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_44
SORT file.name ASC
```

## Connections to other communities
- 32 edges to [[_COMMUNITY_Community 92]]
- 19 edges to [[_COMMUNITY_Community 2]]
- 7 edges to [[_COMMUNITY_Community 21]]
- 6 edges to [[_COMMUNITY_Community 43]]
- 2 edges to [[_COMMUNITY_Community 9]]
- 2 edges to [[_COMMUNITY_Community 5]]
- 1 edge to [[_COMMUNITY_Community 10]]
- 1 edge to [[_COMMUNITY_Community 167]]
- 1 edge to [[_COMMUNITY_Community 20]]
- 1 edge to [[_COMMUNITY_Community 1]]
- 1 edge to [[_COMMUNITY_Community 64]]
- 1 edge to [[_COMMUNITY_Community 38]]

## Top bridge nodes
- [[propose_tags()]] - degree 25, connects to 6 communities
- [[test_kb_auto_tag.py]] - degree 24, connects to 6 communities
- [[KbApplyTags]] - degree 14, connects to 3 communities
- [[seed_inline_tags()]] - degree 23, connects to 2 communities
- [[KbRejectTags]] - degree 12, connects to 2 communities