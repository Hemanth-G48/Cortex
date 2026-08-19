"""Course sync automation job (Second Brain dynamic courses).

Keeps the Courses page in sync with Second Brain ``course:*`` tags AND
top-level vault folders as a Phase 9 automation job: ``auto_course_sync`` runs
``derive_courses_from_tags`` for the user (idempotent, cheap — bounded by the
number of ``course:*`` tags and folders, not the document count). No LLM cost
→ no ``budget_kind``.

Gated by ``KB_AUTO_COURSE_SYNC_ENABLED`` (default ON: it only touches
``source_type='kb_tag'`` / ``'kb_folder'`` rows and is safe/idempotent —
unlike the other proposal-generating jobs it has no review queue).
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.services.course_derivation import derive_courses_from_tags
from app.services.kb.automation import auto_job

logger = logging.getLogger(__name__)


@auto_job(
    "auto_course_sync",
    toggle="KB_AUTO_COURSE_SYNC_ENABLED",
    cap="",
    description=(
        "Refresh Courses from Second Brain ``course:*`` tags and top-level "
        "vault folders (idempotent, no AI cost)."
    ),
)
def run(db: Session, user_id: int, limit: int | None = None) -> dict:
    """Derive/refresh one Course per ``course:*`` tag and vault folder."""
    summary = derive_courses_from_tags(db, user_id)
    return {
        "processed": summary["course_tags"] + summary["course_folders"],
        "created": summary["created"],
        "updated": summary["updated"],
        "removed": summary["removed"],
        "courses": summary["courses"],
    }
