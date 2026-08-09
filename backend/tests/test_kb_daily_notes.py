"""Idea 35 — daily-note integration tests.

Date join, auto-tag, today endpoint, per-user isolation.
"""
from __future__ import annotations

from datetime import date

from app.models import DailyScheduleItem, JournalEntry, KbDocument, KbDocumentTag, KbTag
from app.services.kb.daily_notes import tag_daily_note


def _signup(client, uname="dn-user", email="dn@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Dn", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_doc(db, user_id, title, day: date):
    doc = KbDocument(
        user_id=user_id, title=title, doc_type="md",
        doc_date=day, extracted_text=f"# {title}\n\nContent.", char_count=30,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestAutoTag:
    def test_tag_daily_note_creates_rule_tag(self, db_session):
        day = date(2026, 3, 5)
        doc = _make_doc(db_session, 1, "2026-03-05.md", day)
        tag_daily_note(db_session, doc)
        tag = db_session.query(KbTag).filter_by(name="daily/2026-03-05").first()
        assert tag is not None and tag.kind == "rule"
        dt = db_session.query(KbDocumentTag).filter_by(document_id=doc.id).first()
        assert dt is not None and dt.provenance == "rule"

    def test_tag_idempotent(self, db_session):
        day = date(2026, 3, 5)
        doc = _make_doc(db_session, 1, "2026-03-05.md", day)
        assert tag_daily_note(db_session, doc) is True
        assert tag_daily_note(db_session, doc) is False  # already tagged
        assert db_session.query(KbDocumentTag).filter_by(document_id=doc.id).count() == 1

    def test_non_daily_doc_not_tagged(self, db_session):
        doc = KbDocument(user_id=1, title="Regular", doc_type="md",
                         extracted_text="x", char_count=1)
        db_session.add(doc)
        db_session.commit()
        assert tag_daily_note(db_session, doc) is False


class TestDailyNotesEndpoint:
    def test_date_join(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        day = date(2026, 3, 5)
        _make_doc(db_session, user_id, "daily-note", day)
        db_session.add(DailyScheduleItem(
            user_id=user_id, date=day, time_range="09:00-10:00",
            activity="Study", category="Study Time", done=False,
        ))
        db_session.add(JournalEntry(
            user_id=user_id, date=day, content="Great day.", mood="good",
        ))
        db_session.commit()

        r = client.get(
            "/api/kb/daily-notes?date=2026-03-05",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["date"] == "2026-03-05"
        assert len(data["documents"]) == 1
        assert len(data["schedule"]) == 1
        assert len(data["journal"]) == 1

    def test_today_endpoint(self, client, db_session):
        token = _signup(client)
        r = client.get(
            "/api/kb/daily-notes/today",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "documents" in r.json()

    def test_per_user_isolation(self, client, db_session):
        token_a = _signup(client, "dn-a", "dna@test.com")
        token_b = _signup(client, "dn-b", "dnb@test.com")
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token_a)["user_id"]
        day = date(2026, 3, 6)
        _make_doc(db_session, user_id, "secret-note", day)
        r = client.get(
            "/api/kb/daily-notes?date=2026-03-06",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r.status_code == 200
        assert r.json()["documents"] == []
