"""PortSwigger sign-in session support for the Learning Path Planner.

PortSwigger gates the deep learning-path resource URLs behind a sign-in
wall: anonymous fetches return HTTP 200 but bounce to
``login.portswigger.net`` — never a valid crawl, so those rows are labeled
``auth_required``. With a stored session from the user's own account the
crawler can:

1. **Extract the hrefs public pages hide** — the signed-in path page HTML
   exposes a real URL for *every* resource (public pages only show the
   first one).
2. **Verify those URLs honestly** — fetches carry the session cookies, so
   real content returns ``crawled`` instead of ``auth_required``.

The sign-in flow is Auth0 Universal Login v2 — a single JavaScript-driven
form that POSTs ``state`` + ``username`` + ``password`` to ``/u/login`` in
one step (the old two-step ``/u/login/identifier`` + ``/u/login/password``
endpoints are gone). Two drivers exist:

* ``_login_with_browser`` — drives the site's *real* JavaScript in headless
  Chromium (Playwright). Primary path: it executes whatever Auth0 does and
  survives markup changes. The session is proven **in the same browser** by
  navigating to ``/users`` and confirming it does not bounce to the sign-in
  page — no cross-client mismatch can false-negative a real login.
* ``_login_httpx`` — mirrors the current single POST directly:

      GET https://portswigger.net/users?returnurl=…  → 302 to login.portswigger.net
      POST /u/login {state, username, password}
      → POST the /authorize/resume form → session cookies

**No login is ever reported successful unless it is *proven* to work:** the
resume form's embedded ``error`` fields are checked (Auth0 reports failures
as hidden inputs or HTTP 400 + an inline message), and the resulting cookie
jar must pass the ``/users`` authentication gate — an anonymous or failed
login bounces ``/users`` to ``login.portswigger.net``, a real session
returns the account page. Only cookies that pass the gate are stored.

Credentials are stored *obfuscated* (base64 — obfuscation, NOT encryption;
this is a single-user local app) only when the user chose to remember them,
so an expired session can be refreshed without re-entering them. The API
never returns the password or the raw cookies.
"""

from __future__ import annotations

import base64
import glob
import html as html_mod
import json
import logging
import os
import re
import shutil
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from sqlalchemy.orm import Session

from app.models import LearningPath, LearningPathResource, LearningResource, PortswiggerSession
from app.models.kb.learning_path import (
    CRAWL_AUTH_REQUIRED,
    CRAWL_CRAWLED,
    CRAWL_DISCOVERED,
    CRAWL_EXTRACTION_FAILED,
    CRAWL_HTTP_ERROR,
    CRAWL_NOT_FOUND,
)
from app.services.kb import source_crawler as sc
from app.services.kb import utcnow

logger = logging.getLogger(__name__)

SITE = "https://portswigger.net"
AUTH0 = "https://login.portswigger.net"
RETURN_URL = "%2Fweb-security%2Flearning-paths"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36"
)
LOGIN_TIMEOUT = 25.0


class AuthError(Exception):
    """PortSwigger sign-in failed (invalid credentials, wall changed, …)."""


class MfaRequiredError(AuthError):
    """The account needs a second step (2FA / passkey) that automated sign-in
    cannot complete — the httpx fallback is skipped for this case."""


# ---------------------------------------------------------------------------
# Obfuscation (local single-user app — NOT encryption)
# ---------------------------------------------------------------------------


def _obfuscate(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")


def _deobfuscate(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return base64.urlsafe_b64decode(value.encode("ascii")).decode("utf-8")
    except Exception:  # noqa: BLE001 — corrupt blob → treat as absent
        return None


# ---------------------------------------------------------------------------
# The Auth0 single-POST login (Universal Login v2)
# ---------------------------------------------------------------------------


def _extract_state(final_url: str) -> str:
    state = parse_qs(urlparse(final_url).query).get("state", [""])[0]
    if not state:
        raise AuthError("Sign-in page did not include a session state")
    return state


def _to_naive_datetime(value: datetime | str | None) -> datetime | None:
    """Normalise an ISO string or datetime into a naive UTC datetime (the
    SQLite-friendly form the rest of the app uses)."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


# Paths that mean "we were not signed in" — used by the authentication gate.
_AUTH_GATE_SEGMENTS = (
    "/u/login",
    "/login",
    "/signin",
    "/users/login",
    "/account/login",
    "/error",
)

# Inline errors Auth0 renders on the login page for a failed password step.
_LOGIN_ERROR_MARKERS = (
    "wrong email or password",
    "wrong email",
    "wrong password",
    "invalid email or password",
    "invalid credentials",
    "incorrect email",
    "incorrect password",
)

# Second-step screens Auth0 shows after a CORRECT password (2FA, passkey,
# security challenge). Automated sign-in cannot complete these — the user
# gets a clear message instead of a confusing generic bounce.
_MFA_MARKERS = (
    "two-step verification",
    "two factor authentication",
    "two-factor authentication",
    "enter the code",
    "enter your code",
    "verification code",
    "authenticator app",
    "security code",
    "passkey",
    "webauthn",
    "security key",
    "verify it's you",
    "device verification",
)


def _gate_verdict(cookies: dict[str, str]) -> tuple[bool, str]:
    """Prove a cookie jar actually authenticates — the /users gate.

    GET ``https://portswigger.net/users`` with the cookies: a real session
    returns the account page (HTTP 200 on portswigger.net); an anonymous or
    failed login bounces to the sign-in page. A cookie jar is only ever
    accepted as a session after this gate passes. Never trusts the cookies
    themselves (anonymous site cookies exist regardless of login state).

    Returns ``(authenticated, diagnostics)`` — the diagnostics describe what
    the gate actually saw (HTTP status, final URL, bounce/error detection)
    so a failed login surfaces a self-diagnosing message instead of a bare
    "not authenticated".
    """
    if not cookies:
        return False, "no cookies supplied"
    try:
        import httpx

        with httpx.Client(
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            cookies=cookies,
        ) as client:
            resp = client.get(f"{SITE}/users")
        final = str(resp.url)
        parsed = urlparse(final)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        # Path-and-netloc only (no query string): keeps the one-time Auth0
        # `state` token out of user-facing error messages.
        detail = f"HTTP {resp.status_code} -> {parsed.scheme}://{netloc}{path}"
        if resp.status_code != 200:
            return False, detail
        if "portswigger.net" not in netloc or "login.portswigger.net" in netloc:
            return False, f"{detail} (bounced to the sign-in page)"
        if any(seg in path for seg in _AUTH_GATE_SEGMENTS):
            return False, f"{detail} (sign-in/error page)"
        return True, detail
    except Exception as exc:  # noqa: BLE001 — an unverifiable session is NOT a session
        return False, f"gate request failed: {exc}"


def _session_authenticated(cookies: dict[str, str]) -> bool:
    ok, _ = _gate_verdict(cookies)
    return ok


def _find_chromium() -> str | None:
    """Locate a usable Chromium executable for the browser sign-in path.

    Prefers the newest cached Playwright build, then system binaries, then the
    ``PS_CHROMIUM_PATH`` override.
    """
    cached = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"))
    cached.sort(key=lambda p: _build_number(p), reverse=True)
    candidates: list[str] = cached + [
        shutil.which(n) or ""
        for n in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")
    ]
    if os.environ.get("PS_CHROMIUM_PATH"):
        candidates.append(os.environ["PS_CHROMIUM_PATH"])
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def _build_number(chromium_path: str) -> int:
    """Extract the numeric build from a Playwright cache path (…/chromium-1234/…)."""
    m = re.search(r"chromium-(\d+)", chromium_path or "")
    return int(m.group(1)) if m else 0


def _playwright_available() -> bool:
    """True when the real-browser path can run (playwright + a chromium)."""
    try:
        import playwright  # noqa: F401
        return _find_chromium() is not None
    except Exception:  # noqa: BLE001
        return False


def _wait_login_outcome(page) -> str:
    """Poll the login page after the password submit.

    Returns ``"ok"`` once the page navigates back to portswigger.net with a
    real session page (login accepted), ``"error"`` when Auth0 renders an
    inline credentials error, ``"flow_error"`` when the site renders its own
    error page or an error-carrying redirect (e.g. an expired OIDC session —
    the page that previously masqueraded as a successful login),
    ``"mfa_required"`` when Auth0 asks for a second step (2FA / passkey —
    automated sign-in cannot complete it), or ``"timeout"``. Polling every
    0.5s resolves failures in a few seconds instead of waiting out a fixed
    navigation timeout.

    The transient ``/signin-oidc`` callback hop and Cloudflare challenge
    pages are neither success nor failure — the poll keeps going until the
    real destination renders.
    """
    import time

    deadline = time.monotonic() + 30.0
    while time.monotonic() < deadline:
        page.wait_for_timeout(500)
        parsed = urlparse(page.url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        if "portswigger.net" in netloc and "login.portswigger" not in netloc:
            query = parse_qs(parsed.query)
            if path == "/error" or "error" in query or "error_description" in query:
                return "flow_error"
            if path == "/signin-oidc":
                continue  # transient callback hop — keep polling
            if "cdn-cgi" in path:
                continue  # transient bot challenge — keep polling
            if not any(seg in path for seg in _AUTH_GATE_SEGMENTS):
                return "ok"
        try:
            body = page.inner_text("body").lower()
        except Exception:  # noqa: BLE001
            continue
        if any(marker in body for marker in _LOGIN_ERROR_MARKERS):
            return "error"
        if any(marker in body for marker in _MFA_MARKERS):
            return "mfa_required"
    return "timeout"


def _outcome_error(outcome: str) -> AuthError | None:
    """Map a ``_wait_login_outcome`` verdict to the user-facing error.

    ``None`` for ``"ok"`` (and ``"timeout"`` — handled by the caller). The
    MFA case raises ``MfaRequiredError`` so the caller can skip the httpx
    fallback (which cannot complete a second step either). Extracted as a
    module-level helper so the message mapping is unit-testable without
    faking Playwright.
    """
    if outcome == "error":
        return AuthError("Invalid email or password")
    if outcome == "mfa_required":
        return MfaRequiredError(
            "Your PortSwigger account requires a second step (two-factor "
            "authentication or passkey) that automated sign-in cannot "
            "complete. Sign in once in your own browser, or temporarily "
            "disable two-factor authentication to allow automated access."
        )
    if outcome == "flow_error":
        return AuthError(
            "Sign-in did not complete — the site returned an error page. "
            "Please try again in a moment."
        )
    return None


def _browser_session_authenticated(page) -> tuple[bool, str]:
    """Prove the session using the SAME browser that performed the login.

    Navigates to ``/users`` in the authenticated context: a real session
    stays on portswigger.net (the account page), an anonymous one bounces to
    the sign-in page. This is the ground-truth check for the browser path —
    no cross-client (httpx/Cloudflare/TLS) mismatch is possible.

    Returns ``(authenticated, diagnostics)`` where the diagnostics describe
    exactly what the verification saw (HTTP status + final URL + reason) so
    a failure surfaces a self-diagnosing message instead of a bare
    rejection. A single retry is attempted when the first navigation hits a
    transient challenge or race right after login — one honest second
    chance, then a truthful failure.
    """

    def _check() -> tuple[bool, str]:
        try:
            resp = page.goto(f"{SITE}/users", wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:  # noqa: BLE001
            return False, f"verification navigation failed: {exc}"
        status = None
        if resp is not None:
            status = getattr(resp, "status", getattr(resp, "status_code", None))
        try:
            page.wait_for_timeout(600)  # let any interstitial settle before judging
        except Exception:  # noqa: BLE001
            pass
        final = str(page.url)
        parsed = urlparse(final)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        detail = f"HTTP {status} -> {parsed.scheme}://{netloc}{path}"
        if status not in (None, 200):
            return False, detail
        if "portswigger.net" not in netloc or "login.portswigger.net" in netloc:
            return False, f"{detail} (bounced to the sign-in page)"
        if "cdn-cgi" in path:
            return False, f"{detail} (bot challenge)"
        if any(seg in path for seg in _AUTH_GATE_SEGMENTS):
            return False, f"{detail} (sign-in/error page)"
        return True, detail

    ok, detail = _check()
    if ok:
        return True, detail
    # One retry: a fresh navigation immediately after login can hit a
    # transient Cloudflare challenge or a cookie-flush race. Never retries
    # more than once, and the second verdict is final.
    try:
        page.wait_for_timeout(1200)
    except Exception:  # noqa: BLE001
        pass
    return _check()


def _login_with_browser(email: str, password: str) -> dict:
    """Drive Auth0's real Universal Login in headless Chromium (Playwright).

    This is the primary path: it executes the site's own JavaScript, so it
    stays correct even when Auth0 changes its markup. Completing the login is
    proven IN THIS BROWSER (a ``/users`` navigation must not bounce back to
    the sign-in page), with the httpx gate kept as a logged cross-check only.
    Returns the same shape as ``login()``.
    """
    from playwright.sync_api import sync_playwright

    executable = _find_chromium()
    if not executable:
        raise AuthError("No Chromium browser available for sign-in")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=executable,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        try:
            page.goto(
                f"{SITE}/users?returnurl={RETURN_URL}",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_selector("input[name=username], #username", timeout=30000)
            page.fill("input[name=username], #username", email)
            page.click("button[name=action], button[type=submit]")
            page.wait_for_selector(
                "input[name=password], #password", state="attached", timeout=30000
            )
            page.fill("input[name=password], #password", password)
            page.click("button[name=action], button[type=submit]")
            # Poll for the outcome: success = the site redirects back to a
            # real portswigger.net page; failure = an inline credentials
            # error or the site's own error page. Never waits out a long
            # timeout to discover a failure.
            outcome = _wait_login_outcome(page)
            exc = _outcome_error(outcome)
            if exc is not None:
                raise exc
            if outcome != "ok":
                raise AuthError("Sign-in did not complete — please try again")
            # Prove the session IN THIS BROWSER (ground truth). The old code
            # relied on an external httpx gate, which could false-negative a
            # genuinely authenticated login (cross-client TLS/Cloudflare
            # mismatch) — that locked out real users with the confusing
            # "did not produce an authenticated session" error.
            ok, detail = _browser_session_authenticated(page)
            if not ok:
                raise AuthError(
                    "Sign-in did not produce an authenticated session — the "
                    f"verification request {detail}. If your credentials are "
                    "correct, the verification request was blocked — try again "
                    "in a moment."
                )
        except AuthError:
            raise
        except Exception as exc:  # noqa: BLE001 — browser hiccup (timeout, launch,
            # crash): surface an honest AuthError so login() falls back to
            # httpx instead of returning an HTTP 500.
            raise AuthError(f"Browser sign-in failed: {exc}") from exc
        finally:
            cookies = context.cookies()
            browser.close()

    ps_cookies = {
        c["name"]: c["value"] for c in cookies if "portswigger.net" in c["domain"]
    }
    if not ps_cookies:
        raise AuthError("Sign-in did not produce a PortSwigger session")
    # The session was proven in-browser above. Cross-check via the httpx gate
    # for observability only — the browser verdict is authoritative, so an
    # httpx-side mismatch cannot false-negative a real login.
    ok, detail = _gate_verdict(ps_cookies)
    if not ok:
        # WARNING, not INFO: the crawler verifies with the SAME httpx client,
        # so a gate disagreement predicts crawls may fail later even though
        # the login itself was proven in-browser.
        logger.warning(
            "PortSwigger browser login verified in-browser; httpx gate disagreed "
            "(%s) — accepting the browser-verified session",
            detail,
        )
    return {"cookies": ps_cookies, "expires_at": None, "email": email}


def _login_httpx(email: str, password: str) -> dict:
    """Run the current single-POST Auth0 flow over httpx and return verified
    cookies.

    Universal Login v2 renders one form with both fields and submits
    ``state`` + ``username`` + ``password`` to ``/u/login`` in a single POST
    — the old two-step endpoints no longer exist. Returns
    ``{"cookies": {name: value}, "expires_at": iso|None, "email": email}``.
    Raises ``AuthError`` on invalid credentials, on any resume-form error, or
    when the cookie jar fails the ``/users`` authentication gate — never
    silently succeeds.
    """
    import httpx

    with httpx.Client(
        timeout=LOGIN_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        # 1. Begin the flow from the site (the /users redirect lands on
        #    Auth0 with a fresh `state`).
        resp = client.get(f"{SITE}/users?returnurl={RETURN_URL}")
        state = _extract_state(str(resp.url))

        # 2. Single submit — exactly what the browser's UL v2 form sends
        #    (captured live from the real page; there is no identifier step).
        resp = client.post(
            f"{AUTH0}/u/login",
            data={"state": state, "username": email, "password": password},
        )

        # 3. Honest outcome check. Bad credentials come back as HTTP 400 with
        #    an inline "Wrong email or password" message; other failures
        #    arrive as a bounce back to the login page or as embedded
        #    `error`/`error_description` hidden inputs in the
        #    /authorize/resume completion form. None of these are successes.
        if resp.status_code >= 500:
            raise AuthError(
                f"Sign-in failed — the site returned HTTP {resp.status_code}, "
                "please try again"
            )
        if resp.status_code >= 400:
            raise AuthError("Invalid email or password")
        text = resp.text.lower()
        if any(marker in text for marker in _LOGIN_ERROR_MARKERS):
            raise AuthError("Invalid email or password")
        resume_error = re.search(
            r'name="error_description"[^>]*value="([^"]*)"', resp.text
        ) or re.search(r'name="error"[^>]*value="([^"]+)"', resp.text)
        if resume_error:
            raise AuthError("Invalid email or password")
        final_path = urlparse(str(resp.url)).path
        if "/u/login" in final_path:
            raise AuthError("Invalid email or password")

        # 4. A successful submit lands on the /authorize/resume form, which
        #    completes the OIDC handshake by POSTing the auth code back to
        #    portswigger.net/signin-oidc (this is what sets the real session
        #    cookie). Follow it exactly as the browser would.
        resume_form = re.search(
            r'<form[^>]*action="([^"]+)"[^>]*>(.*?)</form>', resp.text, re.S
        )
        if resume_form and resume_form.group(1):
            action = html_mod.unescape(resume_form.group(1))
            fields = dict(
                re.findall(r'name="([^"]+)"[^>]*value="([^"]*)"', resume_form.group(2))
            )
            fields = {k: html_mod.unescape(v) for k, v in fields.items()}
            resp = client.post(action, data=fields)

        # 5. Collect portswigger.net cookies AND prove they authenticate.
        #    Anonymous site cookies exist regardless of login state — only a
        #    jar that passes the /users gate is a session.
        cookies: dict[str, str] = {}
        expiries: list[datetime] = []
        for cookie in client.cookies.jar:
            domain = cookie.domain or ""
            if "portswigger.net" not in domain:
                continue
            cookies[cookie.name] = cookie.value
            if getattr(cookie, "expires", None):
                try:
                    expiries.append(datetime.fromtimestamp(float(cookie.expires)))
                except (TypeError, ValueError, OSError):
                    pass
        if not cookies:
            raise AuthError("Sign-in did not produce a PortSwigger session")
        ok, detail = _gate_verdict(cookies)
        if not ok:
            logger.info("PortSwigger httpx login gate failed: %s", detail)
            raise AuthError(f"Sign-in did not produce an authenticated session ({detail})")
        return {
            "cookies": cookies,
            "expires_at": min(expiries).isoformat() if expiries else None,
            "email": email,
        }


def login(email: str, password: str) -> dict:
    """Sign in to PortSwigger and return *verified* session cookies.

    Prefers the real-browser path (it executes Auth0's actual JavaScript and
    survives markup changes); falls back to the httpx flow when no browser is
    available. A session is never reported successful unless it is *proven*
    to authenticate — in-browser for the browser path, via the ``/users``
    gate for the httpx path. Raises ``AuthError`` otherwise.
    """
    errors: list[str] = []
    if _playwright_available():
        try:
            result = _login_with_browser(email, password)
            logger.info("PortSwigger login succeeded via the browser path")
            return result
        except MfaRequiredError:
            # The httpx path cannot complete a second step either — raise
            # immediately instead of wasting a doomed fallback attempt.
            raise
        except AuthError as exc:
            errors.append(str(exc))
    try:
        result = _login_httpx(email, password)
        logger.info("PortSwigger login succeeded via the httpx path")
        return result
    except AuthError as exc:
        errors.append(str(exc))
    raise AuthError(errors[0] if errors else "Sign-in failed")


# ---------------------------------------------------------------------------
# Session persistence (one row per user)
# ---------------------------------------------------------------------------


def load_session(db: Session, user_id: int) -> PortswiggerSession | None:
    return (
        db.query(PortswiggerSession)
        .filter(PortswiggerSession.user_id == user_id)
        .first()
    )


def save_session(
    db: Session,
    user_id: int,
    email: str,
    password: str | None,
    cookies: dict[str, str],
    expires_at: datetime | str | None,
    *,
    remember: bool = True,
) -> PortswiggerSession:
    row = load_session(db, user_id)
    if row is None:
        row = PortswiggerSession(user_id=user_id)
        db.add(row)
    row.email = email
    if remember and password:
        row.password_obfuscated = _obfuscate(password)
    row.cookies_json = json.dumps(cookies)
    row.expires_at = _to_naive_datetime(expires_at)
    row.last_login_at = utcnow()
    db.flush()
    return row


def _cookies_of(row: PortswiggerSession) -> dict[str, str]:
    if not row or not row.cookies_json:
        return {}
    try:
        data = json.loads(row.cookies_json)
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def session_status(db: Session, user_id: int) -> dict:
    """Public, password-free status snapshot for the UI."""
    row = load_session(db, user_id)
    if row is None:
        return {
            "configured": False,
            "authenticated": False,
            "email": None,
            "expires_at": None,
            "last_login_at": None,
            "has_cookies": False,
        }
    cookies = _cookies_of(row)
    expired = bool(row.expires_at and row.expires_at <= utcnow())
    return {
        "configured": True,
        "authenticated": bool(cookies) and not expired,
        "email": row.email,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
        "has_cookies": bool(cookies),
    }


def get_cookies(db: Session, user_id: int, *, reauth: bool = True) -> dict[str, str] | None:
    """Return usable session cookies, refreshing from stored credentials when
    the stored session is missing or expired. ``None`` when there is no
    usable session (callers surface an honest message)."""
    row = load_session(db, user_id)
    cookies = _cookies_of(row)
    expired = bool(row and row.expires_at and row.expires_at <= utcnow())
    if cookies and not expired:
        return cookies
    if not (reauth and row and row.password_obfuscated):
        return None
    password = _deobfuscate(row.password_obfuscated)
    if not password:
        return None
    try:
        result = login(row.email, password)
    except AuthError as exc:
        logger.info("PortSwigger re-auth failed: %s", exc)
        return None
    row.cookies_json = json.dumps(result["cookies"])
    row.expires_at = _to_naive_datetime(result["expires_at"])
    row.last_login_at = utcnow()
    db.flush()
    return result["cookies"]


def logout(db: Session, user_id: int, *, clear_credentials: bool = False) -> None:
    row = load_session(db, user_id)
    if row is None:
        return
    if clear_credentials:
        db.delete(row)
        db.flush()
        return
    row.cookies_json = None
    row.expires_at = None
    db.flush()


# ---------------------------------------------------------------------------
# Re-verify a plan's auth-gated resources behind the sign-in wall
# ---------------------------------------------------------------------------

_CRAWL_RECHECKABLE = {
    CRAWL_AUTH_REQUIRED,
    CRAWL_DISCOVERED,
    CRAWL_HTTP_ERROR,
    CRAWL_NOT_FOUND,
    CRAWL_EXTRACTION_FAILED,
}


def reverify_plan(db: Session, user_id: int, plan) -> dict:
    """Re-crawl the plan's paths + re-verify its resources with a live session.

    This is an explicit user action (\"Re-verify\"). It:

    1. Re-crawls each path page signed-in — the HTML now exposes a real URL
       for every resource, which is written back to the matching rows (or new
       rows where the signed-in view reveals resources the public page hid).
    2. Re-verifies every resource that has a URL and was previously gated,
       discovered, or failed — statuses become ``crawled`` only when the
       signed-in fetch actually returns real content.

    Returns an honest report of what changed. Never fabricates URLs or
    success — a failed fetch keeps the row's true status.
    """
    cookies = get_cookies(db, user_id)
    if not cookies:
        raise AuthError(
            "No active PortSwigger session — connect your account first (or re-enter your credentials)."
        )
    report = {
        "paths_rechecked": 0,
        "resources_unlocked": 0,  # rows that gained a real URL from the signed-in view
        "resources_verified": 0,  # URLs fetched successfully with the session
        "resources_failed": 0,
        "statuses": {},
    }
    paths = (
        db.query(LearningPath)
        .filter(LearningPath.plan_id == plan.id, LearningPath.user_id == user_id)
        .all()
    )
    for path in paths:
        if not path.source_url:
            continue
        crawled = sc.crawl_learning_path(path.source_url, cookies=cookies)
        if crawled is None or crawled["crawl_status"] != CRAWL_CRAWLED:
            continue
        report["paths_rechecked"] += 1
        path.crawl_status = crawled["crawl_status"]
        path.final_url = (crawled.get("final_url") or "")[:600] or None
        path.status_code = crawled.get("status_code")
        path.error = None
        if crawled.get("resource_total") is not None:
            path.resource_total = crawled["resource_total"]

        links = {
            link.resource_id: link
            for link in db.query(LearningPathResource)
            .filter(LearningPathResource.path_id == path.id)
            .all()
        }
        existing = {
            res.id: res for res in db.query(LearningResource).filter(LearningResource.id.in_(links.keys())).all()
        } if links else {}
        order = 0
        for item in crawled["items"]:
            order += 1
            title = (item.get("title") or "").strip()
            url = item.get("url")
            if not title:
                continue
            # Match by exact title within the path's current resources first,
            # then fall back to a URL-key match across the plan (dedup).
            res = next((r for r in existing.values() if (r.title or "").strip() == title), None)
            if res is None and url:
                key = sc._url_key(url)
                res = (
                    db.query(LearningResource)
                    .filter(
                        LearningResource.plan_id == plan.id,
                        LearningResource.url_key == key,
                    )
                    .first()
                )
            if res is None:
                res = LearningResource(
                    user_id=user_id,
                    plan_id=plan.id,
                    title=title[:300],
                    url=(url or "")[:600] or None,
                    resource_type=item.get("resource_type") or "reading",
                    difficulty=(item.get("difficulty") or "")[:60] or None,
                    section=(item.get("section") or "")[:200] or None,
                    sort_order=order,
                    url_key=sc._url_key(url) if url else None,
                    crawl_status=CRAWL_DISCOVERED,
                )
                db.add(res)
                db.flush()
                existing[res.id] = res
            else:
                existing[res.id] = res
            # Link this path → resource (junction dedup is the same rule as
            # discovery: one resource row, many paths).
            link = links.get(res.id)
            if link is None:
                db.add(
                    LearningPathResource(
                        path_id=path.id,
                        resource_id=res.id,
                        section=(item.get("section") or "")[:200] or None,
                        sort_order=order,
                    )
                )
            # The signed-in view revealed a URL the public page hid.
            if url and (res.url or "").strip() != url:
                res.url = url[:600]
                res.url_key = sc._url_key(url)
                res.crawl_status = CRAWL_DISCOVERED  # re-verify below
                report["resources_unlocked"] += 1
            elif not res.url and not url:
                # Still hidden even signed-in → leave the honest status.
                if res.crawl_status not in (CRAWL_CRAWLED,):
                    res.crawl_status = CRAWL_DISCOVERED
        path.section_count = len({(i.get("section") or "") for i in crawled["items"]})
        path.resource_count = len(crawled["items"])
        db.flush()

    # Second pass: verify every resource with a URL that is not yet crawled.
    resources = (
        db.query(LearningResource)
        .filter(LearningResource.plan_id == plan.id, LearningResource.user_id == user_id)
        .all()
    )
    resources_by_id: dict[int, LearningResource] = {}
    for res in resources:
        if not res.url:
            continue
        if res.crawl_status not in _CRAWL_RECHECKABLE:
            continue
        sc._verify_resource(db, res, cookies=cookies)
        resources_by_id[res.id] = res
        if res.crawl_status == CRAWL_CRAWLED:
            report["resources_verified"] += 1
        else:
            report["resources_failed"] += 1
        report["statuses"][res.crawl_status] = report["statuses"].get(res.crawl_status, 0) + 1
        db.flush()

    # Third pass: propagate verified URLs into the roadmap tasks that point at
    # these resources, so a previously gated task becomes clickable + CRAWLED.
    from app.models import LearningTask

    for task in (
        db.query(LearningTask)
        .filter(
            LearningTask.plan_id == plan.id,
            LearningTask.user_id == user_id,
            LearningTask.resource_id.isnot(None),
        )
        .all()
    ):
        res = resources_by_id.get(task.resource_id)
        if res is None or not res.url or res.crawl_status != CRAWL_CRAWLED:
            continue
        task.resource_url = res.url
        task.resource_title = res.title
        task.source_crawled = True
        db.flush()

    return report
