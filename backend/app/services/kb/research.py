"""Idea 96 — research assistant.

The paper workflow (phrase 51): ingest → summary → contributions → related
papers → cite-aware synthesis. Every LLM step is budget-capped against
``KB_DAILY_GEN_LIMIT`` (phrase 60); deterministic fallbacks keep the workflow
fully functional with ``AI_ENABLED=false``.

- ``summarize`` reuses the Phase 4 Idea 31 summary service (phrase 52).
- ``extract_contributions`` runs a budget-capped ``generate_json``
  (phrase 53); the fallback derives contributions from the summary key points.
- ``related_papers`` ranks the user's library by shared concepts + title
  overlap + shared citations (phrase 54).
- ``synthesize`` answers "explain this paper given my notes" with the hardened
  RAG pipeline — citations mandatory (phrase 55).

Per-user scoping is non-negotiable.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.models import KbDocument, KbEdge
from app.services import ai_client
from app.services.kb import KbService
from app.services.kb import rag as rag_service
from app.services.kb import summarize as summarize_service
from app.services.kb import ai_log as ai_log_service
from app.services.kb.budget import budget_allows, record_generation

logger = logging.getLogger(__name__)

# Doc types treated as research papers for related-paper ranking.
PAPER_DOC_TYPES = ("pdf", "paper", "research")
# Contribution JSON schema (phrase 53).
CONTRIBUTION_KEYS = ("statement", "novelty", "limitation")


def _owned_document(db: Session, user_id: int, document_id: int) -> KbDocument | None:
    return (
        db.query(KbDocument)
        .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
        .first()
    )


def explain(db: Session, user_id: int, document_id: int, question: str | None = None) -> dict:
    """Full paper workflow for one document (phrases 51–55)."""
    doc = _owned_document(db, user_id, document_id)
    if doc is None:
        raise ValueError("document not found")

    summary = summarize_service.get_or_generate_summary(db, user_id, doc)
    contributions = extract_contributions(db, user_id, doc)
    related = related_papers(db, user_id, document_id, limit=5)
    synthesis = synthesize(db, user_id, doc, question) if question else None

    result = {
        "document_id": doc.id,
        "title": doc.title,
        "summary": summary.get("summary"),
        "cached": summary.get("cached", False),
        "contributions": contributions,
        "related": related,
        "synthesis": synthesis,
    }
    ai_log_service.log_event(
        db, user_id,
        feature="research",
        request=f"explain paper {document_id}: {question or ''}",
        response=(str(result.get("summary", {}).get("content") or "")[:1000]),
        retrieval={"document_id": document_id},
    )
    return result


def extract_contributions(db: Session, user_id: int, doc: KbDocument) -> list[dict]:
    """Budget-capped contribution extraction (phrase 53) + fallback."""
    content = summarize_service.document_content(db, doc)[:8000]
    parsed: object | None = None
    used_ai = False
    if ai_client.ai_available() and budget_allows(db, user_id):
        parsed = ai_client.generate_json(
            (
                "Extract the key contributions of this research note. Return ONLY "
                'JSON: {"contributions": [{"statement": "...", "novelty": "...", '
                '"limitation": "..."}]}. Max 5.\nCONTENT:\n'
                f"{content}"
            ),
            max_tokens=1200,
            temperature=0.4,
        )
        contributions = _normalise_contributions(parsed)
        if contributions:
            used_ai = True
            record_generation(db, user_id, "summary")
            return contributions
    return _fallback_contributions(doc)


def _normalise_contributions(parsed: object) -> list[dict]:
    if not isinstance(parsed, dict):
        return []
    raw = parsed.get("contributions")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        statement = str(c.get("statement") or "").strip()
        if not statement or len(statement) > 800:
            continue
        out.append(
            {
                "statement": statement,
                "novelty": str(c.get("novelty") or "").strip()[:400],
                "limitation": str(c.get("limitation") or "").strip()[:400],
            }
        )
    return out[:5]


def _fallback_contributions(doc: KbDocument) -> list[dict]:
    """Deterministic fallback: reuse the summary's key points (phrase 53)."""
    from app.services.ai_fallback import demo_kb_summary

    content = doc.extracted_text or ""
    fallback = demo_kb_summary(content)
    return [
        {"statement": kp, "novelty": "", "limitation": ""}
        for kp in fallback.get("key_points", [])[:5]
    ]


def related_papers(db: Session, user_id: int, document_id: int, limit: int = 5) -> list[dict]:
    """Rank the user's library against the paper (phrase 54).

    Score = 0.5·concept Jaccard + 0.3·title token overlap + 0.2·shared
    citation refs — all deterministic over kb_edges/kb_citations/documents.
    """
    src = _owned_document(db, user_id, document_id)
    if src is None:
        return []
    src_concepts = _document_concepts(db, user_id, document_id)
    src_tokens = _tokens(src.title or "")
    candidates = (
        db.query(KbDocument)
        .filter(
            KbDocument.user_id == user_id,
            KbDocument.id != document_id,
            KbDocument.status != "deleted",
        )
        .all()
    )
    ranked: list[tuple[float, dict]] = []
    for cand in candidates:
        concepts = _document_concepts(db, user_id, cand.id)
        concept_score = _jaccard(src_concepts, concepts)
        title_score = _title_overlap(src_tokens, _tokens(cand.title or ""))
        cite_score = _shared_citations(db, user_id, document_id, cand.id)
        score = 0.5 * concept_score + 0.3 * title_score + 0.2 * cite_score
        if score > 0:
            ranked.append(
                (
                    round(score, 4),
                    {
                        "document_id": cand.id,
                        "title": cand.title,
                        "doc_type": cand.doc_type,
                        "score": round(score, 4),
                        "signals": {
                            "shared_concepts": concept_score,
                            "title_overlap": title_score,
                            "shared_citations": cite_score,
                        },
                    },
                )
            )
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["document_id"]))
    return [item for _score, item in ranked[:limit]]


def _document_concepts(db: Session, user_id: int, document_id: int) -> set[int]:
    return {
        e.target_concept_id
        for e in db.query(KbEdge)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == document_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_concept_id.is_not(None),
        )
        .all()
    }


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", (text or "").lower()))


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _title_overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def _shared_citations(db: Session, user_id: int, doc_a: int, doc_b: int) -> float:
    from app.models import KbCitation

    def _refs(doc_id: int) -> set[str]:
        rows = (
            db.query(KbCitation)
            .filter(KbCitation.user_id == user_id, KbCitation.document_id == doc_id)
            .all()
        )
        return {r.cite_key or r.title or "" for r in rows}

    a, b = _refs(doc_a), _refs(doc_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def synthesize(db: Session, user_id: int, doc: KbDocument, question: str) -> dict:
    """Cite-aware synthesis: paper chunks + the user's notes (phrase 55)."""
    paper_items = _document_chunks_as_items(db, user_id, doc)
    vault_items = rag_service.retrieve(db, user_id, question, limit=4)
    seen = {i.get("chunk_id") for i in vault_items}
    for i in paper_items:
        if i.get("chunk_id") not in seen:
            vault_items.append(i)
            seen.add(i.get("chunk_id"))
    vault_items = vault_items[:8]

    prompt = (
        f"Explain this paper in the context of the learner's question: {question}\n"
        "Ground every claim in the numbered sources and cite them as "
        "[source: path]."
    )
    result = rag_service.generate_grounded(db, user_id, prompt, vault_items, max_tokens=900)
    citations = rag_service.verify_citations(result["answer"], vault_items)
    return {
        **result,
        "citations": citations.get("citations", []),
        "grounded": result["faithfulness_score"] >= rag_service.FAITHFULNESS_THRESHOLD,
    }


def _document_chunks_as_items(db: Session, user_id: int, doc: KbDocument) -> list[dict]:
    from app.models import KbChunk

    chunks = (
        db.query(KbChunk)
        .filter(KbChunk.document_id == doc.id, KbChunk.user_id == user_id)
        .order_by(KbChunk.seq.asc())
        .limit(6)
        .all()
    )
    return [
        {
            "chunk_id": c.id,
            "document_id": doc.id,
            "seq": c.seq,
            "title": doc.title or f"doc {doc.id}",
            "snippet": c.content[:400],
            "score": 1.0,
            "mode": "paper",
            "source_path": doc.path_rel or f"doc {doc.id}",
            "heading_path": c.heading_path,
            "doc_type": doc.doc_type,
            "doc_date": doc.doc_date.isoformat() if doc.doc_date else None,
            "char_start": c.char_start,
            "char_end": c.char_end,
        }
        for c in chunks
    ]


__all__ = ["explain", "extract_contributions", "related_papers", "synthesize"]
