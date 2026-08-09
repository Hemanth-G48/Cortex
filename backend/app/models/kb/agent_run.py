"""AgentRun model — the Phase 10 multi-agent orchestration record (Idea 91).

One row per ``POST /api/kb/agents/run``: the user request, the planner's
composed ``plan`` (ordered steps with agents + budgets), each step's ``steps``
output, the composed ``result``, plus latency/cost so the observability layer
(Idea 100) can meter agent work exactly like every other AI surface.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func

from app.database import Base


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request = Column(Text, nullable=False)
    # Ordered step spec: [{agent, inputs, expected_output, budget}] (phrase 1).
    plan = Column(Text, nullable=True)
    # Per-step outputs: [{agent, status, output, latency_ms}] (phrase 3).
    steps = Column(Text, nullable=True)
    # Composed final answer (phrase 3).
    result = Column(Text, nullable=True)
    # queued | running | done | failed
    status = Column(String(20), default="queued", index=True)
    latency_ms = Column(Integer, default=0)
    cost_estimate = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    finished_at = Column(DateTime, nullable=True)
