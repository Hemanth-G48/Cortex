"""KbEvalRun model — retrieval evaluation run (Phase 3, Idea 26).

Stores one row per ``python -m app.cli.kb eval`` invocation: the golden-set
name, mode, aggregate metrics (recall@k / precision@k / MRR), and a timestamp,
so the dashboard can chart metric drift across retrieval changes (phrase 55).
The ``faithfulness`` column is the Phase 4 answer-groundedness stub (phrase 58)
— documented but not yet computed.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func

from app.database import Base


class KbEvalRun(Base):
    __tablename__ = "kb_eval_runs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    # Name of the golden set, e.g. "kb_eval/cybersecurity".
    golden_set = Column(String(120), nullable=False, index=True)
    # keyword | semantic | hybrid
    mode = Column(String(20), default="hybrid")
    queries = Column(Integer, default=0)
    recall_at_k = Column(Float, default=0.0)
    precision_at_k = Column(Float, default=0.0)
    mrr = Column(Float, default=0.0)
    # Phase 4 stub: answer groundedness (not computed in Phase 3).
    faithfulness = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
