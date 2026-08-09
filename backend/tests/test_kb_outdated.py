"""Idea 78 — outdated-note detection tests.

Covers the three detectors feeding the review queue: stale (untouched past
KB_STALE_DAYS), material_changed (referenced doc re-indexed later), and
contradiction (LLM verdict over a shared-concept pair, with deterministic
keyword fallback when AI is off). Also covers the scan/review/resolve
lifecycle and per-user isolation.
"""
from __future__ import annotations

import pytest
from datetime import timedelta

from app.models import KbConcept, KbDocument, KbEdge, OutdatedNote
from app.services.kb import utcnow
from app.services.kb.graph import add_edge


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="out-user", email="out@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Out", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _user_id(db_session, token):
    from app.services.security import decode_bearer_token

    return decode_bearer_token(token)["user_id"]


def _make_doc(db, user_id, title, text="content", status="unchanged", updated_at=None):
    doc = KbDocument(user_id=user_id, title=title, doc_type="md", status=status,
                     extracted_text=text, content_hash=f"hash-{title}", char_count=len(text))
    if updated_at is not None:
        doc.updated_at = updated_at
    db.add(doc)
    db.flush()
    return doc


def _with_concept(db, user_id, doc, cname):
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
    return concept


class TestStale:
    def test_old_document_flagged_stale(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.KB_STALE_DAYS", 30)
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Old note", updated_at=utcnow() - timedelta(days=60))
        _make_doc(db_session, user_id, "Fresh note", updated_at=utcnow())
        db_session.commit()

        r = client.post("/api/kb/outdated/scan", headers=_auth(token))
        assert r.status_code == 200, r.text
        stale = [i for i in r.json()["items"] if i["reason"] == "stale"]
        assert len(stale) == 1
        assert stale[0]["evidence"]["stale_days"] >= 30

    def test_scan_is_idempotent(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.KB_STALE_DAYS", 30)
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Old note", updated_at=utcnow() - timedelta(days=60))
        db_session.commit()

        first = client.post("/api/kb/outdated/scan", headers=_auth(token)).json()
        second = client.post("/api/kb/outdated/scan", headers=_auth(token)).json()
        assert second["created"] == 0  # no duplicates


class TestMaterialChanged:
    def test_referenced_doc_reindexed_flags_note(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        note = _make_doc(db_session, user_id, "My note on topic",
                         updated_at=utcnow() - timedelta(days=5))
        material = _make_doc(db_session, user_id, "Source material", status="changed",
                             updated_at=utcnow())
        # The note references the material.
        add_edge(db_session, user_id, note.id, target_document_id=material.id,
                 relation="WIKILINK", provenance="ai")
        db_session.commit()

        r = client.post("/api/kb/outdated/scan", headers=_auth(token))
        items = r.json()["items"]
        changed = [i for i in items if i["reason"] == "material_changed"]
        assert changed
        assert changed[0]["document_id"] == note.id
        assert changed[0]["evidence"]["referenced_document_id"] == material.id


class TestContradiction:
    def test_keyword_fallback_flags_contradiction(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        old = _make_doc(db_session, user_id, "Old", "Earth is flat.", updated_at=utcnow() - timedelta(days=10))
        new = _make_doc(db_session, user_id, "New", "The older note contradicts itself; Earth is round.")
        _with_concept(db_session, user_id, old, "earth")
        _with_concept(db_session, user_id, new, "earth")
        db_session.commit()

        r = client.post("/api/kb/outdated/scan", headers=_auth(token))
        items = r.json()["items"]
        contrad = [i for i in items if i["reason"] == "contradiction"]
        assert contrad
        assert contrad[0]["document_id"] == new.id  # the newer note is flagged

    def test_supporting_text_not_flagged(self, client, db_session):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        old = _make_doc(db_session, user_id, "Old", "Earth is round.", updated_at=utcnow() - timedelta(days=10))
        new = _make_doc(db_session, user_id, "New", "This note supports the earlier claim; Earth is round.")
        _with_concept(db_session, user_id, old, "earth")
        _with_concept(db_session, user_id, new, "earth")
        db_session.commit()

        r = client.post("/api/kb/outdated/scan", headers=_auth(token))
        assert not any(i["reason"] == "contradiction" for i in r.json()["items"])

    def test_mock_llm_verdict(self, client, db_session, monkeypatch):
        token = _signup(client)
        user_id = _user_id(db_session, token)
        old = _make_doc(db_session, user_id, "Old", "Earth is round.", updated_at=utcnow() - timedelta(days=10))
        new = _make_doc(db_session, user_id, "New", "Earth is actually flat.")
        _with_concept(db_session, user_id, old, "earth")
        _with_concept(db_session, user_id, new, "earth")
        db_session.commit()

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)

        def fake_generate_json(prompt, **kwargs):
            return {"verdict": "contradicts", "reason": "The newer note denies the older one."}

        monkeypatch.setattr("app.services.ai_client.generate_json", fake_generate_json)

        r = client.post("/api/kb/outdated/scan", headers=_auth(token))
        contrad = [i for i in r.json()["items"] if i["reason"] == "contradiction"]
        assert contrad
        assert contrad[0]["evidence"]["verdict"] == "contradicts"


class TestReviewLifecycle:
    def test_review_queue_and_resolve(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.KB_STALE_DAYS", 30)
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Old note", updated_at=utcnow() - timedelta(days=60))
        db_session.commit()
        client.post("/api/kb/outdated/scan", headers=_auth(token))

        q = client.get("/api/kb/outdated/review", headers=_auth(token))
        assert q.status_code == 200, q.text
        items = q.json()["items"]
        assert items
        note_id = items[0]["id"]
        assert items[0]["status"] == "open"

        r = client.post(f"/api/kb/outdated/{note_id}/resolve", json={"action": "dismissed"}, headers=_auth(token))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "dismissed"

        # No longer in the open queue.
        q2 = client.get("/api/kb/outdated/review", headers=_auth(token)).json()["items"]
        assert not any(i["id"] == note_id for i in q2)

    def test_resolve_bad_action_400(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.KB_STALE_DAYS", 30)
        token = _signup(client)
        user_id = _user_id(db_session, token)
        _make_doc(db_session, user_id, "Old note", updated_at=utcnow() - timedelta(days=60))
        db_session.commit()
        client.post("/api/kb/outdated/scan", headers=_auth(token))
        note_id = client.get("/api/kb/outdated/review", headers=_auth(token)).json()["items"][0]["id"]

        r = client.post(f"/api/kb/outdated/{note_id}/resolve", json={"action": "banana"}, headers=_auth(token))
        assert r.status_code == 400


class TestIsolation:
    def test_outdated_notes_are_per_user(self, client, db_session, monkeypatch):
        monkeypatch.setattr("app.config.settings.KB_STALE_DAYS", 30)
        t_a = _signup(client, "out-a", "outa@test.com")
        t_b = _signup(client, "out-b", "outb@test.com")
        user_a = _user_id(db_session, t_a)
        _make_doc(db_session, user_a, "A's old note", updated_at=utcnow() - timedelta(days=60))
        db_session.commit()

        client.post("/api/kb/outdated/scan", headers=_auth(t_a))
        assert client.get("/api/kb/outdated/review", headers=_auth(t_a)).json()["items"]
        assert client.get("/api/kb/outdated/review", headers=_auth(t_b)).json()["items"] == []
