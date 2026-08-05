"""Single-user identity helper.

Multi-user auth is deferred (Zenith-Study-Planner G1, Phase 5 deferred per
user decision): every domain row is scoped to the seeded first user. This is
the single place that resolves "current user", so switching to real auth
later only touches this file.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User


def current_user_id(db: Session) -> int:
    """Return the id of the active user (the seeded first user in single-user mode)."""
    user = db.query(User).first()
    return user.id if user else 1
