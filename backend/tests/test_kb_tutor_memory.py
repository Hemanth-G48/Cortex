"""Idea 74 — tutor memory integration tests.

Covers the Phase 8 seam inside the Phase 7 tutor: known-context rendering
(strengths/weaknesses), reference phrasing ("as you saw in your notes on X")
only for concepts in user_memory, the Rule A post-check that strips
references to anything else, memory bumps on tutor turns, and per-user
isolation.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, db_session=None, uname="tmem-user", email="tmem@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Tmem", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["token"]
    if db_session is not None:
        db_session.commit()
    return token


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _scan_md(client, token, root, texts):
    for i, text in enumerate(texts):
        (root / f"doc{i}.md").write_text(text)
    resp = client.post(
        "/api/kb/sources",
        json={"name": "Vault", "source_type": "vault_folder", "root_path": str(root)},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    src = resp.json()
    scan = client.post(f"/api/kb/sources/{src['id']}/scan", headers=_auth(token))
    assert scan.status_code == 200, scan.text
    return src


class TestRuleASanitize:
    def test_strips_unknown_references(self):
        from app.services.kb.tutor import _rule_a_sanitize

        answer = "as you saw in your notes on quantum chromodynamics, quarks bind."
        out = _rule_a_sanitize(answer, {"linear regression"})
        assert "quantum chromodynamics" not in out
        assert "as you saw in your notes" in out

    def test_keeps_known_references(self):
        from app.services.kb.tutor import _rule_a_sanitize

        answer = "as you saw in your notes on Linear Regression, we fit a line."
        out = _rule_a_sanitize(answer, {"linear regression"})
        assert "Linear Regression" in out

    def test_empty_memory_strips_all(self):
        from app.services.kb.tutor import _rule_a_sanitize

        answer = "as you saw in your notes on linear regression, we fit a line."
        out = _rule_a_sanitize(answer, set())
        assert "linear regression" not in out


class TestKnownContext:
    def test_known_context_from_memory(self, db_session, monkeypatch):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.kb.tutor import _known_context, _user_memory

        monkeypatch.setattr("app.config.settings.KB_MEMORY_ANCHOR_MIN", 0.4)
        c1 = KbConcept(user_id=1, canonical_name="linear regression")
        c2 = KbConcept(user_id=1, canonical_name="probability")
        db_session.add_all([c1, c2])
        db_session.flush()
        db_session.add_all([
            UserMemory(user_id=1, concept_id=c1.id, strength=0.8, exposure_count=4, last_seen=utcnow()),
            UserMemory(user_id=1, concept_id=c2.id, strength=0.2, exposure_count=1, last_seen=utcnow()),
        ])
        db_session.commit()

        ctx = _known_context(db_session, 1)
        assert {c["concept"] for c in ctx} == {"linear regression", "probability"}

        mem = _user_memory(db_session, 1)
        assert mem["strengths"] == ["linear regression"]
        assert mem["weaknesses"] == ["probability"]

    def test_empty_memory_returns_none(self, db_session):
        from app.services.kb.tutor import _user_memory

        assert _user_memory(db_session, 1) is None


class TestTutorReferencesKnownOnly:
    def test_tutor_answer_keeps_known_reference(self, client, db_session, tmp_path, monkeypatch):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        token = _signup(client, db_session)
        user_id = decode_bearer_token(token)["user_id"]
        _scan_md(client, token, tmp_path, ["Linear regression predicts a continuous target from features."])

        # User has genuinely studied "linear regression" — memory row exists.
        concept = KbConcept(user_id=user_id, canonical_name="linear regression")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.9,
                                  exposure_count=5, last_seen=utcnow()))
        db_session.commit()

        def fake_generate(prompt, **kwargs):
            return "As you saw in your notes on linear regression, we fit a line. [source: doc0.md]"

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate", fake_generate)

        r = client.post(
            "/api/kb/tutor/chat",
            json={"message": "What is linear regression?"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        assert "as you saw in your notes on linear regression" in r.json()["answer"].lower()

    def test_tutor_strips_unknown_reference(self, client, db_session, tmp_path, monkeypatch):
        from app.services.security import decode_bearer_token

        token = _signup(client, db_session)
        _scan_md(client, token, tmp_path, ["Linear regression predicts a continuous target from features."])

        def fake_generate(prompt, **kwargs):
            return "As you saw in your notes on quantum chromodynamics, quarks bind. [source: doc0.md]"

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr("app.services.ai_client.generate", fake_generate)

        r = client.post(
            "/api/kb/tutor/chat",
            json={"message": "What is linear regression?"},
            headers=_auth(token),
        )
        answer = r.json()["answer"]
        assert "quantum chromodynamics" not in answer


class TestMemoryBump:
    def test_tutor_turn_bumps_concepts(self, client, db_session, tmp_path):
        from app.models import KbConcept, KbDocument, KbEdge, UserMemory
        from app.services.security import decode_bearer_token

        token = _signup(client, db_session)
        user_id = decode_bearer_token(token)["user_id"]
        _scan_md(client, token, tmp_path, ["Gradient descent minimizes the loss."])

        # The doc MENTIONS a concept — a tutor turn about it should bump it.
        concept = KbConcept(user_id=user_id, canonical_name="gradient descent")
        db_session.add(concept)
        db_session.flush()
        doc = db_session.query(KbDocument).first()
        db_session.add(KbEdge(
            user_id=user_id, source_document_id=doc.id, target_type="concept",
            target_concept_id=concept.id, relation="MENTIONS", weight=1.0,
        ))
        db_session.commit()

        r = client.post(
            "/api/kb/tutor/chat",
            json={"message": "gradient descent minimizes the loss"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text

        row = db_session.query(UserMemory).filter(
            UserMemory.user_id == user_id, UserMemory.concept_id == concept.id
        ).first()
        assert row is not None
        assert row.strength > 0
        assert row.source == "tutor"


class TestRecallLogging:
    def test_recall_events_logged(self, client, db_session, tmp_path, monkeypatch):
        from app.models import KbConcept, LearningEvent, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        token = _signup(client, db_session)
        user_id = decode_bearer_token(token)["user_id"]
        _scan_md(client, token, tmp_path, ["Linear regression predicts a continuous target from features."])

        concept = KbConcept(user_id=user_id, canonical_name="linear regression")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_id, concept_id=concept.id, strength=0.9,
                                  exposure_count=5, last_seen=utcnow()))
        db_session.commit()

        monkeypatch.setattr("app.services.ai_client.ai_available", lambda: True)
        monkeypatch.setattr(
            "app.services.ai_client.generate",
            lambda prompt, **kwargs: "As you saw in your notes on linear regression, we fit a line. [source: doc0.md]",
        )

        client.post("/api/kb/tutor/chat", json={"message": "What is linear regression?"}, headers=_auth(token))
        recalls = db_session.query(LearningEvent).filter(
            LearningEvent.user_id == user_id, LearningEvent.event_type == "recall"
        ).all()
        assert len(recalls) >= 1


class TestIsolation:
    def test_memory_is_per_user(self, client, db_session, tmp_path):
        from app.models import KbConcept, UserMemory
        from app.services.kb import utcnow
        from app.services.security import decode_bearer_token

        t_a = _signup(client, db_session, "tmem-a", "tmea@test.com")
        user_a = decode_bearer_token(t_a)["user_id"]
        concept = KbConcept(user_id=user_a, canonical_name="probability")
        db_session.add(concept)
        db_session.flush()
        db_session.add(UserMemory(user_id=user_a, concept_id=concept.id, strength=0.9,
                                  exposure_count=3, last_seen=utcnow()))
        db_session.commit()

        t_b = _signup(client, db_session, "tmem-b", "tmeb@test.com")
        _scan_md(client, t_b, tmp_path, ["Probability content here."])
        r = client.post("/api/kb/tutor/chat", json={"message": "probability"}, headers=_auth(t_b))
        # User B's memory is empty → no known context → references stripped.
        assert "as you saw in your notes on probability" not in r.json()["answer"]
