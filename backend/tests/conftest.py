"""
Pytest configuration for the Student Life OS backend.
Creates an isolated in-memory SQLite database per test session.

Hermetic by construction (audit M2): before anything imports the app, the
environment is redirected away from the developer's real database and uploads
directory — the FastAPI lifespan inside ``TestClient`` runs
``create_all``/``migrate_schema``/``seed_database`` against the *app's* engine,
so without this redirect every ``client`` test would read and mutate
``backend/student_os.db``. The app engine is pointed at a throwaway temp file
that is deleted at session exit.
"""

import os
import tempfile
from pathlib import Path

# ── Hermetic environment (MUST run before any ``app.*`` import) ──
# ``app.database`` binds the engine at import time using
# ``settings.DATABASE_URL``; ``main.py`` mounts ``settings.UPLOAD_DIR`` as a
# static dir and lifespan mkdirs it. Redirect both to a per-session temp
# location so tests never touch the real files.
_TMPDIR = tempfile.mkdtemp(prefix="slos-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"
os.environ.setdefault("UPLOAD_DIR", os.path.join(_TMPDIR, "uploads"))
os.environ.setdefault("KB_WATCH_ENABLED", "false")
os.environ.setdefault("EMBEDDINGS_BACKEND", "hash")

import pytest
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import User
from app.seed import seed_database
from app.services.security import decode_bearer_token
from app.services.users import current_user as _tokenless_current_user
from main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db_session():
    """Create a clean database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    seed_database(session)
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


_test_bearer = HTTPBearer(auto_error=False)


def _test_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_test_bearer),
    db=Depends(get_db),
) -> User:
    """Test-only dependency override for ``current_user``.

    Production ignores any Authorization header and always resolves the
    single owner. In tests, a valid bearer token (minted by the legacy
    ``/api/auth/signup`` shim) still resolves to that token's user so the
    existing per-user isolation tests keep exercising the ``user_id``
    scoping; requests without a token resolve to the single owner.
    """
    if credentials and credentials.credentials:
        payload = decode_bearer_token(credentials.credentials)
        if payload:
            user = db.query(User).filter(User.id == payload["user_id"]).first()
            if user is not None:
                return user
    return _tokenless_current_user(db)


@pytest.fixture(scope="function")
def kb_eval_fixture_dir() -> Path:
    """Shared KB eval golden-set directory (audit T1).

    Centralizes the fixture path so KB eval tests don't each reconstruct
    ``Path(__file__).parent / "fixtures" / "kb_eval"``. Test files can
    parametrize over the JSON files inside instead of duplicating setup.
    """
    return Path(__file__).parent / "fixtures" / "kb_eval"


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with seeded in-memory database."""
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[_tokenless_current_user] = _test_current_user
    with TestClient(app) as c:
        yield c
    # Clean up overrides so no state leaks between tests (audit M2).
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(_tokenless_current_user, None)


def pytest_sessionfinish(session, exitstatus):
    """Delete the throwaway app-engine DB/uploads at session end."""
    import shutil

    shutil.rmtree(_TMPDIR, ignore_errors=True)
