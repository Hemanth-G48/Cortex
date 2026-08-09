"""Idea 69 — knowledge capture & revision XP tests.

Covers the once-per-trigger XP grant guard (mirroring the once-per-quiz rule),
the zero-defaults `KB_XP_REWARDS` config (disabled by default), wallet credit
to User.total_xp + Character.xp, and unknown-kind safety.
"""
from __future__ import annotations

import pytest

from app.models import Character, User
from app.services.kb.capture_xp import award_capture_xp


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="xp-user", email="xp@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Xp", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _user(db_session, token):
    from app.services.security import decode_bearer_token

    user_id = decode_bearer_token(token)["user_id"]
    return db_session.query(User).get(user_id)


class TestDisabledByDefault:
    def test_zero_rewards_grant_nothing(self, client, db_session):
        token = _signup(client)
        user = _user(db_session, token)
        # Default config: KB_XP_REWARDS all zero.
        assert award_capture_xp(db_session, user, "revision", "revision:1") == 0
        assert award_capture_xp(db_session, user, "daily_note", "doc:5") == 0
        db_session.commit()
        assert user.total_xp == 0

    def test_no_grant_rows_when_disabled(self, client, db_session):
        from app.models import CaptureXpGrant

        token = _signup(client)
        user = _user(db_session, token)
        award_capture_xp(db_session, user, "revision", "revision:1")
        db_session.commit()
        rows = db_session.query(CaptureXpGrant).filter(CaptureXpGrant.user_id == user.id).all()
        assert rows == []


class TestEnabled:
    def _enable(self, monkeypatch):
        monkeypatch.setattr(
            "app.config.settings.KB_XP_REWARDS",
            {"revision": 5, "daily_note": 3, "dump_filed": 2},
        )

    def test_grants_and_credits_wallet(self, client, db_session, monkeypatch):
        self._enable(monkeypatch)
        token = _signup(client)
        user = _user(db_session, token)
        # Ensure a character exists (seeded).
        char = db_session.query(Character).filter(Character.user_id == user.id).first()
        before_user = user.total_xp or 0
        before_char = char.xp if char else 0

        granted = award_capture_xp(db_session, user, "revision", "revision:1")
        db_session.commit()
        assert granted == 5
        assert (user.total_xp or 0) == before_user + 5
        if char:
            assert (char.xp or 0) == before_char + 5

    def test_no_double_count_same_trigger(self, client, db_session, monkeypatch):
        self._enable(monkeypatch)
        token = _signup(client)
        user = _user(db_session, token)
        assert award_capture_xp(db_session, user, "revision", "revision:1") == 5
        db_session.commit()
        assert award_capture_xp(db_session, user, "revision", "revision:1") == 0
        db_session.commit()
        assert user.total_xp == 5

    def test_distinct_triggers_both_grant(self, client, db_session, monkeypatch):
        self._enable(monkeypatch)
        token = _signup(client)
        user = _user(db_session, token)
        award_capture_xp(db_session, user, "revision", "revision:1")
        award_capture_xp(db_session, user, "revision", "revision:2")
        db_session.commit()
        assert user.total_xp == 10

    def test_distinct_kinds_grant_independently(self, client, db_session, monkeypatch):
        self._enable(monkeypatch)
        token = _signup(client)
        user = _user(db_session, token)
        award_capture_xp(db_session, user, "revision", "revision:1")
        award_capture_xp(db_session, user, "daily_note", "doc:5")
        db_session.commit()
        assert user.total_xp == 8

    def test_unknown_kind_returns_zero(self, client, db_session, monkeypatch):
        self._enable(monkeypatch)
        token = _signup(client)
        user = _user(db_session, token)
        assert award_capture_xp(db_session, user, "bogus", "x:1") == 0

    def test_grants_are_per_user(self, client, db_session, monkeypatch):
        self._enable(monkeypatch)
        t_a = _signup(client, "xp-a", "xpa@test.com")
        t_b = _signup(client, "xp-b", "xpb@test.com")
        user_a = _user(db_session, t_a)
        user_b = _user(db_session, t_b)
        award_capture_xp(db_session, user_a, "revision", "revision:1")
        db_session.commit()
        # B's identical trigger still grants for B.
        assert award_capture_xp(db_session, user_b, "revision", "revision:1") == 5
        db_session.commit()
        assert user_a.total_xp == 5
        assert user_b.total_xp == 5
