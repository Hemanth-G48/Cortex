"""Phase 7 AI tutor — RAG-grounded answers with mandatory citations (Idea 61).

``tutor_chat`` is the vault-aware counterpart of ``/api/ai/chat``: every user
message is run through Phase 3 hybrid retrieval, the top chunks are injected
as numbered context blocks with ``[source: path]`` markers, and the model must
cite or say it does not know. Empty retrieval → a capture prompt, never
hallucination (Rule A).

``tutor_doubt`` (Idea 62) re-walks a problem after explaining the blocking
concept: retrieved chunks are intersected with the topic DAG + ``kb_concepts``
to find what the student is missing, the gap is explained first, then the
problem is re-walked step by step (phrases 11–17).

The ``user_memory`` seam (Idea 79, Phase 8) is stubbed: when a user_memory
table exists in Phase 8, ``_user_memory`` will return strengths/weaknesses;
until then it returns None and the prompt omits the block gracefully.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbConcept, Topic, TopicDependency, TutorMessage, TutorSession
from app.services import ai_client
from app.services.kb import KbService
from app.services.kb import memory as memory_service
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb.mastery import log_event
from app.services.kb.search import KbSearcher

logger = logging.getLogger(__name__)

CITE_RE = re.compile(r"\[source:\s*[^\]]+\]")
# Reference phrasing the tutor may use for concepts in user_memory (Rule A).
REFERENCE_RE = re.compile(
    r"as you saw in your notes on\s+([A-Za-z0-9][A-Za-z0-9 &'_\-]*?)(?=[.,;!?)]|\s+and\s|\s+but\s|\s+for\s|\s+when\s|$)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Retrieval + context assembly
# --------------------------------------------------------------------------- #
def retrieve_chunks(db: Session, user_id: int, query: str, limit: int | None = None) -> list[dict]:
    """Hybrid retrieval → unified search items (phrase 3). Degrades to [].

    Runs the same query-expansion pipeline as the search router (Idea 24) so
    aliases/abbreviations expand before FTS + semantic retrieval.
    """
    limit = limit or settings.KB_TUTOR_MAX_CHUNKS
    try:
        searcher = KbSearcher(db, user_id)
        # Try the raw query first. FTS AND-joins bare tokens, so expansion
        # that *adds* terms (e.g. alias canonical names) can zero-out results
        # when the doc lacks the added phrase — retry with the expanded query
        # only when the raw pass misses (Idea 24, phrase 38).
        items = _search_once(db, user_id, searcher, query, limit)
        if not items and KbService.bool_setting("KB_QUERY_EXPANSION_ENABLED", True):
            from app.services.kb import query as query_service

            expanded = query_service.expand(db, user_id, query)
            if expanded != query:
                items = _search_once(db, user_id, searcher, expanded, limit)
        # Progressive token drop: natural-language questions carry filler
        # words the vault may never contain ("stuck on choosing the loss…").
        # FTS AND-joins bare tokens, so drop trailing tokens until a pass
        # matches or only the first token remains.
        if not items:
            tokens = re.findall(r"[a-z0-9']+", query.lower())
            while len(tokens) > 1:
                tokens = tokens[:-1]
                items = _search_once(db, user_id, searcher, " ".join(tokens), limit)
                if items:
                    break
        return items
    except Exception as exc:  # noqa: BLE001 — retrieval must never break chat
        logger.warning("Tutor retrieval failed: %s", exc)
        return []


def _search_once(db: Session, user_id: int, searcher: KbSearcher, q: str, limit: int) -> list[dict]:
    """One hybrid search pass; returns unified items (never raises)."""
    try:
        result = searcher.search(q, mode="hybrid", limit=limit)
        return result.get("items", [])[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tutor search pass failed: %s", exc)
        return []


def context_blocks(items: list[dict]) -> str:
    """Numbered context blocks with ``[source: path]`` markers (phrase 4)."""
    blocks = []
    for i, item in enumerate(items, start=1):
        src = item.get("source_path") or f"doc {item.get('document_id')}"
        heading = item.get("heading_path") or ""
        text = item.get("snippet") or ""
        if heading:
            text = f"({heading}) {text}"
        blocks.append(f"[{i}] [source: {src}] {text}")
    return "\n\n".join(blocks)


def _sources_dict(items: list[dict]) -> list[dict]:
    return [
        {
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "title": item.get("title"),
            "source_path": item.get("source_path"),
            "snippet": (item.get("snippet") or "")[:400],
            "score": item.get("score"),
        }
        for item in items
    ]


def _user_memory(db: Session, user_id: int) -> dict | None:
    """Phase 8 (Idea 79) strengths/weaknesses — real memory rows (phrase 31).

    Returns None when the user has no memory yet, so the prompt omits the
    strengths/weaknesses block gracefully (backward-compatible).
    """
    rows = memory_service.get_memory(db, user_id, limit=50)
    if not rows:
        return None
    strengths = [r["concept"] for r in rows if r["strength"] >= settings.kb_memory_anchor_min]
    weaknesses = [r["concept"] for r in rows if 0 < r["strength"] < settings.kb_memory_anchor_min]
    if not strengths and not weaknesses:
        return None
    return {"strengths": strengths, "weaknesses": weaknesses}


def _known_context(db: Session, user_id: int, limit: int = 10) -> list[dict]:
    """Top memory rows by strength for the "Known context" prompt block (phrase 32).

    Only rows with strength > 0 are listed — the exact set Rule A allows the
    tutor to reference.
    """
    return [
        {"concept": r["concept"], "strength": r["strength"], "last_seen": r["last_seen"]}
        for r in memory_service.get_memory(db, user_id, limit=limit)
        if r["strength"] > 0
    ]


def _rule_a_sanitize(answer: str, known: set[str]) -> str:
    """Strip references to concepts NOT in user_memory (Rule A, phrase 35).

    The prompt only authorises "as you saw in your notes on X" for concepts in
    ``known_context``; this post-check neutralises any reference to something
    else (or to anything at all when memory is empty) so the tutor never claims
    prior knowledge it cannot prove.
    """
    if not answer:
        return answer
    if not known:
        return REFERENCE_RE.sub("as you saw in your notes", answer)

    def _replace(match: re.Match) -> str:
        concept = match.group(1).strip()
        if concept.lower() in known:
            return match.group(0)
        return "as you saw in your notes"

    return REFERENCE_RE.sub(_replace, answer)


def _log_recalls(db: Session, user_id: int, answer: str, known: set[str]) -> None:
    """Log every tutor reference into learning_events (event_type=recall, phrase 40)."""
    if not known or not answer:
        return
    for match in REFERENCE_RE.finditer(answer):
        if match.group(1).strip().lower() in known:
            log_event(db, user_id, event_type="recall", topic_id=None, value=1.0)
    db.flush()


def _bump_turn_concepts(db: Session, user_id: int, items: list[dict]) -> None:
    """Bump memory for concepts the tutor actually surfaced this turn (phrase 34).

    The tutor turn is a study surface: any concept MENTIONed by the retrieved
    source documents is reinforced with a small delta under source=tutor.
    """
    doc_ids = {i.get("document_id") for i in items if i.get("document_id")}
    if not doc_ids:
        return
    from app.models import KbEdge

    rows = (
        db.query(KbEdge.target_concept_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
            KbEdge.source_document_id.in_(doc_ids),
        )
        .all()
    )
    concept_ids = list({r[0] for r in rows})
    if concept_ids:
        memory_service.bump(db, user_id, concept_ids, delta=0.05, source="tutor")


def _roll(prompt: str, *, max_tokens: int = 800) -> str | None:
    """One budget-capped LLM call; None when AI is off/unreachable."""
    if not ai_client.ai_available():
        return None
    return ai_client.generate(prompt, max_tokens=max_tokens)


# --------------------------------------------------------------------------- #
# Session history (phrase 8)
# --------------------------------------------------------------------------- #
def get_or_create_session(db: Session, user_id: int, session_id: int | None) -> TutorSession:
    if session_id is not None:
        session = db.query(TutorSession).get(session_id)
        if session is not None and session.user_id == user_id:
            return session
    session = TutorSession(user_id=user_id)
    db.add(session)
    db.flush()
    return session


def _history_turns(db: Session, user_id: int, session_id: int, limit: int | None = None) -> str:
    """Rolling assistant-turn window for prompt context (phrase 8)."""
    limit = limit or settings.KB_TUTOR_HISTORY_TURNS
    rows = (
        db.query(TutorMessage)
        .filter(TutorMessage.session_id == session_id, TutorMessage.user_id == user_id)
        .order_by(TutorMessage.id.desc())
        .limit(limit * 2)
        .all()
    )
    rows.reverse()
    return "\n".join(f"{m.role}: {m.content[:500]}" for m in rows)


def save_message(
    db: Session, user_id: int, session: TutorSession, role: str, content: str, sources: list[dict] | None = None
) -> TutorMessage:
    msg = TutorMessage(
        session_id=session.id,
        user_id=user_id,
        role=role,
        content=content,
        sources=KbService.json_dumps(sources),
    )
    db.add(msg)
    db.flush()
    return msg


def tutor_chat(db: Session, user_id: int, message: str, session_id: int | None = None) -> dict:
    """Full RAG chat turn (phrases 3–9)."""
    items = retrieve_chunks(db, user_id, message)
    session = get_or_create_session(db, user_id, session_id)
    used_ai = False

    if not items:
        # Rule A — empty retrieval: never hallucinate (phrase 6).
        answer = (
            "I don't have this in your Second Brain yet. I can only answer from "
            "your own notes and materials — add a note about it (or link a source) "
            "and I'll be able to help. Want to capture this now?"
        )
        save_message(db, user_id, session, "user", message)
        save_message(db, user_id, session, "assistant", answer, sources=[])
        db.flush()
        return {
            "session_id": session.id,
            "answer": answer,
            "sources": [],
            "empty_retrieval": True,
            "ai_used": False,
        }

    blocks = context_blocks(items)
    memory = _user_memory(db, user_id)
    history = _history_turns(db, user_id, session.id)
    known_context = _known_context(db, user_id)
    known_set = {k["concept"].lower() for k in known_context}
    # Phase 10 (Ideas 92/95): durable facts + learner context blocks.
    from app.services.kb import context as context_service
    from app.services.kb import memory_longterm

    durable_facts = memory_longterm.durable_facts_block(db, user_id)
    learner_context = context_service.context_prompt_block(
        context_service.build_bundle(db, user_id)
    )
    from app.services.prompts import tutor_chat_prompt

    prompt = tutor_chat_prompt(
        message, blocks, memory=memory, history=history, known_context=known_context,
        durable_facts=durable_facts, learner_context=learner_context,
    )

    if budget_allows(db, user_id):
        raw = _roll(prompt)
        if raw:
            used_ai = True
            record_generation(db, user_id, "tutor")
            answer = raw
            # Post-generation citation check — regenerate once if missing (phrase 7).
            if not CITE_RE.search(answer) and budget_allows(db, user_id):
                retry = _roll(tutor_chat_prompt(
                    message, blocks, memory=memory, history=history,
                    insist_cite=True, known_context=known_context,
                ))
                if retry:
                    answer = retry
                    record_generation(db, user_id, "tutor")
        else:
            answer = _fallback_answer(message, items)
    else:
        answer = _fallback_answer(message, items)

    # Rule A post-check: strip references to concepts not in user_memory (phrase 35).
    answer = _rule_a_sanitize(answer, known_set)
    # The tutor turn is a study surface — reinforce concepts it surfaced (phrase 34).
    _bump_turn_concepts(db, user_id, items)
    # Log every surviving reference for trajectory analysis (phrase 40).
    _log_recalls(db, user_id, answer, known_set)

    sources = _sources_dict(items)
    save_message(db, user_id, session, "user", message)
    save_message(db, user_id, session, "assistant", answer, sources=sources)
    # Phase 10 (Rule A, Idea 100): meter every tutor turn into ai_logs.
    try:
        from app.services.kb import ai_log as ai_log_service

        ai_log_service.log_event(
            db, user_id,
            feature="tutor",
            request=message,
            response=answer[:2000],
            retrieval={"mode": "hybrid", "chunk_ids": [i.get("chunk_id") for i in items[:10]]},
            tokens=KbService.token_estimate(f"{message} {answer}"),
        )
    except Exception:  # noqa: BLE001 — logging must never break chat
        pass
    db.flush()
    return {
        "session_id": session.id,
        "answer": answer,
        "sources": sources,
        "empty_retrieval": False,
        "ai_used": used_ai,
    }


def _fallback_answer(message: str, items: list[dict]) -> str:
    """Deterministic cited fallback (phrase 9) — no LLM, always cited."""
    if not items:
        return (
            "I don't have this in your Second Brain yet. Add a note about it and "
            "I'll be able to help."
        )
    lines = ["Here's what your notes say:"]
    for i, item in enumerate(items[:3], start=1):
        src = item.get("source_path") or f"doc {item.get('document_id')}"
        snippet = (item.get("snippet") or "")[:300]
        lines.append(f"{i}. [source: {src}] {snippet}")
    lines.append("(Deterministic answer — AI generation is disabled.)")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Idea 62 — doubt solving
# --------------------------------------------------------------------------- #
def blocking_concepts(db: Session, user_id: int, items: list[dict]) -> list[dict]:
    """Candidate blocking concepts (phrase 12): intersect retrieved chunks with
    the topic DAG prereqs + kb_concepts.

    Returns ``[{concept, definition, topic_id, topic_name}]`` — the prereqs of
    matched topics whose mastery is weak/unknown, plus kb_concepts whose
    canonical name appears in the chunk text.
    """
    matched_topic_ids: set[int] = set()
    # Strip FTS <mark> highlight tags so topic-name substring matching works
    # across highlighted terms (e.g. "<mark>Linear</mark> regression").
    haystack = " ".join(
        (item.get("snippet") or "") + " " + (item.get("heading_path") or "")
        for item in items
    ).replace("<mark>", "").replace("</mark>", "").lower()

    # Topics whose name appears in retrieved chunks.
    for topic in db.query(Topic).filter(Topic.user_id == user_id).all():
        if topic.normalized_name and topic.normalized_name in haystack:
            matched_topic_ids.add(topic.id)
        if topic.name and topic.name.lower() in haystack:
            matched_topic_ids.add(topic.id)

    # Prereq topics (the DAG) of matched topics.
    out: list[dict] = []
    seen: set[int] = set()
    if matched_topic_ids:
        deps = (
            db.query(TopicDependency)
            .filter(
                TopicDependency.user_id == user_id,
                TopicDependency.postreq_topic_id.in_(list(matched_topic_ids)),
            )
            .all()
        )
        for dep in deps:
            prereq = db.query(Topic).get(dep.prereq_topic_id)
            if prereq is None or prereq.id in seen:
                continue
            seen.add(prereq.id)
            # Only surface prereqs the student hasn't mastered (phrase 12).
            if prereq.mastery_classification not in ("strong", "medium"):
                out.append(
                    {
                        "concept": prereq.name,
                        "definition": None,
                        "topic_id": prereq.id,
                        "topic_name": prereq.name,
                        "kind": "prerequisite",
                    }
                )

    # kb_concepts whose canonical name or alias appears in the chunks.
    for concept in db.query(KbConcept).filter(KbConcept.user_id == user_id).all():
        names = [concept.canonical_name or ""] + (KbService.json_loads(concept.aliases) or [])
        if any(str(n).strip().lower() and str(n).strip().lower() in haystack for n in names):
            if concept.id in seen:
                continue
            seen.add(concept.id)
            out.append(
                {
                    "concept": concept.canonical_name,
                    "definition": concept.definition,
                    "topic_id": None,
                    "topic_name": None,
                    "kind": "concept",
                }
            )
    return out[:5]


def tutor_doubt(
    db: Session, user_id: int, question: str, step_where_stuck: str | None = None
) -> dict:
    """Gap-first doubt resolution (phrases 11–17)."""
    items = retrieve_chunks(db, user_id, f"{question} {step_where_stuck or ''}")
    blocking = blocking_concepts(db, user_id, items)
    session = get_or_create_session(db, user_id, None)
    used_ai = False

    if not items:
        return {
            "session_id": session.id,
            "answer": (
                "I don't have notes on this yet — add them to your Second Brain "
                "and I can help you through the stuck step."
            ),
            "sources": [],
            "blocking_concepts": [],
            "ai_used": False,
            "follow_ups": ["capture"],
        }

    blocks = context_blocks(items)
    gap_line = "\n".join(
        f"- {b['concept']}" + (f": {b['definition']}" if b.get("definition") else "")
        for b in blocking
    ) or "none detected"

    from app.services.prompts import tutor_doubt_prompt

    if budget_allows(db, user_id):
        raw = _roll(tutor_doubt_prompt(question, step_where_stuck, blocks, gap_line), max_tokens=900)
        if raw:
            used_ai = True
            record_generation(db, user_id, "doubt")
            answer = raw
        else:
            answer = _doubt_fallback(question, items, blocking)
    else:
        answer = _doubt_fallback(question, items, blocking)

    # Log the doubt event on the first matched topic (phrase 15) — feeds mastery.
    if matched := db.query(Topic).filter(Topic.user_id == user_id).first():
        matched_id = None
        if blocking:
            matched_id = blocking[0].get("topic_id")
        log_event(db, user_id, event_type="doubt", topic_id=matched_id or matched.id, value=0.5)
        db.flush()

    sources = _sources_dict(items)
    save_message(db, user_id, session, "user", question)
    save_message(db, user_id, session, "assistant", answer, sources=sources)
    db.flush()

    follow_ups = ["review_prerequisite"] if blocking else []
    follow_ups.append("try_practice_question")
    return {
        "session_id": session.id,
        "answer": answer,
        "sources": sources,
        "blocking_concepts": blocking,
        "ai_used": used_ai,
        "follow_ups": follow_ups,
    }


def _doubt_fallback(question: str, items: list[dict], blocking: list[dict]) -> str:
    """Deterministic doubt fallback (phrase 17): list the blocking concepts +
    related chunks, no LLM walkthrough."""
    lines = ["Let's work through this step by step."]
    if blocking:
        lines.append("Before we re-walk the problem, review this prerequisite:")
        for b in blocking:
            lines.append(f"- {b['concept']}")
    lines.append("Related notes:")
    for i, item in enumerate(items[:3], start=1):
        src = item.get("source_path") or f"doc {item.get('document_id')}"
        lines.append(f"{i}. [source: {src}] {(item.get('snippet') or '')[:280]}")
    lines.append("(Deterministic answer — AI generation is disabled.)")
    return "\n".join(lines)


__all__ = [
    "tutor_chat",
    "tutor_doubt",
    "retrieve_chunks",
    "blocking_concepts",
    "context_blocks",
    "get_or_create_session",
    "save_message",
]
