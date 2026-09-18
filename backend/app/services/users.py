"""Single-owner identity.

The application is a local, single-user app: there is exactly one owner
(the first ``users`` row, seeded at startup). Every domain row is scoped to
that owner via ``user_id``. This module is the single place that resolves
"the current user" — production requests carry no tokens and no roles.
"""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def current_user(db: Session = Depends(get_db)) -> User:
    """Return the single application owner (the first ``users`` row).

    Self-healing: if no row exists (a bare database file before seeding) a
    minimal profile is created so requests never fail.

    NOTE: this function does NOT verify any auth token — it always returns the
    single owner. This is intentional for the production app (single-user,
    tokenless). For per-user isolation in tests, the conftest overrides this
    with ``_test_current_user`` which does verify bearer tokens.
    """
    user = db.query(User).order_by(User.id).first()
    if user is None:
        user = User(name="Owner")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def owner_from_db(db: Session) -> User:
    """Explicit name for the tokenless owner lookup.

    Use this in service functions that need the owner but should not be
    confused with an auth dependency. The auth dependency is
    ``current_user`` (above) — which, despite the name, is also tokenless in
    production.
    """
    return current_user(db)


def current_user_id(db: Session) -> int:
    """Return the owner's id (kept for the services that take an int)."""
    return current_user(db).id
