"""Learning Path Planner tests.

The network is fully mocked: ``source_crawler.fetch_verified`` serves
PortSwigger-shaped HTML fixtures and ``source_crawler._ps_fetch_widgets``
serves the widget-payload fixture, so the REAL parsers run end-to-end without
any HTTP. ``ai_available`` is off under pytest, so every roadmap exercises the
deterministic Layer-2 fallback — which must reference ONLY real discovered
resources (never invented ones).
"""

from __future__ import annotations

import json

import pytest

from app.models import (
    LearningDependency,
    LearningPath,
    LearningPathResource,
    LearningPlan,
    LearningResource,
    LearningTask,
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

GENERIC_HTML = (
    "<html><body><h1>OWASP Juice Shop</h1><p>A deliberately insecure web application "
    "for security training with realistic vulnerabilities.</p></body></html>"
)


@pytest.fixture(autouse=True)
def _offline_fixtures(monkeypatch):
    """Patch every network seam; serve real-structure fixtures via the real parsers."""
    from app.services.kb import learning_planner as lp

    monkeypatch.setattr(lp, "ai_available", lambda: False)

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
        if url == SSRF_PATH_URL or url == AUTH_PATH_URL:
            base["html"] = PATH_HTML
            base["text"] = "Server-side request forgery contents"
            base["crawl_status"] = "crawled"
            return base
        if "/learning-paths/" in url:
            if cookies:
                # With a live session the auth-gated URL resolves to real content.
                base["html"] = "<html><body><h1>" + url.split("/")[-1] + "</h1><p>real content behind the wall</p></body></html>"
                base["text"] = "real content behind the wall"
                base["crawl_status"] = "crawled"
                return base
            # Deep resource URLs are auth-gated on PortSwigger (200 → sign-in).
            base["crawl_status"] = "auth_required"
            base["final_url"] = "https://login.portswigger.net/u/login"
            base["error"] = "Page requires authentication (redirected to sign-in)"
            return base
        base["html"] = GENERIC_HTML
        base["text"] = "OWASP Juice Shop a deliberately insecure web application"
        base["crawl_status"] = "crawled"
        return base

    monkeypatch.setattr(sc, "fetch_verified", fake_fetch)
    monkeypatch.setattr(sc, "_ps_fetch_widgets", lambda netloc, page_path, widget_ids: WIDGET_HTML)


def _signup(client, uname="lp-user", email="lp@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "LP User", "username": uname, "email": email, "password": "pass123", "role": "student"},
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


class TestLayer1Discovery:
    def test_discover_persists_real_paths_and_resources(self, client, db_session):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        assert resp.status_code == 200, resp.text
        plan = resp.json()["plan"]

        # Layer 1 only: status is "discovered", no roadmap/tasks yet.
        assert plan["status"] == "discovered"
        assert plan["tasks"] == []
        assert plan["stats"]["total_tasks"] == 0

        # Report is honest: 2 real paths discovered and crawled.
        report = plan["source"]["report"]
        assert report["platform"] == "PortSwigger Web Security Academy"
        assert report["paths_discovered"] == 2
        assert report["paths_crawled"] == 2
        assert report["resources_extracted"] >= 3

        # Every path carries the EXACT URL discovered from the site.
        urls = {p["source_url"] for p in plan["source"]["paths"]}
        assert urls == {SSRF_PATH_URL, AUTH_PATH_URL}

        # Resources: titles + labs from the path page; the public page exposes
        # only the first resource URL — the rest stay URL-less (never guessed).
        ssrf = next(p for p in plan["source"]["paths"] if p["title"].startswith("Server-side"))
        assert ssrf["resource_total"] == 23
        titles = {r["title"] for r in ssrf["resources"]}
        assert "What is SSRF?" in titles
        assert "Lab: Basic SSRF against the local server" in titles
        with_url = [r for r in ssrf["resources"] if r["url"]]
        assert len(with_url) == 1
        assert with_url[0]["url"] == RESOURCE_URL
        # The exposed URL was fetched and bounced to sign-in → honest status.
        assert with_url[0]["crawl_status"] == "auth_required"
        # Everything without a URL stays "discovered" — not faked.
        no_url = [r for r in ssrf["resources"] if not r["url"]]
        assert all(r["crawl_status"] == "discovered" for r in no_url)

    def test_discovery_persists_rows_with_junction_dedup(self, client, db_session):
        token = _signup(client)
        client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = db_session.query(LearningPlan).order_by(LearningPlan.id.desc()).first().id

        paths = db_session.query(LearningPath).filter(LearningPath.plan_id == plan_id).all()
        resources = db_session.query(LearningResource).filter(LearningResource.plan_id == plan_id).all()
        assert len(paths) == 2
        assert len(resources) >= 3
        # Dedup: the resource URL (which appears in both fixture paths) is ONE
        # row, linked to both paths through the junction table.
        rows = db_session.query(LearningResource).filter(LearningResource.url == RESOURCE_URL).all()
        assert len(rows) == 1
        res = rows[0]
        assert res.crawl_status == "auth_required"
        links = (
            db_session.query(LearningPathResource)
            .filter(LearningPathResource.resource_id == res.id)
            .count()
        )
        assert links == 2  # appears in both paths — never duplicated as rows

    def test_complete_all_means_all(self, client, db_session):
        """Discovery never prunes paths to a 'curated' subset."""
        token = _signup(client)
        client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = db_session.query(LearningPlan).order_by(LearningPlan.id.desc()).first().id
        count = db_session.query(LearningPath).filter(LearningPath.plan_id == plan_id).count()
        assert count == 2  # every card on the index, not 5 chosen by AI


class TestLayer2Roadmap:
    def test_generate_after_discovery_references_real_resources(self, client, db_session):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]

        resp = client.post(f"/api/kb/learning-plans/{plan_id}/generate", json={}, headers=_auth(token))
        assert resp.status_code == 200, resp.text
        plan = resp.json()["plan"]
        assert plan["status"] == "generated"
        assert plan["engine"] == "deterministic"
        assert plan["stats"]["total_tasks"] >= 3

        # Every task references a REAL Layer-1 resource row.
        task_resource_ids = {t["resource_id"] for t in plan["tasks"]}
        assert task_resource_ids and all(isinstance(i, int) for i in task_resource_ids)
        for t in plan["tasks"]:
            # Task title derives from the real resource; source_crawled is only
            # True for actually-crawled resources (none here — honest).
            assert t["source_crawled"] is False
        # No invented URLs: every task resource_url is either the exact
        # discovered URL or None.
        for t in plan["tasks"]:
            if t["resource_url"]:
                assert t["resource_url"] in (RESOURCE_URL,) or "learning-paths" not in t["resource_url"]
        # Topics are built from real resource titles.
        assert plan["topics"]
        assert all(t["status"] in ("known", "partial", "unknown", "advanced_unknown") for t in plan["topics"])
        # Every resource carries topics/prerequisites arrays — the UI renders
        # these unconditionally (a missing field used to blank the page).
        assert plan["resources"]
        for r in plan["resources"]:
            assert isinstance(r.get("topics"), list)
            assert isinstance(r.get("prerequisites"), list)

    def test_legacy_payload_resources_are_normalized_on_read(self, client, db_session):
        """Stored plans generated before resources carried topics/prerequisites
        must still return complete resource dicts on GET (no blank page)."""
        from app.services.kb.learning_planner import plan_dict

        token = _signup(client)
        resp = client.post("/api/kb/learning-plans", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]
        plan = db_session.query(LearningPlan).filter(LearningPlan.id == plan_id).first()
        payload = json.loads(plan.plan_json)
        for r in payload.get("resources") or []:
            r.pop("topics", None)
            r.pop("prerequisites", None)
        plan.plan_json = json.dumps(payload)
        db_session.commit()

        out = plan_dict(db_session, plan)
        assert out["resources"]
        for r in out["resources"]:
            assert r["topics"] == []
            assert r["prerequisites"] == []

    def test_path_progress_rolls_up_from_task_toggles(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]
        resp = client.post(f"/api/kb/learning-plans/{plan_id}/generate", json={}, headers=_auth(token))
        plan = resp.json()["plan"]
        assert plan["path_progress"]
        assert sum(p["total_tasks"] for p in plan["path_progress"]) == plan["stats"]["total_tasks"]

        first = plan["tasks"][0]
        client.post(
            f"/api/kb/learning-plans/{plan_id}/tasks/{first['id']}/toggle",
            json={"done": True},
            headers=_auth(token),
        )
        resp = client.get(f"/api/kb/learning-plans/{plan_id}", headers=_auth(token))
        got = resp.json()["plan"]
        assert got["stats"]["done_tasks"] == 1
        # The path containing the toggled task advanced by one.
        owning = next(p for p in got["path_progress"] if p["path_id"] == first["path_id"])
        assert owning["done_tasks"] == 1

    def test_dependencies_are_labeled_ai_inferred(self, client, db_session):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]
        resp = client.post(f"/api/kb/learning-plans/{plan_id}/generate", json={}, headers=_auth(token))
        plan = resp.json()["plan"]
        assert plan["dependencies"]
        for d in plan["dependencies"]:
            assert d["source"] == "ai"
            assert d.get("note")  # "Recommended prerequisite" — never official
        rows = db_session.query(LearningDependency).filter(LearningDependency.plan_id == plan_id).all()
        assert len(rows) == len(plan["dependencies"])
        assert all(r.source == "ai" for r in rows)

    def test_one_shot_create_does_discovery_and_roadmap(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans", json=_body(), headers=_auth(token))
        assert resp.status_code == 200, resp.text
        plan = resp.json()["plan"]
        assert plan["status"] == "generated"
        assert plan["source"]["report"]["paths_discovered"] == 2
        assert plan["stats"]["total_tasks"] >= 3
        phases = plan["phases"]
        assert [p["phase"] for p in phases] == list(range(1, len(phases) + 1))

    def test_labs_land_in_practical_phase(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans", json=_body(), headers=_auth(token))
        plan = resp.json()["plan"]
        lab_tasks = [t for t in plan["tasks"] if t["resource_type"] == "lab"]
        assert lab_tasks
        assert all(t["phase"] == 4 for t in lab_tasks)


class TestMixedSubmissions:
    def test_index_url_and_plain_url_are_both_persisted(self, client):
        """Submitting a path index + a plain course URL keeps BOTH in Layer 1
        (the plain URL must not be silently dropped)."""
        token = _signup(client)
        resp = client.post(
            "/api/kb/learning-plans/discover",
            json=_body(
                resources=[
                    {"label": "PortSwigger Academy", "url": INDEX_URL},
                    {"label": "OWASP Juice Shop", "url": "https://owasp.org/www-project-juice-shop/"},
                ]
            ),
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        plan = resp.json()["plan"]
        assert plan["source"]["report"]["paths_discovered"] == 2  # PortSwigger paths
        # The plain URL became a generic resource row (honest crawled status).
        titles = {r["title"] for r in plan["source"]["paths"][0]["resources"]}
        assert any("OWASP Juice Shop" in t for t in titles) or len(plan["source"]["paths"]) >= 2
        all_resources = [r for p in plan["source"]["paths"] for r in p["resources"]]
        assert any(r["title"] == "OWASP Juice Shop" for r in all_resources)

    def test_generate_falls_back_to_stored_knowledge(self, client):
        """Building the roadmap later must not lose the knowledge declared at
        discovery time (known/unknown fall back to the plan's stored copy)."""
        token = _signup(client)
        resp = client.post(
            "/api/kb/learning-plans/discover",
            json=_body(known=["What is SSRF?"]),
            headers=_auth(token),
        )
        plan_id = resp.json()["plan"]["id"]
        # Empty body → backend falls back to the stored knowledge.
        resp = client.post(f"/api/kb/learning-plans/{plan_id}/generate", json={}, headers=_auth(token))
        assert resp.status_code == 200, resp.text
        plan = resp.json()["plan"]
        review_tasks = [t for t in plan["tasks"] if t["title"].startswith("Review (known)")]
        assert review_tasks, "declared knowledge should surface as review tasks"


class TestGenericAndHonest:
    def test_generic_site_fallback_marks_honest_status(self, client):
        token = _signup(client)
        resp = client.post(
            "/api/kb/learning-plans",
            json=_body(resources=[{"label": "OWASP Juice Shop", "url": "https://owasp.org/www-project-juice-shop/"}]),
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        plan = resp.json()["plan"]
        # No path index → the URL itself becomes a resource (crawled honestly).
        assert plan["source"]["report"]["paths_discovered"] == 0
        assert plan["resources"]
        # Deterministic plan from the generic resource; tasks reference it.
        assert plan["tasks"]
        assert all(t["resource_id"] for t in plan["tasks"])

    def test_create_plan_requires_goal_and_resources(self, client):
        token = _signup(client)
        resp = client.post(
            "/api/kb/learning-plans", json={"goal": "", "resources": [{"label": "x"}]}, headers=_auth(token)
        )
        assert resp.status_code in (400, 422)
        resp = client.post(
            "/api/kb/learning-plans", json={"goal": "G", "resources": []}, headers=_auth(token)
        )
        assert resp.status_code in (400, 422)

    def test_list_and_get_plan(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]

        resp = client.get("/api/kb/learning-plans", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(p["id"] == plan_id for p in items)
        # Summary carries the honest discovery counts for the list UI.
        item = next(p for p in items if p["id"] == plan_id)
        assert item["source"]["paths_discovered"] == 2

        resp = client.get(f"/api/kb/learning-plans/{plan_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["plan"]["id"] == plan_id

    def test_toggle_task_scoped_to_plan_and_user(self, client):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans", json=_body(), headers=_auth(token))
        plan = resp.json()["plan"]
        task_id = plan["tasks"][0]["id"]
        resp = client.post(
            f"/api/kb/learning-plans/9999/tasks/{task_id}/toggle",
            json={"done": True},
            headers=_auth(token),
        )
        assert resp.status_code == 404
        token2 = _signup(client, uname="lp-user2", email="lp2@test.com")
        resp = client.post(
            f"/api/kb/learning-plans/{plan['id']}/tasks/{task_id}/toggle",
            json={"done": True},
            headers=_auth(token2),
        )
        assert resp.status_code == 404

    def test_delete_plan_removes_tasks(self, client, db_session):
        token = _signup(client)
        resp = client.post("/api/kb/learning-plans", json=_body(), headers=_auth(token))
        plan_id = resp.json()["plan"]["id"]
        resp = client.delete(f"/api/kb/learning-plans/{plan_id}", headers=_auth(token))
        assert resp.status_code == 200
        assert db_session.query(LearningTask).filter(LearningTask.plan_id == plan_id).count() == 0
        assert db_session.query(LearningPath).filter(LearningPath.plan_id == plan_id).count() == 0
        resp = client.get(f"/api/kb/learning-plans/{plan_id}", headers=_auth(token))
        assert resp.status_code == 404


