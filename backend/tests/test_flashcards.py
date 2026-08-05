"""Tests for the Flashcards feature (Groups 4-5)."""
from __future__ import annotations

from app.services import ai_client


def test_seeded_decks_exist(client):
    resp = client.get("/api/flashcard-decks")
    assert resp.status_code == 200
    decks = resp.json()
    assert len(decks) >= 2
    for d in decks:
        assert d["name"]
        assert "card_count" in d
    assert decks[0]["card_count"] >= 4


def test_deck_crud_and_cards(client):
    # Create deck
    resp = client.post("/api/flashcard-decks", json={"name": "Biology Ch 3"})
    assert resp.status_code == 200
    deck = resp.json()
    assert deck["id"]
    assert deck["cards"] == []

    # Add cards
    resp = client.post(f"/api/flashcard-decks/{deck['id']}/cards", json={
        "front": "What is ATP?", "back": "Adenosine triphosphate — the energy currency of the cell.", "difficulty": "easy",
    })
    assert resp.status_code == 200
    card = resp.json()
    assert card["streak"] == 0

    resp = client.post(f"/api/flashcard-decks/{deck['id']}/cards", json={
        "front": "What is mitosis?", "back": "Cell division producing two identical daughter cells.", "difficulty": "basic",
    })
    assert resp.status_code == 200

    # Update a card (streak/difficulty)
    resp = client.put(f"/api/flashcard-decks/{deck['id']}/cards/{card['id']}", json={"streak": 2, "difficulty": "medium"})
    assert resp.json()["streak"] == 2
    assert resp.json()["difficulty"] == "medium"

    # List cards + deck detail
    cards = client.get(f"/api/flashcard-decks/{deck['id']}/cards").json()
    assert len(cards) == 2

    # Delete a card
    resp = client.delete(f"/api/flashcard-decks/{deck['id']}/cards/{card['id']}")
    assert resp.status_code == 200
    assert len(client.get(f"/api/flashcard-decks/{deck['id']}/cards").json()) == 1

    # Delete the deck (cascade)
    resp = client.delete(f"/api/flashcard-decks/{deck['id']}")
    assert resp.status_code == 200
    assert client.get(f"/api/flashcard-decks/{deck['id']}").status_code == 404


def test_card_in_wrong_deck_404(client):
    decks = client.get("/api/flashcard-decks").json()
    assert len(decks) >= 2
    resp = client.put(f"/api/flashcard-decks/{decks[0]['id']}/cards/99999", json={"streak": 1})
    assert resp.status_code == 404


def test_ai_flashcards_endpoint_fallback(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post("/api/ai/flashcards", json={"topic": "Photosynthesis", "difficulty": "medium"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_used"] is False
    assert len(data["cards"]) >= 2
    for c in data["cards"]:
        assert c["front"] and c["back"]


def test_ai_grade_answer_exact_and_ai(client, monkeypatch):
    monkeypatch.setattr(ai_client, "ai_available", lambda: False)
    resp = client.post(
        "/api/ai/grade-answer",
        json={"question": "2+2?", "expected": "4", "answer": "4"},
    )
    assert resp.json()["correct"] is True

    resp = client.post(
        "/api/ai/grade-answer",
        json={"question": "2+2?", "expected": "4", "answer": "five"},
    )
    assert resp.json()["correct"] is False
