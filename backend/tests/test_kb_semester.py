"""Idea 43 — semester & calendar detection tests.

Keyword cases (Fall/Spring/year variants), deadline cross-check, silent-default
(current term), per-user isolation.
"""
from __future__ import annotations

from datetime import date

from app.services.kb.subjects import (
    current_term,
    detect_semester,
    semester_from_deadlines,
)
from app.services.security import decode_bearer_token


class TestDetect:
    def test_fall_keyword(self):
        assert detect_semester("Course offered Fall 2026.") == "Fall 2026"

    def test_spring_year_first(self):
        assert detect_semester("2026 Spring semester syllabus.") == "Spring 2026"

    def test_semester_word(self):
        # Year found without a season → mapped to the current term (phrase 24).
        result = detect_semester("Semester 2, 2026 begins soon.")
        assert result == current_term()
        assert "2026" in result

    def test_no_match_returns_none(self):
        assert detect_semester("No term mentioned anywhere here.") is None

    def test_filename_scan(self):
        assert detect_semester("just text", filename="CS101_Fall_2026.pdf") == "Fall 2026"

    def test_autumn_normalised(self):
        assert detect_semester("Autumn 2026 term.") == "Fall 2026"

    def test_deadline_cross_check(self):
        assert semester_from_deadlines(["Midterm — Spring 2027"]) == "Spring 2027"
        assert semester_from_deadlines(["Midterm — Mar 10"]) is None

    def test_silent_defaults_to_current_term(self):
        today = date(2026, 10, 15)
        assert current_term(today) == "Fall 2026"
        assert current_term(date(2026, 2, 15)) == "Spring 2026"
        assert current_term(date(2026, 6, 15)) == "Summer 2026"
        assert current_term(date(2026, 12, 15)) == "Winter 2026"


class TestEndpoint:
    def test_import_detects_and_stores_semester(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        from app.services.security import decode_bearer_token

        resp = client.post(
            "/api/auth/signup",
            json={"name": "Sem", "username": "sem-user", "email": "sem@test.com",
                  "password": "pass123", "role": "student"},
        )
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post(
            "/api/subjects/import",
            json={"text": "# Physics\n\nSpring 2027\n\n## Unit 1: Mechanics\n- Vectors\n"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["profile"]["semester"] == "Spring 2027"

    def test_silent_syllabus_gets_current_term(self, client, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        resp = client.post(
            "/api/auth/signup",
            json={"name": "Sem2", "username": "sem2", "email": "sem2@test.com",
                  "password": "pass123", "role": "student"},
        )
        token = resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.post(
            "/api/subjects/import",
            json={"text": "# Chemistry\n\n## Unit 1: Atoms\n- Models\n"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["profile"]["semester"] == current_term()
