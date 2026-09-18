"""Live boot smoke test — real uvicorn server over HTTP.

Spawns ``uvicorn main:app`` against a throwaway SQLite database and makes
real HTTP requests to ``/api/health`` plus one KB endpoint. This catches
startup/registration regressions that the in-process TestClient suite cannot:

* a router imported but never registered in ``main.py`` (path → 404/500)
* a lifespan crash (migrations, FTS schema, seeding, static mount)
* a broken startup env (missing uvicorn, bad DATABASE_URL, port issues)

Hermetic by default — nothing touches the real ``student_os.db`` and no
network is used:

* ``DATABASE_URL``            → temp file
* ``UPLOAD_DIR``              → temp dir
* ``KB_WATCH_ENABLED=false``  → no folder watcher racing the boot
* ``EMBEDDINGS_BACKEND=hash`` → deterministic embeddings, no model load

Escape hatches:
* ``SKIP_LIVE_SMOKE=1``      → skip entirely (sandboxes that forbid
  subprocesses/loopback sockets)
* ``LIVE_SMOKE_TIMEOUT=180`` → override the health-wait deadline (default 120s)
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]

_SKIP = os.environ.get("SKIP_LIVE_SMOKE", "").lower() in ("1", "true", "yes")
_HEALTH_TIMEOUT = float(os.environ.get("LIVE_SMOKE_TIMEOUT", "120"))

# Live marker: spawns a real uvicorn subprocess (audit T2). Excluded from the
# default fast suite via ``-m "not live"`` in pyproject.toml; run explicitly
# with ``pytest -m live``.
pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        _SKIP,
        reason="set SKIP_LIVE_SMOKE=1 to skip the live uvicorn smoke test",
    ),
]


class _PortBusy(RuntimeError):
    """uvicorn could not bind because another process grabbed the port."""


def _free_port() -> int:
    """Ask the OS for a currently-free TCP port (released before uvicorn binds)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _http_get(url: str, timeout: float = 10.0) -> tuple[int, dict]:
    """GET a URL; return (status_code, parsed JSON)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except ValueError:
            return exc.code, {"raw": raw}


def _log_tail(log_path: Path, chars: int = 3000) -> str:
    """Last ``chars`` of the uvicorn log for failure diagnostics."""
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")[-chars:]
    except OSError:
        return "<no log available>"


def _terminate(proc: subprocess.Popen) -> None:
    """Terminate uvicorn and its process group; force-kill if it lingers.

    Uses the process group (``start_new_session``) so a Ctrl+C'd pytest run
    cannot leave an orphaned server behind.
    """
    if os.name == "posix":
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.terminate()
    else:
        proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        proc.kill()
        proc.wait(timeout=5)


def _wait_for_health(
    url: str,
    proc: subprocess.Popen,
    log_path: Path,
    timeout: float = _HEALTH_TIMEOUT,
) -> dict:
    """Poll ``/api/health`` until 200, or fail/raise on a dead server."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            log = _log_tail(log_path)
            # Port TOCTOU race: another process grabbed our port in the gap
            # between _free_port() and uvicorn binding. Retryable — not a
            # startup regression.
            if "address already in use" in log.lower():
                raise _PortBusy(log)
            pytest.fail(
                f"uvicorn exited early (rc={proc.returncode}) before becoming healthy; "
                f"log tail:\n{log}"
            )
        try:
            status, body = _http_get(url, timeout=3.0)
            if status == 200:
                return body
        except (urllib.error.URLError, OSError, TimeoutError):
            pass  # still booting — keep polling
        time.sleep(0.5)
    pytest.fail(
        f"uvicorn did not become healthy within {timeout:.0f}s; log tail:\n{_log_tail(log_path)}"
    )


def test_live_uvicorn_health_and_kb_endpoint():
    """Boot the real server and verify health + one KB endpoint over HTTP."""
    with tempfile.TemporaryDirectory(prefix="kb_live_smoke_") as tmp:
        # Forward slashes keep the sqlite URL valid on Windows temp paths.
        db_path = os.path.join(tmp, "smoke.db").replace("\\", "/")
        uploads_dir = os.path.join(tmp, "uploads")

        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{db_path}",
            "UPLOAD_DIR": uploads_dir,
            "KB_WATCH_ENABLED": "false",
            "EMBEDDINGS_BACKEND": "hash",
        }

        proc: subprocess.Popen | None = None
        try:
            port = _free_port()
            for attempt in range(3):
                if attempt:  # fresh port on a bind-failure retry
                    port = _free_port()
                base = f"http://127.0.0.1:{port}"
                log_path = Path(tmp) / f"uvicorn_{attempt}.log"
                with open(log_path, "w", encoding="utf-8") as log:
                    proc = subprocess.Popen(
                        [
                            sys.executable, "-m", "uvicorn", "main:app",
                            "--host", "127.0.0.1", "--port", str(port),
                            "--log-level", "warning",
                        ],
                        cwd=str(BACKEND_DIR),
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=(os.name == "posix"),
                    )
                try:
                    health = _wait_for_health(f"{base}/api/health", proc, log_path)
                    break
                except _PortBusy:
                    _terminate(proc)
                    proc = None
                    continue
            else:
                pytest.fail("could not bind a free port after 3 attempts")

            # 1) Health — proves the app booted (lifespan: migrations, FTS,
            #    seeding, static mount) and the process is serving HTTP.
            assert health["status"] == "ok"
            assert health["app"] == "Student Life OS"
            assert health["version"] == "0.1.0"

            # 2) One KB endpoint — proves the KB routers are registered and
            #    reach a working DB connection (tokenless single-user auth).
            status, body = _http_get(f"{base}/api/kb/sources")
            assert status == 200, f"GET /api/kb/sources -> {status}: {body}"
            assert isinstance(body.get("items"), list)
            assert isinstance(body.get("total"), int)

            # 3) Registration guard — the endpoint is in the OpenAPI map, so a
            #    router silently dropped from main.py cannot pass unnoticed.
            _, openapi = _http_get(f"{base}/openapi.json")
            assert "/api/kb/sources" in openapi.get("paths", {})
        finally:
            # Always reap the server — including when a health-wait failure
            # raised out of the boot loop.
            if proc is not None:
                _terminate(proc)
