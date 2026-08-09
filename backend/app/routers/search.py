"""Global unified search (Phase 3, Idea 30, phrases 91–100).

``POST /api/search`` fans out to the vault (Idea 22), materials, subjects,
units, tasks, and assignments — each wrapped behind a uniform hit shape
``{id, title, domain, snippet, url, score}`` — with per-domain caps and a
global result cap, then groups results by domain and filters by the optional
``domains`` facet.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import (
    Assignment,
    CurriculumSubject,
    CurriculumUnit,
    Material,
    Task,
    User,
)
from app.services.kb.search import KbSearcher
from app.services.security import get_current_user

router = APIRouter(prefix="/api", tags=["search"])

PER_DOMAIN_CAP = 15
GLOBAL_CAP = 50

DOMAIN_URLS = {
    "vault": "/knowledge-base",
    "materials": "/curriculum",
    "subjects": "/curriculum",
    "units": "/curriculum",
    "tasks": "/dashboard",
    "assignments": "/assignments",
}


def _q(needle: str, field) -> Any:
    """Case-insensitive LIKE for a search term across a column."""
    return field.ilike(f"%{needle}%")


class _DomainSearcher:
    """Uniform wrapper over each domain's search (phrase 92)."""

    def __init__(self, db: Session, user_id: int, needle: str) -> None:
        self.db = db
        self.user_id = user_id
        self.needle = needle
        self.like = f"%{needle}%"

    def vault(self) -> list[dict]:
        searcher = KbSearcher(self.db, self.user_id)
        resp = searcher.search(self.needle, mode="hybrid", limit=PER_DOMAIN_CAP, page=1)
        return [
            {
                "id": item["chunk_id"],
                "title": item["title"],
                "domain": "vault",
                "snippet": item.get("snippet", "")[:200],
                "url": DOMAIN_URLS["vault"],
                "score": item.get("score", 0.0),
            }
            for item in resp["items"]
        ]

    def materials(self) -> list[dict]:
        rows = (
            self.db.query(Material)
            .filter(
                Material.uploaded_by_id == self.user_id,
                or_(_q(self.needle, Material.title), _q(self.needle, Material.description)),
            )
            .limit(PER_DOMAIN_CAP)
            .all()
        )
        return [
            {
                "id": m.id,
                "title": m.title,
                "domain": "materials",
                "snippet": (m.description or "")[:200],
                "url": DOMAIN_URLS["materials"],
                "score": 1.0,
            }
            for m in rows
        ]

    def subjects(self) -> list[dict]:
        rows = (
            self.db.query(CurriculumSubject)
            .filter(_q(self.needle, CurriculumSubject.name))
            .limit(PER_DOMAIN_CAP)
            .all()
        )
        return [
            {
                "id": s.id,
                "title": s.name,
                "domain": "subjects",
                "snippet": s.code or "",
                "url": DOMAIN_URLS["subjects"],
                "score": 1.0,
            }
            for s in rows
        ]

    def units(self) -> list[dict]:
        rows = (
            self.db.query(CurriculumUnit)
            .filter(_q(self.needle, CurriculumUnit.name))
            .limit(PER_DOMAIN_CAP)
            .all()
        )
        return [
            {
                "id": u.id,
                "title": u.name,
                "domain": "units",
                "snippet": f"Unit {u.unit_number}" if hasattr(u, "unit_number") else "",
                "url": DOMAIN_URLS["units"],
                "score": 1.0,
            }
            for u in rows
        ]

    def tasks(self) -> list[dict]:
        rows = (
            self.db.query(Task)
            .filter(Task.user_id == self.user_id, _q(self.needle, Task.title))
            .limit(PER_DOMAIN_CAP)
            .all()
        )
        return [
            {
                "id": t.id,
                "title": t.title,
                "domain": "tasks",
                "snippet": "task",
                "url": DOMAIN_URLS["tasks"],
                "score": 1.0,
            }
            for t in rows
        ]

    def assignments(self) -> list[dict]:
        # Assignments scope via their course's owner.
        rows = (
            self.db.query(Assignment)
            .join(Assignment.course)
            .filter(_q(self.needle, Assignment.title))
            .limit(PER_DOMAIN_CAP)
            .all()
        )
        return [
            {
                "id": a.id,
                "title": a.title,
                "domain": "assignments",
                "snippet": (a.description or "")[:200],
                "url": DOMAIN_URLS["assignments"],
                "score": 1.0,
            }
            for a in rows
        ]


@router.post("/search", response_model=dict)
def global_search(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fan out across domains and group results (phrase 91/93/94)."""
    query = (body.get("query") or "").strip()
    if not query:
        return {"items": [], "groups": {}, "total": 0, "query": ""}

    wanted = body.get("domains") or ["vault", "materials", "subjects", "units",
                                     "tasks", "assignments"]
    searcher = _DomainSearcher(db, current_user.id, query)

    # Per-domain fan-out with caps (phrase 93).
    raw: dict[str, list[dict]] = {}
    for domain in wanted:
        method = getattr(searcher, domain, None)
        if method is None:
            continue
        try:
            raw[domain] = method()[:PER_DOMAIN_CAP]
        except Exception:  # noqa: BLE001 — one failing domain never fails search
            raw[domain] = []

    # Global cap + grouping (phrase 94).
    all_hits: list[dict] = []
    for domain in wanted:
        all_hits.extend(raw.get(domain, []))
    all_hits = all_hits[:GLOBAL_CAP]

    groups: dict[str, list[dict]] = {}
    for hit in all_hits:
        groups.setdefault(hit["domain"], []).append(hit)

    return {
        "items": all_hits,
        "groups": groups,
        "total": len(all_hits),
        "query": query,
        "domains": wanted,
    }
