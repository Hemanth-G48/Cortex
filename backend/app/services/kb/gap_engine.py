"""Actionable learning/skill-gap engine — the redesigned Gap Analysis.

Replaces the percentage-first view with an evidence-based engine that answers:

    What do I already know → What am I missing → Why does it matter
    → What should I learn next → What learning path should I follow?

Pipeline (all evidence is real Second Brain data, never fabricated):

1. **Target set** — curated domain concepts matched to the subject (or a
   goal's full domain map), plus the subject's own topics/mentioned concepts.
2. **Evidence** — per target concept, gather from actual data:
   - ``MENTIONS`` edges (mention count, distinct documents, accumulated
     weight) — scoped to the subject's documents when analyzing a subject;
   - ``user_memory`` strength/exposure (Idea 79);
   - quiz errors + retrieval misses (Idea 72 signals, reused from ``gaps``).
3. **Levels** — Mastered / Strong / Familiar / Weak / Not Found /
   Prerequisite Missing, thresholded on the evidence (a single mention is
   *Weak*, never "known").
4. **Ranking** — gaps are prioritized by curated importance × severity.
5. **Learning path** — topological order over the curated prerequisite graph,
   bucketed into phases; prerequisites always precede dependents.
6. **Resources** — each gap is linked to real Second Brain documents that
   mention it (or that match by title), when they exist.

Both ``analyze_subject`` and ``analyze_goal`` return the same actionable
payload shape; the frontend renders recommendations, not percentages
(coverage is included only as a secondary signal).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import GoalGapAnalysis, KbConcept, KbDocument, KbEdge, UserMemory
from app.services.kb import KbService
from app.services.kb import gaps as gaps_service
from app.services.kb.gap_domains import (
    DOMAINS,
    GOALS,
    concepts_by_name,
    concepts_for_goal,
    domain_for_course,
    goals_payload,
)
from app.services.kb.gap_history import record_gap_history

# Knowledge levels, strongest → weakest (display + sort order).
LEVELS = ("Mastered", "Strong", "Familiar", "Weak", "Not Found", "Prerequisite Missing")

# Thresholds for evidence-based classification.
MASTERED_STRENGTH = 0.7
STRONG_STRENGTH = 0.4
STRONG_DOCS = 2
STRONG_MENTIONS = 4
FAMILIAR_DOCS = 2
FAMILIAR_MENTIONS = 4

# Generic metadata for non-curated targets (subject topics/mentioned concepts).
NOISY_HEADINGS = {
    "introduction", "conclusion", "overview", "references", "summary",
    "abstract", "contents", "appendix", "see also", "acknowledgements",
    "big picture", "key features", "key takeaways", "takeaways",
    "learning objectives", "learning outcomes", "key terms", "key points",
    "what we learned", "chapter overview", "table of contents",
}

MAX_PATH_PHASE = 5  # concepts per learning-path phase
MAX_TARGET_CONCEPTS = 60  # hard cap on evaluated targets per analysis


# ---------------------------------------------------------------------------
# Matching & normalization
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower()).strip(" .,:;!?\"'()[]{}<>-")


def _tokens(name: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (name or "").lower()) if len(t) >= 2}


def _build_vault_index(vault_concepts: list) -> list[dict]:
    """Precompute normalized names/tokens for every vault concept once.

    The matcher below scans this index per target concept; without the cache
    every target×candidate pair re-ran regex + alias JSON parsing (60 targets
    × thousands of concepts ≈ seconds of wasted work per analysis).
    """
    index: list[dict] = []
    for c in vault_concepts:
        canon = c.canonical_name or ""
        index.append(
            {
                "concept": c,
                "canon": _normalize(canon),
                "c_toks": _tokens(canon),
                "aliases": [
                    (str(a).strip(), _normalize(str(a)), _tokens(str(a)))
                    for a in (KbService.json_loads(c.aliases) or [])
                    if str(a).strip()
                ],
            }
        )
    return index


def _match_vault_concepts(target_name: str, vault_index: list[dict]) -> list:
    """Vault KbConcept rows matching a target concept name.

    Strong match: normalized equality of canonical name or any alias (or the
    same token set). Weak match: every target token appears in the candidate
    (e.g. target "sql injection" → vault "sql injection attack"). Strong
    matches win; otherwise weak matches are used. Never raises.
    """
    tn = _normalize(target_name)
    t_toks = _tokens(target_name)
    strong: list = []
    weak: list = []
    for entry in vault_index:
        if entry["canon"] == tn or (t_toks and entry["c_toks"] == t_toks):
            strong.append(entry["concept"])
            continue
        if t_toks and entry["c_toks"] and t_toks.issubset(entry["c_toks"]):
            weak.append(entry["concept"])
            continue
        for _raw, an, a_toks in entry["aliases"]:
            if an == tn or (t_toks and a_toks == t_toks):
                strong.append(entry["concept"])
                break
            if t_toks and a_toks and t_toks.issubset(a_toks):
                weak.append(entry["concept"])
                break
    return strong or weak


def _clean_heading_names(names: list[str]) -> list[str]:
    """Drop boilerplate heading text that would pollute the target set."""
    out: list[str] = []
    for n in names:
        s = (n or "").strip()
        if not s or len(s) < 3:
            continue
        if _normalize(s) in NOISY_HEADINGS:
            continue
        if s.lower() in NOISY_HEADINGS:
            continue
        out.append(s)
    return out


# ---------------------------------------------------------------------------
# Evidence gathering
# ---------------------------------------------------------------------------

def _evidence(
    db: Session,
    user_id: int,
    targets: list[dict],
    vault_index: list[dict],
    *,
    doc_ids: set[int] | None = None,
) -> tuple[dict[str, list], dict[str, dict]]:
    """Per-target evidence + the name→matched-vault-concepts index.

    Returns ``(matched, evidence)`` where ``matched[name]`` is the list of
    vault concepts matching that target and ``evidence[name]`` is::

        {strength, exposure, mentions, documents, weight,
         quiz_errors, retrieval_misses, heading_docs?}

    ``heading_docs`` is only present when seeded from ``doc_hints`` (a heading
    in the user's notes — weak evidence, never fabricated as a mention).
    """
    """Per-target evidence + the name→matched-vault-concepts index.

    Returns ``(matched, evidence)`` where ``matched[name]`` is the list of
    vault concepts matching that target and ``evidence[name]`` is::

        {strength, exposure, mentions, documents, weight,
         quiz_errors, retrieval_misses}
    """
    matched: dict[str, list] = {}
    for spec in targets:
        m = _match_vault_concepts(spec["name"], vault_index)
        if m:
            matched[spec["name"]] = m

    all_ids = {c.id for ids in matched.values() for c in ids}

    # Memory (Idea 79) — user-wide signal.
    mem: dict[int, object] = {}
    if all_ids:
        for row in db.query(UserMemory).filter(
            UserMemory.user_id == user_id, UserMemory.concept_id.in_(all_ids)
        ).all():
            mem[row.concept_id] = row

    # MENTIONS edges — scoped to the subject's documents when provided.
    mention: dict[int, dict] = defaultdict(lambda: {"count": 0, "docs": set(), "weight": 0.0})
    if all_ids:
        q = db.query(KbEdge).filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id.in_(all_ids),
        )
        if doc_ids:
            q = q.filter(KbEdge.source_document_id.in_(doc_ids))
        for e in q.all():
            d = mention[e.target_concept_id]
            d["count"] += 1
            d["docs"].add(e.source_document_id)
            d["weight"] += e.weight or 0.0

    # Quiz errors + retrieval misses (reused Idea 72 helpers).
    all_concept_objs = [c for ids in matched.values() for c in ids]
    errors: dict = {}
    misses: dict = {}
    if all_concept_objs:
        errors = gaps_service._error_counts(
            db, user_id, gaps_service._topic_concept_index(db, user_id)
        )
        misses = gaps_service._retrieval_misses(db, user_id, all_concept_objs)

    def _m(row):
        return (row.strength or 0.0) if row else 0.0

    def _e(row):
        return (row.exposure_count or 0) if row else 0

    evidence: dict[str, dict] = {}
    for name, objs in matched.items():
        strength = max(_m(mem.get(c.id)) for c in objs) if objs else 0.0
        exposure = max(_e(mem.get(c.id)) for c in objs) if objs else 0
        counts = [mention.get(c.id, {"count": 0, "docs": set(), "weight": 0.0}) for c in objs]
        docs: set = set()
        for d in counts:
            docs |= d["docs"]
        evidence[name] = {
            "strength": round(strength, 4),
            "exposure": exposure,
            "mentions": sum(d["count"] for d in counts),
            "documents": len(docs),
            "weight": round(sum(d["weight"] for d in counts), 4),
            "quiz_errors": sum(errors.get(c.id, 0) for c in objs),
            "retrieval_misses": sum(misses.get(c.id, 0) for c in objs),
        }
    return matched, evidence


# ---------------------------------------------------------------------------
# Levels, priority
# ---------------------------------------------------------------------------

def _level_for(ev: dict) -> str:
    strength = ev["strength"]
    docs = ev["documents"]
    mentions = ev["mentions"]
    if strength >= MASTERED_STRENGTH or (docs >= 3 and mentions >= 8):
        return "Mastered"
    if (
        strength >= STRONG_STRENGTH
        or (docs >= STRONG_DOCS and mentions >= STRONG_MENTIONS)
        or (strength > 0 and docs >= 2)
    ):
        return "Strong"
    if strength > 0 or docs >= FAMILIAR_DOCS or mentions >= FAMILIAR_MENTIONS:
        return "Familiar"
    if mentions >= 1 or docs >= 1:
        return "Weak"
    return "Not Found"


def _priority_for(level: str, importance: int) -> str | None:
    """Gap priority from severity × curated importance; None when not a gap."""
    if level in ("Not Found", "Weak"):
        return {3: "High", 2: "Medium", 1: "Low"}.get(importance, "Medium")
    if level in ("Prerequisite Missing", "Familiar"):
        # Missing foundation / partial coverage — one notch lower.
        return {3: "Medium", 2: "Low", 1: "Low"}.get(importance, "Low")
    return None


_PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}


def _gap_sort_key(g: dict) -> tuple:
    return (
        _PRIORITY_RANK.get(g.get("priority") or "Low", 3),
        -(g.get("importance") or 2),
        g["name"].lower(),
    )


# ---------------------------------------------------------------------------
# Resources (Second Brain linking)
# ---------------------------------------------------------------------------

def _resources(
    db: Session,
    user_id: int,
    name: str,
    matched_ids: list[int],
    *,
    doc_ids: set[int] | None = None,
    limit: int = 3,
    doc_index: list[dict] | None = None,
) -> list[dict]:
    """Real Second Brain documents for a concept: MENTIONS first, then title match.

    ``doc_index`` is the per-analysis precomputed ``[{"id", "title", "toks"}]``
    list (see ``_build_doc_index``) — reusing it avoids re-querying and
    re-tokenizing every user document for every target (the title fallback was
    O(targets × all documents) before).
    """
    items: list[dict] = []
    seen: set[int] = set()

    if matched_ids:
        q = db.query(KbEdge, KbDocument).join(
            KbDocument, KbEdge.source_document_id == KbDocument.id
        ).filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_concept_id.in_(matched_ids),
            KbDocument.status != "deleted",
        )
        if doc_ids:
            q = q.filter(KbEdge.source_document_id.in_(doc_ids))
        rows = q.order_by(KbEdge.weight.desc()).limit(limit).all()
        for _edge, doc in rows:
            if doc.id in seen:
                continue
            seen.add(doc.id)
            items.append({"document_id": doc.id, "title": doc.title or doc.path_rel or f"doc {doc.id}"})
        if len(items) >= limit:
            return items

    # Title/path token match (covers subject topics without a vault concept).
    toks = _tokens(name)
    if toks and doc_index:
        for entry in doc_index:
            if len(items) >= limit:
                break
            if entry["id"] in seen:
                continue
            if toks.issubset(entry["toks"]):
                seen.add(entry["id"])
                items.append({"document_id": entry["id"], "title": entry["title"]})
    return items[:limit]


def _build_doc_index(db: Session, user_id: int, *, doc_ids: set[int] | None = None) -> list[dict]:
    """Precompute id/title/token-tuple for the user's documents once per analysis."""
    q = db.query(KbDocument.id, KbDocument.title, KbDocument.path_rel).filter(
        KbDocument.user_id == user_id, KbDocument.status != "deleted"
    )
    if doc_ids:
        q = q.filter(KbDocument.id.in_(doc_ids))
    index: list[dict] = []
    for doc_id, title, path_rel in q.all():
        label = title or path_rel or f"doc {doc_id}"
        toks = _tokens(label)
        if toks:
            index.append({"id": doc_id, "title": label, "toks": toks})
    return index


# ---------------------------------------------------------------------------
# Learning path
# ---------------------------------------------------------------------------

def _build_path(gap_items: list[dict], specs_by_name: dict[str, dict]) -> list[dict]:
    """Phased learning path over the curated prerequisite graph (Kahn topo).

    Prerequisite-first; within the same readiness tier, higher-priority gaps
    come first. Phases hold up to ``MAX_PATH_PHASE`` concepts.
    """
    names = [g["name"] for g in gap_items]
    name_set = set(names)
    by_name = {g["name"]: g for g in gap_items}

    indeg: dict[str, int] = {n: 0 for n in names}
    out: dict[str, list[str]] = {n: [] for n in names}
    for n in names:
        spec = specs_by_name.get(n) or {}
        for p in spec.get("prereqs", []):
            if p in name_set and p != n:
                out[p].append(n)
                indeg[n] += 1

    ready = sorted([n for n in names if indeg[n] == 0], key=lambda n: _gap_sort_key(by_name[n]))
    order: list[str] = []
    remaining = set(names)
    while ready:
        node = ready.pop(0)
        order.append(node)
        remaining.discard(node)
        for nxt in out[node]:
            if nxt not in remaining:
                continue
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
                ready.sort(key=lambda n: _gap_sort_key(by_name[n]))
    # Fall back to priority order for anything the (curated) graph missed.
    order.extend(sorted(remaining, key=lambda n: _gap_sort_key(by_name[n])))

    phases: list[dict] = []
    for i in range(0, len(order), MAX_PATH_PHASE):
        chunk = order[i : i + MAX_PATH_PHASE]
        phases.append(
            {
                "phase": len(phases) + 1,
                "title": f"Phase {len(phases) + 1}",
                "items": [
                    {
                        "name": n,
                        "level": by_name[n]["level"],
                        "priority": by_name[n]["priority"],
                        # Real Second Brain documents already linked to this gap
                        # (MENTIONS + title match) — lets the UI deep-link each
                        # path item to the notes that mention the concept.
                        "sources": by_name[n].get("sources", []),
                    }
                    for n in chunk
                ],
            }
        )
    return phases


# ---------------------------------------------------------------------------
# Summary narrative
# ---------------------------------------------------------------------------

def _summary(
    domain: str | None,
    strengths: list[dict],
    gaps: list[dict],
    *,
    subject_title: str | None = None,
    goal_title: str | None = None,
) -> dict:
    strong = [s["name"] for s in strengths[:6]]
    top = [g["name"] for g in gaps if g.get("priority") == "High"][:3]
    if not top:
        top = [g["name"] for g in gaps[:3]]

    scope = goal_title or (f"{subject_title}" if subject_title else "this area")
    area = domain or scope

    if not gaps:
        text = (
            f"No significant knowledge gaps found for {area} — your notes and practice "
            "cover the target concepts. Keep reinforcing the strongest ones with spaced repetition."
        )
    elif not strengths:
        text = (
            f"You have little or no evidence of learning {area} yet. Your highest-priority "
            f"missing concepts are {', '.join(top)}. Start with the first item in the recommended path."
        )
    else:
        text = (
            f"You are strong in {', '.join(strong)} but have gaps in {area}. "
            f"Your highest-priority missing concepts are {', '.join(top)}. "
            "Follow the recommended path below — foundations first."
        )

    next_name = gaps[0]["name"] if gaps else None
    if next_name:
        text += f" Recommended next step: learn {next_name}."

    return {
        "text": text,
        "priorities": top,
        "strong_areas": strong,
    }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def _run_analysis(
    db: Session,
    user_id: int,
    *,
    targets: list[dict],
    specs_by_name: dict[str, dict],
    domain: str | None,
    doc_ids: set[int] | None = None,
    subject_title: str | None = None,
    goal_title: str | None = None,
    doc_hints: dict[str, int] | None = None,
) -> dict:
    vault_concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
    if not targets:
        return {
            "goal": goal_title,
            "domain": domain,
            "summary": {
                "text": "Nothing to analyze yet — add Second Brain notes for this area, then re-run Gap Analysis.",
                "priorities": [],
                "strong_areas": [],
            },
            "strengths": [],
            "gaps": [],
            "path": [],
            "next": None,
            "coverage": {"known": 0, "gaps": 0, "total": 0, "percent": 0.0},
        }

    vault_index = _build_vault_index(vault_concepts)
    doc_index = _build_doc_index(db, user_id, doc_ids=doc_ids)
    matched, evidence = _evidence(db, user_id, targets, vault_index, doc_ids=doc_ids)

    # Heading-presence seeding: a topic that appears as a heading in the
    # subject's own documents is *weak* evidence of familiarity — never more
    # (a heading is not an explanation or worked example). Without this, a
    # subject topic present in the user's notes would be reported "Not Found".
    # Evidence stays honest: ``documents`` reflects the real presence and
    # ``mentions`` stays 0 (no MENTIONS edge exists) — level classification
    # only needs ``documents >= 1`` to be "Weak".
    if doc_hints:
        target_names = {spec["name"] for spec in targets}
        for name, count in doc_hints.items():
            if count <= 0 or name not in target_names or name in evidence:
                continue
            evidence[name] = {
                "strength": 0.0, "exposure": 0, "mentions": 0, "documents": 1,
                "weight": 0.0, "quiz_errors": 0, "retrieval_misses": 0,
                "heading_docs": count,
            }

    # Level per target (name-based; "Not Found" when no evidence at all).
    level_by_name: dict[str, str] = {}
    for spec in targets:
        ev = evidence.get(spec["name"])
        level_by_name[spec["name"]] = _level_for(ev) if ev else "Not Found"

    # Build strengths + gaps with full metadata.
    strengths: list[dict] = []
    gaps: list[dict] = []
    for spec in targets:
        name = spec["name"]
        level = level_by_name[name]
        importance = spec.get("importance") or 2
        ev = evidence.get(name) or {
            "strength": 0.0, "exposure": 0, "mentions": 0, "documents": 0,
            "weight": 0.0, "quiz_errors": 0, "retrieval_misses": 0,
        }
        entry = {
            "name": name,
            "level": level,
            "skill": spec.get("skill"),
            "domain": spec.get("domain") or domain,
            "importance": importance,
            "why": spec.get("why"),
            "prerequisites": [],  # filled below (needs full level map)
            "blocked": False,
            "learn": spec.get("learn") or [],
            "practice": spec.get("practice") or [],
            "next": spec.get("next"),
            "sources": _resources(
                db, user_id, name, [c.id for c in matched.get(name, [])],
                doc_ids=doc_ids, doc_index=doc_index,
            ),
            "evidence": {
                "strength": ev["strength"],
                "exposure": ev["exposure"],
                "mentions": ev["mentions"],
                "documents": ev["documents"],
                "quiz_errors": ev["quiz_errors"],
                "retrieval_misses": ev["retrieval_misses"],
            },
        }
        if level in ("Mastered", "Strong"):
            strengths.append(entry)
        else:
            entry["prerequisites"] = []
            entry["blocked"] = False
            entry["priority"] = _priority_for(level, importance)
            gaps.append(entry)

    # Second pass — prerequisites / blocked / Prerequisite-Missing downgrade,
    # after ALL levels are settled. Doing this inline would be order-dependent:
    # a target iterated before its prereq is downgraded would not see it.
    for entry in gaps:
        spec = specs_by_name.get(entry["name"]) or {}
        pre: list[dict] = []
        blocked = False
        for p in spec.get("prereqs", []):
            pl = level_by_name.get(p, "Not Found")
            pre.append({"name": p, "level": pl, "known": pl in ("Mastered", "Strong", "Familiar")})
            if pl in ("Not Found", "Weak", "Prerequisite Missing"):
                blocked = True
        entry["prerequisites"] = pre
        entry["blocked"] = blocked
        if blocked and entry["level"] in ("Familiar",):
            entry["level"] = "Prerequisite Missing"
            level_by_name[entry["name"]] = "Prerequisite Missing"
        entry["priority"] = _priority_for(entry["level"], entry.get("importance") or 2)

    # Related known concepts (knowledge-graph connection) for each gap.
    known_names = {s["name"] for s in strengths}
    for g in gaps:
        spec = specs_by_name.get(g["name"]) or {}
        g_domain = g.get("domain")
        related = [
            n for n in known_names
            if n != g["name"]
            and (
                n in spec.get("prereqs", [])
                or (specs_by_name.get(n, {}).get("domain") == g_domain)
            )
        ][:5]
        g["related_known"] = related

    strengths.sort(key=lambda s: (-(s["evidence"]["strength"]), -(s["evidence"]["mentions"]), s["name"].lower()))
    gaps.sort(key=_gap_sort_key)

    # Learning path over the gaps (prerequisite-aware).
    path = _build_path(gaps, specs_by_name)
    next_item = gaps[0] if gaps else None

    total = len(targets)
    known_count = len(strengths)
    summary = _summary(
        domain,
        strengths,
        gaps,
        subject_title=subject_title,
        goal_title=goal_title,
    )

    return {
        "goal": goal_title,
        "domain": domain,
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "path": path,
        "next": next_item,
        "coverage": {
            "known": known_count,
            "gaps": len(gaps),
            "total": total,
            "percent": round(known_count / total * 100, 1) if total else 0.0,
        },
    }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def analyze_subject(
    db: Session,
    user_id: int,
    *,
    title: str,
    doc_ids: list[int] | None = None,
    topic_names: list[str] | None = None,
    concept_names: list[str] | None = None,
    doc_hints: dict[str, int] | None = None,
) -> dict:
    """Gap analysis for one subject (course).

    Target set = matched curated domain concepts ∪ the subject's own topics
    ∪ the subject's mentioned concepts. Evidence is scoped to the subject's
    documents where it makes sense (MENTIONS counts, resources).

    ``doc_hints`` maps heading text → document count for the subject's
    documents, used to seed *weak* evidence for topics the user actually
    wrote about (so present-but-unmentioned topics are not "Not Found").
    """
    domain = domain_for_course(title)
    specs_by_name: dict[str, dict] = {}

    if domain:
        for spec in DOMAINS[domain]["concepts"]:
            entry = dict(spec)
            entry["domain"] = domain
            specs_by_name[entry["name"]] = entry

    heading_names = _clean_heading_names(topic_names or [])
    mentioned = [c for c in (concept_names or []) if c and c not in specs_by_name][:MAX_TARGET_CONCEPTS]
    for name in heading_names[:MAX_TARGET_CONCEPTS] + mentioned:
        specs_by_name.setdefault(
            name,
            {
                "name": name,
                "skill": "Subject topics",
                "why": f"Covered by your “{title}” materials",
                "prereqs": [],
                "learn": [
                    f"Review your notes on {name}",
                    "Capture a focused note explaining it in your own words",
                ],
                "practice": [
                    "Summarize it in one paragraph from memory",
                    "Test yourself with a quiz or flashcard",
                ],
                "next": None,
                "importance": 2,
                "aliases": [],
                "domain": domain or "Subject",
            },
        )

    targets = list(specs_by_name.values())[:MAX_TARGET_CONCEPTS]
    return _run_analysis(
        db,
        user_id,
        targets=targets,
        specs_by_name=specs_by_name,
        domain=domain,
        doc_ids=set(doc_ids) if doc_ids else None,
        subject_title=title,
        doc_hints=doc_hints,
    )


def analyze_goal(db: Session, user_id: int, goal_key: str) -> dict | None:
    """Goal/career-level gap analysis across all of the goal's domains."""
    goal = GOALS.get(goal_key)
    if not goal:
        return None

    specs = concepts_for_goal(goal_key)
    specs_by_name = {s["name"]: s for s in specs}
    result = _run_analysis(
        db,
        user_id,
        targets=specs,
        specs_by_name=specs_by_name,
        domain=None,
        goal_title=goal["title"],
    )

    # Domain-level rollup for the goal view.
    breakdown: list[dict] = []
    for domain_name in goal["domains"]:
        domain_specs = [s for s in specs if s.get("domain") == domain_name]
        total = len(domain_specs)
        if not total:
            continue
        strong = [r["name"] for r in result["strengths"] if r.get("domain") == domain_name]
        gaps_n = [r["name"] for r in result["gaps"] if r.get("domain") == domain_name]
        developing = [r["name"] for r in result["gaps"] if r.get("domain") == domain_name and r.get("level") == "Familiar"]
        gap_ratio = len(gaps_n) / total
        strong_ratio = len(strong) / total
        status = "Strong" if strong_ratio >= 0.5 else ("Major gap" if gap_ratio >= 0.5 else "Developing")
        breakdown.append(
            {
                "domain": domain_name,
                "total": total,
                "strong": strong,
                "developing": developing,
                "gaps": [g for g in gaps_n if g not in developing],
                "status": status,
                "strong_ratio": round(strong_ratio, 3),
                "gap_ratio": round(gap_ratio, 3),
            }
        )
    result["domain_breakdown"] = breakdown
    result["goal_key"] = goal_key
    return result


def list_domains() -> list[dict]:
    """Goals + domains for the goal selector UI."""
    return goals_payload()


def goal_exists(goal_key: str) -> bool:
    """Whether the career goal exists in the static catalog."""
    return goal_key in GOALS


# ---------------------------------------------------------------------------
# Saved Goal-level Gap Analysis (save-and-reuse cache)
# ---------------------------------------------------------------------------
# Mirrors the course-level pattern (``CourseGapAnalysis``): the first request
# for a goal computes the analysis, stores it, and later requests reuse the
# saved copy (``cached: True`` + ``analyzed_at``) without recomputing. Only
# the explicit Re-analyze action or a KB reindex (evidence changed) refreshes.


def user_document_count(db: Session, user_id: int) -> int:
    """Count of the user's non-deleted Second Brain documents."""
    return (
        db.query(KbDocument.id)
        .filter(KbDocument.user_id == user_id, KbDocument.status != "deleted")
        .count()
    )


def normalize_gap_payload(payload: dict) -> dict:
    """Guarantee the full gap-analysis response shape on every read.

    Saved payloads (``GoalGapAnalysis`` / ``FolderGapAnalysis`` rows) are
    stored verbatim and returned on later views — a payload written by an
    older or alternative engine may lack fields the UI reads unconditionally.
    Normalize here (the read path) so every consumer gets a complete shape,
    mirroring how ``plan_dict`` normalizes stored learning-plan payloads.
    """
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    summary.setdefault("text", "")
    if not isinstance(summary.get("priorities"), list):
        summary["priorities"] = []
    if not isinstance(summary.get("strong_areas"), list):
        summary["strong_areas"] = []
    payload["summary"] = summary

    def _list(key: str) -> None:
        if not isinstance(payload.get(key), list):
            payload[key] = []

    _list("strengths")
    _list("gaps")
    _list("path")
    _list("domain_breakdown")

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        coverage = {}
    payload["coverage"] = {
        "known": coverage.get("known", 0),
        "gaps": coverage.get("gaps", 0),
        "total": coverage.get("total", 0),
        "percent": coverage.get("percent", 0.0),
    }
    return payload


def load_saved_goal_gaps(db: Session, user_id: int, goal_key: str) -> dict | None:
    """Return a previously saved goal analysis payload, or None.

    Also computes ``new_notes_since_analysis`` (how many documents were added
    since the analysis) when the payload carries a ``document_count``, so the
    UI can surface staleness next to the cached notice.
    """
    saved = (
        db.query(GoalGapAnalysis)
        .filter(
            GoalGapAnalysis.user_id == user_id,
            GoalGapAnalysis.goal_key == goal_key,
        )
        .first()
    )
    if saved is None:
        return None
    payload = normalize_gap_payload(json.loads(saved.payload_json or "{}"))
    payload["cached"] = True
    # SQLite stores DateTime without tzinfo — re-attach UTC so the timestamp
    # matches freshly-computed responses exactly (``+00:00`` suffix).
    analyzed = saved.analyzed_at
    if analyzed is not None and analyzed.tzinfo is None:
        analyzed = analyzed.replace(tzinfo=timezone.utc)
    payload["analyzed_at"] = analyzed.isoformat() if analyzed else None
    if isinstance(payload.get("document_count"), int):
        payload["new_notes_since_analysis"] = max(
            0, user_document_count(db, user_id) - payload["document_count"]
        )
    return payload


def save_goal_gaps(db: Session, user_id: int, goal_key: str, payload: dict) -> None:
    """Upsert the analysis payload for a user + goal (one row).

    The stored ``analyzed_at`` is the payload's own timestamp, so a later GET
    that reloads the saved copy reports exactly the moment the analysis was
    actually computed.
    """
    row = (
        db.query(GoalGapAnalysis)
        .filter(
            GoalGapAnalysis.user_id == user_id,
            GoalGapAnalysis.goal_key == goal_key,
        )
        .first()
    )
    if row is None:
        row = GoalGapAnalysis(user_id=user_id, goal_key=goal_key)
        db.add(row)
    row.payload_json = json.dumps(payload, default=str)
    row.analyzed_at = (
        datetime.fromisoformat(payload["analyzed_at"])
        if payload.get("analyzed_at")
        else datetime.now(timezone.utc)
    )
    db.commit()
    # Every goal analysis (first compute AND explicit re-analyze) is logged to
    # the history so the UI can show how this goal's gaps changed over time.
    record_gap_history(db, user_id, goal_key=goal_key, payload=payload)


def invalidate_goal_gaps(db: Session, user_id: int, goal_key: str | None = None) -> None:
    """Drop the cached goal analyses for a user.

    Used after a KB reindex (all saved analyses are stale, since the evidence
    changed); pass ``goal_key`` to drop a single goal's copy.
    """
    q = db.query(GoalGapAnalysis).filter(GoalGapAnalysis.user_id == user_id)
    if goal_key is not None:
        q = q.filter(GoalGapAnalysis.goal_key == goal_key)
    q.delete()
    db.commit()


# ---------------------------------------------------------------------------
# Capture-note drafting ("Create note for this gap")
# ---------------------------------------------------------------------------

GAP_NOTE_ORIGIN = "gap_note"


def _is_gap_note_draft(doc: KbDocument) -> bool:
    meta = KbService.json_loads(doc.metadata_json) or {}
    return meta.get("origin") == GAP_NOTE_ORIGIN


def find_gap_note_draft(db: Session, user_id: int, name: str) -> KbDocument | None:
    """Existing draft capture note for this exact gap name (idempotency).

    The key is normalized (stripped, lowercased) on both sides so "SSRF" and
    "ssrf" resolve to the same draft instead of creating duplicates.
    """
    key = (name or "").strip().lower()
    for d in (
        db.query(KbDocument)
        .filter(KbDocument.user_id == user_id, KbDocument.status == "draft")
        .all()
    ):
        meta = KbService.json_loads(d.metadata_json) or {}
        if (
            meta.get("origin") == GAP_NOTE_ORIGIN
            and (meta.get("gap") or "").strip().lower() == key
        ):
            return d
    return None


def create_gap_note(
    db: Session,
    user_id: int,
    name: str,
    *,
    subject: str | None = None,
    why: str | None = None,
    learn: list[str] | None = None,
    practice: list[str] | None = None,
    sources: list[dict] | None = None,
) -> tuple[KbDocument, bool]:
    """Draft a capture note (``status='draft'`` KbDocument) for one gap.

    The note is pre-filled with the gap's why / learn / practice steps and the
    real Second Brain documents already linked to it, so the user gets a
    ready-to-edit study note instead of a blank capture. Idempotent: clicking
    "Create note" twice on the same gap reuses the existing draft and returns
    ``(doc, created=False)`` — no duplicate rows.
    """
    name = (name or "").strip()[:200]
    if not name:
        raise ValueError("Gap name is required")

    existing = find_gap_note_draft(db, user_id, name)
    if existing is not None:
        return existing, False

    from app.services.kb.pipeline import re_chunk

    lines: list[str] = [f"# Study: {name}"]
    scope = f" for {subject}" if subject else ""
    lines.append(
        f"> Drafted from Gap Analysis{scope}. Fill this note in as you learn — "
        "explain the concept in your own words, then check off the steps below."
    )
    lines.append("")
    lines.append("## Why it matters")
    lines.append(why or f"{name} is part of the target knowledge for {subject or 'your learning goal'}.")
    lines.append("")

    learn = [s.strip()[:500] for s in (learn or []) if s and s.strip()]
    if learn:
        lines.append("## What I need to learn")
        lines.extend(f"- [ ] {s}" for s in learn)
        lines.append("")

    practice = [s.strip()[:500] for s in (practice or []) if s and s.strip()]
    if practice:
        lines.append("## Practice")
        lines.extend(f"- [ ] {s}" for s in practice)
        lines.append("")

    refs = [s for s in (sources or []) if isinstance(s, dict) and s.get("document_id")]
    if refs:
        lines.append("## Related Second Brain documents")
        for s in refs:
            lines.append(f"- {s.get('title') or 'document'} (doc #{s['document_id']})")
        lines.append("")

    content = "\n".join(lines).strip()
    doc = KbDocument(
        user_id=user_id,
        title=f"Study: {name}"[:500],
        doc_type="md",
        status="draft",
        extracted_text=content,
        char_count=len(content),
        content_hash=KbService.content_hash(content.encode("utf-8")),
        metadata_json=KbService.json_dumps(
            {"origin": GAP_NOTE_ORIGIN, "gap": name.strip().lower(), "subject": subject}
        ),
    )
    db.add(doc)
    db.flush()
    re_chunk(db, doc)
    db.commit()
    db.refresh(doc)
    return doc, True
