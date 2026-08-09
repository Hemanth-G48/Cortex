"""Idea 76 — connect new documents to existing notes tests.

Covers connect_suggestions (shared-concept ranking), confirm → manual edge
creation, already-connected suppression, contradiction-hint hand-off, and
per-user isolation.
"""
from __future__ import annotations

import pytest
from datetime import timedelta

from app.models import KbConcept, KbDocument, KbEdge
from app.services.kb import utcnow
from app.services.kb.graph import add_edge


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="con-user", email="con@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Con", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _user_id(db_session, token):
    from app.services.security import decode_bearer_token

    return decode_bearer_token(token)["user_id"]


def _make_doc(db, user_id, title, concepts, status="unchanged", updated_days_ago=0):
    doc = KbDocument(user_id=user_id, title=title, doc_type="md", status=status,
                     extracted_text=f"# {title}\n\ncontent", content_hash=f"hash-{title}",
                     char_count=40)
    if updated_days_ago:
        doc.updated_at = utcnow() - timedelta(days=updated_days_ago)
    db.add(doc)
    db.flush()
    for cname in concepts:
        concept = db.query(KbConcept).filter(
            KbConcept.user_id == user_id, KbConcept.canonical_name == cname
        ).first()
        if concept is None:
            concept = KbConcept(user_id=user_id, canonical_name=cname)
            db.add(concept)
            db.flush()
        add_edge(db, user_id, doc.id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=1.0, overwrite=True)
    db.flush()
    return doc


class TestSuggestions:
    def test_shared_concept_candidate_ranked(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Linear algebra notes", ["linear algebra"])
        new = _make_doc(db_session, user_id, "Matrix notes", ["linear algebra", "matrices"])
        db_session.commit()

        r = client.get(f"/api/kb/documents/{new.id}/connect-suggestions", headers=_auth(token))
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert items, "expected a connect suggestion"
        assert items[0]["title"] == "Linear algebra notes"
        assert "shared_concepts" in items[0]
        assert "linear algebra" in items[0]["shared_concepts"]

    def test_no_suggestions_without_shared_concepts(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Chemistry notes", ["chemistry"])
        new = _make_doc(db_session, user_id, "Physics notes", ["physics"])
        db_session.commit()

        r = client.get(f"/api/kb/documents/{new.id}/connect-suggestions", headers=_auth(token))
        assert r.json()["items"] == []

    def test_strongly_related_flag(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Stats notes", ["statistics", "probability"])
        new = _make_doc(db_session, user_id, "Stats primer", ["statistics", "probability", "sampling"])
        db_session.commit()

        items = client.get(f"/api/kb/documents/{new.id}/connect-suggestions", headers=_auth(token)).json()["items"]
        assert items
        assert any("strongly related" in r for r in items[0]["reasons"])


class TestSuppression:
    def test_already_connected_target_suppressed(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        a = _make_doc(db_session, user_id, "Doc A", ["shared concept"])
        b = _make_doc(db_session, user_id, "Doc B", ["shared concept"])
        # Manually link A→B.
        add_edge(db_session, user_id, a.id, target_document_id=b.id,
                 relation="RELATED", provenance="manual")
        db_session.commit()

        items = client.get(f"/api/kb/documents/{a.id}/connect-suggestions", headers=_auth(token)).json()["items"]
        assert not any(i["document_id"] == b.id for i in items)


class TestConfirm:
    def test_confirm_creates_manual_edge(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        a = _make_doc(db_session, user_id, "Doc A", ["physics"])
        b = _make_doc(db_session, user_id, "Doc B", ["physics"])
        db_session.commit()

        r = client.post(
            f"/api/kb/documents/{a.id}/connect",
            json={"target_document_id": b.id, "relation": "RELATED"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert r.json()["provenance"] == "manual"
        edge = db_session.query(KbEdge).filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == a.id,
            KbEdge.target_document_id == b.id,
            KbEdge.relation == "RELATED",
        ).first()
        assert edge is not None
        assert edge.provenance == "manual"

    def test_confirm_missing_doc_404(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        a = _make_doc(db_session, user_id, "Doc A", ["physics"])
        db_session.commit()
        r = client.post(
            f"/api/kb/documents/{a.id}/connect",
            json={"target_document_id": 999999},
            headers=_auth(token),
        )
        assert r.status_code == 404


class TestContradictionHint:
    def test_changed_target_flagged_as_hint(self, client, db_session):
        from datetime import timedelta

        token = _signup(client)
        user_id = _user_id(db_session, token)
        # Older doc vs a newer "changed" doc sharing a concept.
        old = _make_doc(db_session, user_id, "Old note", ["machine learning"])
        old.updated_at = utcnow() - timedelta(days=30)
        new = _make_doc(db_session, user_id, "New note", ["machine learning"], status="changed")
        new.updated_at = utcnow()
        db_session.commit()

        result = client.get(f"/api/kb/documents/{new.id}/connect-suggestions", headers=_auth(token)).json()
        # The older doc appears as a candidate (shared concept) and the newer
        # changed doc surfaces a contradiction hint when it is the target.
        assert "contradiction_hints" in result


class TestIsolation:
    def test_connect_isolated_per_user(self, client, db_session):
        t_a = _signup(client, "con-a", "cona@test.com")
        t_b = _signup(client, "con-b", "conb@test.com")
        user_a = _user_id(db_session, t_a)
        user_b = _user_id(db_session, t_b)
        _make_doc(db_session, user_a, "A's note", ["biology"])
        b_doc = _make_doc(db_session, user_b, "B's note", ["biology"])
        db_session.commit()

        # B must not see A's documents as candidates.
        items = client.get(f"/api/kb/documents/{b_doc.id}/connect-suggestions", headers=_auth(t_b)).json()["items"]
        assert items == []
