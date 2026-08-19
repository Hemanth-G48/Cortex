"""Folder watcher (Idea 3, phrases 28–29).

An optional ``watchdog`` observer (native dependency) with a pure-polling
fallback behind an import guard — CI never needs watchdog installed. The
watcher is started/stopped from the app lifespan and skipped under pytest.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable

from app.config import settings

logger = logging.getLogger(__name__)

_stop = threading.Event()
_poll_thread: threading.Thread | None = None
_auto_thread: threading.Thread | None = None
_observer = None


def _retry_locked(db, fn: Callable, attempts: int = 3, base_delay: float = 0.8) -> None:
    """Run ``fn`` retrying on SQLite ``database is locked``.

    The API server and the watcher both write to the same SQLite file; a long
    request transaction can briefly hold the write lock past the connect
    ``timeout``. A scan failing with ``OperationalError … database is locked``
    used to abort the whole poll with an ugly traceback — instead retry with
    rollback (to clear the pending-rollback state) and a short backoff, then
    surface the real error only after the attempts are exhausted.
    """
    import time

    from sqlalchemy.exc import OperationalError

    delay = base_delay
    for attempt in range(1, attempts + 1):
        try:
            fn()
            return
        except OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == attempts:
                raise
            # A failed flush leaves the session in pending-rollback; the retry
            # needs a clean session or it would fail with PendingRollbackError.
            db.rollback()
            logger.info(
                "Watcher scan hit a locked database (attempt %s/%s) — retrying",
                attempt,
                attempts,
            )
            time.sleep(delay)
            delay *= 2


def _maybe_derive_courses(db, user_id: int) -> None:
    """Event hook: after a source scan, refresh KB-derived courses.

    Cheap (bounded by the number of ``course:*`` tags) and idempotent, so
    running it on every watcher poll is safe. Errors propagate to the
    caller's retry + outer catch (same uniform handling as scans).
    """
    from app.services.course_derivation import derive_courses_from_tags

    derive_courses_from_tags(db, user_id)


def _poll_once(session_factory: Callable) -> None:
    from app.models import KbSource
    from app.services.kb.scanner import scan_and_ingest

    db = session_factory()
    try:
        sources = (
            db.query(KbSource).filter(KbSource.enabled == True).all()  # noqa: E712
        )
        for source in sources:
            if not source.root_path:
                continue
            try:
                # Both writes share the SQLite file with the API server —
                # retry each on a transient "database is locked" instead of
                # logging a crash-loop traceback every poll.
                _retry_locked(db, lambda: scan_and_ingest(db, source.id))
                _retry_locked(db, lambda: _maybe_derive_courses(db, source.user_id))
            except Exception:  # noqa: BLE001 — one bad source must not kill the loop
                # Roll back the failed transaction first: after a failed flush
                # the session is in a pending-rollback state and the log line
                # below (which reloads source.id) would re-raise
                # PendingRollbackError instead of reporting the real cause.
                db.rollback()
                logger.exception("Watcher scan failed for source %s", source.id)
    finally:
        db.close()


_auto_last_run: float = 0.0


def _maybe_run_automations(session_factory: Callable) -> None:
    """Periodic automation pass — drives every KB_AUTO_* job on a timer.

    Runs at most once per ``KB_AUTO_RUN_INTERVAL_SECONDS`` (0 = disabled),
    only for users with at least one enabled source, in its own session with
    the same locked-DB retry as scans. Each job still respects its own toggle
    (e.g. ``KB_AUTO_LOCAL_SYNC_ENABLED`` for Copy Recent Notes).
    """
    interval = getattr(settings, "KB_AUTO_RUN_INTERVAL_SECONDS", 0)
    if interval <= 0:
        return
    global _auto_last_run
    now = time.monotonic()
    if now - _auto_last_run < interval:
        return

    db = session_factory()
    try:
        from app.models import KbSource
        from app.services.kb import automation

        users = sorted(
            {
                s.user_id
                for s in db.query(KbSource)
                .filter(KbSource.enabled == True)  # noqa: E712
                .all()
                if s.user_id
            }
        )
        for uid in users:
            try:
                _retry_locked(db, lambda: automation.run_all(db, uid, force=False))
            except Exception:  # noqa: BLE001 — one user's jobs must not kill the loop
                db.rollback()
                logger.exception("Automation pass failed for user %s", uid)
        # Stamp the timer only after the pass completed (or was fully handled)
        # so a crash does not skip the next scheduled window.
        _auto_last_run = time.monotonic()
    finally:
        db.close()


def _auto_loop(session_factory: Callable) -> None:
    """Dedicated automation timer — independent of watcher mode (watchdog or
    polling) so the KB_AUTO_* jobs always run on their own schedule."""
    interval = getattr(settings, "KB_AUTO_RUN_INTERVAL_SECONDS", 0)
    if interval <= 0:
        return
    while not _stop.wait(interval):
        try:
            _maybe_run_automations(session_factory)
        except Exception:  # noqa: BLE001
            logger.exception("Automation pass iteration failed")


def _poll_loop(session_factory: Callable) -> None:
    while not _stop.wait(settings.KB_WATCH_POLL_INTERVAL):
        try:
            _poll_once(session_factory)
        except Exception:  # noqa: BLE001
            logger.exception("Watcher poll iteration failed")


def _start_watchdog(session_factory: Callable) -> bool:
    """Prefer a native watchdog observer; falls back to polling on ImportError."""
    global _observer
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event):  # noqa: ARG002
                if not _stop.is_set():
                    threading.Thread(
                        target=_poll_once, args=(session_factory,), daemon=True
                    ).start()

        observer = Observer()
        db = session_factory()
        try:
            from app.models import KbSource

            sources = (
                db.query(KbSource).filter(KbSource.enabled == True).all()  # noqa: E712
            )
            for source in sources:
                if source.root_path:
                    observer.schedule(_Handler(), source.root_path, recursive=True)
        finally:
            db.close()
        observer.daemon = True
        observer.start()
        _observer = observer
        return True
    except Exception as exc:  # noqa: BLE001 — watchdog missing/broken
        logger.info("watchdog unavailable (%s) — using polling fallback", exc)
        return False


def start_watcher(session_factory: Callable | None = None) -> None:
    """Start the watcher (idempotent). Pass a factory in tests, else app default."""
    global _poll_thread, _auto_thread
    if (_poll_thread and _poll_thread.is_alive()) or _observer is not None:
        return
    _stop.clear()
    if session_factory is None:
        from app.database import SessionLocal

        session_factory = SessionLocal
    # The automation timer runs in its own thread so it fires regardless of
    # whether the native watchdog observer or the polling fallback is active.
    if _auto_thread is None or not _auto_thread.is_alive():
        _auto_thread = threading.Thread(
            target=_auto_loop,
            args=(session_factory,),
            daemon=True,
            name="kb-automation",
        )
        _auto_thread.start()
    if _start_watchdog(session_factory):
        return
    _poll_thread = threading.Thread(
        target=_poll_loop, args=(session_factory,), daemon=True, name="kb-watcher"
    )
    _poll_thread.start()


def stop_watcher() -> None:
    """Stop the watcher, the automation timer, and any in-flight threads."""
    _stop.set()
    global _observer, _poll_thread, _auto_thread
    if _observer is not None:
        try:
            _observer.stop()
            _observer.join(timeout=2)
        except Exception:  # noqa: BLE001
            pass
        _observer = None
    for name, thread in (("poll", _poll_thread), ("auto", _auto_thread)):
        if thread is not None:
            try:
                thread.join(timeout=2)
            except Exception:  # noqa: BLE001
                pass
    _poll_thread = None
    _auto_thread = None
