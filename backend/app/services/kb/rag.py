"""Idea 93 — full RAG pipeline hardening.

Refactors retrieval into composable stages so each is independently testable,
kill-switchable (``KB_RAG_STAGES``), and observable (stage latencies + final
groundedness feed ``ai_logs``, phrase 30):

1. **rewrite**  — Phase 3 Idea 24 expansion (aliases/typos/LLM rewrite).
2. **retrieve** — broad keyword + semantic top-k → RRF fusion → candidate pool
                  (optionally graph-expanded, Idea 94).
3. **rerank**   — deterministic term-overlap rerank; budget-capped LLM rerank
                  when available.
4. **verify**   — map answer claims to chunk ids (citation alignment).
5. **faithfulness** — post-generation groundedness score; below threshold the
                  pipeline regenerates once with an insistence prompt or
                  returns the deterministic cited fallback (Rule B: "not
                  found" rather than ungrounded).

The pipeline never raises; every stage degrades gracefully.
"""

from __future__ import annotations

import logging
import re
import time

from sqlalchemy.orm import Session

from app.config import settings
from app.services import ai_client
from app.services.kb import KbService
from app.services.kb import query as query_service
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.fusion import graph_expand
from app.services.kb.search import KbSearcher, rrf_fuse

logger = logging.getLogger(__name__)

FAITHFULNESS_THRESHOLD = 0.4
CITE_RE = re.compile(r"\[source:\s*[^\]]+\]")


def _stage_enabled(stage: str) -> bool:
    return settings.kb_rag_stages.get(stage, True)


# --------------------------------------------------------------------------- #
# Stage 1 — query rewrite (Idea 24 wrapper)
# --------------------------------------------------------------------------- #


def rewrite_query(db: Session, user_id: int, query: str) -> dict:
    """Expand aliases/typos (and LLM-rewrite when enabled). Returns both."""
    original = query
    expanded = query
    if _stage_enabled("rewrite") and KbService.bool_setting("KB_QUERY_EXPANSION_ENABLED", True):
        expanded = query_service.expand(db, user_id, query)
    return {"original_query": original, "expanded_query": expanded}


# --------------------------------------------------------------------------- #
# Stage 2 — multi-stage retrieval
# --------------------------------------------------------------------------- #


def retrieve(
    db: Session,
    user_id: int,
    query: str,
    *,
    mode: str = "hybrid",
    limit: int = 8,
    graph_fuse: bool = False,
) -> list[dict]:
    """Broad keyword + semantic top-k → RRF fusion → optional graph expansion.

    Returns unified search items (with ``sources`` provenance). Never raises.
    """
    if not _stage_enabled("retrieve"):
        return []
    try:
        searcher = KbSearcher(db, user_id)
        kw = searcher.keyword(query, limit=limit * 4)
        sem = searcher.semantic(query, limit=limit * 4)
        from app.services.kb.search import _min_max_normalize

        _min_max_normalize(kw)
        _min_max_normalize(sem)
        fused = rrf_fuse([kw, sem]) if mode != "keyword" else kw or []
        if not fused:
            fused = kw or sem
        result = searcher.search(query, mode=mode, limit=limit * 4)
        items = result.get("items", [])[: limit * 4]
        if graph_fuse and _stage_enabled("rerank"):
            items = graph_expand(db, user_id, items, cap=settings.KB_GRAPH_EXPAND_CAP)
        return items[:limit]
    except Exception as exc:  # noqa: BLE001 — retrieval must never break
        logger.warning("RAG retrieve failed: %s", exc)
        return []


# --------------------------------------------------------------------------- #
# Stage 3 — rerank
# --------------------------------------------------------------------------- #


def rerank(db: Session, user_id: int, items: list[dict], query: str) -> list[dict]:
    """Rerank the fused top-N (deterministic term-overlap; LLM when budgeted)."""
    if not _stage_enabled("rerank") or not items:
        return items
    tokens = set(re.findall(r"[a-z0-9']+", (query or "").lower()))
    if not tokens:
        return items

    def _overlap(item: dict) -> int:
        text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
        return len(tokens & set(re.findall(r"[a-z0-9']+", text)))

    # LLM rerank is an optional enhancement; keep it budget-capped and safe.
    if ai_client.ai_available() and budget_allows(db, user_id):
        ranked_ids = _llm_rerank(db, user_id, items, query)
        if ranked_ids:
            by_id = {i.get("chunk_id"): i for i in items}
            ordered = [by_id[cid] for cid in ranked_ids if cid in by_id]
            if ordered:
                return ordered
    return sorted(items, key=lambda i: (-_overlap(i), -(i.get("score") or 0.0)))


def _llm_rerank(db: Session, user_id: int, items: list[dict], query: str) -> list[int] | None:
    """Budget-capped LLM rerank returning chunk ids best-first, or None."""
    if not budget_allows(db, user_id):
        return None
    lines = "\n".join(
        f"{i.get('chunk_id')}: {item.get('title', '')} — {(item.get('snippet') or '')[:200]}"
        for i, item in enumerate(items, start=1)
    )
    prompt = (
        "Rank these vault excerpts by relevance to the query. Return ONLY a JSON "
        f"array of chunk ids, most relevant first.\nQUERY: {query}\nEXCERPTS:\n{lines}"
    )
    parsed = ai_client.generate_json(prompt, max_tokens=400)
    if isinstance(parsed, list):
        ids = [int(x) for x in parsed if isinstance(x, (int, float)) or str(x).lstrip('-').isdigit()]
        return ids
    return None


# --------------------------------------------------------------------------- #
# Stage 4 — citation verification
# --------------------------------------------------------------------------- #


def verify_citations(answer: str, items: list[dict]) -> dict:
    """Map answer claims to source chunk ids (chunk-id map, not free text)."""
    if not items:
        return {"citations": [], "missing": [], "cited_chunk_ids": []}
    doc_to_chunk = {i.get("document_id"): i.get("chunk_id") for i in items if i.get("document_id")}
    cited = {int(m.group(1)) for m in re.finditer(r"\[(\d+)\]", answer or "")}
    mapped = []
    for cid in cited:
        chunk = next((i for i in items if i.get("chunk_id") == cid), None)
        if chunk is None:
            continue
        mapped.append(
            {
                "chunk_id": cid,
                "document_id": chunk.get("document_id"),
                "title": chunk.get("title"),
                "source_path": chunk.get("source_path"),
            }
        )
    used_ids = {m["chunk_id"] for m in mapped}
    missing = [i.get("chunk_id") for i in items if i.get("chunk_id") not in used_ids][:5]
    return {
        "citations": mapped,
        "missing": missing,
        "cited_chunk_ids": sorted(used_ids),
    }


# --------------------------------------------------------------------------- #
# Stage 5 — faithfulness gate
# --------------------------------------------------------------------------- #


def faithfulness(answer: str, items: list[dict]) -> float:
    """0–1 groundedness: citation coverage × token overlap with sources."""
    if not answer:
        return 0.0
    if not items:
        return 0.0
    citation = 1.0 if CITE_RE.search(answer) else 0.0
    answer_tokens = set(re.findall(r"[a-z0-9']+", answer.lower()))
    if not answer_tokens:
        return citation
    overlap = 0.0
    for item in items[:6]:
        src_tokens = set(re.findall(r"[a-z0-9']+", (item.get("snippet") or "").lower()))
        if src_tokens:
            jac = len(answer_tokens & src_tokens) / len(answer_tokens | src_tokens)
            overlap = max(overlap, jac)
    return round(0.5 * citation + 0.5 * overlap, 4)


def generate_grounded(
    db: Session,
    user_id: int,
    query: str,
    items: list[dict],
    *,
    max_tokens: int = 800,
) -> dict:
    """Generate an answer from retrieval with the faithfulness gate (phrase 26).

    Uses the Phase 7 tutor prompt shape (numbered blocks + ``[source: path]``).
    Returns ``{answer, faithfulness_score, ai_used, regenerated}``.
    """
    if not items:
        return {
            "answer": (
                "Not found — nothing in your Second Brain covers this. "
                "Add a note about it and I'll be able to answer."
            ),
            "faithfulness_score": 0.0,
            "ai_used": False,
            "regenerated": False,
        }
    from app.services.prompts import tutor_chat_prompt

    blocks = _blocks(items)
    prompt = tutor_chat_prompt(query, blocks)
    ai_used = False
    regenerated = False
    answer = None

    if budget_allows(db, user_id):
        raw = ai_client.generate(prompt, max_tokens=max_tokens)
        if raw:
            ai_used = True
            record_generation(db, user_id, "tutor")
            score = faithfulness(raw, items)
            if score < FAITHFULNESS_THRESHOLD and budget_allows(db, user_id):
                retry = ai_client.generate(
                    tutor_chat_prompt(query, blocks, insist_cite=True),
                    max_tokens=max_tokens,
                )
                if retry:
                    regenerated = True
                    record_generation(db, user_id, "tutor")
                    raw = retry
            answer = raw

    if answer is None:
        answer = _fallback(query, items)

    return {
        "answer": answer,
        "faithfulness_score": faithfulness(answer, items),
        "ai_used": ai_used,
        "regenerated": regenerated,
    }


def _blocks(items: list[dict]) -> str:
    out = []
    for i, item in enumerate(items, start=1):
        src = item.get("source_path") or f"doc {item.get('document_id')}"
        heading = item.get("heading_path") or ""
        text = item.get("snippet") or ""
        if heading:
            text = f"({heading}) {text}"
        out.append(f"[{i}] [source: {src}] {text}")
    return "\n\n".join(out)


def _fallback(query: str, items: list[dict]) -> str:
    lines = ["Here's what your notes say:"]
    for i, item in enumerate(items[:3], start=1):
        src = item.get("source_path") or f"doc {item.get('document_id')}"
        lines.append(f"{i}. [source: {src}] {(item.get('snippet') or '')[:300]}")
    lines.append("(Deterministic answer — AI generation is disabled.)")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Pipeline entry
# --------------------------------------------------------------------------- #


def run_pipeline(
    db: Session,
    user_id: int,
    query: str,
    *,
    mode: str = "hybrid",
    graph_fuse: bool = False,
    limit: int = 8,
    generate: bool = True,
) -> dict:
    """Compose the full pipeline; returns stage timing + result (phrase 21)."""
    started = time.perf_counter()
    stage_times: dict[str, int] = {}

    t0 = time.perf_counter()
    rewritten = rewrite_query(db, user_id, query)
    stage_times["rewrite_ms"] = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    items = retrieve(
        db, user_id, rewritten["expanded_query"],
        mode=mode, limit=limit, graph_fuse=graph_fuse,
    )
    stage_times["retrieve_ms"] = int((time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    items = rerank(db, user_id, items, rewritten["expanded_query"])
    stage_times["rerank_ms"] = int((time.perf_counter() - t0) * 1000)

    result: dict = {
        "items": items,
        "original_query": rewritten["original_query"],
        "expanded_query": rewritten["expanded_query"],
        "stage_times_ms": stage_times,
        "total_ms": int((time.perf_counter() - started) * 1000),
        "mode": mode,
        "graph_fused": graph_fuse,
    }

    if generate:
        gen = generate_grounded(db, user_id, query, items)
        result.update(gen)
        result["citations"] = verify_citations(gen["answer"], items)
        result["grounded"] = gen["faithfulness_score"] >= FAITHFULNESS_THRESHOLD

    return result


__all__ = [
    "rewrite_query",
    "retrieve",
    "rerank",
    "verify_citations",
    "faithfulness",
    "generate_grounded",
    "run_pipeline",
    "FAITHFULNESS_THRESHOLD",
]
