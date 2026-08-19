"""PortSwigger sign-in session tests for the Learning Path Planner.

Covers the Auth0 single-POST login flow (driven against a fake httpx client),
the session endpoints (credentials never leaked), and the re-verify flow that
re-crawls a plan's paths behind the sign-in wall and honestly re-verifies the
previously gated resource URLs. Network is fully mocked.

``TestLivePortSwiggerLogin`` is opt-in and hits the REAL site in a real
headless browser (see the class docstring for how to enable it).
"""

from __future__ import annotations

import datetime
import os

import httpx
import pytest

from app.models import LearningResource, PortswiggerSession, User
from app.services.kb import portswigger_session as ps

AUTH = "Authorization"

INDEX_URL = "https://portswigger.net/web-security/learning-paths"
SSRF_PATH_URL = "https://portswigger.net/web-security/learning-paths/ssrf-attacks"
RESOURCE_URL = (
    "https://portswigger.net/web-security/learning-paths/ssrf-attacks/"
    "ssrf-attacks-what-is-ssrf/ssrf/what-is-ssrf"
)
COMMON_URL = (
    "https://portswigger.net/web-security/learning-paths/ssrf-attacks/"
    "ssrf-attacks-common-ssrf-attacks/ssrf/common-ssrf-attacks"
)
LAB_URL = (
    "https://portswigger.net/web-security/learning-paths/ssrf-attacks/"
    "ssrf-attacks-basic-ssrf-against-the-local-server/lab/basic-ssrf-against-the-local-server"
)

INDEX_HTML = (
    '<html><body><div class="wrapper"><h1>Web Security Academy Learning Paths</h1>'
    '<div widget-id="academy-available-learning-paths"></div></div></body></html>'
)

WIDGET_HTML = """
<div class="container-columns">
  <div class="progress-cards theme-navy-9"><div class="progress-cards-content">
    <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
    <p class="font-size-16"><h5>Server-side request forgery (SSRF) attacks</h5></p>
    <p class="font-size-14">This learning path covers SSRF vulnerabilities.</p>
    <div class="progress-cards-content-buttons ">
      <a class="chevron-after no-wrap" href="/web-security/learning-paths/ssrf-attacks">View path</a>
    </div>
  </div></div>
  <div class="progress-cards theme-navy-9"><div class="progress-cards-content">
    <div class="progress-cards-content-labels"><span class="label theme-enterprise-2">PRACTITIONER</span></div>
    <p class="font-size-16"><h5>Authentication vulnerabilities</h5></p>
    <div class="progress-cards-content-buttons ">
      <a class="chevron-after no-wrap" href="/web-security/learning-paths/authentication-vulnerabilities">View path</a>
    </div>
  </div></div>
</div>
"""

PATH_HTML = f"""
<div class="learning-path-summary"><div class="learning-path-summary-header">
  <h3 class="heading-orange-1">Get started: What is SSRF?</h3>
  <p><span class="margin-left-small heading-navy-1">0 of 23</span></p>
</div>
<a class="button-orange margin-bottom-medium" href="{RESOURCE_URL}">GET STARTED</a>
</div>
<div class="expandable-progress-wrapper">
  <details class="expandable-progress-container progress-status-in-progress" open>
    <summary class="expandable-progress-container-summary"><p><strong>What is SSRF?</strong></p></summary>
    <div class="content">
      <div class="expandable-progress-container-item progress-item-link">
        <p class="progress-status-circle">What is SSRF?<span class="label theme-dastardly margin-left-tiny">APPRENTICE</span><a class="chevron-after margin-left-tiny" href="{RESOURCE_URL}">Get started</a></p>
      </div>
    </div>
  </details>
  <details class="expandable-progress-container">
    <summary class="expandable-progress-container-summary"><p><strong>Common SSRF attacks</strong></p></summary>
    <div class="content">
      <div class="expandable-progress-container-item progress-item-link"><p class="progress-status-circle">Common SSRF attacks<span class="label theme-dastardly margin-left-tiny">APPRENTICE</span></p></div>
      <div class="expandable-progress-container-item progress-item-link"><p class="progress-status-circle">Lab: Basic SSRF against the local server<span class="label theme-dastardly margin-left-tiny">APPRENTICE</span></p></div>
    </div>
  </details>
</div>
"""


class _Resp:
    def __init__(
        self,
        text: str = "",
        url: str = "",
        history: list | None = None,
        status_code: int = 200,
    ):
        self.text = text
        self.url = url
        self.history = history or []
        self.status_code = status_code

    @property
    def status(self):
        # Playwright responses expose ``.status``; the fake uses
        # ``.status_code`` (httpx-style). Alias for realism.
        return self.status_code


class _Cookie:
    def __init__(self, name: str, value: str, domain: str, expires=None):
        self.name = name
        self.value = value
        self.domain = domain
        self.expires = expires


class _FakeCookies:
    """Mirrors ``httpx.Client.cookies`` (with its ``.jar``) for the login flow."""

    def __init__(self, *, no_cookies: bool = False):
        self.jar: list[_Cookie] = []
        self.no_cookies = no_cookies

    def add(self, name: str, value: str, domain: str):
        if self.no_cookies:
            return
        self.jar.append(_Cookie(name, value, domain))


class _FakeAuth0Client:
    """Scripted stand-in for ``httpx.Client`` implementing the single-POST
    Universal Login v2 flow plus the ``/users`` authentication gate used by
    ``_gate_verdict``/``_session_authenticated``.

    A successful submit marks the instance authenticated; the gate client is
    constructed with the collected cookies and mirrors what the real site
    does: a real session serves the account page, anything else bounces to
    the sign-in page.
    """

    def __init__(
        self,
        *,
        bad_creds: bool = False,
        no_cookies: bool = False,
        gate_fails: bool = False,
        resume_error: bool = False,
        cookies: dict | None = None,
        **kwargs,  # noqa: ARG002 — httpx.Client options ignored by the fake
    ):
        self.bad_creds = bad_creds
        self.no_cookies = no_cookies
        self.gate_fails = gate_fails
        self.resume_error = resume_error
        self.cookies = _FakeCookies(no_cookies=no_cookies)
        self.passed_cookies = cookies or {}
        self.authenticated = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url: str):
        # The /users authentication gate: a real session returns the account
        # page; anonymous/expired sessions bounce to the sign-in page.
        if url == "https://portswigger.net/users":
            if (self.authenticated or "portswigger-session" in self.passed_cookies) and not self.gate_fails:
                return _Resp(
                    text="<h1>My account</h1>",
                    url="https://portswigger.net/users",
                )
            return _Resp(
                text="<form>login shell</form>",
                url="https://login.portswigger.net/u/login?state=STATE-123",
            )
        if url.startswith("https://portswigger.net/users"):
            return _Resp(
                text="<form>login shell</form>",
                url="https://login.portswigger.net/u/login?state=STATE-123",
            )
        return _Resp(text="", url=url)

    def post(self, url: str, data: dict | None = None):
        if url.endswith("/u/login"):
            if self.bad_creds:
                return _Resp(
                    text="<div class=\"alert\">Wrong email or password</div>",
                    url="https://login.portswigger.net/u/login?state=STATE-123",
                    status_code=400,
                )
            if self.resume_error:
                # Auth0 reports the failure as hidden fields in the resume
                # form — this is what the real driver missed before.
                return _Resp(
                    text=(
                        '<form action="https://portswigger.net/signin-oidc">'
                        '<input type="hidden" name="error" value="invalid_request">'
                        '<input type="hidden" name="error_description" value="User identifier prompt skipped.">'
                        "</form>"
                    ),
                    url="https://login.portswigger.net/authorize/resume?state=X",
                )
            if not self.no_cookies:
                self.cookies.add("portswigger-session", "session-abc", "portswigger.net")
                self.authenticated = True
            return _Resp(
                text=(
                    '<form action="https://portswigger.net/signin-oidc">'
                    '<input type="hidden" name="code" value="abc">'
                    "</form>"
                ),
                url="https://login.portswigger.net/authorize/resume?state=STATE-123",
            )
        return _Resp(text="", url=url)


class _FakeLoginPage:
    """Minimal page stand-in for the browser-side helpers
    (``_wait_login_outcome``, ``_browser_session_authenticated``).

    ``url_script`` is a list of URLs: the first becomes the initial ``url``,
    and each ``wait_for_timeout`` advances to the next one (mirroring the
    poll loop). ``goto`` lands on the given URL — or on ``bounce_to`` when
    set (simulating an anonymous /users navigation that bounces to the
    sign-in page). ``goto_targets`` scripts successive ``goto`` calls (for
    the verification retry path).
    """

    def __init__(
        self,
        url_script: list[str],
        body: str = "",
        bounce_to: str | None = None,
        goto_targets: list[str] | None = None,
    ):
        self._script = list(url_script)
        self.url = self._script.pop(0) if self._script else ""
        self._body = body
        self._bounce_to = bounce_to
        self._goto_targets = list(goto_targets or [])

    def wait_for_timeout(self, _ms):
        if self._script:
            self.url = self._script.pop(0)

    def inner_text(self, _selector):
        return self._body

    def goto(self, url: str, **_kw):
        if self._goto_targets:
            self.url = self._goto_targets.pop(0)
        elif self._bounce_to is not None:
            self.url = self._bounce_to
        else:
            self.url = url
        return _Resp(text="", url=self.url, status_code=200)


@pytest.fixture(autouse=True)
def _offline_fixtures(monkeypatch):
    """Serve real-structure fixtures through the real parsers (no HTTP)."""
    from app.services.kb import learning_planner as lp
    from app.services.kb import source_crawler as sc

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
        elif url in (SSRF_PATH_URL, "https://portswigger.net/web-security/learning-paths/authentication-vulnerabilities"):
            base["html"] = PATH_HTML
            base["text"] = "Server-side request forgery contents"
            base["crawl_status"] = "crawled"
        elif "/learning-paths/" in url and cookies:
            base["html"] = "<html><body><h1>real content</h1></body></html>"
            base["text"] = "real content behind the wall"
            base["crawl_status"] = "crawled"
        elif "/learning-paths/" in url:
            base["crawl_status"] = "auth_required"
            base["final_url"] = "https://login.portswigger.net/u/login"
            base["error"] = "Page requires authentication (redirected to sign-in)"
        else:
            base["html"] = "<html><body><p>generic</p></body></html>"
            base["text"] = "generic"
            base["crawl_status"] = "crawled"
        return base

    monkeypatch.setattr(sc, "fetch_verified", fake_fetch)
    monkeypatch.setattr(sc, "_ps_fetch_widgets", lambda netloc, page_path, widget_ids: WIDGET_HTML)


def _signup(client, uname="ps-user", email="ps@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "PS User", "username": uname, "email": email, "password": "pass123", "role": "student"},
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


class TestAuth0LoginFlow:
    def _force_httpx(self, monkeypatch):
        # The unit tests below exercise the httpx flow deterministically (no
        # real browser even when playwright is installed).
        monkeypatch.setattr(ps, "_playwright_available", lambda: False)

    def test_success_extracts_session_cookies(self, monkeypatch):
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(**kw))
        result = ps.login("me@example.com", "hunter2")
        assert result["cookies"] == {"portswigger-session": "session-abc"}
        assert result["email"] == "me@example.com"
        assert result["expires_at"] is None

    def test_invalid_credentials_raises(self, monkeypatch):
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(bad_creds=True, **kw))
        with pytest.raises(ps.AuthError, match="Invalid email or password"):
            ps.login("me@example.com", "wrong")

    def test_no_session_cookies_raises(self, monkeypatch):
        # The flow completes but the site never sets a session cookie → honest
        # AuthError, never a silent "success" with an empty session.
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(no_cookies=True, **kw))
        with pytest.raises(ps.AuthError, match="did not produce"):
            ps.login("me@example.com", "hunter2")

    def test_resume_form_error_raises(self, monkeypatch):
        """Auth0 reports failed logins as hidden error fields in the
        /authorize/resume form (NOT an HTTP error or a URL param) — the
        driver must read them and fail honestly."""
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(resume_error=True, **kw))
        with pytest.raises(ps.AuthError, match="Invalid email or password"):
            ps.login("me@example.com", "wrong")

    def test_anonymous_cookies_fail_authentication_gate(self, monkeypatch):
        """The site always sets anonymous cookies during the redirect dance
        (SessionId, auth0, …). A login must be rejected unless the cookie jar
        actually authenticates — the /users gate is the proof."""
        self._force_httpx(monkeypatch)
        # Password step "succeeds" and sets cookies, but /users still redirects
        # to sign-in → the jar is NOT a session.
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(gate_fails=True, **kw))
        with pytest.raises(ps.AuthError, match="authenticated session"):
            ps.login("me@example.com", "hunter2")

    def test_browser_path_wins_when_available(self, monkeypatch):
        monkeypatch.setattr(ps, "_playwright_available", lambda: True)
        monkeypatch.setattr(
            ps,
            "_login_with_browser",
            lambda e, p: {"cookies": {"browser-session": "b1"}, "expires_at": None, "email": e},
        )
        result = ps.login("me@example.com", "hunter2")
        assert result["cookies"] == {"browser-session": "b1"}

    def test_browser_failure_falls_back_to_httpx(self, monkeypatch):
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(ps, "_playwright_available", lambda: True)
        monkeypatch.setattr(
            ps, "_login_with_browser", lambda e, p: (_ for _ in ()).throw(ps.AuthError("Browser exploded"))
        )
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(**kw))
        result = ps.login("me@example.com", "hunter2")
        assert result["cookies"] == {"portswigger-session": "session-abc"}

    def test_session_gate_accepts_real_account_page(self, monkeypatch):
        """The gate must accept a jar that returns the real account page."""
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(**kw))
        assert ps._session_authenticated({"portswigger-session": "session-abc"}) is True

    def test_session_gate_rejects_signin_redirect(self, monkeypatch):
        self._force_httpx(monkeypatch)
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(gate_fails=True, **kw))
        assert ps._session_authenticated({"portswigger-session": "anon"}) is False

    def test_gate_verdict_reports_diagnostics(self, monkeypatch):
        """A failed gate returns a self-diagnosing detail string (status +
        final URL) so the surfaced error explains what the gate actually saw."""
        monkeypatch.setattr(httpx, "Client", lambda **kw: _FakeAuth0Client(gate_fails=True, **kw))
        ok, detail = ps._gate_verdict({"portswigger-session": "anon"})
        assert ok is False
        assert "HTTP 200" in detail
        assert "login.portswigger.net" in detail

    def test_wait_login_outcome_flags_site_error_page(self):
        """The site's own error page (expired OIDC session) must NOT be read
        as a successful login — that false success produced the confusing
        "did not produce an authenticated session" gate failure."""
        page = _FakeLoginPage(["https://portswigger.net/error?error=invalid_request"])
        assert ps._wait_login_outcome(page) == "flow_error"

    def test_wait_login_outcome_waits_out_oidc_callback_hop(self):
        """The transient /signin-oidc hop is neither success nor failure —
        the poll keeps going until the real destination renders. The first
        two polls land on the callback hop (exercising the continue branch)
        before the real page appears."""
        page = _FakeLoginPage(
            [
                "https://portswigger.net/signin-oidc",
                "https://portswigger.net/signin-oidc",
                "https://portswigger.net/web-security/learning-paths",
            ]
        )
        assert ps._wait_login_outcome(page) == "ok"

    def test_wait_login_outcome_flags_inline_credentials_error(self):
        page = _FakeLoginPage(
            ["https://login.portswigger.net/u/login?state=X"],
            body="Wrong email or password",
        )
        assert ps._wait_login_outcome(page) == "error"

    def test_outcome_error_maps_mfa_to_clear_message(self):
        """The outcome → message mapping is testable without faking
        Playwright: MFA surfaces a distinct error type with an actionable
        message, and known failures map to the honest texts."""
        mfa = ps._outcome_error("mfa_required")
        assert isinstance(mfa, ps.MfaRequiredError)
        assert "second step" in str(mfa)
        assert ps._outcome_error("error") is not None
        assert "Invalid email or password" in str(ps._outcome_error("error"))
        assert ps._outcome_error("flow_error") is not None
        assert ps._outcome_error("ok") is None
        assert ps._outcome_error("timeout") is None

    def test_mfa_error_skips_doomed_httpx_fallback(self, monkeypatch):
        """When the browser proves the account needs a second step, login()
        raises the MFA error immediately — the httpx path (which cannot
        complete a second step either) must NOT be attempted."""
        monkeypatch.setattr(ps, "_playwright_available", lambda: True)
        monkeypatch.setattr(
            ps,
            "_login_with_browser",
            lambda e, p: (_ for _ in ()).throw(
                ps.MfaRequiredError("requires a second step (two-factor)")
            ),
        )
        calls: list = []
        monkeypatch.setattr(httpx, "Client", lambda **kw: calls.append(kw) or _FakeAuth0Client(**kw))
        with pytest.raises(ps.MfaRequiredError):
            ps.login("me@example.com", "hunter2")
        assert calls == []  # httpx was never constructed

    def test_wait_login_outcome_flags_mfa_second_step(self):
        """A CORRECT password followed by a 2FA / passkey prompt is not a
        generic bounce — the user must be told the account needs a second
        step that automation cannot complete."""
        page = _FakeLoginPage(
            ["https://login.portswigger.net/u/mfa-otp-challenge?state=X"],
            body="Enter the verification code from your authenticator app",
        )
        assert ps._wait_login_outcome(page) == "mfa_required"

    def test_wait_login_outcome_flags_error_carrying_redirect(self):
        """A redirect back to portswigger.net carrying an error query param
        (failed OIDC callback) must not be read as a successful login."""
        page = _FakeLoginPage(["https://portswigger.net/web-security/learning-paths?error=invalid_request"])
        assert ps._wait_login_outcome(page) == "flow_error"

    def test_browser_session_authenticated_true_on_account_page(self):
        """The browser-side ground-truth check accepts a jar whose own
        context lands on the account page after /users, with diagnostics."""
        # The /users navigation redirects to the real account page.
        page = _FakeLoginPage([], goto_targets=["https://portswigger.net/users/youraccount"])
        ok, detail = ps._browser_session_authenticated(page)
        assert ok is True
        assert "users/youraccount" in detail

    def test_browser_session_authenticated_false_on_login_bounce(self):
        # The /users navigation in an unauthenticated context bounces back
        # to the sign-in page — the browser must report NOT authenticated,
        # and the diagnostics must say exactly what it saw.
        page = _FakeLoginPage([], bounce_to="https://login.portswigger.net/u/login?state=X")
        ok, detail = ps._browser_session_authenticated(page)
        assert ok is False
        assert "bounced to the sign-in page" in detail
        assert "login.portswigger.net" in detail

    def test_browser_session_authenticated_retries_transient_challenge(self):
        """A one-off bot challenge on the verification navigation must not
        fail a real login: a single retry lands on the account page and the
        session is accepted. Only ONE retry happens (the next test covers
        the persistent-challenge case)."""
        page = _FakeLoginPage(
            [],
            goto_targets=[
                "https://portswigger.net/cdn-cgi/challenge-platform/h/g/orchestrate/jsch/v1?x=1",
                "https://portswigger.net/users/youraccount",
            ],
        )
        ok, detail = ps._browser_session_authenticated(page)
        assert ok is True
        assert "users/youraccount" in detail

    def test_browser_session_authenticated_persistent_challenge_fails_honestly(self):
        """If the challenge persists past the single retry, the login is
        rejected — never reported as a session."""
        page = _FakeLoginPage(
            [],
            goto_targets=[
                "https://portswigger.net/cdn-cgi/challenge-platform/h/g/orchestrate/jsch/v1?x=1",
                "https://portswigger.net/cdn-cgi/challenge-platform/h/g/orchestrate/jsch/v1?x=2",
            ],
        )
        ok, detail = ps._browser_session_authenticated(page)
        assert ok is False
        assert "bot challenge" in detail


class TestSessionEndpoints:
    def test_login_stores_session_and_never_leaks_password(self, client, db_session, monkeypatch):
        monkeypatch.setattr(
            ps, "login", lambda e, p: {"cookies": {"portswigger-session": "sess"}, "expires_at": None, "email": e}
        )
        token = _signup(client)
        resp = client.post(
            "/api/kb/learning-plans/session/login",
            json={"email": "me@example.com", "password": "hunter2-secret", "remember": True},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        body = resp.text
        assert "me@example.com" in body
        assert "hunter2-secret" not in body  # password never returned
        assert "cookies" not in body or "portswigger-session" not in body  # raw cookies never returned

        row = db_session.query(PortswiggerSession).first()
        assert row is not None
        assert row.email == "me@example.com"
        assert row.password_obfuscated != "hunter2-secret"
        assert ps._deobfuscate(row.password_obfuscated) == "hunter2-secret"

    def test_status_and_logout(self, client, db_session, monkeypatch):
        monkeypatch.setattr(
            ps, "login", lambda e, p: {"cookies": {"portswigger-session": "sess"}, "expires_at": None, "email": e}
        )
        token = _signup(client)
        client.post(
            "/api/kb/learning-plans/session/login",
            json={"email": "me@example.com", "password": "hunter2", "remember": True},
            headers=_auth(token),
        )
        resp = client.get("/api/kb/learning-plans/session", headers=_auth(token))
        status = resp.json()["session"]
        assert status["configured"] is True
        assert status["authenticated"] is True
        assert status["email"] == "me@example.com"
        assert status["has_cookies"] is True

        # Logout clears cookies but keeps stored credentials for re-login.
        resp = client.post("/api/kb/learning-plans/session/logout", json={}, headers=_auth(token))
        status = resp.json()["session"]
        assert status["authenticated"] is False
        assert status["configured"] is True  # creds kept
        row = db_session.query(PortswiggerSession).first()
        assert row.cookies_json is None

        # Clearing credentials removes the row entirely.
        client.post(
            "/api/kb/learning-plans/session/logout",
            json={"clear_credentials": True},
            headers=_auth(token),
        )
        assert db_session.query(PortswiggerSession).count() == 0

    def test_reauth_from_stored_credentials_when_session_expired(self, db_session, monkeypatch):
        uid = db_session.query(User).first().id
        past = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=1)
        ps.save_session(
            db_session, uid, "me@example.com", "hunter2", {"portswigger-session": "old"}, past, remember=True
        )
        future_iso = (datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(hours=12)).isoformat()
        monkeypatch.setattr(
            ps,
            "login",
            lambda e, p: {"cookies": {"portswigger-session": "fresh"}, "expires_at": future_iso, "email": e},
        )
        cookies = ps.get_cookies(db_session, uid)
        assert cookies == {"portswigger-session": "fresh"}
        row = db_session.query(PortswiggerSession).first()
        assert row.cookies_json == '{"portswigger-session": "fresh"}'
        # The refreshed expiry is a real datetime (ISO string must be normalised)
        # so the status snapshot and the next get_cookies don't crash.
        status = ps.session_status(db_session, uid)
        assert status["authenticated"] is True
        assert status["expires_at"] is not None
        assert ps.get_cookies(db_session, uid) == {"portswigger-session": "fresh"}

    def test_expired_session_without_credentials_returns_none(self, db_session):
        uid = db_session.query(User).first().id
        past = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - datetime.timedelta(days=1)
        ps.save_session(
            db_session, uid, "me@example.com", None, {"portswigger-session": "old"}, past, remember=False
        )
        assert ps.get_cookies(db_session, uid) is None


class TestReverify:
    def _discover(self, client, token):
        resp = client.post("/api/kb/learning-plans/discover", json=_body(), headers=_auth(token))
        assert resp.status_code == 200, resp.text
        return resp.json()["plan"]["id"]

    def _login(self, client, token):
        resp = client.post(
            "/api/kb/learning-plans/session/login",
            json={"email": "me@example.com", "password": "hunter2", "remember": True},
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["session"]["authenticated"] is True

    def test_reverify_requires_an_active_session(self, client):
        token = _signup(client)
        plan_id = self._discover(client, token)
        resp = client.post(f"/api/kb/learning-plans/{plan_id}/reverify", headers=_auth(token))
        assert resp.status_code == 400
        assert "session" in resp.text.lower()

    def test_reverify_unlocks_gated_urls_and_marks_crawled(self, client, db_session, monkeypatch):
        # Log in (login endpoint mocked; session stored).
        monkeypatch.setattr(
            ps, "login", lambda e, p: {"cookies": {"portswigger-session": "sess"}, "expires_at": None, "email": e}
        )
        token = _signup(client)
        plan_id = self._discover(client, token)
        self._login(client, token)

        # Signed-in view of the path pages exposes a URL for EVERY resource.
        signed_items = [
            {"title": "What is SSRF?", "url": RESOURCE_URL, "resource_type": "reading", "difficulty": "APPRENTICE", "section": "What is SSRF?"},
            {"title": "Common SSRF attacks", "url": COMMON_URL, "resource_type": "reading", "difficulty": "APPRENTICE", "section": "Common SSRF attacks"},
            {"title": "Lab: Basic SSRF against the local server", "url": LAB_URL, "resource_type": "lab", "difficulty": "APPRENTICE", "section": "Common SSRF attacks"},
        ]

        def signed_crawl(path_url: str, *, cookies=None):  # noqa: ARG001
            return {
                "path_url": path_url,
                "crawl_status": "crawled",
                "final_url": path_url,
                "status_code": 200,
                "error": None,
                "resource_total": 23,
                "items": signed_items,
            }

        from app.services.kb import source_crawler as sc

        monkeypatch.setattr(sc, "crawl_learning_path", signed_crawl)

        def verify_with_session(db, res, *, cookies=None):  # noqa: ARG001
            res.crawl_status = "crawled"
            res.status_code = 200
            res.final_url = res.url
            res.error = None
            db.flush()

        monkeypatch.setattr(sc, "_verify_resource", verify_with_session)

        resp = client.post(f"/api/kb/learning-plans/{plan_id}/reverify", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        report = data["reverify"]
        assert report["paths_rechecked"] == 2
        assert report["resources_unlocked"] >= 2
        assert report["resources_verified"] >= 3
        assert report["resources_failed"] == 0

        # The plan's source now shows real URLs with honest CRAWLED status.
        plan = data["plan"]
        all_resources = [r for p in plan["source"]["paths"] for r in p["resources"]]
        labs = [r for r in all_resources if r["resource_type"] == "lab"]
        assert any(r["url"] == LAB_URL and r["crawl_status"] == "crawled" for r in labs)
        with_url = [r for r in all_resources if r["url"]]
        assert with_url and all(r["crawl_status"] == "crawled" for r in with_url)

        # Persisted rows agree.
        rows = (
            db_session.query(LearningResource)
            .filter(LearningResource.plan_id == plan_id, LearningResource.crawl_status == "crawled")
            .count()
        )
        assert rows >= 3

    def test_reverify_does_not_fabricate_urls_when_still_gated(self, client, monkeypatch):
        monkeypatch.setattr(
            ps, "login", lambda e, p: {"cookies": {"portswigger-session": "sess"}, "expires_at": None, "email": e}
        )
        token = _signup(client)
        plan_id = self._discover(client, token)
        self._login(client, token)

        from app.services.kb import source_crawler as sc

        # Even signed in, the site exposes no URLs → rows must NOT gain fake ones.
        def gated_crawl(path_url: str, *, cookies=None):  # noqa: ARG001
            return {
                "path_url": path_url,
                "crawl_status": "crawled",
                "final_url": path_url,
                "status_code": 200,
                "error": None,
                "resource_total": 23,
                "items": [
                    {"title": "What is SSRF?", "url": None, "resource_type": "reading", "difficulty": None, "section": "What is SSRF?"},
                    {"title": "Lab: Basic SSRF against the local server", "url": None, "resource_type": "lab", "difficulty": None, "section": "Common SSRF attacks"},
                ],
            }

        monkeypatch.setattr(sc, "crawl_learning_path", gated_crawl)
        monkeypatch.setattr(sc, "_verify_resource", lambda db, res, *, cookies=None: None)

        resp = client.post(f"/api/kb/learning-plans/{plan_id}/reverify", headers=_auth(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # No URLs were "unlocked" and nothing was verified — honest.
        assert data["reverify"]["resources_unlocked"] == 0
        assert data["reverify"]["resources_verified"] == 0
        plan = data["plan"]
        all_resources = [r for p in plan["source"]["paths"] for r in p["resources"]]
        # The lab stayed hidden even signed-in — its URL must NOT be invented.
        labs = [r for r in all_resources if r["resource_type"] == "lab"]
        assert labs and all(not r["url"] for r in labs)
        # Nothing is marked crawled: no fetch succeeded (verify was a no-op).
        assert all(r["crawl_status"] != "crawled" for r in all_resources)


# ---------------------------------------------------------------------------
# Live end-to-end tests against the real PortSwigger site (OPT-IN)
# ---------------------------------------------------------------------------
# These launch a real headless Chromium, drive the real Auth0 Universal Login
# and fetch real pages — they are skipped unless explicitly enabled:
#
#   PS_LIVE_TESTS=1 pytest tests/test_kb_learning_sessions.py
#
# To also exercise the happy path with a real account:
#
#   PS_LIVE_TESTS=1 PS_PORT_SWIGGER_EMAIL=you@example.com \
#     PS_PORT_SWIGGER_PASSWORD='your-password' \
#     pytest tests/test_kb_learning_sessions.py
#
# Requires playwright + a Chromium build on PATH (or PS_CHROMIUM_PATH). The
# tests assert the honesty guarantees: bad credentials are NEVER reported as
# a session, and a cookie jar is only accepted after the /users gate passes.
# ---------------------------------------------------------------------------

_LIVE_TESTS = os.environ.get("PS_LIVE_TESTS", "").lower() in ("1", "true", "yes")
_LIVE_EMAIL = os.environ.get("PS_PORT_SWIGGER_EMAIL", "").strip()
_LIVE_PASSWORD = os.environ.get("PS_PORT_SWIGGER_PASSWORD", "") or None


@pytest.mark.skipif(
    not _LIVE_TESTS,
    reason="set PS_LIVE_TESTS=1 to run live PortSwigger network tests",
)
class TestLivePortSwiggerLogin:
    """End-to-end sign-in against the real site in a real headless browser.

    The rest of this module mocks the network; these tests do not. They are
    deliberately slow (browser launch + real Auth0 flow) and opt-in via
    ``PS_LIVE_TESTS``.
    """

    def test_browser_path_rejects_bad_credentials_honestly(self):
        """The Playwright driver must run the real flow and then FAIL loudly
        for wrong credentials — never report anonymous cookies as a session."""
        if not ps._playwright_available():
            pytest.skip("playwright + a Chromium build are required for the browser path")
        with pytest.raises(ps.AuthError):
            ps.login("definitely-not-a-real-account@example.com", "wrong-password-123")

    def test_httpx_path_rejects_bad_credentials_honestly(self):
        """The httpx fallback must also detect Auth0's resume-form error fields
        against the live site, not just in fixtures."""
        with pytest.raises(ps.AuthError):
            ps._login_httpx("definitely-not-a-real-account@example.com", "wrong-password-123")

    def test_authentication_gate_rejects_anonymous_cookies_live(self):
        """Browsing the site as a logged-out visitor must NOT produce a jar
        that passes the /users authentication gate — whether the site set
        anonymous cookies (Auth0 session cookies) or none at all."""
        import httpx

        with httpx.Client(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": ps.USER_AGENT},
        ) as client:
            # Logged-out browse: /users bounces through Auth0 and can set
            # anonymous cookies. Whatever jar results must fail the gate.
            client.get(f"{ps.SITE}/users")
            anonymous = {c.name: c.value for c in client.cookies.jar}
        assert ps._session_authenticated(anonymous) is False

    @pytest.mark.skipif(
        not (_LIVE_EMAIL and _LIVE_PASSWORD),
        reason="set PS_PORT_SWIGGER_EMAIL + PS_PORT_SWIGGER_PASSWORD for the live happy path",
    )
    def test_real_credentials_produce_verified_session(self):
        """With real credentials the login returns session cookies and the
        email round-trips — the full end-to-end happy path.

        The gate assertion below is an intentional CANARY, not the login
        contract: the browser path is authoritative (it proves the session
        in its own context), while this gate is the same httpx request the
        crawler will make later. If login succeeds but the gate disagrees,
        crawls may show HTTP errors and "Re-verify" is the workaround.
        """
        result = ps.login(_LIVE_EMAIL, _LIVE_PASSWORD)
        assert result["cookies"], "login must produce session cookies"
        assert result["email"] == _LIVE_EMAIL
        ok, detail = ps._gate_verdict(result["cookies"])
        assert ok, f"crawler-facing /users gate should pass for a real session: {detail}"

    def test_authentication_gate_rejects_empty_jar(self):
        """An empty jar is rejected outright (no session, no network needed)."""
        assert ps._session_authenticated({}) is False
