"""Tests for the folder-hierarchy-as-source-of-truth model.

The Second Brain folder hierarchy is the canonical organization: top-level
folder → Course, child folders → Domains, notes inside → Documents. These
tests cover:

- ``sync_all_folders`` derives one ``KbFolder`` per course child folder
  (nested folders included), keyed by path, idempotent, and stale rows are
  removed when a folder is renamed/moved/deleted.
- ``GET /api/kb/folders?course_id=`` returns the domain tree.
- ``GET /api/kb/folders/{id}`` returns one domain with its documents.
- ``GET /api/kb/folders/{id}/gaps`` persists: first call computes + saves,
  later calls reuse the saved copy (``cached: True``) — no recompute on view.
- ``POST /api/kb/folders/{id}/gaps/analyze`` is the explicit recompute path.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Course, KbFolder, KbSource, KbDocument, User

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "sb-domains", email: str = "sb-domains@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "SB Domains",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "sb-domains@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_source(db: Session, user_id: int, name: str = "Vault") -> KbSource:
    src = KbSource(
        user_id=user_id,
        name=name,
        source_type="local_dir",
        root_path=f"/tmp/{name}",
        enabled=True,
    )
    db.add(src)
    db.commit()
    db.refresh(src)
    return src


def _make_doc(
    db: Session,
    user_id: int,
    source_id: int,
    title: str,
    path: str,
) -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        source_id=source_id,
        title=title,
        doc_type="md",
        path_rel=path,
        extracted_text="# Title\n\ncontent",
        content_hash=f"hash-{path}",
        char_count=40,
        status="unchanged",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _sync(client: TestClient, token: str) -> dict:
    resp = client.post("/api/courses/sync-kb", headers={AUTH: f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _domain_row(db: Session, user_id: int, path: str) -> KbFolder | None:
    return (
        db.query(KbFolder)
        .filter(KbFolder.user_id == user_id, KbFolder.path == path)
        .first()
    )


# ---------------------------------------------------------------------------
# Canonical folder sync (folder hierarchy = source of truth)
# ---------------------------------------------------------------------------


def test_sync_derives_domain_folders_from_course_folders(client: TestClient, db_session: Session):
    """``Cybersecurity/Web Security/SQL Injection.md`` → Course Cybersecurity,
    domain ``Cybersecurity/Web Security`` — no manual triage or tagging."""
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "SQL Injection", "Cybersecurity/Web Security/sqli.md")
    _make_doc(db_session, uid, src.id, "XSS", "Cybersecurity/Web Security/xss.md")
    _make_doc(db_session, uid, src.id, "Ghidra", "Cybersecurity/Reverse Engineering/ghidra.md")
    _make_doc(db_session, uid, src.id, "Recon", "Cybersecurity/OSINT/recon.md")
    _make_doc(db_session, uid, src.id, "Root Note", "Cybersecurity/root.md")  # in course root → no domain

    body = _sync(client, token)
    assert body["course_folders"] == 1  # one course: Cybersecurity
    assert body["domains"] == 3  # three domains: Web Security, RE, OSINT

    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_folder", Course.title == "Cybersecurity")
        .first()
    )
    assert course is not None

    web = _domain_row(db_session, uid, "Cybersecurity/Web Security")
    assert web is not None
    assert web.course_id == course.id
    assert web.name == "Web Security"
    assert web.depth == 1
    assert web.parent_id is None
    assert web.doc_count == 2  # direct children only

    rev = _domain_row(db_session, uid, "Cybersecurity/Reverse Engineering")
    assert rev is not None and rev.doc_count == 1
    osint = _domain_row(db_session, uid, "Cybersecurity/OSINT")
    assert osint is not None and osint.doc_count == 1


def test_sync_is_idempotent_and_counts_direct_children(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "SQLi", "Cybersecurity/Web Security/sqli.md")
    _make_doc(db_session, uid, src.id, "Nested", "Cybersecurity/Web Security/Advanced/deep.md")

    _sync(client, token)
    web = _domain_row(db_session, uid, "Cybersecurity/Web Security")
    advanced = _domain_row(db_session, uid, "Cybersecurity/Web Security/Advanced")
    assert web is not None and web.doc_count == 1  # sqli is direct; deep is nested
    assert advanced is not None and advanced.doc_count == 1
    assert advanced.parent_id == web.id
    assert advanced.depth == 2

    # Idempotent: a second sync updates, creates nothing new.
    body = _sync(client, token)
    assert body["domains"] == 2
    rows = db_session.query(KbFolder).filter(KbFolder.user_id == uid).count()
    assert rows == 2


def test_sync_removes_stale_domain_when_folder_deleted(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "SQLi", "Cybersecurity/Web Security/sqli.md")

    _sync(client, token)
    assert _domain_row(db_session, uid, "Cybersecurity/Web Security") is not None

    # Move the document to a new folder → old domain vanishes, new one appears.
    doc.path_rel = "Cybersecurity/Penetration Testing/nmap.md"
    db_session.commit()

    body = _sync(client, token)
    assert _domain_row(db_session, uid, "Cybersecurity/Web Security") is None
    assert _domain_row(db_session, uid, "Cybersecurity/Penetration Testing") is not None
    # Folder rows are 1:1 with currently-resolving folders — no stale rows left.
    assert (
        db_session.query(KbFolder).filter(KbFolder.user_id == uid).count()
        == body["domains"]
        == 1
    )


def test_sync_cleans_domain_gaps_with_stale_folder(client: TestClient, db_session: Session):
    """Deleting a folder removes its saved gap analysis (no orphaned rows)."""
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "SQLi", "Cybersecurity/Web Security/sqli.md")
    _sync(client, token)

    web = _domain_row(db_session, uid, "Cybersecurity/Web Security")
    assert web is not None

    # Compute + save a domain analysis, then delete the folder.
    resp = client.get(f"/api/kb/folders/{web.id}/gaps", headers={AUTH: f"Bearer {token}"})
    assert resp.status_code == 200
    from app.models import FolderGapAnalysis

    assert db_session.query(FolderGapAnalysis).filter(FolderGapAnalysis.folder_id == web.id).count() == 1

    doc.path_rel = "elsewhere.md"
    db_session.commit()
    _sync(client, token)
    assert db_session.query(FolderGapAnalysis).filter(FolderGapAnalysis.folder_id == web.id).count() == 0


# ---------------------------------------------------------------------------
# Domain views (tree + detail)
# ---------------------------------------------------------------------------


def test_domain_tree_endpoint_returns_hierarchy(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "A", "Cybersecurity/Web Security/a.md")
    _make_doc(db_session, uid, src.id, "B", "Cybersecurity/Web Security/Advanced/b.md")
    _make_doc(db_session, uid, src.id, "C", "Cybersecurity/Reverse Engineering/c.md")
    _sync(client, token)

    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.title == "Cybersecurity")
        .first()
    )
    resp = client.get(
        f"/api/kb/folders?course_id={course.id}",
        headers={AUTH: f"Bearer {token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    names = {i["name"] for i in items}
    assert names == {"Web Security", "Reverse Engineering"}
    web = next(i for i in items if i["name"] == "Web Security")
    assert web["doc_count"] == 1  # direct child only
    assert {c["name"] for c in web["children"]} == {"Advanced"}


def test_domain_detail_returns_documents_and_subfolders(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "SQL Injection", "Cybersecurity/Web Security/sqli.md")
    _make_doc(db_session, uid, src.id, "XSS", "Cybersecurity/Web Security/xss.md")
    _make_doc(db_session, uid, src.id, "Deep", "Cybersecurity/Web Security/Advanced/deep.md")
    _make_doc(db_session, uid, src.id, "Other", "Cybersecurity/OSINT/recon.md")
    _sync(client, token)

    web = _domain_row(db_session, uid, "Cybersecurity/Web Security")
    resp = client.get(f"/api/kb/folders/{web.id}", headers={AUTH: f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Web Security"
    assert {d["title"] for d in data["documents"]} == {"SQL Injection", "XSS"}
    assert [s["name"] for s in data["subfolders"]] == ["Advanced"]
    assert data["course"]["title"] == "Cybersecurity"
    assert data["breadcrumb"][-1]["name"] == "Web Security"


def test_domain_detail_404_for_unknown(client: TestClient):
    token = _signup(client)
    resp = client.get("/api/kb/folders/999999", headers={AUTH: f"Bearer {token}"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Persisted domain gap analysis (no recompute on navigation)
# ---------------------------------------------------------------------------


def test_domain_gaps_compute_once_then_reuse(client: TestClient, db_session: Session, monkeypatch):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "SQL Injection", "Cybersecurity/Web Security/sqli.md")
    _make_doc(db_session, uid, src.id, "XSS", "Cybersecurity/Web Security/xss.md")
    _sync(client, token)

    web = _domain_row(db_session, uid, "Cybersecurity/Web Security")
    assert web is not None

    calls = {"n": 0}
    from app.services.kb import gap_engine as _ge

    real_analyze = _ge.analyze_subject

    def counting_analyze(*args, **kwargs):
        calls["n"] += 1
        return real_analyze(*args, **kwargs)

    monkeypatch.setattr(_ge, "analyze_subject", counting_analyze)

    # First request: computes (calls the engine), saves, cached=False.
    r1 = client.get(f"/api/kb/folders/{web.id}/gaps", headers={AUTH: f"Bearer {token}"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["cached"] is False
    assert d1["analyzed_at"]
    assert "summary" in d1
    assert d1["folder"]["name"] == "Web Security"
    assert calls["n"] == 1

    # Second request (navigation/refresh): reuses the saved copy — no engine.
    r2 = client.get(f"/api/kb/folders/{web.id}/gaps", headers={AUTH: f"Bearer {token}"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["cached"] is True
    assert d2["analyzed_at"] == d1["analyzed_at"]
    assert calls["n"] == 1  # NOT called again


def test_domain_gaps_reanalyze_is_explicit(client: TestClient, db_session: Session, monkeypatch):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "SQLi", "Cybersecurity/Web Security/sqli.md")
    _sync(client, token)

    web = _domain_row(db_session, uid, "Cybersecurity/Web Security")
    calls = {"n": 0}
    from app.services.kb import gap_engine as _ge

    real_analyze = _ge.analyze_subject

    def counting_analyze(*args, **kwargs):
        calls["n"] += 1
        return real_analyze(*args, **kwargs)

    monkeypatch.setattr(_ge, "analyze_subject", counting_analyze)

    client.get(f"/api/kb/folders/{web.id}/gaps", headers={AUTH: f"Bearer {token}"})
    assert calls["n"] == 1

    # Re-analyze → the explicit recompute path → engine called again + saved.
    resp = client.post(
        f"/api/kb/folders/{web.id}/gaps/analyze",
        headers={AUTH: f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["cached"] is False
    assert calls["n"] == 2

    # Subsequent view reuses the freshly saved copy.
    again = client.get(f"/api/kb/folders/{web.id}/gaps", headers={AUTH: f"Bearer {token}"})
    assert again.json()["cached"] is True
    assert calls["n"] == 2


def test_course_content_includes_domains_grid(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "SQLi", "Cybersecurity/Web Security/sqli.md")
    _make_doc(db_session, uid, src.id, "Ghidra", "Cybersecurity/Reverse Engineering/ghidra.md")
    _sync(client, token)

    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.title == "Cybersecurity")
        .first()
    )
    data = client.get(f"/api/courses/{course.id}/content", headers={AUTH: f"Bearer {token}"}).json()
    domains = data["second_brain"]["domains"]
    assert {d["name"] for d in domains} == {"Web Security", "Reverse Engineering"}
    web = next(d for d in domains if d["name"] == "Web Security")
    assert web["id"] is not None
    assert web["doc_count"] == 1
