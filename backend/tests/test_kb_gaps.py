"""Idea 28 — missing knowledge detection tests.

Uses the Phase-5 stub topic→coverage source; verifies threshold math, the gap
list shape, and per-user isolation.
"""
from __future__ import annotations

from app.services.kb import health as h


def _signup(client, uname="gap-user", email="gap@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Gap", "username": uname, "email": email,
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


class TestGapsEndpoint:
    def test_gaps_returns_shape(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Gap content."])
        r = client.get("/api/kb/gaps",
                       headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data
        assert "gaps" in data
        assert "threshold" in data

    def test_gaps_per_user_isolation(self, client, tmp_path):
        t1 = _signup(client, "gap-u1", "gap1@test.com")
        t2 = _signup(client, "gap-u2", "gap2@test.com")
        _scan(client, t1, tmp_path, ["Content for gap detection."])
        r2 = client.get("/api/kb/gaps",
                        headers={"Authorization": f"Bearer {t2}"})
        # user2 has no docs → coverage 0 → "untagged" flagged as a gap.
        assert any(g["is_gap"] for g in r2.json()["items"])


class TestCoverageStub:
    def test_zero_docs_is_full_gap(self, db_session):
        gaps = h.coverage_gaps(db_session, 1)
        assert gaps[0]["topic"] == "untagged"
        assert gaps[0]["coverage"] == 0.0

    def test_threshold_math(self, db_session):
        from app.models import KbDocument, KbDocumentTag, KbTag
        d1 = KbDocument(user_id=1, path_rel="a.md", title="a", doc_type="md",
                        status="new")
        d2 = KbDocument(user_id=1, path_rel="b.md", title="b", doc_type="md",
                        status="new")
        db_session.add_all([d1, d2])
        db_session.flush()
        tag = KbTag(user_id=1, name="math")
        db_session.add(tag)
        db_session.flush()
        # Tag only d1 → coverage 0.5 (> threshold 0.2 → not a gap).
        db_session.add(KbDocumentTag(user_id=1, document_id=d1.id, tag_id=tag.id))
        db_session.commit()
        gaps = h.coverage_gaps(db_session, 1)
        assert gaps[0]["coverage"] == 0.5
        assert gaps[0]["coverage"] >= 0.2
