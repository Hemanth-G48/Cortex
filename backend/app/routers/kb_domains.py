"""Flat vault-domain endpoint (audit defect #83).

``GET /api/kb/domains`` returns every top-level vault folder (a "domain") with
its live ``doc_count``, across all courses. Study pages use the nested
``/api/kb/folders?course_id=`` tree; surfaces outside the study flow — the RPG
Life-Areas grid, the habit tracker — only need a flat list they can match by
name against their own areas, so they can show how much vault material backs
each one.

Read-only and cheap: it reads persisted ``KbFolder`` rows, no recomputation.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb.domain_service import list_domains
from app.services.users import current_user

router = APIRouter(prefix="/api/kb", tags=["kb-domains"])


@router.get("/domains")
def get_domains(
    current_user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Top-level vault domains with document counts (all courses)."""
    domains = list_domains(db, current_user.id)
    return {
        "domains": domains,
        "total_documents": sum(d.get("doc_count", 0) for d in domains),
    }
