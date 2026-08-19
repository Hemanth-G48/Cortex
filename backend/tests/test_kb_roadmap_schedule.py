"""Roadmap → Study Schedule tests.

Covers ``roadmap_schedule`` (the day-by-day scheduling service) through the
HTTP API: the four deterministic modes, the ``ai_instruction`` fallback when
AI is unavailable, the stale fingerprint, read-only GET re-rolling done state,
DELETE, and ``session/start`` with an explicit ``task_id`` (scheduled-day
start).

The network is fully mocked exactly like ``test_kb_learning_plans.py``: the
real parsers run end-to-end against PortSwigger-shaped fixtures.
"""

from __future__ import annotations

import json

import pytest

from app.models import LearningPlan, LearningTask
from app.services.kb import source_crawler as sc

AUTH = "Authorization"

INDEX_URL = "https://portswigger.net/web-security/learning-paths"
SSRF_PATH_URL = "https://portswigger.net/web-security/learning-paths/ssrf-attacks"
RESOURCE_URL = (
    "https://portswigger.net/web-security/learning-paths/ssrf-attacks/"
    "ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf"
)

INDEX_HTML = (
    '<html><body><div class="wrapper"><h1>Web Security Academy Learning Paths</h1>'
    '<div widget-id="academy-available-learning-paths"></div></div></body></html>'
)

WIDGET_HTML = """
<div class="section-full-width"><h2>All learning paths</h2><div class="container-columns">
  <div class="progress-cards theme-navy-9">
    <div class="progress-cards-content">
      <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
      <p class="font-size-16"><h5>Server-side request forgery (SSRF) attacks</h5></p>
      <p class="font-size-14">This learning path covers SSRF vulnerabilities.</p>
      <hr class="margin-top-small">
      <div class="progress-cards-content-buttons ">
        <a class="chevron-after no-wrap" href="/web-security/learning-paths/ssrf-attacks">View path</a>
        <a class="button-view-path button-outline-small no-wrap" href="/web-security/learning-paths/ssrf-attacks/ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf">
          <span class="button-view-path-label">GET STARTED</span><span class="icon-arrow2-right"></span></a>
      </div>
    </div>
  </div>
  <div class="progress-cards theme-navy-9">
    <div class="progress-cards-content">
      <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
      <p class="font-size-16"><h5>Authentication vulnerabilities</h5></p>
      <p class="font-size-14">Authentication vulnerabilities learning path.</p>
      <hr class="margin-top-small">
      <div class="progress-cards-content-buttons ">
        <a class="chevron-after no-wrap" href="/web-security/learning-paths/authentication-vulnerabilities">View path</a>
        <a class="button-view-path button-outline-small no-wrap" href="/web-security/learning-paths/authentication-vulnerabilities/what-is-authentication/authentication/what-is-authentication">
          <span class="button-view-path-label">GET STARTED</span><span class="icon-arrow2-right"></span></a>
      </div>
    </div>
  </div>
</div></div>
"""

PATH_HTML = f"""
<div class="learning-path-summary">
  <h2 class="heading-navy-1">Contents</h2>
  <div class="learning-path-summary-content">
    <div class="learning-path-summary-header">
      <h3 class="heading-orange-1">Get started: What is SSRF?</h3>
      <p><svg height="11"></svg><span class="margin-left-small heading-navy-1">0 of 23</span></p>
    </div>
    <a class="button-orange margin-bottom-medium" href="{RESOURCE_URL}">GET STARTED <span class="icon-arrow-right margin-left-tiny"></span></a>
  </div>
  <hr class="custom-hr"/>
</div>
<div class="expandable-progress-wrapper">
  <details class="expandable-progress-container progress-status-in-progress" open>
    <hr>
    <summary class="expandable-progress-container-summary"><p><strong>What is SSRF?</strong><span></span><span class="expandable-progress-container-summary-amount">0 of 1</span></p></summary>
    <hr>
    <div class="content">
      <div class="expandable-progress-container-item progress-item-link">
        <p class="progress-status-circle">What is SSRF?<span class="label theme-dastardly margin-left-tiny">APPRENTICE</span><a class="chevron-after margin-left-tiny" href="{RESOURCE_URL}">Get started</a></p>
      </div>
    </div>
  </details>
  <details class="expandable-progress-container">
    <hr>
    <summary class="expandable-progress-container-summary"><p><strong>Common SSRF attacks</strong><span></span><span class="expandable-progress-container-summary-amount">0 of 3</span></p></summary>
    <hr>
    <div class="content">
      <div class="expandable-progress-container-item progress-item-link"><p class="progress-status-circle">Common SSRF attacks<span class="label theme-dastardly margin-left-tiny">APPRENTICE</span></p></div>
      <div class="expandable-progress-container-item progress-item-link"><p class="progress-status-circle">Lab: Basic SSRF against the local server<span class="label theme-dastardly margin-left-tiny">APPRENTICE</span></p></div>
    </div>
  </details>
</div>
"""


@pytest.fixture(autouse=True)
def _offline_fixtures(monkeypatch):
    """Patch every network seam; serve real-structure fixtures via the real parsers."""
    from app.services.kb import learning_planner as lp
    from app.services.kb import roadmap_schedule as rs

    monkeypatch.setattr(lp, "ai_available", lambda: False)
    monkeypatch.setattr(rs, "ai_available", lambda: False)

    def fake_fetch(url: str, include_body: bool = True, cookies: dict | None = None):
        base = {
            "requested_url": url,
            "final_url": url,
            "status_code": 200,
            "redirect_chain": [],
            "html": None,
            "text": None,
            "error": None,
        }
        if url == INDEX_URL:
            base["html"] = INDEX_HTML
            base["text"] = "Web Security Academy Learning Paths"
            base["crawl_status"] = "crawled"
            return base
        if url == SSRF_PATH_URL:
            base["html"] = PATH_HTML
            base["text"] = "Server-side request forgery contents"
            base["crawl_status"] = "crawled"
            return base
        if "/learning-paths/" in url:
            if cookies:
                base["html"] = "<html><body><h1>real content behind the wall</h1></body></html>"
                base["text"] = "real content behind the wall"
                base["crawl_status"] = "crawled"
                return base
            base["crawl_status"] = "auth_required"
            base["final_url"] = "https://login.portswigger.net/u/login"
            base["error"] = "Page requires authentication (redirected to sign-in)"
            return base
        base["html"] = "<html><body><h1>Generic</h1></body></html>"
        base["text"] = "Generic page"
        base["crawl_status"] = "crawled"
        return base

    monkeypatch.setattr(sc, "fetch_verified", fake_fetch)
    monkeypatch.setattr(sc, "_ps_fetch_widgets", lambda netloc, page_path, widget_ids: WIDGET_HTML)


def _signup(client, uname="rs-user", email="rs@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "RS User", "username": uname, "email": email, "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _auth(token):
    return {AUTH: f"Bearer {token}"}


def _body(**overrides):
    return {
        "goal": "Become proficient in Web Security",
        "resources": [{"label": "PortSwigger Academy", "url": INDEX_URL}],
        "known": ["XSS"],
        "unknown": ["SSRF"],
        **overrides,
    }


def _generated_plan(client, token):
    """One-shot create → a generated plan with roadmap tasks."""
    resp = client.post("/api/kb/learning-plans", json=_body(), headers=_auth(token))
    assert resp.status_code == 200, resp.text
    plan = resp.json()["plan"]
    assert plan["status"] == "generated"
    assert plan["tasks"], "expected roadmap tasks"
    return plan


class TestScheduleModes:
    def test_daily_hours_packs_tasks_within_budget(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert s["engine"] == "deterministic"
        assert s["mode"] == "daily_hours"
        assert s["days"]
        # Every scheduled task is a REAL roadmap task.
        task_ids = [t["task_id"] for d in s["days"] for t in d["tasks"]]
        plan_ids = {t["id"] for t in plan["tasks"]}
        assert set(task_ids) == plan_ids  # every task scheduled exactly once
        # Each day respects the per-day budget (hour cap + safety max).
        assert all(d["total_minutes"] <= 60 + 60 for d in s["days"])
        assert all(len(d["tasks"]) <= 12 for d in s["days"])
        # Stats tie out.
        assert s["stats"]["tasks_scheduled"] == len(plan_ids)
        assert s["stats"]["days"] == len(s["days"])

    def test_modules_per_day_caps_task_count(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "modules_per_day", "modules_per_day": 2},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert all(len(d["tasks"]) <= 2 for d in s["days"])

    def test_hybrid_respects_both_constraints(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "hybrid", "daily_hours": 0.5, "modules_per_day": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert all(len(d["tasks"]) <= 1 for d in s["days"])
        assert all(d["total_minutes"] <= 30 + 30 for d in s["days"])

    def test_time_slots_require_valid_slots(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)

        # Invalid slot → honest 400, not a silently unconstrained plan.
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "time_slots", "time_slots": ["not-a-slot"]},
            headers=_auth(token),
        )
        assert resp.status_code == 400

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "time_slots", "time_slots": ["07:00-08:00", "20:00-21:00"]},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert s["params"]["time_slots"] == ["07:00-08:00", "20:00-21:00"]
        # Budget = the slot total (2h).
        assert s["params"]["budget_minutes"] == 120
        assert all(d["total_minutes"] <= 120 + 60 for d in s["days"])

    def test_ai_instruction_falls_back_to_deterministic_when_ai_off(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)

        # ai_available is False under pytest → deterministic fallback, honest label.
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "ai_instruction", "instruction": "1 hour every morning at 7am"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert s["engine"] == "deterministic"
        assert s["days"]
        assert s["params"]["instruction"] == "1 hour every morning at 7am"

    def test_unknown_mode_defaults_to_daily_hours(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "bogus_mode"},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["schedule"]["mode"] == "daily_hours"


class TestScheduleLifecycle:
    def test_schedule_is_persisted_and_readable_without_llm(self, client, db_session):
        """POST stores it; GET returns it read-only (never regenerates)."""
        token = _signup(client)
        plan = _generated_plan(client, token)
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.5},
            headers=_auth(token),
        )

        resp = client.get(f"/api/kb/learning-plans/{plan['id']}/schedule", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert s["plan_id"] == plan["id"]
        assert s["stats"]["days"] > 0
        assert s["stale"] is False

        # Persisted on the row, not recomputed.
        row = db_session.query(LearningPlan).filter(LearningPlan.id == plan["id"]).first()
        stored = json.loads(row.schedule_json)
        assert stored["goal"] == plan["goal"]

    def test_progress_change_marks_schedule_stale(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        first = plan["tasks"][0]
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/tasks/{first['id']}/toggle",
            json={"done": True},
            headers=_auth(token),
        )

        resp = client.get(f"/api/kb/learning-plans/{plan['id']}/schedule", headers=_auth(token))
        s = resp.json()["schedule"]
        assert s["stale"] is True
        # The toggled task shows done in the schedule without regenerating.
        marked = [t for d in s["days"] for t in d["tasks"] if t["task_id"] == first["id"]]
        assert marked and all(m["done"] for m in marked)
        # Completed tasks are skipped from remaining counts.
        assert s["stats"]["done_tasks"] == 1

    def test_delete_clears_schedule(self, client, db_session):
        token = _signup(client)
        plan = _generated_plan(client, token)
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        resp = client.delete(f"/api/kb/learning-plans/{plan['id']}/schedule", headers=_auth(token))
        assert resp.status_code == 200
        resp = client.get(f"/api/kb/learning-plans/{plan['id']}/schedule", headers=_auth(token))
        assert resp.json()["schedule"] is None
        row = db_session.query(LearningPlan).filter(LearningPlan.id == plan["id"]).first()
        assert row.schedule_json is None

    def test_schedule_requires_roadmap_tasks(self, client):
        """A discovered-only plan (no tasks) cannot be scheduled — honest 400."""
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]
        resp = client.post(
            f"/api/kb/learning-plans/{plan_id}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    def test_partial_progress_at_build_time_counts_remaining_correctly(self, client):
        """Schedule built when some tasks are ALREADY done: remaining counts
        only the not-done scheduled tasks (done tasks are skipped, never
        subtracted from the scheduled total)."""
        token = _signup(client)
        plan = _generated_plan(client, token)
        # Complete the first task BEFORE building the schedule.
        first = plan["tasks"][0]
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/tasks/{first['id']}/toggle",
            json={"done": True},
            headers=_auth(token),
        )
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert s["stats"]["done_tasks"] == 1  # skipped, reported
        scheduled_ids = [t["task_id"] for d in s["days"] for t in d["tasks"]]
        assert first["id"] not in scheduled_ids  # completed task is not scheduled
        # Every scheduled task is still to do.
        assert s["stats"]["remaining_tasks"] == len(scheduled_ids)
        assert s["stats"]["remaining_tasks"] == s["stats"]["tasks_scheduled"]

        # After completing one scheduled task, remaining drops by exactly one.
        second = plan["tasks"][1]
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/tasks/{second['id']}/toggle",
            json={"done": True},
            headers=_auth(token),
        )
        resp = client.get(f"/api/kb/learning-plans/{plan['id']}/schedule", headers=_auth(token))
        s2 = resp.json()["schedule"]
        assert s2["stats"]["remaining_tasks"] == max(0, len(scheduled_ids) - 1)

    def test_all_tasks_done_returns_finished_schedule(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)
        for t in plan["tasks"]:
            client.post(
                f"/api/kb/learning-plans/{plan['id']}/tasks/{t['id']}/toggle",
                json={"done": True},
                headers=_auth(token),
            )
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        s = resp.json()["schedule"]
        assert s["stats"]["days"] == 0
        assert s["days"] == []
        assert s["note"]  # finished message, not an error


class TestScheduleTaskSession:
    def test_session_start_on_scheduled_task_id(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/schedule",
            json={"mode": "daily_hours", "daily_hours": 1.0},
            headers=_auth(token),
        )
        # First task of the first scheduled day.
        resp = client.get(f"/api/kb/learning-plans/{plan['id']}/schedule", headers=_auth(token))
        day_task = resp.json()["schedule"]["days"][0]["tasks"][0]

        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={"task_id": day_task["task_id"]},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        state = resp.json()["state"]
        assert state["live_session"]["practice_task"] == day_task["title"]

    def test_session_start_rejects_done_or_foreign_task(self, client):
        token = _signup(client)
        plan = _generated_plan(client, token)
        first = plan["tasks"][0]
        client.post(
            f"/api/kb/learning-plans/{plan['id']}/tasks/{first['id']}/toggle",
            json={"done": True},
            headers=_auth(token),
        )
        # Completed task → 400.
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={"task_id": first["id"]},
            headers=_auth(token),
        )
        assert resp.status_code == 400
        # Foreign task id → 400.
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={"task_id": 999999},
            headers=_auth(token),
        )
        assert resp.status_code == 400

    def test_session_start_supports_task_that_becomes_next(self, client, db_session):
        """A scheduled task the AI/plan didn't pick as global-next is startable."""
        token = _signup(client)
        plan = _generated_plan(client, token)
        # Use the LAST roadmap task explicitly.
        last = plan["tasks"][-1]
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/session/start",
            json={"task_id": last["id"]},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["state"]["live_session"]["practice_task"] == last["title"]
