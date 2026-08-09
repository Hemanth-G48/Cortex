"""Idea 27 — knowledge health analysis tests.

Each detector is exercised with crafted fixtures; the score math is checked;
per-user isolation is verified.
"""
from __future__ import annotations

from app.models import KbDocument, KbEdge, KbSource
from app.services.kb import health as h


def _signup(client, uname="hl-user", email="hl@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Hl", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _scan(client, token, root, texts):
    for i, text in enumerate(texts):
        (root / f"d{i}.md").write_text(text)
    r = client.post(
        "/api/kb/sources",
        json={"name": "V", "root_path": str(root)},
        headers={"Authorization": f"Bearer {token}"},
    )
    src = r.json()
    client.post(f"/api/kb/sources/{src['id']}/scan",
                headers={"Authorization": f"Bearer {token}"})


def _doc(db, user_id, source_id=None, status="new", path="x.md"):
    d = KbDocument(
        user_id=user_id,
        source_id=source_id,
        path_rel=path,
        title=path,
        doc_type="md",
        status=status,
    )
    db.add(d)
    db.flush()
    return d


class TestHealthEndpoint:
    def test_health_returns_shape(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Some content."])
        r = client.get("/api/kb/health",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "score" in data
        assert "signals" in data
        assert "orphans" in data["signals"]

    def test_health_per_user_isolation(self, client, tmp_path, db_session):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Isolated content."])
        # A second user with no docs → score is 100 (no documents = no problems).
        t2 = _signup(client, "hl-u2", "hl2@test.com")
        r2 = client.get("/api/kb/health",
                        headers={"Authorization": f"Bearer {t2}"})
        assert r2.json()["score"] == 100.0


class TestDetectors:
    def test_orphan_detection(self, db_session):
        d = _doc(db_session, 1, status="unchanged")
        db_session.commit()
        assert d.id in h.detect_orphans(db_session, 1)

    def test_orphan_excluded_when_linked(self, db_session):
        a = _doc(db_session, 1, status="unchanged", path="a.md")
        b = _doc(db_session, 1, status="unchanged", path="b.md")
        db_session.add(KbEdge(
            user_id=1, source_document_id=a.id, target_document_id=b.id,
            relation="WIKILINK",
        ))
        db_session.commit()
        orphans = h.detect_orphans(db_session, 1)
        assert a.id not in orphans

    def test_dead_link_detection(self, db_session):
        a = _doc(db_session, 1, status="unchanged", path="a.md")
        db_session.flush()
        # Edge pointing at a document that doesn't exist.
        db_session.add(KbEdge(
            user_id=1, source_document_id=a.id, target_document_id=99999,
            relation="WIKILINK",
        ))
        db_session.commit()
        dead = h.detect_dead_links(db_session, 1)
        assert len(dead) == 1
        assert dead[0]["target_document_id"] == 99999

    def test_stale_note_detection(self, db_session):
        from datetime import datetime, timedelta, timezone
        d = _doc(db_session, 1, status="unchanged", path="old.md")
        d.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=500)
        db_session.commit()
        stale = h.detect_stale_notes(db_session, 1, stale_days=90)
        assert d.id in stale

    def test_unindexed_detection(self, db_session):
        d = _doc(db_session, 1, status="unchanged", path="un.md")
        db_session.commit()
        issues = h.detect_unindexed_files(db_session, 1)
        assert any(i["document_id"] == d.id for i in issues)
        assert "no_chunks" in issues[0]["missing"]

    def test_score_math(self, db_session):
        # Two docs, both orphaned + unindexed → score well below 100.
        _doc(db_session, 1, status="unchanged", path="a.md")
        _doc(db_session, 1, status="unchanged", path="b.md")
        db_session.commit()
        result = h.compute_health(db_session, 1)
        assert 0 <= result["score"] <= 100
        assert result["document_count"] == 2
        # Orphans + unindexed both fire → score must be < 100.
        assert result["score"] < 100.0
