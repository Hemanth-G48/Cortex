"""Tests for the Google OAuth + sync features (Group 14)."""
from __future__ import annotations

import pytest

from app.services import google_oauth


@pytest.fixture
def unconfigured(monkeypatch):
    """Simulate GOOGLE_* env vars being blank."""
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_CLIENT_SECRET", "")
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    return google_oauth


def test_status_disconnected(client, unconfigured):
    resp = client.get("/api/auth/google/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["configured"] is False


def test_connect_returns_error_when_unconfigured(client, unconfigured):
    resp = client.get("/api/auth/google")
    assert resp.status_code == 200
    data = resp.json()
    assert data["url"] is None
    assert "not configured" in (data.get("error") or "").lower()


def test_callback_requires_code(client):
    resp = client.get("/api/auth/google/callback")
    assert resp.status_code == 400


def test_disconnect_is_safe(client, unconfigured):
    resp = client.post("/api/auth/google/disconnect")
    assert resp.status_code == 200
    assert resp.json()["connected"] is False


def test_google_connect_with_credentials(client, monkeypatch):
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_CLIENT_SECRET", "fake-secret")
    resp = client.get("/api/auth/google")
    assert resp.status_code == 200
    url = resp.json()["url"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "scope=" in url
    assert "access_type=offline" in url


def test_exchange_code_success(client, monkeypatch):
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setattr(google_oauth.settings, "GOOGLE_CLIENT_SECRET", "csec")

    class FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "tok-123", "refresh_token": "ref-1", "expires_in": 3600, "token_type": "Bearer"}

    class FakeUserResp:
        def json(self):
            return {"email": "alex@student.edu"}

    monkeypatch.setattr(google_oauth.httpx, "post", lambda *a, **k: FakeResp())
    monkeypatch.setattr(google_oauth.httpx, "get", lambda *a, **k: FakeUserResp())

    resp = client.get("/api/auth/google/callback?code=abc123")
    assert resp.status_code == 200
    # Callback now returns HTML with postMessage for popup communication
    html = resp.text
    assert "google-oauth" in html
    assert "alex@student.edu" in html

    # Status should now report connected (token stored).
    status = client.get("/api/auth/google/status").json()
    assert status["connected"] is True
    assert status["email"] == "alex@student.edu"


def test_classroom_courses_mock_fallback(client, unconfigured):
    resp = client.get("/api/classroom/courses")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "mock"
    courses = body["courses"]
    assert len(courses) >= 3
    assert courses[0]["id"] == "gc-1"


def test_classroom_assignments_mock_fallback(client, unconfigured):
    resp = client.get("/api/classroom/assignments")
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "mock"
    assignments = body["assignments"]
    assert len(assignments) >= 3
    assert all("title" in a for a in assignments)


def test_classroom_mock_never_persists_courses(client, unconfigured, db_session):
    """Mocks are display-only — no Course rows are created by a mock sync."""
    from app.models import Course

    before = db_session.query(Course).count()
    client.get("/api/classroom/courses")
    client.get("/api/classroom/assignments")
    assert db_session.query(Course).count() == before


def test_gmail_unread_mock_fallback(client, unconfigured):
    resp = client.get("/api/gmail/unread")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


def test_gmail_messages_mock_fallback(client, unconfigured):
    resp = client.get("/api/gmail/messages")
    assert resp.status_code == 200
    messages = resp.json()
    assert len(messages) >= 2
    assert all("subject" in m for m in messages)


def test_calendar_events_mock_fallback(client, unconfigured):
    resp = client.get("/api/calendar/events")
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 3
    assert all("title" in e for e in events)
