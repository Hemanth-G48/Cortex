"""Audit defects #49, #52, #66 — writing back into the vault.

- ``POST /api/kb/daily-notes/complete-task`` echoes a completed task into today's
  ``daily-life/YYYY-MM-DD.md`` under a ``## Tasks`` section (#66).
- ``POST /api/kb/reflections`` appends a reflection line under ``## Reflections``
  so completing a goal is recorded in the user's own vault (#52).
- ``POST /api/habits/{id}/archive`` records *why* a habit was archived (#49).

All three fail soft when the vault has no reachable ``daily-life/`` folder —
they must never 500 on a missing/read-only vault.
"""
from __future__ import annotations

from datetime import date

from app.models import Habit, KbSource, User

AUTH = "Authorization"


def _signup(client, uname="append-user", email="append@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Append", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _vault_source(db, tmp_path, user_id):
    """Register a vault laid out as ``<root>/notes`` + ``<root>/daily-life``."""
    (tmp_path / "notes").mkdir(exist_ok=True)
    (tmp_path / "daily-life").mkdir(exist_ok=True)
    source = KbSource(
        user_id=user_id,
        name="Vault",
        source_type="vault_folder",
        root_path=str(tmp_path / "notes"),
        enabled=True,
    )
    db.add(source)
    db.commit()
    return source


def _uid(db, email="append@test.com"):
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


class TestCompleteTaskAppend:
    def test_appends_under_tasks_section(self, client, db_session, tmp_path):
        token = _signup(client)
        _vault_source(db_session, tmp_path, _uid(db_session))

        resp = client.post(
            "/api/kb/daily-notes/complete-task",
            json={"title": "Finish OS assignment"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["created"] is True
        assert body["date"] == date.today().isoformat()

        note = tmp_path / "daily-life" / f"{date.today().isoformat()}.md"
        assert note.is_file()
        text = note.read_text()
        assert "## Tasks" in text
        assert "- [x] Finish OS assignment" in text

    def test_second_append_keeps_section_order(self, client, db_session, tmp_path):
        token = _signup(client)
        _vault_source(db_session, tmp_path, _uid(db_session))
        for title in ("First", "Second"):
            client.post(
                "/api/kb/daily-notes/complete-task",
                json={"title": title},
                headers={AUTH: f"Bearer {token}"},
            )
        text = (tmp_path / "daily-life" / f"{date.today().isoformat()}.md").read_text()
        assert text.count("## Tasks") == 1
        assert text.index("- [x] First") < text.index("- [x] Second")

    def test_requires_a_title(self, client, db_session):
        token = _signup(client)
        resp = client.post(
            "/api/kb/daily-notes/complete-task",
            json={"title": "   "},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_without_a_vault_fails_soft(self, client, db_session):
        token = _signup(client)
        resp = client.post(
            "/api/kb/daily-notes/complete-task",
            json={"title": "No vault here"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is False
        assert "daily-life" in body["reason"]


class TestReflectionAppend:
    def test_appends_under_reflections_section(self, client, db_session, tmp_path):
        token = _signup(client)
        _vault_source(db_session, tmp_path, _uid(db_session))

        resp = client.post(
            "/api/kb/reflections",
            json={"content": "Goal achieved: Ace finals", "kind": "goal"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True
        text = (tmp_path / "daily-life" / f"{date.today().isoformat()}.md").read_text()
        assert "## Reflections" in text
        assert "- [goal] Goal achieved: Ace finals" in text

    def test_empty_content_is_rejected(self, client, db_session):
        token = _signup(client)
        resp = client.post(
            "/api/kb/reflections",
            json={"content": ""},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 400


class TestHabitArchiveProvenance:
    def test_archive_records_reason_and_unarchive_clears_it(self, client, db_session):
        token = _signup(client)
        habit = Habit(name="Late night doomscroll", user_id=_uid(db_session))
        db_session.add(habit)
        db_session.commit()

        resp = client.post(
            f"/api/habits/{habit.id}/archive",
            json={"reason": "Vault note flagged late-night habits"},
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["archived_reason"] == "Vault note flagged late-night habits"

        archived = client.get(
            "/api/habits?include_archived=true", headers={AUTH: f"Bearer {token}"},
        ).json()
        assert any(h["archived_reason"] for h in archived)

        again = client.post(
            f"/api/habits/{habit.id}/unarchive", headers={AUTH: f"Bearer {token}"},
        ).json()
        assert again["is_archived"] is False
        assert again["archived_reason"] is None

    def test_archive_without_a_reason_records_a_default(self, client, db_session):
        token = _signup(client)
        habit = Habit(name="Old habit", user_id=_uid(db_session))
        db_session.add(habit)
        db_session.commit()

        body = client.post(
            f"/api/habits/{habit.id}/archive", headers={AUTH: f"Bearer {token}"},
        ).json()
        assert body["archived_reason"] == "Archived manually"
