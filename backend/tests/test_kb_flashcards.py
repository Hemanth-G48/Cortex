"""Idea 34 — flashcard candidate tests.

Candidate generation (mocked), dedupe, approve→deck, reject, fallback.
"""
from __future__ import annotations

from unittest.mock import patch

from app.models import (
    Flashcard,
    FlashcardDeck,
    KbConcept,
    KbEdge,
    KbFlashcardCandidate,
)
from app.services.kb.graph import add_edge


def _signup(client, uname="fc-user", email="fc@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Fc", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _upload(client, token, name="note.md", content=b"# Title\n\n" + b"word " * 200):
    resp = client.post(
        "/api/kb/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (name, content, "test.md")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["document"]["id"]


class TestCandidateGeneration:
    def test_mocked_candidates(self, client, db_session):
        token = _signup(client)
        doc_id = _upload(client, token)
        mock = {
            "cards": [
                {"question": "What is X?", "answer": "X is Y.", "source_chunk_id": 1},
                {"question": "What is Z?", "answer": "Z is W.", "source_chunk_id": 2},
            ]
        }
        with patch("app.services.ai_client.generate_json", return_value=mock):
            r = client.post(
                f"/api/kb/documents/{doc_id}/flashcards",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] == 2
        assert all(c["status"] == "pending" for c in data["candidates"])
        assert db_session.query(KbFlashcardCandidate).count() == 2

    def test_fallback_from_concepts(self, client, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_id = _upload(client, token)

        # Wire concepts → MENTIONS edges so the fallback has material.
        concept = KbConcept(user_id=user_id, canonical_name="photosynthesis",
                            definition="Plants convert light to energy.")
        db_session.add(concept)
        db_session.commit()
        add_edge(db_session, user_id, doc_id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=0.9)
        db_session.commit()

        r = client.post(
            f"/api/kb/documents/{doc_id}/flashcards",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["generated"] >= 1
        assert data["fallback"] is True
        assert "photosynthesis" in data["candidates"][0]["question"]

    def test_dedupe_skips_covered(self, client, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_id = _upload(client, token)

        concept = KbConcept(user_id=user_id, canonical_name="mitochondria",
                            definition="The powerhouse of the cell.")
        db_session.add(concept)
        db_session.commit()
        add_edge(db_session, user_id, doc_id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=0.9)
        db_session.commit()

        first = client.post(
            f"/api/kb/documents/{doc_id}/flashcards",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        second = client.post(
            f"/api/kb/documents/{doc_id}/flashcards",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        assert first["generated"] >= 1
        assert second["generated"] == 0  # all covered
        assert second["skipped_duplicates"] >= 1


class TestReviewQueue:
    def test_approve_creates_deck_and_cards(self, client, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_id = _upload(client, token)
        concept = KbConcept(user_id=user_id, canonical_name="enzyme",
                            definition="A biological catalyst.")
        db_session.add(concept)
        db_session.commit()
        add_edge(db_session, user_id, doc_id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=0.9)
        db_session.commit()

        gen = client.post(
            f"/api/kb/documents/{doc_id}/flashcards",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        candidate_id = gen["candidates"][0]["id"]

        r = client.post(
            "/api/kb/flashcards/review",
            json={"approve": [candidate_id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["approved"] == 1
        deck = db_session.query(FlashcardDeck).filter_by(name="From notes").first()
        assert deck is not None
        assert db_session.query(Flashcard).filter_by(deck_id=deck.id).count() == 1
        cand = db_session.query(KbFlashcardCandidate).get(candidate_id)
        assert cand.status == "approved" and cand.deck_id == deck.id

    def test_reject_marks_candidate(self, client, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_id = _upload(client, token)
        concept = KbConcept(user_id=user_id, canonical_name="ribosome",
                            definition="Builds proteins.")
        db_session.add(concept)
        db_session.commit()
        add_edge(db_session, user_id, doc_id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=0.9)
        db_session.commit()
        gen = client.post(
            f"/api/kb/documents/{doc_id}/flashcards",
            headers={"Authorization": f"Bearer {token}"},
        ).json()
        candidate_id = gen["candidates"][0]["id"]

        r = client.post(
            "/api/kb/flashcards/review",
            json={"reject": [candidate_id]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.json()["rejected"] == 1
        assert db_session.query(KbFlashcardCandidate).get(candidate_id).status == "rejected"

    def test_queue_lists_pending(self, client, db_session, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        doc_id = _upload(client, token)
        r = client.get(
            "/api/kb/flashcards/candidates?status=pending",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_review_requires_ids(self, client):
        token = _signup(client)
        r = client.post(
            "/api/kb/flashcards/review",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 400
