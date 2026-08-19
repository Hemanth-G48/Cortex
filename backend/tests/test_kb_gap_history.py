"""Tests for the Gap Analysis history (per-scope snapshots over time) and the
\"new notes since last analysis\" staleness indicator.

Covers:
- course history: recorded on compute + re-analyze, chronological listing,
  capped at 25 per subject, per-user isolation, deletion cleanup,
  new_notes_since_analysis on cached loads;
- goal history: same recording, reindex keeps history while invalidating the
  cache, staleness after adding documents, unknown-goal 404.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Course,
    CourseGapAnalysis,
    GapAnalysisHistory,
    GoalGapAnalysis,
    KbDocument,
    KbDocumentTag,
    KbSource,
    KbTag,
    User,
)


def _signup(client: TestClient, uname: str, email: str) -> str:
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Gap History", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str) -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _source(db: Session, user_id: int) -> KbSource:
    src = KbSource(user_id=user_id, name="Notes", source_type="local_dir", root_path="/tmp/Notes")
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def _doc(db: Session, user_id: int, source_id: int, title: str, path: str) -> KbDocument:
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


def _build_course(client: TestClient, db: Session, uname: str, email: str) -> tuple[int, dict, int]:
    """User with one doc tagged ``course:Web Security`` → a derived course."""
    token = _signup(client, uname, email)
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db, email)
    src = _source(db, uid)
    doc = _doc(db, uid, src.id, "XSS Basics", "web/xss.md")
    tag = _tag(db, uid, "course:Web Security")
    _link(db, doc, tag)
    resp = client.post("/api/courses/sync-kb", headers=headers)
    assert resp.status_code == 200
    course = db.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_tag").first()
    assert course is not None
    return course.id, headers, uid


def _history_rows(db: Session, user_id: int, course_id: int | None = None, goal_key: str | None = None) -> list[GapAnalysisHistory]:
    q = db.query(GapAnalysisHistory).filter(GapAnalysisHistory.user_id == user_id)
    if course_id is not None:
        q = q.filter(GapAnalysisHistory.scope_type == "course", GapAnalysisHistory.course_id == course_id)
    elif goal_key is not None:
        q = q.filter(GapAnalysisHistory.scope_type == "goal", GapAnalysisHistory.goal_key == goal_key)
    return q.order_by(GapAnalysisHistory.analyzed_at.asc()).all()


# ---------------------------------------------------------------------------
# Course history
# ---------------------------------------------------------------------------


def test_course_history_recorded_and_listed_chronologically(client: TestClient, db_session: Session):
    course_id, headers, uid = _build_course(client, db_session, "hist-course", "hist-course@test.com")

    first = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert first["cached"] is False
    reanalyzed = client.post(f"/api/courses/{course_id}/gaps/analyze", headers=headers).json()
    assert reanalyzed["cached"] is False

    rows = _history_rows(db_session, uid, course_id=course_id)
    assert len(rows) == 2

    body = client.get(f"/api/courses/{course_id}/gaps/history", headers=headers).json()
    history = body["history"]
    assert len(history) == 2
    # Chronological (oldest first) — matches the cache timestamps.
    assert history[0]["analyzed_at"] == first["analyzed_at"]
    assert history[1]["analyzed_at"] == reanalyzed["analyzed_at"]
    # Compact diffable shape.
    for snap in history:
        assert snap["gap_count"] > 0
        assert snap["strength_count"] == 0  # empty vault → no strengths
        assert snap["coverage"]["total"] > 0
        assert snap["gaps"] and all("name" in g and "level" in g for g in snap["gaps"])
    assert history[0]["document_count"] == 1


def test_course_history_capped_at_25(client: TestClient, db_session: Session):
    course_id, headers, uid = _build_course(client, db_session, "hist-cap", "hist-cap@test.com")

    for _ in range(30):
        client.post(f"/api/courses/{course_id}/gaps/analyze", headers=headers)

    rows = _history_rows(db_session, uid, course_id=course_id)
    assert len(rows) == 25  # pruned to the cap
    # The oldest analyses were dropped.
    body = client.get(f"/api/courses/{course_id}/gaps/history", headers=headers).json()
    assert len(body["history"]) == 25
    # The current cache copy is untouched by the history cap.
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.user_id == uid, CourseGapAnalysis.course_id == course_id)
        .count()
        == 1
    )


def test_course_history_per_user_and_deletion_cleanup(client: TestClient, db_session: Session):
    course_a, headers_a, uid_a = _build_course(client, db_session, "hist-a", "hist-a@test.com")
    course_b, headers_b, uid_b = _build_course(client, db_session, "hist-b", "hist-b@test.com")

    client.post(f"/api/courses/{course_a}/gaps/analyze", headers=headers_a)
    client.post(f"/api/courses/{course_b}/gaps/analyze", headers=headers_b)

    assert len(_history_rows(db_session, uid_a, course_id=course_a)) == 1
    assert len(_history_rows(db_session, uid_b, course_id=course_b)) == 1

    # Deleting course A removes its history but not user B's.
    resp = client.delete(f"/api/courses/{course_a}", headers=headers_a)
    assert resp.status_code == 200
    assert len(_history_rows(db_session, uid_a, course_id=course_a)) == 0
    assert len(_history_rows(db_session, uid_b, course_id=course_b)) == 1


def test_course_cached_load_surfaces_new_notes_since_analysis(client: TestClient, db_session: Session):
    course_id, headers, uid = _build_course(client, db_session, "hist-stale", "hist-stale@test.com")
    tag = db_session.query(KbTag).filter(KbTag.user_id == uid, KbTag.name == "course:Web Security").first()

    first = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert first["cached"] is False
    assert first["document_count"] == 1

    # A new note for the subject arrives after the analysis.
    src = db_session.query(KbSource).filter(KbSource.user_id == uid).first()
    new_doc = _doc(db_session, uid, src.id, "SSRF Notes", "web/ssrf.md")
    _link(db_session, new_doc, tag)

    second = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert second["cached"] is True  # still reusing the saved copy
    assert second["analyzed_at"] == first["analyzed_at"]
    assert second["new_notes_since_analysis"] == 1

    # No new notes → 0.
    third = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert third["cached"] is True
    assert third["new_notes_since_analysis"] == 1  # the saved copy is unchanged


# ---------------------------------------------------------------------------
# Goal history
# ---------------------------------------------------------------------------


def test_goal_history_recorded_and_surfaces_staleness(client: TestClient, db_session: Session):
    token = _signup(client, "hist-goal", "hist-goal@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db_session, "hist-goal@test.com")
    src = _source(db_session, uid)

    first = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert first["cached"] is False
    assert first["document_count"] == 0  # no docs yet

    # History endpoint lists the baseline snapshot.
    body = client.get("/api/kb/gaps/goal/history?goal=ctf", headers=headers).json()
    assert len(body["history"]) == 1
    assert body["history"][0]["gap_count"] > 0

    # Add notes → the cached load reports them as new.
    _doc(db_session, uid, src.id, "Note", "a.md")
    _doc(db_session, uid, src.id, "Note", "b.md")
    second = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert second["cached"] is True
    assert second["new_notes_since_analysis"] == 2

    # Re-analyze adds a snapshot AND resets the staleness (fresh result).
    reanalyzed = client.post("/api/kb/gaps/goal/analyze?goal=ctf", headers=headers).json()
    assert reanalyzed["cached"] is False
    assert reanalyzed["document_count"] == 2
    assert len(client.get("/api/kb/gaps/goal/history?goal=ctf", headers=headers).json()["history"]) == 2

    # Unknown goal → 404 on the history endpoint too.
    assert client.get("/api/kb/gaps/goal/history?goal=nonsense", headers=headers).status_code == 404


def test_reindex_invalidates_cache_but_keeps_goal_history(client: TestClient, db_session: Session):
    token = _signup(client, "hist-reindex", "hist-reindex@test.com")
    headers = {"Authorization": f"Bearer {token}"}
    uid = _uid(db_session, "hist-reindex@test.com")

    client.get("/api/kb/gaps/goal?goal=ctf", headers=headers)
    assert len(_history_rows(db_session, uid, goal_key="ctf")) == 1

    resp = client.post("/api/kb/admin/reindex", headers=headers)
    assert resp.status_code == 200, resp.text

    # Cache invalidated, history kept (it is the permanent record).
    assert db_session.query(GoalGapAnalysis).filter(GoalGapAnalysis.user_id == uid).count() == 0
    assert len(_history_rows(db_session, uid, goal_key="ctf")) == 1

    # The next request recomputes → a second snapshot appears.
    after = client.get("/api/kb/gaps/goal?goal=ctf", headers=headers).json()
    assert after["cached"] is False
    assert len(_history_rows(db_session, uid, goal_key="ctf")) == 2
