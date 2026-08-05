"""Tests for the daily schedule API endpoints."""

from datetime import date

import pytest


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    return resp.json()["token"]


def _create_block(client, token, date_str, time_range, activity, **kwargs):
    resp = client.post(
        "/api/dailyschedule",
        json={"date": date_str, "time_range": time_range, "activity": activity, **kwargs},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


def test_create_and_list_by_date(client):
    token = _get_token(client)
    today = "2026-08-05"

    resp = _create_block(client, token, today, "08:00-09:30", "Math class", category="School")
    assert resp.status_code == 201

    resp = _create_block(client, token, today, "10:00-11:30", "Physics study", category="Study Time")
    assert resp.status_code == 201

    list_resp = client.get(
        f"/api/dailyschedule?date={today}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert len(data) == 2
    assert data[0]["activity"] == "Math class"
    assert data[1]["activity"] == "Physics study"


def test_ownership_isolation(client):
    token1 = _get_token(client)

    # Create a second user
    signup_resp = client.post(
        "/api/auth/signup",
        json={"name": "Other User", "username": "otheruser", "email": "other@test.com", "password": "pass1234"},
    )
    assert signup_resp.status_code == 201
    token2 = signup_resp.json()["token"]

    today = "2026-08-05"
    resp = _create_block(client, token1, today, "08:00-09:30", "My class", category="School")
    assert resp.status_code == 201
    item_id = resp.json()["id"]

    # Second user cannot update
    resp = client.put(
        f"/api/dailyschedule/{item_id}",
        json={"activity": "Hacked"},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404

    # Second user cannot delete
    resp = client.delete(
        f"/api/dailyschedule/{item_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404

    # Second user cannot toggle
    resp = client.post(
        f"/api/dailyschedule/{item_id}/toggle",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404


def test_toggle_flips_done(client):
    token = _get_token(client)
    today = "2026-08-05"

    resp = _create_block(client, token, today, "08:00-09:30", "Gym", category="Break")
    assert resp.status_code == 201
    item_id = resp.json()["id"]
    assert resp.json()["done"] is False

    resp = client.post(
        f"/api/dailyschedule/{item_id}/toggle",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["done"] is True

    resp = client.post(
        f"/api/dailyschedule/{item_id}/toggle",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["done"] is False


def test_stats_math(client):
    token = _get_token(client)
    today = "2026-08-05"

    # No blocks yet
    resp = client.get(
        f"/api/dailyschedule/stats?date={today}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["done"] == 0
    assert data["ratio"] == 0.0

    # Add blocks
    _create_block(client, token, today, "08:00-09:30", "Math", category="School")
    _create_block(client, token, today, "10:00-11:30", "Science", category="Study Time")
    _create_block(client, token, today, "13:00-14:00", "Lunch break", category="Break")

    # Mark one as done
    list_resp = client.get(
        f"/api/dailyschedule?date={today}",
        headers={"Authorization": f"Bearer {token}"},
    )
    items = list_resp.json()
    assert len(items) == 3
    item_id = items[0]["id"]
    client.post(
        f"/api/dailyschedule/{item_id}/toggle",
        headers={"Authorization": f"Bearer {token}"},
    )

    resp = client.get(
        f"/api/dailyschedule/stats?date={today}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert data["done"] == 1
    assert data["ratio"] == round(1 / 3, 2)


def test_validation_malformed_time_range(client):
    token = _get_token(client)
    today = "2026-08-05"

    resp = _create_block(client, token, today, "8am-9am", "Bad time", category="School")
    assert resp.status_code == 400


def test_validation_overlapping_blocks(client):
    token = _get_token(client)
    today = "2026-08-05"

    resp = _create_block(client, token, today, "08:00-09:30", "First block", category="School")
    assert resp.status_code == 201

    # Exact overlap
    resp = _create_block(client, token, today, "08:00-09:30", "Overlap block", category="Study Time")
    assert resp.status_code == 400
    assert "Overlapping" in resp.json()["detail"]

    # Partial overlap (starts inside)
    resp = _create_block(client, token, today, "09:00-10:30", "Partial overlap", category="Break")
    assert resp.status_code == 400

    # Partial overlap (ends inside)
    resp = _create_block(client, token, today, "07:30-08:30", "Partial overlap start", category="Break")
    assert resp.status_code == 400

    # Non-overlapping should pass
    resp = _create_block(client, token, today, "10:00-11:30", "Non-overlapping", category="Break")
    assert resp.status_code == 201


def test_list_without_date_query_422(client):
    token = _get_token(client)

    resp = client.get(
        "/api/dailyschedule",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422
