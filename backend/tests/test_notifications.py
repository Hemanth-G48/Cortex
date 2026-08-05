"""Tests for the notifications API endpoints."""

import pytest
from app.models import Notification, User
from app.services.security import create_bearer_token


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    return resp.json()["token"]


def _make_token_for_user(client, name, username, email, password):
    resp = client.post("/api/auth/signup", json={
        "name": name,
        "username": username,
        "email": email,
        "password": password,
    })
    return resp.json()["token"]


def test_list_returns_user_notifications_newest_first(client, db_session):
    user = db_session.query(User).first()
    db_session.add(Notification(user_id=user.id, title="Old", kind="broadcast", read=False))
    db_session.add(Notification(user_id=user.id, title="New", kind="broadcast", read=False))
    db_session.commit()

    token = _get_token(client)
    resp = client.get("/api/notifications", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2
    assert data[0]["title"] == "New"
    assert data[1]["title"] == "Old"


def test_unread_count_reflects_read_unread(client, db_session):
    user = db_session.query(User).first()
    db_session.add(Notification(user_id=user.id, title="Unread 1", kind="broadcast", read=False))
    db_session.add(Notification(user_id=user.id, title="Unread 2", kind="broadcast", read=False))
    db_session.add(Notification(user_id=user.id, title="Read 1", kind="broadcast", read=True))
    db_session.commit()

    token = _get_token(client)
    resp = client.get("/api/notifications/unread-count", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert resp.json()["unread"] == 2


def test_mark_read_flips_single_notification(client, db_session):
    user = db_session.query(User).first()
    n = Notification(user_id=user.id, title="To mark", kind="broadcast", read=False)
    db_session.add(n)
    db_session.commit()

    token = _get_token(client)
    resp = client.post(f"/api/notifications/{n.id}/read", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert resp.json()["read"] is True

    # Verify in DB
    updated = db_session.query(Notification).filter(Notification.id == n.id).first()
    assert updated.read is True


def test_mark_all_read_zeroes_unread_count(client, db_session):
    user = db_session.query(User).first()
    db_session.add(Notification(user_id=user.id, title="Unread A", kind="broadcast", read=False))
    db_session.add(Notification(user_id=user.id, title="Unread B", kind="broadcast", read=False))
    db_session.commit()

    token = _get_token(client)
    resp = client.post("/api/notifications/mark-all-read", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    count_resp = client.get("/api/notifications/unread-count", headers={
        "Authorization": f"Bearer {token}",
    })
    assert count_resp.json()["unread"] == 0


def test_ownership_second_user_cannot_access_first_users_notification(client, db_session):
    user1 = db_session.query(User).first()
    n = Notification(user_id=user1.id, title="Private", kind="broadcast", read=False)
    db_session.add(n)
    db_session.commit()

    token2 = _make_token_for_user(client, "Other User", "otheruser", "other@user.com", "secret123")

    # Second user's list should not include user1's notification
    resp = client.get("/api/notifications", headers={
        "Authorization": f"Bearer {token2}",
    })
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()]
    assert "Private" not in titles

    # Second user gets 404 trying to read user1's notification
    resp = client.post(f"/api/notifications/{n.id}/read", headers={
        "Authorization": f"Bearer {token2}",
    })
    assert resp.status_code == 404

    # Second user gets 404 trying to delete user1's notification
    resp = client.delete(f"/api/notifications/{n.id}", headers={
        "Authorization": f"Bearer {token2}",
    })
    assert resp.status_code == 404


def test_clear_all_deletes_and_returns_count(client, db_session):
    user = db_session.query(User).first()
    db_session.add(Notification(user_id=user.id, title="A", kind="broadcast", read=False))
    db_session.add(Notification(user_id=user.id, title="B", kind="broadcast", read=False))
    db_session.add(Notification(user_id=user.id, title="C", kind="broadcast", read=True))
    db_session.commit()

    token = _get_token(client)
    resp = client.delete("/api/notifications", headers={
        "Authorization": f"Bearer {token}",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["deleted"] == 3

    # Verify all gone
    remaining = db_session.query(Notification).filter(Notification.user_id == user.id).count()
    assert remaining == 0