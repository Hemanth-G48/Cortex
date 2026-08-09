"""Search endpoints (Phase 3, Ideas 21–25).

``GET /api/kb/search`` / ``POST /api/kb/search`` — keyword, semantic, and
hybrid modes behind one response shape. Query expansion (Idea 24) and search
feedback (Idea 29) mount here.
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import KbSearchEvent, User
from app.schemas.kb import (
    KbSearchRequest,
    KbSearchResponse,
    KbSearchItem,
)
from app.services.kb import KbService
from app.services.kb import query as query_service
from app.services.kb.search import KbSearcher
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-search"])


@router.post("/search", response_model=KbSearchResponse)
def search(
    body: KbSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run retrieval in the requested mode (keyword|semantic|hybrid).

    Records the search into ``kb_search_events`` automatically (Idea 29,
    phrase 83) so every query is covered without frontend cooperation.
    """
    raw = (body.query or "").strip()
    if not raw:
        raise HTTPException(400, "query must not be empty")
    if len(raw) < 1:
        raise HTTPException(400, "query too short")

    # Query expansion pipeline (Idea 24) — kill-switchable.
    expanded = raw
    if KbService.bool_setting("KB_QUERY_EXPANSION_ENABLED", True):
        expanded = query_service.expand(db, current_user.id, raw)

    searcher = KbSearcher(db, current_user.id)
    mode = (body.mode or "hybrid").lower()
    result = searcher.search(
        expanded,
        mode=mode if mode != "graph_fused" else "hybrid",
        limit=body.page_size,
        page=body.page,
    )
    # Phase 10 (Idea 94, phrase 35): graph+vector fusion — expand the hybrid
    # hits via kb_edges neighbors and re-label the mode.
    if mode == "graph_fused":
        from app.services.kb.fusion import graph_expand

        items = result.get("items", [])
        fused = graph_expand(
            db, current_user.id, items, cap=settings.KB_GRAPH_EXPAND_CAP
        )
        result["items"] = fused
        result["total"] = len(fused)
        result["mode"] = "graph_fused"
    result["original_query"] = raw
    result["expanded_query"] = expanded

    # Log the search event (best-effort; never fail the request).
    try:
        top_ids = [i["chunk_id"] for i in result["items"][:20]]
        db.add(
            KbSearchEvent(
                user_id=current_user.id,
                query=raw,
                mode=result["mode"],
                result_ids=json.dumps(top_ids) if top_ids else None,
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()

    items = [KbSearchItem(**i) for i in result["items"]]
    return KbSearchResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        mode=result["mode"],
        original_query=result["original_query"],
        expanded_query=result["expanded_query"],
    )


@router.get("/search", response_model=KbSearchResponse)
def search_get(
    q: str,
    mode: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """GET variant of the search endpoint (simple curl / linkable results)."""
    if not q or not q.strip():
        raise HTTPException(400, "query must not be empty")
    return search(
        KbSearchRequest(query=q.strip(), mode=mode, page=page, page_size=page_size),
        current_user=current_user,
        db=db,
    )


# --------------------------------------------------------------------------- #
# Idea 29 — search feedback & implicit click tracking
# --------------------------------------------------------------------------- #

@router.post("/search/feedback", response_model=dict)
def search_feedback(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record explicit thumbs up/down (or implicit click) on a search result.

    Body: ``{query, mode?, chunk_id?, clicked?, rating?}``. Rating is
    ``-1 | 0 | 1``; ``clicked=true`` records an implicit click (Idea 25,
    phrase 48). Writes into ``kb_search_events``.
    """
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(400, "query is required")
    chunk_id = body.get("chunk_id")
    clicked = bool(body.get("clicked", False))
    rating = body.get("rating")

    event = KbSearchEvent(
        user_id=current_user.id,
        query=query,
        mode=body.get("mode") or "hybrid",
        result_ids=json.dumps([chunk_id]) if chunk_id else None,
        clicked_id=chunk_id if clicked else None,
        rating=rating,
    )
    db.add(event)
    db.commit()
    return {"ok": True, "event_id": event.id}


@router.get("/search/events", response_model=dict)
def search_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
):
    """Per-user search history + feedback (Idea 29, phrase 89).

    The same list backs the frontend "preferred sources" hint and the
    privacy purge endpoint.
    """
    events = (
        db.query(KbSearchEvent)
        .filter(KbSearchEvent.user_id == current_user.id)
        .order_by(KbSearchEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": e.id,
                "query": e.query,
                "mode": e.mode,
                "clicked_id": e.clicked_id,
                "rating": e.rating,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "total": len(events),
    }


@router.delete("/search/events", response_model=dict)
def purge_search_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Privacy: delete this user's search events (phrase 89)."""
    deleted = (
        db.query(KbSearchEvent)
        .filter(KbSearchEvent.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "deleted": deleted}
