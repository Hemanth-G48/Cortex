"""Tests for the redesigned Gap Analysis engine (gap_engine + gap_domains).

Covers:
- evidence-based knowledge levels (single mention ≠ knowledge),
- prerequisite-aware learning-path ordering,
- subject-scoped analysis with real Second Brain resource linking,
- goal/career-level analysis with a per-domain breakdown,
- per-user isolation,
- graceful empty state for subjects with no data.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Course,
    GoalGapAnalysis,
    KbConcept,
    KbDocument,
    KbDocumentTag,
    KbEdge,
    KbSource,
    KbTag,
    User,
    UserMemory,
)
from app.services.kb import utcnow


def _signup(client: TestClient, uname: str = "gap-engine", email: str = "gap-engine@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Gap Engine", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "gap-engine@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _source(db: Session, user_id: int, name: str = "Notes") -> KbSource:
    src = KbSource(user_id=user_id, name=name, source_type="local_dir", root_path=f"/tmp/{name}")
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def _doc(db: Session, user_id: int, source_id: int, title: str, path: str, outline=None) -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        source_id=source_id,
        title=title,
        doc_type="md",
        path_rel=path,
        extracted_text=f"# {title}\n\ncontent",
        content_hash=f"hash-{path}",
        char_count=40,
        status="unchanged",
    )
    if outline is not None:
        doc.outline_json = json.dumps(outline)
    doc.metadata_json = json.dumps({"tags": ["course:Web Security"]})
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _tag(db: Session, user_id: int, name: str) -> KbTag:
    tag = KbTag(user_id=user_id, name=name, kind="manual")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def _link(db: Session, doc: KbDocument, tag: KbTag) -> None:
    db.add(KbDocumentTag(user_id=doc.user_id, document_id=doc.id, tag_id=tag.id, provenance="manual"))
    db.commit()


def _concept(db: Session, user_id: int, name: str) -> KbConcept:
    concept = KbConcept(user_id=user_id, canonical_name=name, definition=f"{name} definition")
    db.add(concept)
    db.commit()
    db.refresh(concept)
    return concept


def _mention(db: Session, user_id: int, doc_id: int, concept_id: int, weight: float = 0.5) -> None:
    db.add(
        KbEdge(
            user_id=user_id,
            source_document_id=doc_id,
            target_concept_id=concept_id,
            relation="MENTIONS",
            target_type="concept",
            weight=weight,
            provenance="rule",
        )
    )
    db.commit()


def _build_web_security_course(client: TestClient, db: Session) -> tuple[int, dict]:
    """Course with one doc mentioning XSS once (weak evidence) and nothing for SSRF."""
    token = _signup(client)
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db)
    src = _source(db, uid)

    doc = _doc(db, uid, src.id, "XSS Basics", "web/xss.md")
    tag = _tag(db, uid, "course:Web Security")
    _link(db, doc, tag)
    xss = _concept(db, uid, "XSS")
    _mention(db, uid, doc.id, xss.id)

    resp = client.post("/api/courses/sync-kb", headers=headers)
    assert resp.status_code == 200
    course = db.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_tag").first()
    assert course is not None
    return course.id, headers


def _flatten_path(path: list[dict]) -> list[str]:
    return [item["name"] for phase in path for item in phase["items"]]


def test_single_mention_is_weak_not_known(client: TestClient, db_session: Session):
    """Evidence quality matters: one mention must NOT classify as knowledge."""
    course_id, headers = _build_web_security_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()

    assert data["domain"] == "Web Security"
    xss = next(g for g in data["gaps"] if g["name"] == "XSS")
    assert xss["level"] == "Weak"
    assert xss["evidence"]["documents"] == 1
    # The real document that mentions XSS is linked back to the gap.
    assert xss["sources"], "expected a real Second Brain resource"
    assert xss["sources"][0]["title"] == "XSS Basics"

    ssrf = next(g for g in data["gaps"] if g["name"] == "SSRF")
    assert ssrf["level"] == "Not Found"
    assert ssrf["sources"] == []  # no fabrication — no resource, empty list


def test_strong_memory_marks_mastered(client: TestClient, db_session: Session):
    course_id, headers = _build_web_security_course(client, db_session)
    uid = _uid(db_session)
    concept = db_session.query(KbConcept).filter(KbConcept.user_id == uid, KbConcept.canonical_name == "XSS").first()
    db_session.add(UserMemory(user_id=uid, concept_id=concept.id, strength=0.9,
                              exposure_count=12, last_seen=utcnow()))
    db_session.commit()

    data = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    strengths = {s["name"]: s for s in data["strengths"]}
    assert "XSS" in strengths
    assert strengths["XSS"]["level"] == "Mastered"


def test_learning_path_respects_prerequisites(client: TestClient, db_session: Session):
    """On an empty vault every CTF concept is a gap; the path must still
    order foundations before dependents (HTTP before SSRF, C before buffer
    overflow, buffer overflow before ret2libc)."""
    token = _signup(client, uname="gap-path", email="gap-path@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    data = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert data["goal_key"] == "ctf"
    order = _flatten_path(data["path"])

    def idx(name: str) -> int:
        return order.index(name)

    # Foundations before dependents.
    assert idx("Networking fundamentals") < idx("HTTP fundamentals") < idx("SSRF")
    assert idx("C programming fundamentals") < idx("Memory layout") < idx("Buffer overflow")
    assert idx("Buffer overflow") < idx("ret2libc")
    assert idx("Modular arithmetic") < idx("RSA") < idx("Common crypto attacks")
    # Every path item is actionable.
    for g in data["gaps"]:
        assert g["priority"] in ("High", "Medium", "Low")
        assert g["learn"] and g["practice"]
    assert data["next"] is not None


def test_goal_analysis_has_domain_breakdown(client: TestClient, db_session: Session):
    token = _signup(client, uname="gap-goal", email="gap-goal@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    data = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    domains = {d["domain"]: d for d in data["domain_breakdown"]}
    for name in ("Web Security", "Binary Exploitation", "Cryptography", "Forensics", "Reverse Engineering"):
        assert name in domains
    # Empty vault → every domain is a Major gap (gap_ratio == 1.0).
    assert all(d["status"] == "Major gap" for d in data["domain_breakdown"])

    # Unknown goal → 404.
    resp = client.get("/api/kb/gaps/goal?goal=nonsense", headers=headers)
    assert resp.status_code == 404


def test_domains_endpoint_lists_goals(client: TestClient, db_session: Session):
    token = _signup(client, uname="gap-domains", email="gap-domains@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = client.get("/api/kb/gaps/domains", headers=headers).json()
    keys = {g["key"] for g in body["goals"]}
    assert "ctf" in keys and "software-engineering" in keys
    ctf = next(g for g in body["goals"] if g["key"] == "ctf")
    assert "Web Security" in ctf["domains"] and "Binary Exploitation" in ctf["domains"]


def test_learning_path_items_link_real_documents(client: TestClient, db_session: Session):
    """Every learning-path item carries the same real Second Brain sources as
    its gap card — so the path deep-links into the vault (never fabricated)."""
    course_id, headers = _build_web_security_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()

    flat = {item["name"]: item for phase in data["path"] for item in phase["items"]}
    # XSS is a real gap with a linked document → the path item links it too.
    assert "XSS" in flat
    assert flat["XSS"]["sources"], "path item must link the real document"
    assert flat["XSS"]["sources"][0]["title"] == "XSS Basics"
    # SSRF has no vault evidence → the path item honestly has no sources.
    assert "SSRF" in flat
    assert flat["SSRF"]["sources"] == []


def test_create_gap_note_drafts_capture_and_is_idempotent(client: TestClient, db_session: Session):
    """Create-note drafts a ready-to-edit capture note; re-creating the same
    gap reuses the existing draft instead of duplicating it."""
    token = _signup(client, uname="gap-note", email="gap-note@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db_session, email="gap-note@test.com")

    resp = client.post(
        "/api/kb/gaps/note",
        headers=headers,
        json={
            "name": "SSRF",
            "subject": "Web Security",
            "why": "Server-side request forgery lets attackers pivot into internal networks.",
            "learn": ["Understand the SSRF request flow", "Identify SSRF sinks"],
            "practice": ["Exploit a lab target", "Write a mitigation checklist"],
            "sources": [{"document_id": 1, "title": "Some doc"}],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["created"] is True
    doc_id = body["document"]["id"]
    assert body["document"]["status"] == "draft"

    doc = db_session.query(KbDocument).filter(KbDocument.id == doc_id).first()
    assert doc is not None and doc.user_id == uid
    assert doc.status == "draft"
    assert doc.title == "Study: SSRF"
    text = doc.extracted_text or ""
    assert "# Study: SSRF" in text
    assert "Understand the SSRF request flow" in text
    assert "Exploit a lab target" in text
    assert "Some doc" in text
    meta = json.loads(doc.metadata_json or "{}")
    # The dedupe key is stored normalized (lowercased) for idempotency.
    assert meta["origin"] == "gap_note" and meta["gap"] == "ssrf"

    # Idempotent: a second create returns the SAME draft (created=False).
    resp2 = client.post("/api/kb/gaps/note", headers=headers, json={"name": "SSRF"})
    assert resp2.status_code == 200
    assert resp2.json()["created"] is False
    assert resp2.json()["document"]["id"] == doc_id

    # The dedupe key is normalized: a differently-cased name is the same gap.
    resp3 = client.post("/api/kb/gaps/note", headers=headers, json={"name": "  ssrf "})
    assert resp3.status_code == 200
    assert resp3.json()["created"] is False
    assert resp3.json()["document"]["id"] == doc_id

    drafts = (
        db_session.query(KbDocument)
        .filter(KbDocument.user_id == uid, KbDocument.status == "draft")
        .count()
    )
    assert drafts == 1  # no duplicate drafts


# ---------------------------------------------------------------------------
# Saved Goal-level Gap Analysis (save-and-reuse cache)
# ---------------------------------------------------------------------------


def test_goal_gaps_saved_and_reused_until_explicit_reanalyze(client: TestClient, db_session: Session):
    """First GET computes & saves; later GETs reuse the saved copy (same
    ``analyzed_at``); only the explicit Re-analyze POST recomputes."""
    token = _signup(client, uname="gap-cache", email="gap-cache@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db_session, email="gap-cache@test.com")

    first = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert first["cached"] is False
    assert first["analyzed_at"]
    assert first["goal_key"] == "ctf"
    # The payload is complete (not just cache metadata).
    assert first["strengths"] == [] and first["gaps"]

    rows = (
        db_session.query(GoalGapAnalysis)
        .filter(GoalGapAnalysis.user_id == uid, GoalGapAnalysis.goal_key == "ctf")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].analyzed_at is not None

    # Second GET → the saved copy, same timestamp, no recompute.
    second = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert second["cached"] is True
    assert second["analyzed_at"] == first["analyzed_at"]
    assert second["gaps"][0]["name"] == first["gaps"][0]["name"]

    # Explicit Re-analyze → fresh timestamp, saved again.
    third = client.post("/api/kb/gaps/goal/analyze?goal=ctf", headers=headers).json()
    assert third["cached"] is False
    assert third["analyzed_at"] != second["analyzed_at"]

    # Subsequent GET serves the refreshed copy.
    fourth = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert fourth["cached"] is True
    assert fourth["analyzed_at"] == third["analyzed_at"]

    # Exactly one saved row per (user, goal) — upsert, never duplicate.
    assert (
        db_session.query(GoalGapAnalysis)
        .filter(GoalGapAnalysis.user_id == uid, GoalGapAnalysis.goal_key == "ctf")
        .count()
        == 1
    )

    # Unknown goals → 404 on both the GET and the Re-analyze POST.
    assert client.get("/api/kb/gaps/goal?goal=nonsense", headers=headers).status_code == 404
    assert client.post("/api/kb/gaps/goal/analyze?goal=nonsense", headers=headers).status_code == 404


def test_saved_goal_payload_missing_fields_is_normalized_on_read(client: TestClient, db_session: Session):
    """Stored payloads are returned verbatim by the loader — a payload written
    by an older/other engine must still come back with the complete shape so
    the UI never crashes on unguarded reads (regression: LearningPlanner)."""
    token = _signup(client, uname="gap-legacy", email="gap-legacy@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db_session, email="gap-legacy@test.com")

    # Compute + save a fresh analysis, then corrupt the stored payload to
    # simulate a legacy row missing the UI-critical fields.
    client.get("/api/kb/gaps/goal?goal=ctf", headers=headers)
    row = (
        db_session.query(GoalGapAnalysis)
        .filter(GoalGapAnalysis.user_id == uid, GoalGapAnalysis.goal_key == "ctf")
        .first()
    )
    assert row is not None
    payload = json.loads(row.payload_json)
    for key in ("summary", "strengths", "path", "domain_breakdown", "coverage"):
        payload.pop(key, None)
    payload["summary"] = "legacy string summary"  # not a dict at all
    row.payload_json = json.dumps(payload)
    db_session.commit()

    # The next GET serves the saved copy, normalized to the full shape.
    data = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert data["cached"] is True
    assert data["summary"] == {"text": "", "priorities": [], "strong_areas": []}
    assert data["strengths"] == []
    assert isinstance(data["path"], list)
    assert isinstance(data["domain_breakdown"], list)
    assert data["coverage"] == {"known": 0, "gaps": 0, "total": 0, "percent": 0.0}
    # A real normalized gap still carries its actionable fields.
    assert data["gaps"]
    assert all("learn" in g and "practice" in g for g in data["gaps"])


def test_goal_gap_cache_is_per_user(client: TestClient, db_session: Session):
    """Each user's saved goal analysis is stored under their own user_id."""
    token_a = _signup(client, uname="gap-cache-a", email="gap-cache-a@test.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    uid_a = _uid(db_session, email="gap-cache-a@test.com")

    token_b = _signup(client, uname="gap-cache-b", email="gap-cache-b@test.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    uid_b = _uid(db_session, email="gap-cache-b@test.com")

    client.get("/api/kb/gaps/goal?goal=ctf", headers=headers_a)
    client.get("/api/kb/gaps/goal?goal=ctf", headers=headers_b)

    rows = db_session.query(GoalGapAnalysis).filter(GoalGapAnalysis.goal_key == "ctf").all()
    assert len(rows) == 2
    assert {r.user_id for r in rows} == {uid_a, uid_b}

    # Re-analyzing for user A does not touch user B's saved copy.
    client.post("/api/kb/gaps/goal/analyze?goal=ctf", headers=headers_a)
    assert (
        db_session.query(GoalGapAnalysis)
        .filter(GoalGapAnalysis.user_id == uid_b, GoalGapAnalysis.goal_key == "ctf")
        .count()
        == 1
    )


def test_reindex_invalidates_goal_gap_cache(client: TestClient, db_session: Session):
    """A KB reindex changes the evidence — the saved goal analyses are dropped
    so the next request recomputes from the fresh data."""
    token = _signup(client, uname="gap-cache-c", email="gap-cache-c@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db_session, email="gap-cache-c@test.com")

    client.get("/api/kb/gaps/goal?goal=ctf", headers=headers)
    client.get("/api/kb/gaps/goal?goal=software-engineering", headers=headers)
    assert (
        db_session.query(GoalGapAnalysis).filter(GoalGapAnalysis.user_id == uid).count()
        == 2
    )

    resp = client.post("/api/kb/admin/reindex", headers=headers)
    assert resp.status_code == 200, resp.text

    assert (
        db_session.query(GoalGapAnalysis).filter(GoalGapAnalysis.user_id == uid).count()
        == 0
    )
    # The next GET recomputes (cached=False again).
    after = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert after["cached"] is False
    assert after["analyzed_at"]


def test_gaps_are_per_user(client: TestClient, db_session: Session):
    course_id, headers_a = _build_web_security_course(client, db_session)
    data_a = client.get(f"/api/courses/{course_id}/gaps", headers=headers_a).json()

    token_b = _signup(client, uname="gap-b", email="gap-b@test.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    data_b = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers_b).json()

    xss_a = next(g for g in data_a["gaps"] if g["name"] == "XSS")
    assert xss_a["evidence"]["mentions"] == 1
    # User B's vault has no XSS evidence → Not Found, no sources.
    xss_b = next(g for g in data_b["gaps"] if g["name"] == "XSS")
    assert xss_b["level"] == "Not Found"
    assert xss_b["sources"] == []
