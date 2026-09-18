"""Workflow-glue tests: Today command center, new-note triage, vault backup,
and the weekly review ritual.

All four are read-mostly aggregation flows that reuse existing services, so
the tests assert the payload shapes, the safe-restore default, and that the
triage actions (apply/dismiss/tag) mutate state as documented.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime, timedelta

from app.models import (
    Course,
    KbDocument,
    KbSource,
    MicroSession,
    PomodoroSession,
    Topic,
    User,
)
from app.services.kb import utcnow

AUTH = "Authorization"


def _signup(client, uname="wf-user", email="wf@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "WF User",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {AUTH: f"Bearer {token}"}


def _uid(db, uname="wf-user") -> int:
    user = db.query(User).filter(User.username == uname).first()
    assert user is not None
    return user.id


def _make_source(client, token, root, name="Vault"):
    resp = client.post(
        "/api/kb/sources",
        json={"name": name, "source_type": "vault_folder", "root_path": str(root)},
        headers=_auth(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _scan(client, token, source_id):
    resp = client.post(
        f"/api/kb/sources/{source_id}/scan", headers=_auth(token)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _seed_topic(db, user_id, name="Cryptography", subject_id=9999):
    topic = Topic(
        user_id=user_id,
        name=name,
        normalized_name=name.lower(),
        subject_id=subject_id,
        status="confirmed",
        bloom_level="Understand",
    )
    db.add(topic)
    db.flush()
    return topic


# ---------------------------------------------------------------------------
# Today command center
# ---------------------------------------------------------------------------


class TestToday:
    def test_today_overview_shape(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        (db_session.query(PomodoroSession).delete())
        db_session.flush()
        from app.services.kb import utcnow as _utcnow
        db_session.add(
            PomodoroSession(
                user_id=uid,
                start_time=datetime(2026, 9, 13, 9, 0, 0),
                duration_minutes=25,
                completed=True,
                mode="Focus",
            )
        )
        db_session.flush()

        resp = client.get("/api/kb/today", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        from datetime import timezone
        from app.services.kb import utcnow as _utcnow
        test_day = date(2026, 9, 13)  # deterministic day for the pomodoro we add
        assert body["date"] == test_day.isoformat()
        assert body["day_name"] in (
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
        )
        # Morning sections exist (may be empty for a fresh DB).
        assert isinstance(body["morning"]["reviews_due"], list)
        assert isinstance(body["morning"]["next_actions"], list)
        assert isinstance(body["morning"]["schedule"], list)
        assert isinstance(body["morning"]["deadlines"], list)
        # Evening: the pomodoro created above surfaces (created with the same
        # naive-UTC `utcnow()` so it lands on the same calendar day).
        assert body["evening"]["focus_minutes"] == 25
        assert body["evening"]["pomodoros"][0]["completed"] is True
        assert isinstance(body["evening"]["journal"], list)
        assert isinstance(body["evening"]["daily"]["documents"], list)

    def test_today_accepts_date_param(self, client):
        token = _signup(client)
        resp = client.get("/api/kb/today?date=2026-01-05", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["date"] == "2026-01-05"
        assert resp.json()["day_name"] == "Monday"

    def test_today_deadlines_include_assignments(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        course = Course(
            user_id=uid,
            title="Cyber Security",
            status="active",
            credits=3,
        )
        db_session.add(course)
        db_session.flush()
        from app.models import Assignment

        db_session.add(
            Assignment(
                course_id=course.id,
                title="Wireshark Lab",
                due_date=date.today() + timedelta(days=2),
                status="Not started",
            )
        )
        db_session.flush()

        resp = client.get("/api/kb/today", headers=_auth(token))
        deadlines = resp.json()["morning"]["deadlines"]
        assert any(d["kind"] == "assignment" and d["title"] == "Wireshark Lab" for d in deadlines)


# ---------------------------------------------------------------------------
# New-note triage queue
# ---------------------------------------------------------------------------


class TestTriage:
    def test_queue_lists_untriaged_documents_with_subjects(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "network.md").write_text("# TCP/IP\nnetwork fundamentals")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])
        # Doc is ingested → status unchanged; created recently → in window.
        doc = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).first()
        assert doc is not None

        resp = client.get("/api/kb/triage", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = body["items"]
        assert any(i["id"] == doc.id for i in items)
        assert body["stats"]["pending"] >= 1
        item = next(i for i in items if i["id"] == doc.id)
        assert item["title"] == "network.md" or item["title"].startswith("network")
        assert isinstance(item["detected_subjects"], list)
        assert isinstance(item["tags"], list)

    def test_apply_subjects_tags_and_leaves_queue(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "cybersecurity.md").write_text("# cybersecurity\nAES and firewall notes")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).first()

        resp = client.post(
            f"/api/kb/triage/{doc.id}/apply-subjects", headers=_auth(token)
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["subjects"]  # at least one detected subject

        # Doc has course: tags and no longer appears in the queue.
        from app.models import KbDocumentTag, KbTag

        tag_names = [
            t.name
            for t in db_session.query(KbTag)
            .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
            .filter(KbDocumentTag.document_id == doc.id)
            .all()
        ]
        assert any(name.startswith("course:") for name in tag_names)
        resp = client.get("/api/kb/triage", headers=_auth(token))
        assert all(i["id"] != doc.id for i in resp.json()["items"])

    def test_manual_tag(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "note.md").write_text("hello vault")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).first()

        resp = client.post(
            f"/api/kb/triage/{doc.id}/tag",
            json={"name": "course:Networking"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True

        from app.models import KbDocumentTag, KbTag

        names = [
            t.name
            for t in db_session.query(KbTag)
            .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
            .filter(KbDocumentTag.document_id == doc.id)
            .all()
        ]
        assert "course:Networking" in names

    def test_triage_stats_pending_scoped_to_window(self, client, db_session):
        """Old triaged docs (outside the window) must not shrink ``pending``."""
        token = _signup(client)
        uid = _uid(db_session)
        from app.models import KbTag

        # A doc created outside the 30-day window, already marked triaged.
        old = KbDocument(
            user_id=uid,
            path_rel="old/note.md",
            title="old",
            status="unchanged",
            created_at=utcnow() - timedelta(days=60),
        )
        db_session.add(old)
        db_session.flush()
        tag = KbTag(user_id=uid, name="triage/done", kind="rule")
        db_session.add(tag)
        db_session.flush()
        from app.models import KbDocumentTag

        db_session.add(
            KbDocumentTag(
                user_id=uid, document_id=old.id, tag_id=tag.id, provenance="rule"
            )
        )
        # A fresh doc inside the window, untriaged.
        fresh = KbDocument(
            user_id=uid,
            path_rel="fresh/note.md",
            title="fresh",
            status="unchanged",
            created_at=utcnow(),
        )
        db_session.add(fresh)
        db_session.flush()

        resp = client.get("/api/kb/triage", headers=_auth(token))
        stats = resp.json()["stats"]
        assert stats["total_in_window"] == 1  # only the fresh doc
        assert stats["triaged"] == 0  # the old triaged doc is out of window
        assert stats["pending"] == 1  # never undercounted

    def test_dismiss_leaves_queue_without_tagging(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "note.md").write_text("hello vault")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])
        doc = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).first()

        resp = client.post(
            f"/api/kb/triage/{doc.id}/dismiss", headers=_auth(token)
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True
        from app.models import KbDocumentTag

        # No course tag, but a triage/done rule tag exists.
        tags = db_session.query(KbDocumentTag).filter(KbDocumentTag.document_id == doc.id).all()
        assert len(tags) == 1
        assert tags[0].provenance == "rule"

        resp = client.get("/api/kb/triage", headers=_auth(token))
        assert all(i["id"] != doc.id for i in resp.json()["items"])

    def test_accept_all_files_every_detected_subject(self, client, tmp_path, db_session):
        """Bulk accept applies course tags + leaves the queue for all docs."""
        token = _signup(client)
        (tmp_path / "cybersecurity.md").write_text("# cybersecurity\nAES and firewall notes")
        (tmp_path / "data structures.md").write_text("# data structures\narrays and linked lists")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])
        docs = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).all()
        assert len(docs) == 2

        resp = client.post("/api/kb/triage/accept-all", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["processed"] == 2
        assert body["accepted"] == 2
        assert body["subjects_applied"] >= 2
        assert body["remaining_pending"] == 0

        # Every doc left the queue and carries a course: tag.
        from app.models import KbDocumentTag, KbTag

        for doc in docs:
            names = [
                t.name
                for t in db_session.query(KbTag)
                .join(KbDocumentTag, KbDocumentTag.tag_id == KbTag.id)
                .filter(KbDocumentTag.document_id == doc.id)
                .all()
            ]
            assert any(name.startswith("course:") for name in names)
        resp = client.get("/api/kb/triage", headers=_auth(token))
        assert resp.json()["items"] == []

    def test_accept_all_leaves_no_subject_docs_queued(self, client, tmp_path, db_session):
        """Docs with no detected subjects stay in the queue (skipped)."""
        token = _signup(client)
        (tmp_path / "cybersecurity.md").write_text("# cybersecurity\nAES notes")
        (tmp_path / "random.md").write_text("no subject here at all")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])

        resp = client.post("/api/kb/triage/accept-all", headers=_auth(token))
        body = resp.json()
        assert body["ok"] is True
        assert body["accepted"] >= 1
        assert body["skipped_no_subjects"] >= 1
        assert body["remaining_pending"] == body["skipped_no_subjects"]

        # The subject-less doc remains; the accepted one is gone.
        resp = client.get("/api/kb/triage", headers=_auth(token))
        items = resp.json()["items"]
        assert len(items) == body["skipped_no_subjects"]
        assert all("random" in (i["title"] or "") for i in items)

    def test_dismiss_all_clears_queue_without_tagging(self, client, tmp_path, db_session):
        token = _signup(client)
        (tmp_path / "a.md").write_text("file a")
        (tmp_path / "b.md").write_text("file b")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])

        resp = client.post("/api/kb/triage/dismiss-all", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["dismissed"] == 2
        assert body["remaining_pending"] == 0

        from app.models import KbDocumentTag

        docs = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).all()
        for doc in docs:
            tags = db_session.query(KbDocumentTag).filter(KbDocumentTag.document_id == doc.id).all()
            # Only the triage/done rule tag — no course tags.
            assert len(tags) == 1
            assert tags[0].provenance == "rule"
        resp = client.get("/api/kb/triage", headers=_auth(token))
        assert resp.json()["items"] == []

    def test_stats_endpoint_lightweight_counts(self, client, tmp_path, db_session):
        """Dashboard reminder source: counts only, no document payload."""
        token = _signup(client)
        (tmp_path / "cybersecurity.md").write_text("# cybersecurity\nAES notes")
        src = _make_source(client, token, tmp_path)
        _scan(client, token, src["id"])

        resp = client.get("/api/kb/triage/stats", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert set(body.keys()) == {"pending", "total_in_window", "triaged", "window_days"}
        assert body["pending"] >= 1
        assert body["window_days"] == 30

        # Dismissing drops pending without shipping items.
        doc = db_session.query(KbDocument).filter(KbDocument.source_id == src["id"]).first()
        client.post(f"/api/kb/triage/{doc.id}/dismiss", headers=_auth(token))
        resp = client.get("/api/kb/triage/stats", headers=_auth(token))
        assert resp.json()["pending"] == 0

    def test_dismiss_all_idempotent_and_window_scoped(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        # One doc inside the window, one old (60 days) — old must not be touched.
        fresh = KbDocument(
            user_id=uid, path_rel="fresh.md", title="fresh", status="unchanged", created_at=utcnow()
        )
        old = KbDocument(
            user_id=uid, path_rel="old.md", title="old", status="unchanged", created_at=utcnow() - timedelta(days=60)
        )
        db_session.add_all([fresh, old])
        db_session.flush()

        resp = client.post("/api/kb/triage/dismiss-all", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["dismissed"] == 1

        # Second call dismisses nothing (queue already empty in window).
        resp = client.post("/api/kb/triage/dismiss-all", headers=_auth(token))
        assert resp.json()["dismissed"] == 0

        from app.models import KbDocumentTag, KbTag

        old_tagged = (
            db_session.query(KbDocumentTag.id)
            .join(KbTag, KbTag.id == KbDocumentTag.tag_id)
            .filter(
                KbDocumentTag.document_id == old.id,
                KbTag.name == "triage/done",
            )
            .first()
        )
        assert old_tagged is None  # outside the window → untouched


# ---------------------------------------------------------------------------
# Vault backup & restore
# ---------------------------------------------------------------------------


class TestBackup:
    def test_export_returns_zip_with_manifest(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "a.md").write_text("file A")
        _make_source(client, token, tmp_path, name="BackupSrc")

        resp = client.post("/api/kb/backup/export", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/zip"

        zf = zipfile.ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert "manifest.json" in names
        manifest = __import__("json").loads(zf.read("manifest.json"))
        assert manifest["app"] == "Student Life OS"
        assert len(manifest["sources"]) >= 1
        # At least one vault file entry.
        assert any(n.startswith("vault/") and n.endswith("a.md") for n in names)

    def test_restore_rejects_non_backup(self, client):
        token = _signup(client)
        bad = io.BytesIO()
        with zipfile.ZipFile(bad, "w") as zf:
            zf.writestr("random.txt", "not a backup")
        bad.seek(0)

        resp = client.post(
            "/api/kb/backup/restore",
            files={"file": ("random.zip", bad.getvalue(), "application/zip")},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    def test_restore_writes_vault_files_but_skips_db_by_default(
        self, client, tmp_path, db_session
    ):
        token = _signup(client)
        uid = _uid(db_session)
        root = tmp_path / "restore-root"
        root.mkdir()
        source = KbSource(
            user_id=uid,
            name="RestoreSrc",
            source_type="local_dir",
            root_path=str(root),
            enabled=True,
        )
        db_session.add(source)
        db_session.flush()

        # Build a backup zip from another folder.
        other = tmp_path / "other"
        other.mkdir()
        (other / "b.md").write_text("restored content")
        src2 = KbSource(
            user_id=uid,
            name="OtherSrc",
            source_type="local_dir",
            root_path=str(other),
            enabled=True,
        )
        db_session.add(src2)
        db_session.flush()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.write(other / "b.md", f"vault/{src2.id}/b.md")
            zf.writestr("manifest.json", '{"app": "Student Life OS", "sources": []}')
        buf.seek(0)

        resp = client.post(
            "/api/kb/backup/restore",
            files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["restored_files"] == 1
        # No student_os.db in this archive → nothing to apply, no clobber.
        assert body["database_restored"] is False
        assert (other / "b.md").read_text() == "restored content"

    def test_restore_rejects_path_traversal(self, client, tmp_path, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        root = tmp_path / "safe-root"
        root.mkdir()
        source = KbSource(
            user_id=uid, name="Safe", source_type="local_dir", root_path=str(root), enabled=True
        )
        db_session.add(source)
        db_session.flush()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("vault/../../evil.md", "pwn")
            zf.writestr("manifest.json", '{"app": "Student Life OS"}')
        buf.seek(0)

        resp = client.post(
            "/api/kb/backup/restore",
            files={"file": ("evil.zip", buf.getvalue(), "application/zip")},
            headers=_auth(token),
        )
        # Unsafe member is skipped; restore still succeeds without writing.
        assert resp.status_code == 200
        assert resp.json()["restored_files"] == 0
        assert not (tmp_path / "evil.md").exists()


# ---------------------------------------------------------------------------
# Weekly review ritual
# ---------------------------------------------------------------------------


class TestWeeklyReview:
    def test_weekly_review_payload(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        topic = _seed_topic(db_session, uid)

        resp = client.get("/api/kb/weekly-review", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["week_start"] <= body["week_end"]
        assert isinstance(body["activity"]["captures"], list)
        assert isinstance(body["activity"]["sessions_done"], int)
        assert isinstance(body["goals"], list)
        assert isinstance(body["derived_goals"], list)
        assert isinstance(body["weak_topics"], list)
        assert body["reflection"] is None  # not generated on read

    def test_generate_reflection_creates_row(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        _seed_topic(db_session, uid)
        from app.models import LearningEvent

        db_session.add(
            LearningEvent(
                user_id=uid,
                event_type="session",
                value=25.0,
                created_at=utcnow(),
            )
        )
        db_session.flush()

        resp = client.post(
            "/api/kb/weekly-review/generate-reflection", headers=_auth(token)
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["reflection"]["week_start"] == body["week_start"]
        # Deterministic fallback content (AI off in tests).
        assert body["reflection"]["content"]

        # Second call returns the cached row (not duplicated).
        resp2 = client.post(
            "/api/kb/weekly-review/generate-reflection", headers=_auth(token)
        )
        assert resp2.json()["reflection"]["id"] == body["reflection"]["id"]

    def test_confirm_derived_goal(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        profile = _seed_subject_profile(db_session, uid)

        resp = client.post(
            "/api/kb/weekly-review/goals/confirm",
            json={
                "title": "Master Cyber Security",
                "subject_id": profile.curriculum_subject_id,
                "quarter": "Q3",
                "year": 2026,
            },
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["ok"] is True
        # Goal now appears in the goals list.
        resp = client.get("/api/kb/weekly-review", headers=_auth(token))
        assert any(g["title"] == "Master Cyber Security" for g in resp.json()["goals"])


def _seed_subject_profile(db, user_id):
    from app.models import SubjectProfile

    profile = SubjectProfile(
        user_id=user_id,
        status="confirmed",
        parsed_json='{"title": "Cyber Security"}',
        curriculum_subject_id=9999,
    )
    db.add(profile)
    db.flush()
    return profile
