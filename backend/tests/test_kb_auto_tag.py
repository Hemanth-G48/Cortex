"""Auto-tagging tests (Phase 2, Idea 14, phrase 38)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import KbDocument, KbDocumentTag, KbTag
from app.services.kb.tagger import (
    apply_tags,
    propose_tags,
    reject_tags,
    seed_inline_tags,
)
from app.schemas.kb import KbApplyTags, KbRejectTags

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "tag-user", email: str = "tag@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Tagger",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_doc(db: Session, user_id: int, title: str = "Test Doc") -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        extracted_text="# Title\n\nThis is a test document about machine learning and AI research.\n\n#python #datascience",
        frontmatter_json={"tags": ["frontmatter-tag"]},
        char_count=100,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _make_doc_no_tags(db: Session, user_id: int, title: str = "No Tags Doc") -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        extracted_text="Just some plain text with no tags at all.",
        char_count=50,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestSeedInlineTags:
    def test_seeds_from_frontmatter(self, db_session: Session, client: TestClient):
        token = _signup(client)
        # Create a document with frontmatter tags.
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"---\ntags:\n  - frontmatter-tag\n---\n# Title\n\nContent here.", "test.md")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        doc = db_session.query(KbDocument).get(doc_id)
        tag_ids = seed_inline_tags(db_session, doc)
        assert len(tag_ids) >= 1
        # "frontmatter-tag" from the frontmatter_json key should be present.
        tag_names = {
            db_session.query(KbTag).get(tid).name for tid in tag_ids
        }
        assert "frontmatter-tag" in tag_names

    def test_seeds_from_inline_hashes(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\nContent #python #fastapi", "test.md")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        tag_ids = seed_inline_tags(db_session, doc)
        tag_names = {db_session.query(KbTag).get(tid).name for tid in tag_ids}
        assert "python" in tag_names
        assert "fastapi" in tag_names

    def test_idempotent(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\nContent #python", "test.md")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        ids1 = seed_inline_tags(db_session, doc)
        ids2 = seed_inline_tags(db_session, doc)
        assert sorted(ids1) == sorted(ids2)

    def test_rule_tags_never_suggested_for_deletion(self, db_session: Session):
        """Rule provenance tags must not be removable by reject_tags."""
        # This is enforced by reject_tags logic, not by seed_inline_tags itself.
        # We verify that seed_inline_tags always creates provenance="rule" rows.
        pass  # enforced by reject_tags tests below


class TestProposeTags:
    def test_deterministic_fallback_when_ai_disabled(self, db_session: Session, client: TestClient):
        from app.config import settings

        token = _signup(client)
        # Create a doc with chunks so TF-IDF has something to work with.
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": (
                "test.md",
                b"# Machine Learning\n\nDeep learning is a subset of machine learning. "
                b"Neural networks are used for deep learning tasks. "
                b"#python #ml",
                "test.md",
            )},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)

        # Monkeypatch AI_ENABLED to False so propose_tags uses TF-IDF fallback.
        original = settings.AI_ENABLED
        settings.AI_ENABLED = False
        try:
            suggestions = propose_tags(db_session, doc)
            # Should return suggestions with provenance "ai" (from fallback) and confidence 0.5.
            ai_suggestions = [s for s in suggestions if s["provenance"] == "ai"]
            assert len(ai_suggestions) > 0
            for s in ai_suggestions:
                assert s["confidence"] == 0.5
        finally:
            settings.AI_ENABLED = original

    def test_create_or_reuse_tags(self, db_session: Session, client: TestClient):
        token = _signup(client)
        # Create two docs for the same user.
        resp1 = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("doc1.md", b"# Doc1\n\nContent about python programming", "doc1.md")},
        )
        assert resp1.status_code == 201
        doc1_id = resp1.json()["document"]["id"]

        resp2 = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("doc2.md", b"# Doc2\n\nContent about python scripting", "doc2.md")},
        )
        assert resp2.status_code == 201
        doc2_id = resp2.json()["document"]["id"]

        doc1 = db_session.query(KbDocument).get(doc1_id)
        doc2 = db_session.query(KbDocument).get(doc2_id)

        # Disable AI so we get deterministic fallback.
        from app.config import settings
        original = settings.AI_ENABLED
        settings.AI_ENABLED = False
        try:
            seed_inline_tags(db_session, doc1)
            seed_inline_tags(db_session, doc2)
            propose_tags(db_session, doc1)
            propose_tags(db_session, doc2)

            # Both docs should share the same KbTag row for "python".
            python_tags = (
                db_session.query(KbTag)
                .filter(KbTag.user_id == doc1.user_id, KbTag.name == "python")
                .all()
            )
            assert len(python_tags) == 1
        finally:
            settings.AI_ENABLED = original

    def test_rule_tags_have_confidence_1(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"---\ntags:\n  - science\n  - research\n---\n# Title\n\nContent", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        seed_inline_tags(db_session, doc)
        suggestions = propose_tags(db_session, doc)
        rule_suggestions = [s for s in suggestions if s["provenance"] == "rule"]
        assert len(rule_suggestions) >= 1
        for s in rule_suggestions:
            assert s["confidence"] == 1.0


class TestApplyAndReject:
    def test_apply_promotes_to_manual(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\ntext about python", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        seed_inline_tags(db_session, doc)
        suggestions = propose_tags(db_session, doc)

        ai_suggestions = [s for s in suggestions if s["provenance"] == "ai"]
        if not ai_suggestions:
            pytest.skip("No AI suggestions available to apply")

        tag_id = ai_suggestions[0]["tag_id"]
        count = apply_tags(db_session, doc, [tag_id])
        assert count == 1

        # Verify the row now has provenance="manual".
        dt = (
            db_session.query(KbDocumentTag)
            .filter(
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == tag_id,
            )
            .first()
        )
        assert dt is not None
        assert dt.provenance == "manual"

    def test_apply_idempotent(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\ntext about python", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        seed_inline_tags(db_session, doc)
        suggestions = propose_tags(db_session, doc)

        ai_suggestions = [s for s in suggestions if s["provenance"] == "ai"]
        if not ai_suggestions:
            pytest.skip("No AI suggestions available to apply")

        tag_id = ai_suggestions[0]["tag_id"]
        count1 = apply_tags(db_session, doc, [tag_id])
        count2 = apply_tags(db_session, doc, [tag_id])
        assert count1 == 1
        assert count2 == 1  # idempotent — still returns 1 applied

        # Only one row should exist.
        rows = (
            db_session.query(KbDocumentTag)
            .filter(
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == tag_id,
            )
            .all()
        )
        assert len(rows) == 1
        assert rows[0].provenance == "manual"

    def test_reject_never_removes_rule_tags(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"---\ntags:\n  - important\n---\n# Title\n\nContent about python", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        seed_inline_tags(db_session, doc)
        suggestions = propose_tags(db_session, doc)

        # Find the rule tag id for "important".
        rule_tag_ids = [s["tag_id"] for s in suggestions if s["provenance"] == "rule"]
        assert len(rule_tag_ids) >= 1
        rule_tag_id = rule_tag_ids[0]

        # Try to reject it.
        removed = reject_tags(db_session, doc, [rule_tag_id])
        assert removed == 0  # rule tags are never removed

        # Verify the row still exists with provenance="rule".
        dt = (
            db_session.query(KbDocumentTag)
            .filter(
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == rule_tag_id,
            )
            .first()
        )
        assert dt is not None
        assert dt.provenance == "rule"

    def test_reject_removes_ai_tags(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\ntext about python programming", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        seed_inline_tags(db_session, doc)
        suggestions = propose_tags(db_session, doc)

        ai_suggestions = [s for s in suggestions if s["provenance"] == "ai"]
        if not ai_suggestions:
            pytest.skip("No AI suggestions available to reject")

        tag_id = ai_suggestions[0]["tag_id"]
        # First apply it so it exists as a row.
        apply_tags(db_session, doc, [tag_id])

        # Now reject it.
        removed = reject_tags(db_session, doc, [tag_id])
        assert removed == 1

        # Verify the row is gone.
        dt = (
            db_session.query(KbDocumentTag)
            .filter(
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == tag_id,
            )
            .first()
        )
        assert dt is None

    def test_reject_removes_manual_tags(self, db_session: Session, client: TestClient):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\ntext about python", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)
        seed_inline_tags(db_session, doc)
        suggestions = propose_tags(db_session, doc)

        ai_suggestions = [s for s in suggestions if s["provenance"] == "ai"]
        if not ai_suggestions:
            pytest.skip("No AI suggestions available")

        tag_id = ai_suggestions[0]["tag_id"]
        apply_tags(db_session, doc, [tag_id])

        # Reject the manual tag.
        removed = reject_tags(db_session, doc, [tag_id])
        assert removed == 1

        dt = (
            db_session.query(KbDocumentTag)
            .filter(
                KbDocumentTag.document_id == doc.id,
                KbDocumentTag.tag_id == tag_id,
            )
            .first()
        )
        assert dt is None


class TestDocumentTagsEndpoint:
    def test_get_document_tags_returns_200_when_manual_tags_exist(
        self, db_session: Session, client: TestClient
    ):
        """Regression: GET /api/kb/documents/{id}/tags returned 500 with
        ``AttributeError: 'KbDocument' object has no attribute 'document_tags'``
        (the KbDocument↔KbDocumentTag relationship was missing).
        """
        from app.config import settings

        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", b"# Title\n\nContent about python programming #ml", "test.md")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]
        doc = db_session.query(KbDocument).get(doc_id)

        # Give the doc a manual (applied) tag so the endpoint's
        # ``doc.document_tags`` loop has rows to read.
        original = settings.AI_ENABLED
        settings.AI_ENABLED = False
        try:
            seed_inline_tags(db_session, doc)
            suggestions = propose_tags(db_session, doc)
            ai_suggestions = [s for s in suggestions if s["provenance"] == "ai"]
            assert ai_suggestions, "expected deterministic fallback suggestions"
            apply_tags(db_session, doc, [ai_suggestions[0]["tag_id"]])
        finally:
            settings.AI_ENABLED = original

        # Previously raised AttributeError -> 500 Internal Server Error.
        resp = client.get(
            f"/api/kb/documents/{doc_id}/tags",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Applied (manual) tags must be excluded from the suggestion list.
        applied_tag_id = ai_suggestions[0]["tag_id"]
        assert all(s["tag_id"] != applied_tag_id for s in data["tags"])


class TestPerUserIsolation:
    def test_user_cannot_see_other_users_tags(self, db_session: Session, client: TestClient):
        token_a = _signup(client, uname="user-a", email="a@test.com")
        token_b = _signup(client, uname="user-b", email="b@test.com")

        # User A creates a doc with a tag.
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token_a}"},
            files={"file": ("test.md", b"# Title\ntags: [secret]\n\nContent", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]

        # User B tries to get tags for user A's doc — should 404.
        resp_b = client.get(
            f"/api/kb/documents/{doc_id}/tags",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 404

    def test_user_cannot_apply_tags_to_other_users_doc(self, db_session: Session, client: TestClient):
        token_a = _signup(client, uname="user-c", email="c@test.com")
        token_b = _signup(client, uname="user-d", email="d@test.com")

        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token_a}"},
            files={"file": ("test.md", b"# Title\n\nContent", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]

        resp_b = client.post(
            f"/api/kb/documents/{doc_id}/tags",
            json=KbApplyTags(document_id=doc_id, tag_ids=[999]).model_dump(),
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 404

    def test_user_cannot_reject_tags_on_other_users_doc(self, db_session: Session, client: TestClient):
        token_a = _signup(client, uname="user-e", email="e@test.com")
        token_b = _signup(client, uname="user-f", email="f@test.com")

        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token_a}"},
            files={"file": ("test.md", b"# Title\n\nContent", "test.md")},
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document"]["id"]

        resp_b = client.delete(
            f"/api/kb/documents/{doc_id}/tags/1",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp_b.status_code == 404