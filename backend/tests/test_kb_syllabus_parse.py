"""Idea 42 — syllabus parsing tests.

Mocked LLM happy path, deterministic fallback path, file ingestion, chunk
merge, schema validation, budget cap.
"""
from __future__ import annotations

from unittest.mock import patch

from app.config import settings
from app.services.security import decode_bearer_token

# Long enough that the parser must chunk (> PARSE_CHUNK_CHARS = 12_000).
LONG_SYLLABUS = (
    "# Computer Networks\n\n"
    "Fall 2026\n\n"
    + "".join(
        f"## Unit {i}: Topic Area {i}\n"
        f"- Concept A{i}\n- Concept B{i}\n1. Analyze protocols {i}\n"
        + f"This unit covers the fundamentals of computer networking including "
        f"protocols, topologies, addressing, routing, switching, and the OSI "
        f"model in depth, with worked examples and practice exercises. Students "
        f"learn about data-link layer frames, IP addressing and subnetting, "
        f"routing protocols such as OSPF and BGP, transport-layer reliability, "
        f"congestion control, and application-layer protocols.\n"
        f"Students are expected to understand the theory and apply it to "
        f"realistic network design problems before moving on, including capacity "
        f"planning, security considerations, and performance trade-offs.\n\n"
        for i in range(1, 30)
    )
    + "Final — May 10\n"
)


import pytest


@pytest.fixture(autouse=True)
def _disable_ai(monkeypatch):
    """Phase 5 tests are deterministic: no real LLM calls by default.
    Tests that need AI set ``AI_ENABLED`` True in-body (overrides this)."""
    monkeypatch.setattr("app.config.settings.AI_ENABLED", False)


def _signup(client, uname="parse-user", email="parse@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Parse", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestParse:
    def test_mocked_llm_happy_path(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", True)
        token = _signup(client)
        parsed = {
            "title": "Data Structures",
            "semester": "Spring 2027",
            "credits": 4,
            "grading": "Homework 40%, Exams 60%",
            "units": [
                {
                    "title": "Arrays",
                    "description": "Basic arrays",
                    "topics": [{"name": "Dynamic arrays", "outcomes": ["Implement a dynamic array"]}],
                    "deadlines": ["Quiz 1 — Feb 1"],
                }
            ],
        }
        with patch("app.services.ai_client.generate_json", return_value=parsed):
            r = client.post(
                "/api/subjects/import", json={"text": "# DS\n\nArrays!"}, headers=_auth(token)
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["fallback"] is False
        assert body["profile"]["parsed"]["title"] == "Data Structures"
        assert body["profile"]["semester"] == "Spring 2027"
        assert body["profile"]["parsed"]["units"][0]["topics"][0]["name"] == "Dynamic arrays"

    def test_llm_garbage_falls_back(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", True)
        token = _signup(client)
        with patch("app.services.ai_client.generate_json", return_value="not json"):
            r = client.post(
                "/api/subjects/import",
                json={"text": "# ML\n\n## Unit 1: Basics\n- Linear regression"},
                headers=_auth(token),
            )
        assert r.status_code == 200
        body = r.json()
        assert body["fallback"] is True
        assert body["profile"]["parsed"]["title"] == "ML"

    def test_fallback_parse(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        r = client.post(
            "/api/subjects/import",
            json={
                "text": (
                    "# Operating Systems\n\n## Unit 1: Processes\n- Process states\n"
                    "- Scheduling\n\n## Unit 2: Memory\n- Virtual memory\n"
                    "Upon completion, students will be able to design a scheduler.\n"
                )
            },
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        profile = r.json()["profile"]
        assert profile["parsed"]["title"] == "Operating Systems"
        units = profile["parsed"]["units"]
        assert [u["title"] for u in units] == ["Processes", "Memory"]
        assert "Process states" in [t["name"] for t in units[0]["topics"]]

    def test_schema_validation_strips_junk(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        r = client.post(
            "/api/subjects/import",
            json={"text": "# Ok\n\n## Unit 1: U\n- real topic\n\norphan line\n"},
            headers=_auth(token),
        )
        body = r.json()
        units = body["profile"]["parsed"]["units"]
        assert len(units) == 1
        assert units[0]["title"] == "U"


class TestChunkMerge:
    def test_long_syllabus_merges_units(self, client, monkeypatch):
        """Phrase 14: >12k chars → parsed per chunk, units merged + deduped."""
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        token = _signup(client)
        r = client.post("/api/subjects/import", json={"text": LONG_SYLLABUS}, headers=_auth(token))
        assert r.status_code == 200, r.text
        units = r.json()["profile"]["parsed"]["units"]
        # 29 units, chunked into 3 slices — all must survive merge, no dups.
        assert len(units) == 29
        titles = [u["title"] for u in units]
        assert len(set(titles)) == 29

    def test_mocked_llm_chunk_merge(self, client, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", True)
        token = _signup(client)
        calls = {"n": 0}

        def fake_generate_json(prompt, **kwargs):
            calls["n"] += 1
            return {
                "title": "Networks",
                "semester": None,
                "credits": None,
                "grading": None,
                "units": [{"title": f"Unit {calls['n']}", "description": None,
                           "topics": [{"name": "TCP", "outcomes": []}], "deadlines": []}],
            }

        with patch("app.services.ai_client.generate_json", side_effect=fake_generate_json):
            r = client.post("/api/subjects/import", json={"text": LONG_SYLLABUS}, headers=_auth(token))
        assert r.status_code == 200
        assert calls["n"] >= 2  # multi-chunk parse really happened
        units = r.json()["profile"]["parsed"]["units"]
        assert len(units) >= 2
        assert {u["title"] for u in units} <= {"Unit 1", "Unit 2", "Unit 3"}


class TestFileImport:
    def test_import_md_file(self, client):
        token = _signup(client)
        r = client.post(
            "/api/subjects/import-file",
            headers=_auth(token),
            files={"file": ("syllabus.md", b"# Networks\n\n## Unit 1: Links\n- Ethernet\n", "text/markdown")},
        )
        assert r.status_code == 200, r.text
        profile = r.json()["profile"]
        assert profile["parsed"]["title"] == "Networks"
        assert profile["parsed"]["units"][0]["title"] == "Links"

    def test_bad_extension_rejected(self, client):
        token = _signup(client)
        r = client.post(
            "/api/subjects/import-file",
            headers=_auth(token),
            files={"file": ("evil.exe", b"MZ\x90\x00", "application/octet-stream")},
        )
        assert r.status_code == 400
