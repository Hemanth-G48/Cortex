"""Workflow loop tests — Study-Session Loop, Vault Health Audit, Plan Re-sync,
Focus/Readiness Loop.

All four follow the established workflow pattern: read-only GETs on
navigation (no LLM, no mutation) + explicit POST actions. Network is fully
mocked via the same fixture style as ``test_kb_learning_plans``.
"""

from __future__ import annotations

import json

import pytest

from app.models import (
    KbDocument,
    LearningPath,
    LearningPlan,
    LearningTask,
    MicroSession,
    MissingNoteSuggestion,
    OutdatedNote,
)
from app.services.kb import source_crawler as sc

AUTH = "Authorization"

INDEX_URL = "https://portswigger.net/web-security/learning-paths"
SSRF_PATH_URL = "https://portswigger.net/web-security/learning-paths/ssrf-attacks"
AUTH_PATH_URL = "https://portswigger.net/web-security/learning-paths/authentication-vulnerabilities"
RESOURCE_URL = (
    "https://portswigger.net/web-security/learning-paths/ssrf-attacks/"
    "ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf"
)

INDEX_HTML = (
    '<html><body><div class="wrapper"><h1>Web Security Academy Learning Paths</h1>'
    '<div widget-id="academy-available-learning-paths"></div></div></body></html>'
)

WIDGET_HTML = """
<div class="section-full-width"><div class="container-columns">
  <div class="progress-cards theme-navy-9">
    <div class="progress-cards-content">
      <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
      <p class="font-size-16"><h5>Server-side request forgery (SSRF) attacks</h5></p>
      <p class="font-size-14">This learning path covers SSRF vulnerabilities.</p>
      <div class="progress-cards-content-buttons ">
        <a class="chevron-after no-wrap" href="/web-security/learning-paths/ssrf-attacks">View path</a>
        <a class="button-view-path button-outline-small no-wrap" href="/web-security/learning-paths/ssrf-attacks/ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf">
          <span class="button-view-path-label">GET STARTED</span></a>
      </div>
    </div>
  </div>
  <div class="progress-cards theme-navy-9">
    <div class="progress-cards-content">
      <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
      <p class="font-size-16"><h5>Authentication vulnerabilities</h5></p>
      <p class="font-size-14">Authentication vulnerabilities learning path.</p>
      <div class="progress-cards-content-buttons ">
        <a class="chevron-after no-wrap" href="/web-security/learning-paths/authentication-vulnerabilities">View path</a>
        <a class="button-view-path button-outline-small no-wrap" href="/web-security/learning-paths/authentication-vulnerabilities/what-is-authentication/authentication/what-is-authentication">
          <span class="button-view-path-label">GET STARTED</span></a>
      </div>
    </div>
  </div>
</div></div>
"""

# Resync fixture: only the SSRF path is still on the index (the auth path was
# removed from the site) and a NEW path (Clickjacking) appeared.
RESYNC_WIDGET_HTML = """
<div class="section-full-width"><div class="container-columns">
  <div class="progress-cards theme-navy-9">
    <div class="progress-cards-content">
      <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
      <p class="font-size-16"><h5>Server-side request forgery (SSRF) attacks</h5></p>
      <div class="progress-cards-content-buttons ">
        <a class="chevron-after no-wrap" href="/web-security/learning-paths/ssrf-attacks">View path</a>
        <a class="button-view-path button-outline-small no-wrap" href="/web-security/learning-paths/ssrf-attacks/ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf">
          <span class="button-view-path-label">GET STARTED</span></a>
      </div>
    </div>
  </div>
  <div class="progress-cards theme-navy-9">
    <div class="progress-cards-content">
      <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
      <p class="font-size-16"><h5>Clickjacking (UI redressing)</h5></p>
      <div class="progress-cards-content-buttons ">
        <a class="chevron-after no-wrap" href="/web-security/learning-paths/clickjacking">View path</a>
        <a class="button-view-path button-outline-small no-wrap" href="/web-security/learning-paths/clickjacking/what-is-clickjacking/clickjacking/what-is-clickjacking">
          <span class="button-view-path-label">GET STARTED</span></a>
      </div>
    </div>
  </div>
</div></div>
"""

PATH_HTML = f"""
<div class="learning-path-summary">
  <div class="learning-path-summary-header">
    <h3 class="heading-orange-1">Get started: What is SSRF?</h3>
    <p><span class="margin-left-small heading-navy-1">0 of 23</span></p>
  </div>
  <a class="button-orange margin-bottom-medium" href="{RESOURCE_URL}">GET STARTED</a>
</div>
<div class="expandable-progress-wrapper">
  <details class="expandable-progress-container" open>
    <summary class="expandable-progress-container-summary"><p><strong>What is SSRF?</strong></p></summary>
    <div class="content">
      <div class="expandable-progress-container-item progress-item-link">
        <p class="progress-status-circle">What is SSRF?<a class="chevron-after margin-left-tiny" href="{RESOURCE_URL}">Get started</a></p>
      </div>
    </div>
  </details>
</div>
"""

CLICKJACKING_PATH_URL = "https://portswigger.net/web-security/learning-paths/clickjacking"


@pytest.fixture(autouse=True)
def _offline_fixtures(monkeypatch):
    from app.services.kb import learning_planner as lp

    monkeypatch.setattr(lp, "ai_available", lambda: False)
    state = {"widget_html": WIDGET_HTML}

    def fake_fetch(url: str, include_body: bool = True, cookies: dict | None = None):
        base = {
            "requested_url": url,
            "final_url": url,
            "status_code": 200,
            "redirect_chain": [],
            "html": None,
            "text": None,
            "error": None,
            "crawl_status": "crawled",
        }
        if url == INDEX_URL:
            base["html"] = INDEX_HTML
            base["text"] = "Web Security Academy Learning Paths"
            return base
        if url in (SSRF_PATH_URL, AUTH_PATH_URL, CLICKJACKING_PATH_URL):
            base["html"] = PATH_HTML
            base["text"] = "Server-side request forgery contents"
            return base
        if "/learning-paths/" in url:
            base["crawl_status"] = "auth_required"
            base["final_url"] = "https://login.portswigger.net/u/login"
            base["error"] = "Page requires authentication (redirected to sign-in)"
            return base
        base["html"] = "<html><body><h1>Generic</h1><p>content</p></body></html>"
        base["text"] = "Generic content"
        return base

    monkeypatch.setattr(sc, "fetch_verified", fake_fetch)
    monkeypatch.setattr(
        sc,
        "_ps_fetch_widgets",
        lambda netloc, page_path, widget_ids: state["widget_html"],
    )
    return state


def _signup(client, uname="wf-user", email="wf@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "WF User", "username": uname, "email": email, "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {AUTH: f"Bearer {token}"}


def _create_plan(client, token):
    resp = client.post(
        "/api/kb/learning-plans",
        json={
            "goal": "Become proficient in Web Security",
            "resources": [{"label": "PortSwigger Academy", "url": INDEX_URL}],
            "known": ["XSS"],
            "unknown": ["SSRF"],
        },
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["plan"]


# ---------------------------------------------------------------------------
# Workflow 1 — Study-Session Loop
# ---------------------------------------------------------------------------


class TestStudySessionLoop:
    def test_state_is_read_only_and_empty_before_start(self, client):
        token = _signup(client)
        plan = _create_plan(client, token)
        resp = client.get(f"/api/kb/learning-plans/{plan['id']}/session", headers=_auth(token))
        assert resp.status_code == 200
        state = resp.json()["session"]
        assert state["live_session"] is None
        assert state["next_task"] is not None  # deterministic roadmap generated
        assert state["progress"]["total_tasks"] == plan["stats"]["total_tasks"]
        assert state["completed"] is False
        # No rows were created by the read.
        from app.database import SessionLocal
        from app.models import MicroSession

        with SessionLocal() as db:
            assert db.query(MicroSession).count() == 0

    def test_start_opens_session_on_next_task(self, client, db_session):
        token = _signup(client)
        plan = _create_plan(client, token)
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        session = resp.json()["session"]
        assert session["status"] == "started"
        assert session["learning_plan_id"] == plan["id"]
        assert session["learning_task_id"] == plan["next_task"]["id"]
        assert session["practice_task"] == plan["next_task"]["title"]

        # Row persisted, linked to the task.
        row = db_session.get(MicroSession, session["id"])
        assert row is not None
        assert row.learning_task_id == plan["next_task"]["id"]

        # Starting again while one is live → honest 400 (no dupes).
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        assert "already in progress" in resp.json()["detail"]

    def test_complete_marks_task_done_and_recommends_next(self, client, db_session):
        token = _signup(client)
        plan = _create_plan(client, token)
        first = plan["next_task"]
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={},
            headers=_auth(token),
        )
        session_id = resp.json()["session"]["id"]

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/{session_id}/complete",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["task_completed"] is True
        assert body["session"]["status"] == "done"
        assert body["progress"]["done_tasks"] == 1

        task = db_session.get(LearningTask, first["id"])
        assert task.done is True
        # The next task is a different, incomplete one.
        assert body["next_task"] is not None
        assert body["next_task"]["id"] != first["id"]

    def test_complete_updates_plan_dict_progress(self, client):
        token = _signup(client)
        plan = _create_plan(client, token)
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={},
            headers=_auth(token),
        )
        session_id = resp.json()["session"]["id"]
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/{session_id}/complete",
            headers=_auth(token),
        )
        # The canonical plan payload reflects the completed task.
        resp = client.get(f"/api/kb/learning-plans/{plan['id']}", headers=_auth(token))
        got = resp.json()["plan"]
        assert got["stats"]["done_tasks"] == 1

    def test_complete_when_nothing_started_is_honest(self, client):
        token = _signup(client)
        plan = _create_plan(client, token)
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/99999/complete",
            headers=_auth(token),
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Workflow 2 — Vault Health Audit
# ---------------------------------------------------------------------------


class TestVaultHealthAudit:
    def test_audit_is_read_only_and_aggregates(self, client):
        token = _signup(client)
        resp = client.get("/api/kb/health-audit", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "sections" in body
        assert body["counts"]["missing_notes"] == 0  # empty vault → empty sections
        assert body["counts"]["duplicates"] == 0
        assert body["health"]["score"] is not None
        assert body["health"]["document_count"] >= 0

    def test_dismiss_missing_is_explicit_and_persistent(self, client, db_session):
        token = _signup(client)
        user = db_session.query(__import__("app.models", fromlist=["User"]).User).filter(
            __import__("app.models", fromlist=["User"]).User.username == "wf-user"
        ).first()

        # Seed a missing-note suggestion directly (the suggestion engine needs
        # topics/concepts — too heavy to arrange through HTTP in this test).
        suggestion = MissingNoteSuggestion(
            user_id=user.id, concept_id=None, reason="You study X but have no note.",
            outline_template=json.dumps(["# X"]), linked_material_ids="[]", status="suggested",
        )
        db_session.add(suggestion)
        db_session.commit()

        resp = client.get("/api/kb/health-audit", headers=_auth(token))
        assert any(s["id"] == suggestion.id for s in resp.json()["sections"]["missing_notes"])

        resp = client.post(
            f"/api/kb/health-audit/missing/{suggestion.id}/dismiss", headers=_auth(token)
        )
        assert resp.status_code == 200
        db_session.refresh(suggestion)
        assert suggestion.status == "dismissed"

    def test_resolve_outdated_and_archive_duplicate(self, client, db_session):
        token = _signup(client)
        user = db_session.query(__import__("app.models", fromlist=["User"]).User).filter(
            __import__("app.models", fromlist=["User"]).User.username == "wf-user"
        ).first()

        doc = KbDocument(user_id=user.id, title="Legacy note", doc_type="md", status="unchanged",
                         extracted_text="old", char_count=4)
        db_session.add(doc)
        db_session.flush()
        outdated = OutdatedNote(user_id=user.id, document_id=doc.id, reason="stale",
                                evidence_json="{}")
        db_session.add(outdated)
        db_session.commit()

        resp = client.post(
            f"/api/kb/health-audit/outdated/{outdated.id}/resolve",
            json={"action": "dismissed"},
            headers=_auth(token),
        )
        assert resp.status_code == 200
        db_session.refresh(outdated)
        assert outdated.status == "dismissed"

        # Archive the document as a duplicate via the audit action.
        resp = client.post(f"/api/kb/health-audit/duplicates/{doc.id}/archive", headers=_auth(token))
        assert resp.status_code == 200
        db_session.refresh(doc)
        assert doc.status == "archived"

    def test_rescan_is_explicit(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/health-audit/rescan", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        assert resp.json()["health_score"] is not None


# ---------------------------------------------------------------------------
# Workflow 3 — Plan Re-sync
# ---------------------------------------------------------------------------


class TestPlanResync:
    def test_resync_adds_new_paths_and_flags_removed(self, client, db_session, _offline_fixtures):
        token = _signup(client)
        plan = _create_plan(client, token)
        assert db_session.query(LearningPath).filter(LearningPath.plan_id == plan["id"]).count() == 2

        # The site changed: auth path removed, clickjacking added.
        _offline_fixtures["widget_html"] = RESYNC_WIDGET_HTML

        resp = client.post(f"/api/kb/learning-plans/{plan['id']}/resync", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        report = resp.json()["resync"]
        assert report["urls_checked"] == 1
        added = {p["source_url"] for p in report["paths_added"]}
        assert CLICKJACKING_PATH_URL in added
        removed = {p["source_url"] for p in report["paths_removed"]}
        assert AUTH_PATH_URL in removed

        # Persisted: new path exists, removed one flagged — row kept (task refs
        # survive), roadmap untouched (no new tasks, no task mutations).
        paths = db_session.query(LearningPath).filter(LearningPath.plan_id == plan["id"]).all()
        by_url = {p.source_url: p for p in paths}
        assert CLICKJACKING_PATH_URL in by_url
        assert by_url[AUTH_PATH_URL].crawl_status == "removed"
        assert db_session.query(LearningTask).filter(LearningTask.plan_id == plan["id"]).count() == plan["stats"]["total_tasks"]

        # The plan payload now lists 3 paths (added kept, removed flagged).
        got = resp.json()["plan"]
        assert len(got["source"]["paths"]) == 3
        removed_path = next(p for p in got["source"]["paths"] if p["source_url"] == AUTH_PATH_URL)
        assert removed_path["crawl_status"] == "removed"

    def test_resync_is_idempotent(self, client, db_session, _offline_fixtures):
        token = _signup(client)
        plan = _create_plan(client, token)
        _offline_fixtures["widget_html"] = RESYNC_WIDGET_HTML
        client.post(f"/api/kb/learning-plans/{plan['id']}/resync", headers=_auth(token))
        resp = client.post(f"/api/kb/learning-plans/{plan['id']}/resync", headers=_auth(token))
        assert resp.status_code == 200
        # No duplicate path rows for the same source URL.
        count = (
            db_session.query(LearningPath)
            .filter(LearningPath.plan_id == plan["id"], LearningPath.source_url == CLICKJACKING_PATH_URL)
            .count()
        )
        assert count == 1

    def test_resync_requires_stored_url(self, client, db_session):
        token = _signup(client)
        user = db_session.query(__import__("app.models", fromlist=["User"]).User).filter(
            __import__("app.models", fromlist=["User"]).User.username == "wf-user"
        ).first()
        plan = LearningPlan(user_id=user.id, goal="no sources", status="draft")
        db_session.add(plan)
        db_session.commit()
        resp = client.post(f"/api/kb/learning-plans/{plan.id}/resync", headers=_auth(token))
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Workflow 4 — Focus/Readiness Loop
# ---------------------------------------------------------------------------


class TestFocusLoop:
    def test_focus_board_is_read_only(self, client, db_session):
        token = _signup(client)
        resp = client.get("/api/kb/focus", headers=_auth(token))
        assert resp.status_code == 200
        body = resp.json()
        assert "subjects" in body
        assert "recommendations" in body
        assert body["total_subjects"] >= 0
        # Read-only: no sessions created by the GET.
        assert db_session.query(MicroSession).count() == 0

    def test_focus_board_lists_at_risk_and_exam_approaching(self, client):
        token = _signup(client)
        resp = client.get("/api/kb/focus", headers=_auth(token))
        body = resp.json()
        assert "at_risk_count" in body
        assert "exam_approaching" in body
        # Deterministic shape: subject rows carry readiness fields.
        for s in body["subjects"]:
            assert "readiness" in s and "at_risk" in s

    def test_start_focus_session_reuses_micro_session(self, client, db_session):
        token = _signup(client)
        # No curriculum topics in the seeded test DB → board is empty, so seed
        # one topic directly and start a session on it.
        topic = _seed_topic(db_session, token)
        resp = client.post(
            "/api/kb/focus/start",
            json={"topic_id": topic.id, "duration_mins": 25},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        session = resp.json()["session"]
        assert session["status"] == "started"
        assert session["topic_id"] == topic.id
        assert session["duration_mins"] == 25

    def test_start_focus_session_404_on_unknown_topic(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/focus/start", json={"topic_id": 99999}, headers=_auth(token))
        assert resp.status_code == 404


def _seed_topic(db_session, token):
    from app.models import CurriculumSubject, Topic, TopicDependency

    user = db_session.query(__import__("app.models", fromlist=["User"]).User).filter(
        __import__("app.models", fromlist=["User"]).User.username == "wf-user"
    ).first()
    subject = CurriculumSubject(program_id=1, name="Focus Subject", code="FS", semester=1, credits=3)
    db_session.add(subject)
    db_session.flush()
    topic = Topic(
        user_id=user.id,
        subject_id=subject.id,
        name="Test Topic",
        normalized_name="test topic",
        status="pending",
    )
    db_session.add(topic)
    db_session.commit()
    db_session.refresh(topic)
    return topic
