"""Tests for Phase 87: auth rate limiting + input validation.

The login endpoint throttles repeated *failed* credential attempts per client
IP (in-memory sliding window). The legacy no-body login is exempt by design,
so the rest of the suite is unaffected. A successful login resets the budget.
"""
from __future__ import annotations

from app.routers.auth import reset_login_failures


def _clear_failures():
    reset_login_failures()


class TestLoginThrottling:
    def test_repeated_failed_logins_are_throttled(self, client):
        _clear_failures()
        try:
            for _ in range(10):
                resp = client.post(
                    "/api/auth/login",
                    json={"identifier": "nobody", "password": "wrong"},
                )
                assert resp.status_code == 401, resp.text
            resp = client.post(
                "/api/auth/login",
                json={"identifier": "nobody", "password": "wrong"},
            )
            assert resp.status_code == 429, resp.text
        finally:
            _clear_failures()

    def test_successful_login_resets_failure_budget(self, client):
        _clear_failures()
        try:
            signup = client.post("/api/auth/signup", json={
                "name": "Rate User",
                "username": "rateuser",
                "email": "rate@test.com",
                "password": "goodpass",
                "role": "student",
            })
            assert signup.status_code == 201, signup.text

            # Burn most of the budget, then log in successfully.
            for _ in range(9):
                client.post(
                    "/api/auth/login",
                    json={"identifier": "rateuser", "password": "bad"},
                )
            ok = client.post(
                "/api/auth/login",
                json={"identifier": "rateuser", "password": "goodpass"},
            )
            assert ok.status_code == 200

            # Budget was reset: one more failure is allowed (401, not 429).
            resp = client.post(
                "/api/auth/login",
                json={"identifier": "rateuser", "password": "bad"},
            )
            assert resp.status_code == 401
        finally:
            _clear_failures()

    def test_legacy_no_body_login_is_not_throttled(self, client):
        """The legacy single-user login keeps working regardless of failures."""
        _clear_failures()
        try:
            for _ in range(15):
                client.post("/api/auth/login", json={
                    "identifier": "nobody", "password": "wrong",
                })
            resp = client.post("/api/auth/login", json={})
            assert resp.status_code == 200
        finally:
            _clear_failures()


class TestInputValidation:
    def test_malformed_signup_returns_422(self, client):
        resp = client.post("/api/auth/signup", json={"name": "Incomplete"})
        assert resp.status_code == 422

    def test_malformed_login_payload_returns_422(self, client):
        resp = client.post("/api/auth/login", json={"nope": True})
        assert resp.status_code == 422

    def test_teacher_signup_requires_secret(self, client):
        # TEACHER_SECRET_KEY is empty in tests → teacher signups must 403.
        resp = client.post("/api/auth/signup", json={
            "name": "Sneaky Teacher", "username": "sneaky",
            "email": "sneaky@test.com", "password": "x", "role": "teacher",
        })
        assert resp.status_code == 403
