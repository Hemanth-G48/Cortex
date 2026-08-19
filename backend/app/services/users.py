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
    """
    user = db.query(User).order_by(User.id).first()
    if user is None:
        user = User(name="Owner")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def current_user_id(db: Session) -> int:
    """Return the owner's id (kept for the services that take an int)."""
    return current_user(db).id
