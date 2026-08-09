"""Idea 91 — multi-agent orchestration router.

- ``POST /api/kb/agents/run`` — run the orchestrator on a request (phrase 5).
- ``GET /api/kb/agents/runs`` — history of agent runs for the user.

Every run is user-scoped, budget-capped, and recorded in ``agent_runs``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.kb import agents as agents_service
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-agents"])


class AgentRunRequest(BaseModel):
    request: str = Field(min_length=2, max_length=2000)
    context: dict | None = None


@router.post("/agents/run")
def run_agents(
    body: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = agents_service.run(db, current_user.id, body.request, body.context)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


@router.get("/agents/runs")
def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"items": agents_service.list_runs(db, current_user.id, limit=limit)}
