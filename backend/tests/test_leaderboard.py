"""Leaderboard tests (adapted from Shiori-v1 / QuestLog)."""
from __future__ import annotations

from app.models import Character, User
from app.services.security import decode_bearer_token


def _signup(client, uname, email):
    resp = client.post(
        "/api/auth/signup",
        json={"name": uname.title(), "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_leaderboard_requires_auth(client):
    assert client.get("/api/leaderboard").status_code == 401


def test_leaderboard_ranks_by_xp(client, db_session):
    token_low = _signup(client, "lowxp", "low@test.com")
    token_high = _signup(client, "highxp", "high@test.com")

    low_id = decode_bearer_token(token_low)["user_id"]
    high_id = decode_bearer_token(token_high)["user_id"]

    # Zero out seeded demo users so only our two users hold XP.
    db_session.query(User).update({User.total_xp: 0})
    low = db_session.query(User).filter(User.id == low_id).first()
    high = db_session.query(User).filter(User.id == high_id).first()
    low.total_xp = 100
    high.total_xp = 500
    db_session.add(Character(user_id=high_id, name="Hero", class_name="Knight", level=3, xp=500))
    db_session.commit()

    r = client.get("/api/leaderboard?limit=10", headers=_auth(token_low))
    assert r.status_code == 200, r.text
    data = r.json()
    items = data["items"]
    assert len(items) == 2
    # High XP ranks first.
    assert items[0]["user_id"] == high_id
    assert items[0]["rank"] == 1
    assert items[0]["total_xp"] == 500
    assert items[0]["level"] == 3
    assert items[0]["avatar_class"] == "Knight"
    assert items[1]["me"] is True  # caller flagged
    # Caller metadata: rank 2 of 2 → 50th percentile.
    me = data["me"]
    assert me["rank"] == 2
    assert me["total_users"] == 2
    assert me["percentile"] == 50.0
