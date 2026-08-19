"""Tests for the TOC-first Book Knowledge Gap Analyzer workflow.

Two-stage model:
- Stage 1 (``analyze_toc`` / ``_extract_toc``): deterministic heading
  hierarchy (chapters → sections → subsections) + semantic matching against
  the Second Brain. NO LLM — uploading a book never triggers AI analysis.
- Stage 2 (``analyze_topic_deep``): per-topic deep comparison, only on an
  explicit user action; persisted (never recomputed on navigation); missing
  sub-concepts become ``BookGapItem`` rows with page evidence; re-run only
  on explicit Re-analyze.
- ``add_topic_to_brain``: unknown topics become Second Brain study notes.
"""
from __future__ import annotations

import json

import pytest

from app.models import (
    Book,
    BookConceptState,
    BookGapAnalysis,
    BookGapItem,
    BookGapTopic,
    KbConcept,
    KbDocument,
    KbEdge,
    KbSource,
    User,
)
from app.services.kb import book_gaps

pytestmark = pytest.mark.usefixtures("_disable_ai")


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname: str, email: str):
    resp = client.post(
        "/api/auth/signup",
        json={"name": uname, "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _uid(db, email: str) -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_book(client, token: str, title: str = "Penetration Testing") -> dict:
    resp = client.post(
        "/api/books",
        json={"title": title, "author": "Author", "category": "reading"},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _vault_doc(db, user_id: int, title: str, text: str) -> KbDocument:
    src = KbSource(user_id=user_id, name="Notes", source_type="local_dir", root_path=f"/tmp/{title}")
    db.add(src)
    db.commit()
    db.refresh(src)
    doc = KbDocument(
        user_id=user_id,
        source_id=src.id,
        title=title,
        doc_type="md",
        path_rel=f"notes/{title}.md",
        extracted_text=text,
        content_hash=f"hash-{title}",
        char_count=len(text),
        status="unchanged",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _vault_concept(db, user_id: int, name: str, aliases: list[str] | None = None) -> KbConcept:
    concept = KbConcept(
        user_id=user_id,
        canonical_name=name,
        definition=f"{name} definition",
        aliases=json.dumps(aliases) if aliases else None,
    )
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def _mention(db, user_id: int, doc: KbDocument, concept: KbConcept) -> None:
    db.add(KbEdge(
        user_id=user_id, source_document_id=doc.id, target_concept_id=concept.id,
        relation="MENTIONS", target_type="concept", weight=1.0, provenance="rule",
    ))
    db.commit()


# Chapter + numbered-section pages (a realistic book TOC).
TOC_PAGES = [
    "Chapter 1 Introduction\nSome overview text here.\n1.1 Why security matters\n1.2 Threat model",
    "Chapter 2 Authentication\n2.1 Password-based authentication\n2.2 Session management\n2.3 MFA",
    "Chapter 3 Access Control\n3.1 IDOR\n3.2 Privilege escalation\n3.3 Authorization flaws",
    "Chapter 4 Server-Side Request Forgery\n4.1 Basic SSRF\n4.2 Blind SSRF\n4.3 SSRF bypass techniques",
    "Chapter 5 Path Traversal\n5.1 Basic path traversal\n5.2 URL encoding\n5.3 Double URL encoding\n5.4 Null byte bypass",
]


class TestTocExtraction:
    def test_hierarchy_and_page_ranges(self):
        chapter_map, chapters_meta = book_gaps._detect_structure(TOC_PAGES)
        toc = book_gaps._extract_toc(TOC_PAGES, chapter_map, chapters_meta)
        # 5 chapters + their numbered sections.
        chapters = [t for t in toc if t["level"] == 1]
        sections = [t for t in toc if t["level"] == 2]
        assert len(chapters) == 5
        assert len(sections) >= 10
        assert chapters[0]["title"].startswith("Introduction")
        assert chapters[0]["page_start"] == 1
        assert chapters[-1]["page_end"] == 5
        # Sections belong to their chapter and carry page ranges.
        ssrf_sections = [
            t for t in toc
            if t["level"] == 2 and t["parent_title"] == "Server-Side Request Forgery"
        ]
        assert ssrf_sections
        assert any("Basic SSRF" in t["title"] for t in ssrf_sections)
        assert all(t["page_start"] <= t["page_end"] for t in toc)
        # Hierarchy is preserved: section level == 2, chapter level == 1.
        assert all(t["level"] in (1, 2, 3) for t in toc)

    def test_pseudo_chapters_fallback_still_yields_topics(self):
        pages = [f"plain text page {i}" for i in range(90)]
        chapter_map, chapters_meta = book_gaps._detect_structure(pages)
        toc = book_gaps._extract_toc(pages, chapter_map, chapters_meta)
        assert len(toc) >= 2
        assert all(t["page_start"] >= 1 and t["page_end"] <= 90 for t in toc)


class TestStage1AnalyzeToc:
    def test_no_llm_and_topics_persisted(self, client, db_session, monkeypatch):
        token = _signup(client, "toc-nollm", "toc-nollm@test.com")
        uid = _uid(db_session, "toc-nollm@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        # The LLM must never be reached during Stage 1.
        called = {"n": 0}

        def boom(*args, **kwargs):
            called["n"] += 1
            raise AssertionError("Stage 1 must not call the LLM")

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate_json", boom)

        result = book_gaps.analyze_toc(db_session, uid, book_obj, TOC_PAGES)
        assert called["n"] == 0

        topics = db_session.query(BookGapTopic).filter(BookGapTopic.book_id == book["id"]).all()
        assert len(topics) >= 15
        assert result["analysis"]["chapters"] == 5
        assert result["analysis"]["total_concepts"] == len(topics)
        # Every topic starts NOT_ANALYZED (deep analysis is a separate step).
        assert all(t.deep_status == book_gaps.NOT_ANALYZED for t in topics)

    def test_semantic_alias_match_ssrf(self, client, db_session):
        """Server-Side Request Forgery (book) ↔ SSRF (Second Brain)."""
        token = _signup(client, "toc-alias", "toc-alias@test.com")
        uid = _uid(db_session, "toc-alias@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        # Vault holds the alias form "SSRF"; the book uses the full name.
        # 4 mentions across 2 docs → Strong evidence → KNOWN.
        concept = _vault_concept(db_session, uid, "SSRF")
        for i in range(2):
            doc = _vault_doc(db_session, uid, f"SSRF notes {i}", "SSRF lets an attacker make the server fetch internal URLs.")
            _mention(db_session, uid, doc, concept)
            _mention(db_session, uid, doc, concept)

        book_gaps.analyze_toc(db_session, uid, book_obj, TOC_PAGES)
        topics = db_session.query(BookGapTopic).filter(BookGapTopic.book_id == book["id"]).all()
        chapter = [t for t in topics if t.title == "Server-Side Request Forgery"]
        assert chapter
        # The alias expansion must resolve to the vault concept (alias source).
        assert chapter[0].second_brain_match in ("SSRF", "server-side request forgery")
        # Child-coverage rule (spec's Authentication example): the broad topic
        # exists in the Second Brain, but the book's subtopics (Blind SSRF,
        # SSRF bypass techniques) are missing → PARTIALLY_KNOWN, never falsely
        # KNOWN just because the parent name matched.
        assert chapter[0].status == book_gaps.PARTIAL
        # The subtopics themselves are unknown (they are the actual gaps).
        blind = [t for t in topics if "Blind SSRF" in t.title]
        assert blind and blind[0].status == book_gaps.UNKNOWN

    def test_known_partial_unknown_needs_review(self, client, db_session):
        token = _signup(client, "toc-st", "toc-st@test.com")
        uid = _uid(db_session, "toc-st@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        # Strong evidence for Authentication (multiple mentions + 2 docs).
        for i in range(2):
            d = _vault_doc(db_session, uid, f"auth notes {i}", "Password authentication and session management details.")
            _mention(db_session, uid, d, _vault_concept(db_session, uid, f"authentication-{i}", ["authentication"]))
        # Path Traversal known via alias "directory traversal" mention.
        d = _vault_doc(db_session, uid, "PT notes", "Directory traversal basics with ../ sequences.")
        _mention(db_session, uid, d, _vault_concept(db_session, uid, "path traversal", ["directory traversal", "path traversal"]))

        book_gaps.analyze_toc(db_session, uid, book_obj, TOC_PAGES)
        by_title = {
            t.title: t
            for t in db_session.query(BookGapTopic).filter(BookGapTopic.book_id == book["id"]).all()
        }
        # Section headings are stored without their numbers ("Authorization
        # flaws", not "3.3 Authorization flaws").
        assert by_title.get("Authorization flaws", None) is not None
        assert by_title["Authorization flaws"].status == book_gaps.UNKNOWN
        # Path Traversal: single mention of the alias → weak evidence →
        # PARTIALLY_KNOWN (never falsely "known" from one mention).
        pt = by_title.get("Path Traversal")
        assert pt is not None
        assert pt.status == book_gaps.PARTIAL

    def test_add_topic_to_brain_creates_study_note(self, client, db_session):
        token = _signup(client, "toc-add", "toc-add@test.com")
        uid = _uid(db_session, "toc-add@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()
        book_gaps.analyze_toc(db_session, uid, book_obj, TOC_PAGES)

        topic = db_session.query(BookGapTopic).filter(
            BookGapTopic.book_id == book["id"], BookGapTopic.title.like("%IDOR%")
        ).first()
        assert topic is not None

        result = book_gaps.add_topic_to_brain(db_session, uid, book["id"], topic.id)
        assert result["created"] is True
        assert result["document"]["status"] == "draft"

        # Idempotent: a second call reuses the existing draft.
        result2 = book_gaps.add_topic_to_brain(db_session, uid, book["id"], topic.id)
        assert result2["created"] is False
        assert result2["document"]["id"] == result["document"]["id"]


class TestStage2DeepAnalysis:
    def _analyzed_topic(self, client, db_session, email: str):
        token = _signup(client, email, f"{email}@test.com")
        uid = _uid(db_session, f"{email}@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()
        book_gaps.analyze_toc(db_session, uid, book_obj, TOC_PAGES)
        return uid, book_obj

    def test_deep_analysis_persists_and_creates_items(self, client, db_session, monkeypatch):
        uid, book_obj = self._analyzed_topic(client, db_session, "deep-a")
        topic = db_session.query(BookGapTopic).filter(
            BookGapTopic.book_id == book_obj.id, BookGapTopic.title.like("%Blind SSRF%")
        ).first()
        assert topic is not None

        monkeypatch.setattr(
            "app.services.kb.book_gaps.extract_pdf_pages",
            lambda path: TOC_PAGES,
        )
        monkeypatch.setattr("app.services.kb.book_gaps._book_file_path", lambda book: __import__("pathlib").Path("/tmp/none.pdf"))

        payload = book_gaps.analyze_topic_deep(db_session, uid, book_obj.id, topic.id)
        assert payload["deep_status"] == book_gaps.ANALYZED
        assert payload["deep_result"] is not None

        # Missing sub-concepts became BookGapItem rows linked to the topic.
        items = db_session.query(BookGapItem).filter(BookGapItem.deep_topic_id == topic.id).all()
        assert items
        assert all(it.page_start is not None for it in items)

    def test_deep_reanalyze_replaces_not_duplicates(self, client, db_session, monkeypatch):
        uid, book_obj = self._analyzed_topic(client, db_session, "deep-b")
        topic = db_session.query(BookGapTopic).filter(
            BookGapTopic.book_id == book_obj.id, BookGapTopic.title.like("%Blind SSRF%")
        ).first()
        monkeypatch.setattr("app.services.kb.book_gaps.extract_pdf_pages", lambda path: TOC_PAGES)
        monkeypatch.setattr("app.services.kb.book_gaps._book_file_path", lambda book: __import__("pathlib").Path("/tmp/none.pdf"))

        first = book_gaps.analyze_topic_deep(db_session, uid, book_obj.id, topic.id)
        first_count = db_session.query(BookGapItem).filter(BookGapItem.deep_topic_id == topic.id).count()
        second = book_gaps.analyze_topic_deep(db_session, uid, book_obj.id, topic.id)
        second_count = db_session.query(BookGapItem).filter(BookGapItem.deep_topic_id == topic.id).count()
        # Same number of rows after an explicit re-analyze (replaced, not stacked).
        assert first_count == second_count
        assert first["deep_status"] == book_gaps.ANALYZED
        assert second["deep_status"] == book_gaps.ANALYZED

    def test_deep_llm_failure_marks_failed(self, client, db_session, monkeypatch):
        uid, book_obj = self._analyzed_topic(client, db_session, "deep-c")
        topic = db_session.query(BookGapTopic).filter(
            BookGapTopic.book_id == book_obj.id, BookGapTopic.title.like("%Blind SSRF%")
        ).first()
        monkeypatch.setattr("app.services.kb.book_gaps.extract_pdf_pages", lambda path: TOC_PAGES)
        monkeypatch.setattr("app.services.kb.book_gaps._book_file_path", lambda book: __import__("pathlib").Path("/tmp/none.pdf"))
        monkeypatch.setattr(
            "app.services.kb.book_gaps._llm_deep_compare",
            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        payload = book_gaps.analyze_topic_deep(db_session, uid, book_obj.id, topic.id)
        assert payload["deep_status"] == book_gaps.FAILED


class TestEndpoints:
    def test_stage1_analyze_topics_endpoints(self, client, db_session, monkeypatch):
        token = _signup(client, "bg-toc-api", "bg-toc-api@test.com")
        headers = _auth(token)
        book = _make_book(client, token)

        # Real Stage-1 flow with synthetic pages (PDF extraction covered elsewhere).
        def fake_analyze(db, user_id, book_id):
            b = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
            return book_gaps.analyze_toc(db, user_id, b, TOC_PAGES)

        monkeypatch.setattr("app.services.kb.book_gaps.analyze_book", fake_analyze)

        r = client.post(f"/api/kb/books/{book['id']}/analyze", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["analysis"]["total_pages"] == 5
        assert body["analysis"]["chapters"] == 5
        assert body["items"] == 0  # Stage 1 creates topics, not items
        assert body["topics"]

        # Topics endpoint returns the persisted topics.
        tr = client.get(f"/api/kb/books/{book['id']}/topics", headers=headers)
        assert tr.status_code == 200
        assert len(tr.json()["topics"]) == len(body["topics"])

        # Dashboard now includes topics + chapter rollup.
        dash = client.get(f"/api/kb/books/{book['id']}/dashboard", headers=headers).json()
        assert dash["topics"]
        assert dash["chapters"]

    def test_deep_analyze_endpoint(self, client, db_session, monkeypatch):
        token = _signup(client, "bg-deep-api", "bg-deep-api@test.com")
        headers = _auth(token)
        book = _make_book(client, token)

        def fake_analyze(db, user_id, book_id):
            b = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
            return book_gaps.analyze_toc(db, user_id, b, TOC_PAGES)

        monkeypatch.setattr("app.services.kb.book_gaps.analyze_book", fake_analyze)
        monkeypatch.setattr("app.services.kb.book_gaps.extract_pdf_pages", lambda path: TOC_PAGES)
        monkeypatch.setattr("app.services.kb.book_gaps._book_file_path", lambda book: __import__("pathlib").Path("/tmp/none.pdf"))

        client.post(f"/api/kb/books/{book['id']}/analyze", headers=headers)
        topic = db_session.query(BookGapTopic).filter(BookGapTopic.book_id == book["id"]).first()

        r = client.post(
            f"/api/kb/books/{book['id']}/topics/{topic.id}/analyze", headers=headers
        )
        assert r.status_code == 200, r.text
        assert r.json()["deep_status"] == book_gaps.ANALYZED

        # Ownership: another user cannot analyze the topic.
        token_b = _signup(client, "bg-deep-own", "bg-deep-own@test.com")
        r_b = client.post(
            f"/api/kb/books/{book['id']}/topics/{topic.id}/analyze",
            headers=_auth(token_b),
        )
        assert r_b.status_code == 404

        # Unknown topic → 404.
        r_miss = client.post(
            f"/api/kb/books/{book['id']}/topics/999999/analyze", headers=headers
        )
        assert r_miss.status_code == 404

    def test_add_to_brain_endpoint(self, client, db_session, monkeypatch):
        token = _signup(client, "bg-add-api", "bg-add-api@test.com")
        headers = _auth(token)
        book = _make_book(client, token)

        def fake_analyze(db, user_id, book_id):
            b = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
            return book_gaps.analyze_toc(db, user_id, b, TOC_PAGES)

        monkeypatch.setattr("app.services.kb.book_gaps.analyze_book", fake_analyze)
        client.post(f"/api/kb/books/{book['id']}/analyze", headers=headers)
        topic = db_session.query(BookGapTopic).filter(BookGapTopic.book_id == book["id"]).first()

        r = client.post(
            f"/api/kb/books/{book['id']}/topics/{topic.id}/add-to-brain", headers=headers
        )
        assert r.status_code == 200, r.text
        assert r.json()["document"]["status"] == "draft"

        # Unknown topic → 404.
        r_miss = client.post(
            f"/api/kb/books/{book['id']}/topics/999999/add-to-brain", headers=headers
        )
        assert r_miss.status_code == 404

    def test_items_status_validation_allows_needs_review(self, client, db_session, monkeypatch):
        token = _signup(client, "bg-items-api", "bg-items-api@test.com")
        headers = _auth(token)
        book = _make_book(client, token)

        def fake_analyze(db, user_id, book_id):
            b = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
            return book_gaps.analyze_toc(db, user_id, b, TOC_PAGES)

        monkeypatch.setattr("app.services.kb.book_gaps.analyze_book", fake_analyze)
        client.post(f"/api/kb/books/{book['id']}/analyze", headers=headers)

        bad = client.get(f"/api/kb/books/{book['id']}/items?status=NOPE", headers=headers)
        assert bad.status_code == 400
        ok = client.get(f"/api/kb/books/{book['id']}/items?status=UNKNOWN", headers=headers)
        assert ok.status_code == 200
