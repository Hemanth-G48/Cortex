"""Idea 39 — note-quality tests.

Component math, weight config, caching/recompute, suggestion lifecycle, and
the health avg-quality signal.
"""
from __future__ import annotations

import json

from app.config import settings
from app.models import KbDocument, KbQualitySuggestion
from app.services.kb import health, quality


def _signup(client, uname="q-user", email="q@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Q", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_doc(db, user_id, char_count=1000, outline=None):
    doc = KbDocument(
        user_id=user_id, title="Doc", doc_type="md",
        char_count=char_count,
        outline_json=json.dumps(outline or [{"level": 1, "text": "H1", "char_start": 0}]),
        extracted_text="x" * char_count,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestQualityService:
    def test_component_math(self, db_session):
        doc = _make_doc(db_session, 1, char_count=3000)
        result = quality.compute_quality(db_session, doc)
        assert 0 <= result["score"] <= 100
        assert set(result["components"]) == set(quality.COMPONENTS)
        # Long doc with headings → length + headings components > 0.
        assert result["components"]["length"] > 0.5
        assert result["components"]["headings"] > 0

    def test_weight_config_normalizes(self):
        weights = settings.kb_quality_weights
        assert abs(sum(weights.values()) - 1.0) < 0.01
        assert set(weights) == set(quality.COMPONENTS)

    def test_caching_and_recompute(self, db_session):
        doc = _make_doc(db_session, 1)
        result = quality.get_or_compute(db_session, doc)
        assert doc.quality_score == result["score"]
        cached = quality.get_or_compute(db_session, doc)
        assert cached["score"] == result["score"]
        # Force recompute still returns a valid result.
        forced = quality.get_or_compute(db_session, doc, force=True)
        assert forced["score"] == result["score"]

    def test_suggestion_lifecycle(self, db_session, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        doc = _make_doc(db_session, 1, char_count=100)  # short → expand suggestion
        items = quality.generate_suggestions(db_session, doc)
        assert items, "heuristic suggestions should be generated"
        sid = items[0]["id"]
        row = db_session.query(KbQualitySuggestion).get(sid)
        assert row.status == "pending"
        assert quality.dismiss_suggestion(db_session, 1, sid) is True
        assert db_session.query(KbQualitySuggestion).get(sid).status == "dismissed"


class TestQualityEndpoints:
    def test_document_quality_endpoint(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc = _make_doc(db_session, user_id)
        r = client.get(
            f"/api/kb/documents/{doc.id}/quality",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert "score" in data and "components" in data
        assert "suggestions" in data

    def test_quality_list_sorted(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        _make_doc(db_session, user_id, char_count=100)   # low score
        _make_doc(db_session, user_id, char_count=5000)  # higher score
        r = client.get(
            "/api/kb/quality?sort=score",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) == 2
        assert items[0]["score"] <= items[1]["score"]

    def test_generate_and_dismiss_suggestions(self, client, db_session, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc = _make_doc(db_session, user_id, char_count=100)
        r = client.post(
            f"/api/kb/documents/{doc.id}/quality/suggestions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        assert len(items) >= 1
        sid = items[0]["id"]
        r2 = client.post(
            f"/api/kb/quality/suggestions/{sid}/dismiss",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200
        assert db_session.query(KbQualitySuggestion).get(sid).status == "dismissed"


class TestHealthQualitySignal:
    def test_health_includes_avg_quality(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        _make_doc(db_session, user_id)
        r = client.get(
            "/api/kb/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        signal = r.json()["signals"].get("avg_quality")
        assert signal is not None
        assert "average" in signal

    def test_average_quality_math(self, db_session):
        # No scored docs → 100.0 (no quality problems).
        assert health.average_quality(db_session, 1) == 100.0
