"""Leaderboard tests (single-owner view)."""
from __future__ import annotations

from app.models import Character


def test_leaderboard_works_without_auth(client):
    """No login required — the board resolves to the single owner."""
    assert client.get("/api/leaderboard").status_code == 200


def test_leaderboard_shows_single_owner(client, db_session):
    # The single owner is the seeded first user — no signup needed.
    from app.models import User

    db_session.query(Character).delete()
    owner = db_session.query(User).order_by(User.id).first()
    owner.total_xp = 500
    db_session.add(Character(user_id=owner.id, name="Hero", class_name="Knight", level=3, xp=500))
    db_session.commit()

    r = client.get("/api/leaderboard?limit=10")
    assert r.status_code == 200, r.text
    data = r.json()
    items = data["items"]
    assert len(items) == 1
    assert items[0]["user_id"] == owner.id
    assert items[0]["rank"] == 1
    assert items[0]["total_xp"] == 500
    assert items[0]["level"] == 3
    assert items[0]["avatar_class"] == "Knight"
    assert items[0]["me"] is True

    me = data["me"]
    assert me["user_id"] == owner.id
    assert me["rank"] == 1
    assert me["percentile"] == 100.0
