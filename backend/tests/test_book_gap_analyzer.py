"""Tests for the Book Knowledge Gap Analyzer.

Covers the pipeline end-to-end (structure detection, concept extraction,
vault-evidence classification, cross-book dedup, reading queue, status
transitions) plus the REST endpoints and ownership rules. Uses synthetic
page text — ``analyze_pages`` is the testable core; PDF extraction itself is
covered by the text-extractor tests.
"""
from __future__ import annotations

import pytest

from app.models import Book, BookConceptState, BookGapItem, KbConcept, KbDocument, KbEdge, KbSource, User
from app.services.kb import book_gaps


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


def _vault_concept_with_mention(db, user_id: int, name: str, doc: KbDocument) -> KbConcept:
    concept = KbConcept(user_id=user_id, canonical_name=name, definition=f"{name} definition")
    db.add(concept)
    db.commit()
    db.refresh(concept)
    db.add(KbEdge(
        user_id=user_id, source_document_id=doc.id, target_concept_id=concept.id,
        relation="MENTIONS", target_type="concept", weight=0.5, provenance="rule",
    ))
    db.commit()
    return concept


BOOK_PAGES = [
    "Chapter 1 Introduction\n"
    "A reverse shell allows an attacker to establish a connection from the "
    "compromised host back to the attacker's machine.",
    "Chapter 2 Enumeration\n"
    "Nmap port scanning basics. LD_PRELOAD privilege escalation via "
    "environment variables.",
    "Chapter 3 Exploitation\n"
    "Metasploit exploitation and meterpreter sessions.",
    "Chapter 4 Post Exploitation\n"
    "Pass-the-hash and lateral movement.",
    "Chapter 5 Advanced\n"
    "Kerberos delegation is a deep topic. Kerberos delegation spans many "
    "pages of detail. Kerberos delegation has variants. Kerberos delegation "
    "needs careful configuration.",
]


class TestStructureDetection:
    def test_chapter_headings_detected(self):
        chapter_map, chapters = book_gaps._detect_structure(BOOK_PAGES)
        assert len(chapters) == 5
        assert chapters[0]["title"].startswith("Introduction")
        assert chapters[0]["start_page"] == 1
        assert chapters[-1]["end_page"] == 5

    def test_pseudo_chapters_when_no_headings(self):
        pages = [f"plain text page {i}" for i in range(90)]
        chapter_map, chapters = book_gaps._detect_structure(pages)
        # No headings → bucketed; every page still belongs to a chapter.
        assert len(chapters) >= 2
        assert all(t is not None for t in chapter_map)
        assert chapters[0]["start_page"] == 1
        assert chapters[-1]["end_page"] == 90


class TestConceptExtraction:
    def test_lexicon_extracts_concepts_not_words(self, client, db_session):
        token = _signup(client, "bg-lex", "bg-lex@test.com")
        uid = _uid(db_session, "bg-lex@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        # No vault concepts — the seed lexicon still drives extraction.
        result = book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        items = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book["id"]).all()
        by_concept = {i.concept: i for i in items}
        # Concept-level extraction: the canonical concepts exist as items.
        assert "reverse shell" in by_concept
        assert "ld_preload" in by_concept
        assert "metasploit" in by_concept
        assert "pass-the-hash" in by_concept
        # Display uses the book's own spelling when available.
        assert by_concept["nmap"].display_name == "Nmap"
        # The book-level rollup exists and counts items.
        assert result["analysis"]["total_concepts"] >= 5

    def test_kerberos_delegation_stays_one_item_across_pages(self, client, db_session):
        token = _signup(client, "bg-group", "bg-group@test.com")
        uid = _uid(db_session, "bg-group@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        items = db_session.query(BookGapItem).filter(BookGapItem.book_id == book["id"]).all()
        kerb = [i for i in items if "kerberos" in (i.concept or "").lower()]
        # One item, not one per page (requirement 8: group spans).
        assert len(kerb) == 1
        assert kerb[0].page_start <= 5 <= kerb[0].page_end


class TestClassification:
    def test_unknown_when_no_vault_evidence(self, client, db_session):
        token = _signup(client, "bg-unk", "bg-unk@test.com")
        uid = _uid(db_session, "bg-unk@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        item = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book["id"],
            BookGapItem.concept.ilike("%kerberos%"),
        ).first()
        assert item is not None
        assert item.status == "UNKNOWN"
        assert item.knowledge_level == 0
        assert item.est_minutes >= 5

    def test_partial_when_vault_only_mentions(self, client, db_session):
        token = _signup(client, "bg-part", "bg-part@test.com")
        uid = _uid(db_session, "bg-part@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        doc = _vault_doc(db_session, uid, "LD_PRELOAD notes", "LD_PRELOAD lets a binary load a shared library first.")
        _vault_concept_with_mention(db_session, uid, "LD_PRELOAD", doc)

        book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        item = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book["id"],
            BookGapItem.concept.ilike("%ld_preload%"),
        ).first()
        assert item is not None
        # A single mention is weak evidence → PARTIALLY_KNOWN, deeper reading.
        assert item.status == "PARTIALLY_KNOWN"
        assert 1 <= item.knowledge_level <= 3
        assert "deeper" in (item.why or "").lower() or "mentions" in (item.why or "").lower()

    def test_known_when_marked_learned_cumulatively(self, client, db_session):
        token = _signup(client, "bg-known", "bg-known@test.com")
        uid = _uid(db_session, "bg-known@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        # Explicit override: the user studied Nmap before this book.
        db_session.add(BookConceptState(user_id=uid, concept="nmap", my_status="MASTERED"))
        db_session.commit()

        book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        item = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book["id"],
            BookGapItem.concept == "nmap",
        ).first()
        assert item is not None
        assert item.status == "KNOWN"
        assert item.knowledge_level == 5


class TestCrossBookDedup:
    def test_learned_in_book_a_counts_for_book_b(self, client, db_session):
        token = _signup(client, "bg-dedup", "bg-dedup@test.com")
        uid = _uid(db_session, "bg-dedup@test.com")

        book_a = _make_book(client, token, "Book A")
        book_a_obj = db_session.query(Book).filter(Book.id == book_a["id"]).first()
        book_gaps.analyze_pages(db_session, uid, book_a_obj, BOOK_PAGES)

        item = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book_a["id"],
            BookGapItem.concept == "metasploit",
        ).first()
        assert item is not None and item.status == "UNKNOWN"

        book_gaps.mark_item_status(db_session, uid, book_a["id"], item.id, "LEARNED")

        # Book B explains Metasploit again → now recognized as already learned.
        book_b = _make_book(client, token, "Book B")
        book_b_obj = db_session.query(Book).filter(Book.id == book_b["id"]).first()
        book_gaps.analyze_pages(db_session, uid, book_b_obj, BOOK_PAGES)
        item_b = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book_b["id"],
            BookGapItem.concept == "metasploit",
        ).first()
        assert item_b is not None
        assert item_b.status == "KNOWN"
        assert item_b.my_status == "LEARNED"
        assert "Book A" in (item_b.why or "")

    def test_cross_book_state_is_shared_not_per_item(self, client, db_session):
        token = _signup(client, "bg-state", "bg-state@test.com")
        uid = _uid(db_session, "bg-state@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        item = db_session.query(BookGapItem).filter(
            BookGapItem.book_id == book["id"],
            BookGapItem.concept == "pass-the-hash",
        ).first()
        assert item is not None

        updated = book_gaps.mark_item_status(db_session, uid, book["id"], item.id, "LEARNING")
        assert updated["my_status"] == "LEARNING"

        state = db_session.query(BookConceptState).filter(
            BookConceptState.user_id == uid, BookConceptState.concept == item.concept
        ).first()
        assert state is not None and state.my_status == "LEARNING"
        # Same canonical concept in the same book has one state row.
        assert (
            db_session.query(BookConceptState).filter(
                BookConceptState.user_id == uid, BookConceptState.concept == item.concept
            ).count()
            == 1
        )


class TestReadingQueue:
    def test_unknown_before_partial_learned_excluded(self, client, db_session):
        token = _signup(client, "bg-queue", "bg-queue@test.com")
        uid = _uid(db_session, "bg-queue@test.com")
        book = _make_book(client, token)
        book_obj = db_session.query(Book).filter(Book.id == book["id"]).first()

        book_gaps.analyze_pages(db_session, uid, book_obj, BOOK_PAGES)
        queue = book_gaps.reading_queue(db_session, uid, book["id"])
        assert queue, "expected a non-empty queue"
        statuses = [q["status"] for q in queue]
        # No KNOWN items in the reading queue.
        assert all(s != "KNOWN" for s in statuses)
        # UNKNOWN first, PARTIALLY_KNOWN after (stable within a rank).
        first_unknown = statuses.index("UNKNOWN") if "UNKNOWN" in statuses else len(statuses)
        assert all(s == "UNKNOWN" for s in statuses[:first_unknown])

        # Marking the top item learned drops it from the queue.
        top_id = queue[0]["id"]
        book_gaps.mark_item_status(db_session, uid, book["id"], top_id, "LEARNED")
        after = [q["id"] for q in book_gaps.reading_queue(db_session, uid, book["id"])]
        assert top_id not in after


class TestOverview:
    def test_overview_includes_unanalyzed_and_analyzed_books(self, client, db_session):
        token = _signup(client, "bg-ov", "bg-ov@test.com")
        uid = _uid(db_session, "bg-ov@test.com")

        unanalyzed = _make_book(client, token, "Not Analyzed Yet")
        analyzed = _make_book(client, token, "Analyzed Book")
        analyzed_obj = db_session.query(Book).filter(Book.id == analyzed["id"]).first()
        book_gaps.analyze_pages(db_session, uid, analyzed_obj, BOOK_PAGES)

        data = book_gaps.overview(db_session, uid)
        by_id = {b["book_id"]: b for b in data["books"]}
        assert by_id[unanalyzed["id"]]["analyzed"] is False
        assert by_id[analyzed["id"]]["analyzed"] is True
        assert by_id[analyzed["id"]]["unknown"] > 0
        assert data["total_concepts"] > 0
        assert data["learned_concepts"] == 0


class TestEndpoints:
    def test_analyze_dashboard_items_queue_status_flow(self, client, db_session, monkeypatch):
        token = _signup(client, "bg-api", "bg-api@test.com")
        headers = _auth(token)
        book = _make_book(client, token)

        # Analyze via the real pipeline using synthetic pages (PDF extraction
        # is covered by text-extractor tests).
        def fake_analyze(db, user_id, book_id):
            b = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
            return book_gaps.analyze_pages(db, user_id, b, BOOK_PAGES)

        monkeypatch.setattr("app.services.kb.book_gaps.analyze_book", fake_analyze)

        r = client.post(f"/api/kb/books/{book['id']}/analyze", headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["analysis"]["total_pages"] == 5
        assert body["analysis"]["chapters"] == 5
        assert body["items"] >= 5

        # Idempotent re-analysis: same counts, no duplicate items.
        r2 = client.post(f"/api/kb/books/{book['id']}/analyze", headers=headers)
        assert r2.status_code == 200
        assert db_session.query(BookGapItem).filter(BookGapItem.book_id == book["id"]).count() == r2.json()["items"]

        dash = client.get(f"/api/kb/books/{book['id']}/dashboard", headers=headers).json()
        assert dash["analysis"]["total_concepts"] == body["analysis"]["total_concepts"]
        assert dash["chapters"], "expected per-chapter rollup"

        items = client.get(f"/api/kb/books/{book['id']}/items", headers=headers).json()["items"]
        assert items, "expected items"
        unknown = client.get(f"/api/kb/books/{book['id']}/items?status=UNKNOWN", headers=headers).json()["items"]
        assert len(unknown) >= 1
        assert all(i["status"] == "UNKNOWN" for i in unknown)

        queue = client.get(f"/api/kb/books/{book['id']}/queue", headers=headers).json()["items"]
        assert queue and all(i["status"] != "KNOWN" for i in queue)

        # Status transition through the API.
        top = queue[0]
        s = client.post(
            f"/api/kb/books/{book['id']}/items/{top['id']}/status",
            json={"status": "learned"},
            headers=headers,
        )
        assert s.status_code == 200, s.text
        assert s.json()["my_status"] == "LEARNED"
        # Invalid status rejected.
        bad = client.post(
            f"/api/kb/books/{book['id']}/items/{top['id']}/status",
            json={"status": "nope"},
            headers=headers,
        )
        assert bad.status_code == 400
        # Unknown item → 404.
        missing = client.post(
            f"/api/kb/books/{book['id']}/items/999999/status",
            json={"status": "learned"},
            headers=headers,
        )
        assert missing.status_code == 404

    def test_ownership_and_not_found(self, client, db_session):
        token_a = _signup(client, "bg-own-a", "bg-own-a@test.com")
        token_b = _signup(client, "bg-own-b", "bg-own-b@test.com")
        book = _make_book(client, token_a)

        # User B cannot analyze or read A's book.
        assert client.post(f"/api/kb/books/{book['id']}/analyze", headers=_auth(token_b)).status_code == 404
        assert client.get(f"/api/kb/books/{book['id']}/dashboard", headers=_auth(token_b)).status_code == 404
        assert client.get(f"/api/kb/books/{book['id']}/items", headers=_auth(token_b)).status_code == 404
        assert client.get(f"/api/kb/books/{book['id']}/queue", headers=_auth(token_b)).status_code == 404
        # B's overview does not list A's book.
        ov = client.get("/api/kb/books/overview", headers=_auth(token_b)).json()
        assert all(b["book_id"] != book["id"] for b in ov["books"])
        # Unknown book → 404.
        assert client.post("/api/kb/books/999999/analyze", headers=_auth(token_a)).status_code == 404
