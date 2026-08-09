"""Folder watcher (Idea 3, phrases 28–29).

An optional ``watchdog`` observer (native dependency) with a pure-polling
fallback behind an import guard — CI never needs watchdog installed. The
watcher is started/stopped from the app lifespan and skipped under pytest.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from app.config import settings

logger = logging.getLogger(__name__)

_stop = threading.Event()
_poll_thread: threading.Thread | None = None
_observer = None


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
                scan_and_ingest(db, source.id)
            except Exception:  # noqa: BLE001 — one bad source must not kill the loop
                logger.exception("Watcher scan failed for source %s", source.id)
    finally:
        db.close()


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
    global _poll_thread
    if (_poll_thread and _poll_thread.is_alive()) or _observer is not None:
        return
    _stop.clear()
    if session_factory is None:
        from app.database import SessionLocal

        session_factory = SessionLocal
    if _start_watchdog(session_factory):
        return
    _poll_thread = threading.Thread(
        target=_poll_loop, args=(session_factory,), daemon=True, name="kb-watcher"
    )
    _poll_thread.start()


def stop_watcher() -> None:
    """Stop the watcher and any in-flight poll thread."""
    _stop.set()
    global _observer
    if _observer is not None:
        try:
            _observer.stop()
            _observer.join(timeout=2)
        except Exception:  # noqa: BLE001
            pass
        _observer = None
