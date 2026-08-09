"""Phase 8 missing-note suggestions (Idea 77).

"you study X but have no note on it". Concepts the user *studies* (they are in
the syllabus topic graph, or they appear in ``user_memory``) but that no
document MENTIONS become suggestions, ranked by Group 2 gap evidence. Each
suggestion carries a deterministic heading outline and the material ids to
capture from. Accepting creates a pre-filled draft ``KbDocument`` (the Phase 4
Idea 40 quick-capture flow); dismissing is permanent (phrase 67).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import KbConcept, KbDocument, KbEdge, MissingNoteSuggestion, Topic, UserMemory
from app.services.kb import KbService, utcnow
from app.services.kb.gaps import concept_gaps

DEFAULT_OUTLINE = [
    "# {concept}",
    "## Definition",
    "## Key points",
    "## Examples",
    "## Practice questions",
]
LIVE_STATUSES = ("suggested", "accepted")


def outline_for(concept: str) -> list[str]:
    return [heading.format(concept=concept) for heading in DEFAULT_OUTLINE]


def _covered_concepts(db: Session, user_id: int) -> set[int]:
    """Concepts with at least one document note (MENTIONS edge)."""
    rows = (
        db.query(KbEdge.target_concept_id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.is_not(None),
        )
        .all()
    )
    return {r[0] for r in rows}


def _studied_concepts(db: Session, user_id: int) -> dict[int, tuple[str, list[int]]]:
    """concept_id -> (concept_name, linked_material_ids) for concepts the user
    actually studies: those in the topic graph or in ``user_memory``."""
    concepts = {c.id: c for c in db.query(KbConcept).filter(KbConcept.user_id == user_id).all()}
    studied: dict[int, tuple[str, list[int]]] = {}

    # Topics → concepts by name/alias; linked materials = documents whose
    # title/path matches the topic name (single pass over docs).
    topics = db.query(Topic).filter(Topic.user_id == user_id).all()
    docs = [d for d in db.query(KbDocument).filter(KbDocument.user_id == user_id, KbDocument.status != "draft").all()]
    haystacks = {d.id: f"{d.title or ''} {d.path_rel or ''}".lower() for d in docs}
    topic_docs: dict[int, list[int]] = {t.id: [] for t in topics}
    for t in topics:
        tname = (t.name or "").strip().lower()
        if not tname:
            continue
        topic_docs[t.id] = [d.id for d in docs if tname in haystacks.get(d.id, "")][:5]

    for t in topics:
        tname = (t.name or "").strip().lower()
        if not tname:
            continue
        for c in concepts.values():
            cand = [c.canonical_name or ""] + (KbService.json_loads(c.aliases) or [])
            if any(str(n).strip().lower() == tname for n in cand if str(n).strip()):
                studied.setdefault(c.id, (c.canonical_name, []))
                studied[c.id] = (studied[c.id][0], list(dict.fromkeys(studied[c.id][1] + topic_docs.get(t.id, []))))

    # user_memory concepts are studied regardless of topic mapping.
    for m in db.query(UserMemory).filter(UserMemory.user_id == user_id).all():
        c = concepts.get(m.concept_id)
        if c is not None:
            studied.setdefault(m.concept_id, (c.canonical_name, []))
    return studied


def suggest_missing_notes(db: Session, user_id: int, *, limit: int = 10) -> list[dict]:
    """Rank and persist missing-note suggestions (phrases 63–65)."""
    covered = _covered_concepts(db, user_id)
    studied = _studied_concepts(db, user_id)
    gaps = {g["concept_id"]: g for g in concept_gaps(db, user_id, limit=500)}

    # Dedupe against already-suggested/accepted rows, and never re-suggest
    # a concept the user explicitly dismissed (phrase 67 — permanent).
    existing = {
        s.concept_id
        for s in db.query(MissingNoteSuggestion)
        .filter(
            MissingNoteSuggestion.user_id == user_id,
            MissingNoteSuggestion.status.in_(LIVE_STATUSES + ("dismissed",)),
        )
        .all()
    }

    created: list[dict] = []
    for cid, (name, material_ids) in studied.items():
        if cid in covered or cid in existing:
            continue
        gap = gaps.get(cid)
        reason = _reason_for(gap, name)
        outline = outline_for(name)
        row = MissingNoteSuggestion(
            user_id=user_id,
            concept_id=cid,
            reason=reason,
            outline_template=KbService.json_dumps(outline),
            linked_material_ids=KbService.json_dumps(material_ids),
            status="suggested",
        )
        db.add(row)
        db.flush()
        created.append(
            {
                "id": row.id,
                "concept_id": cid,
                "concept": name,
                "reason": reason,
                "outline": outline,
                "linked_material_ids": material_ids,
                "status": row.status,
            }
        )

    # Rank by gap score, then error/miss evidence.
    def _rank(item: dict) -> float:
        g = gaps.get(item["concept_id"])
        if not g:
            return 0.0
        ev = g.get("evidence", {})
        return g["score"] + min(ev.get("quiz_errors", 0), 3) * 0.1 + min(ev.get("retrieval_misses", 0), 3) * 0.1

    created.sort(key=_rank, reverse=True)
    if created:
        db.commit()
    return created[:limit]


def _reason_for(gap: dict | None, name: str) -> str:
    if gap is None:
        return f"You study {name} but have no note covering it."
    ev = gap.get("evidence", {})
    bits = [f"You study {name} but have no note covering it."]
    if ev.get("quiz_errors"):
        bits.append(f"{ev['quiz_errors']} wrong answer(s) touch it.")
    if ev.get("retrieval_misses"):
        bits.append(f"{ev['retrieval_misses']} search(es) for it found nothing.")
    if gap.get("sources"):
        bits.append("Related material is available to capture from.")
    return " ".join(bits)


def list_suggestions(db: Session, user_id: int, *, status: str = "suggested", limit: int = 50) -> list[dict]:
    rows = (
        db.query(MissingNoteSuggestion, KbConcept)
        .outerjoin(KbConcept, KbConcept.id == MissingNoteSuggestion.concept_id)
        .filter(MissingNoteSuggestion.user_id == user_id, MissingNoteSuggestion.status == status)
        .order_by(MissingNoteSuggestion.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": s.id,
            "concept_id": s.concept_id,
            "concept": (c.canonical_name if c else s.concept_id),
            "reason": s.reason,
            "outline": KbService.json_loads(s.outline_template) or [],
            "linked_material_ids": KbService.json_loads(s.linked_material_ids) or [],
            "status": s.status,
        }
        for s, c in rows
    ]


def accept_suggestion(db: Session, user_id: int, suggestion_id: int) -> dict:
    """Create a pre-filled draft note and mark the suggestion accepted (phrase 66)."""
    row = (
        db.query(MissingNoteSuggestion)
        .filter(MissingNoteSuggestion.id == suggestion_id, MissingNoteSuggestion.user_id == user_id)
        .first()
    )
    if row is None:
        raise ValueError("Suggestion not found")
    if row.status != "suggested":
        raise ValueError("Suggestion already handled")

    concept = db.query(KbConcept).filter(KbConcept.id == row.concept_id, KbConcept.user_id == user_id).first()
    name = concept.canonical_name if concept else f"concept {row.concept_id}"
    outline = KbService.json_loads(row.outline_template) or outline_for(name)
    body = "\n\n".join(outline)

    doc = KbDocument(
        user_id=user_id,
        title=name,
        doc_type="md",
        status="draft",
        extracted_text=body,
        char_count=len(body),
        content_hash=KbService.content_hash(body.encode("utf-8")),
        metadata_json=KbService.json_dumps({"origin": "missing-note-suggestion"}),
    )
    db.add(doc)
    db.flush()

    # Link the draft to the concept so it's now "covered" (no repeat suggestion).
    if row.concept_id:
        edge = KbEdge(
            user_id=user_id,
            source_document_id=doc.id,
            target_type="concept",
            target_concept_id=row.concept_id,
            relation="MENTIONS",
            weight=1.0,
            provenance="manual",
        )
        db.add(edge)

    row.status = "accepted"
    db.flush()
    return {
        "suggestion_id": row.id,
        "document_id": doc.id,
        "title": doc.title,
        "status": row.status,
    }


def dismiss_suggestion(db: Session, user_id: int, suggestion_id: int) -> dict:
    """Mark dismissed — never re-suggested (phrase 67)."""
    row = (
        db.query(MissingNoteSuggestion)
        .filter(MissingNoteSuggestion.id == suggestion_id, MissingNoteSuggestion.user_id == user_id)
        .first()
    )
    if row is None:
        raise ValueError("Suggestion not found")
    row.status = "dismissed"
    db.flush()
    return {"id": row.id, "status": row.status}
