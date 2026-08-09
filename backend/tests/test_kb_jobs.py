"""Idea 10 — ingestion job queue & status tests: submit, await completion,
status transitions, error capture, and interrupted-resume behavior.
"""
from __future__ import annotations

import json
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import KbJob, User
from app.services.kb import jobs

AUTH = "Authorization"


def _signup(client, uname="job-user", email="job@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Jobs", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _source(client, token, root):
    resp = client.post(
        "/api/kb/sources",
        json={"name": "Vault", "source_type": "vault_folder", "root_path": str(root)},
        headers={AUTH: f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestJobApi:
    def test_scan_job_runs_synchronously_and_is_pollable(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "a.md").write_text("# Hi\ncontent")
        src = _source(client, token, tmp_path)

        resp = client.post(
            f"/api/kb/sources/{src['id']}/scan", headers={AUTH: f"Bearer {token}"}
        )
        assert resp.status_code == 200, resp.text
        job = resp.json()["job"]
        assert job["status"] == "done"
        assert job["total_items"] == 1

        # Pollable via the jobs endpoints (phrase 94).
        jobs_resp = client.get("/api/kb/jobs", headers={AUTH: f"Bearer {token}"}).json()
        assert jobs_resp["total"] >= 1
        polled = client.get(
            f"/api/kb/jobs/{job['id']}", headers={AUTH: f"Bearer {token}"}
        ).json()
        assert polled["status"] == "done"
        assert polled["finished_at"] is not None

    def test_jobs_are_user_scoped(self, client, tmp_path):
        token_a = _signup(client, "job-a", "job-a@test.com")
        token_b = _signup(client, "job-b", "job-b@test.com")
        (tmp_path / "a.md").write_text("x")
        src = _source(client, token_a, tmp_path)
        resp = client.post(
            f"/api/kb/sources/{src['id']}/scan", headers={AUTH: f"Bearer {token_a}"}
        )
        job_id = resp.json()["job"]["id"]
        other = client.get(
            f"/api/kb/jobs/{job_id}", headers={AUTH: f"Bearer {token_b}"}
        )
        assert other.status_code == 404


class TestJobEngine:
    @pytest.fixture()
    def tmp_db(self, tmp_path):
        """File-based SQLite so worker threads can share the database."""
        engine = create_engine(
            f"sqlite:///{tmp_path / 'jobs.db'}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        db = Session()
        user = User(name="J", username="j-user", email="j-user@t.com", role="student")
        db.add(user)
        db.commit()
        db.refresh(user)
        yield Session, user.id
        db.close()

    def test_async_ingest_job_completes(self, tmp_db, monkeypatch):
        Session, user_id = tmp_db
        monkeypatch.setattr(jobs, "sync_mode", lambda: False)
        db = Session()
        job = jobs.submit_ingest_job(db, user_id, [], session_factory=Session)
        assert job.status == "queued"

        deadline = time.time() + 10
        while time.time() < deadline:
            db.expire_all()
            current = db.query(KbJob).filter(KbJob.id == job.id).first()
            if current.status in ("done", "failed"):
                break
            time.sleep(0.05)
        assert current.status == "done"
        assert current.processed_items == 0
        db.close()

    def test_error_capture_sets_failed_status(self, tmp_db):
        Session, user_id = tmp_db
        db = Session()
        job = KbJob(
            user_id=user_id,
            job_type="ingest",
            status="queued",
            ref_type="documents",
            ref_ids_json="[1,2",  # invalid JSON → job fails
        )
        db.add(job)
        db.commit()
        jobs._dispatch(job, Session, db=db)  # sync under pytest
        db.refresh(job)
        assert job.status == "failed"
        assert job.error
        assert job.finished_at is not None
        db.close()

    def test_running_job_not_rerun(self, tmp_db):
        Session, user_id = tmp_db
        db = Session()
        job = KbJob(user_id=user_id, job_type="scan", status="running", ref_type="source", ref_id=999)
        db.add(job)
        db.commit()
        jobs.run_job(Session, job.id)  # idempotent — running jobs are skipped
        db.expire_all()
        assert db.query(KbJob).filter(KbJob.id == job.id).first().status == "running"
        db.close()

    def test_resume_interrupted_flips_stuck_jobs_and_redispatch(self, tmp_db, monkeypatch):
        Session, user_id = tmp_db
        db = Session()
        stuck = KbJob(user_id=user_id, job_type="scan", status="running", ref_type="source", ref_id=999)
        queued = KbJob(user_id=user_id, job_type="ingest", status="queued", ref_type="documents", ref_ids_json="[]")
        db.add_all([stuck, queued])
        db.commit()
        stuck_id, queued_id = stuck.id, queued.id

        dispatched: list[int] = []
        monkeypatch.setattr(
            jobs, "_dispatch", lambda job, session_factory=None, db=None: dispatched.append(job.id)
        )
        recovered = jobs.resume_interrupted_jobs(session_factory=Session)
        assert recovered == 1
        db.expire_all()
        assert db.query(KbJob).filter(KbJob.id == stuck_id).first().status == "interrupted"
        # Queued + interrupted jobs are re-dispatched (phrase 95).
        assert set(dispatched) == {stuck_id, queued_id}
        db.close()
