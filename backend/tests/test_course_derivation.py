"""Tests for dynamic courses derived from Second Brain tags + Classroom resources."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Course, KbDocument, KbDocumentTag, KbSource, KbTag, User

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "sb-courses", email: str = "sb-courses@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "SB Courses",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "sb-courses@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_source(db: Session, user_id: int, name: str = "Notes", enabled: bool = True) -> KbSource:
    src = KbSource(
        user_id=user_id,
        name=name,
        source_type="local_dir",
        root_path=f"/tmp/{name}",
        enabled=enabled,
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
    frontmatter: dict | None = None,
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
        frontmatter_json=json.dumps(frontmatter) if frontmatter else None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _make_tag(db: Session, user_id: int, name: str) -> KbTag:
    tag = KbTag(user_id=user_id, name=name, kind="manual")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def _link(db: Session, doc: KbDocument, tag: KbTag) -> None:
    db.add(KbDocumentTag(user_id=doc.user_id, document_id=doc.id, tag_id=tag.id, provenance="manual"))
    db.commit()


def test_derive_creates_courses_from_tags(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    # Root-level paths: these tests target tag derivation, so no folder
    # subjects should be derived from the fixture documents.
    doc1 = _make_doc(db_session, uid, src.id, "Intro", "intro.md")
    doc2 = _make_doc(db_session, uid, src.id, "Scheduling", "sched.md")
    doc3 = _make_doc(db_session, uid, src.id, "Limits", "limits.md")

    os_tag = _make_tag(db_session, uid, "course:Operating Systems")
    math_tag = _make_tag(db_session, uid, "course:Math")
    _make_tag(db_session, uid, "random")  # non-course tag must be ignored
    _link(db_session, doc1, os_tag)
    _link(db_session, doc2, os_tag)
    _link(db_session, doc3, math_tag)

    resp = client.post("/api/courses/sync-kb", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2
    assert body["removed"] == 0

    courses = db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_tag").all()
    titles = {c.title for c in courses}
    assert titles == {"Operating Systems", "Math"}
    assert all(c.kb_tag_id is not None for c in courses)
    by_title = {c.title: c for c in courses}
    assert by_title["Operating Systems"].total_assignments == 2
    assert by_title["Operating Systems"].status == "In progress"
    assert by_title["Math"].total_assignments == 1


def test_derive_is_idempotent(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "01.md")
    tag = _make_tag(db_session, uid, "course:Data Structures")
    _link(db_session, doc, tag)

    first = client.post("/api/courses/sync-kb", headers=headers).json()
    assert first["created"] == 1

    second = client.post("/api/courses/sync-kb", headers=headers).json()
    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["removed"] == 0

    count = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .count()
    )
    assert count == 1


def test_derive_removes_stale_tag_course(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Old", "01.md")
    tag = _make_tag(db_session, uid, "course:Deprecated")
    _link(db_session, doc, tag)

    client.post("/api/courses/sync-kb", headers=headers)
    assert db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_tag").count() == 1

    db_session.delete(tag)
    db_session.commit()

    resp = client.post("/api/courses/sync-kb", headers=headers).json()
    assert resp["removed"] == 1
    assert db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_tag").count() == 0


def test_resources_endpoint_combines_sources(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid, name="OS Notes", enabled=True)
    _make_source(db_session, uid, name="Disabled", enabled=False)  # excluded
    db_session.add(Course(
        title="Biology",
        source_type="classroom",
        google_id="gc-bio",
        classroom_url="https://classroom.google.com/c/123",
        user_id=uid,
        status="In progress",
    ))
    db_session.commit()

    resp = client.get("/api/courses/resources", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    folder = next(r for r in data if r["type"] == "folder")
    assert folder["title"] == "OS Notes"
    assert folder["url"] == f"/tmp/OS Notes"

    classroom = next(r for r in data if r["type"] == "classroom")
    assert classroom["title"] == "Biology"
    assert classroom["url"] == "https://classroom.google.com/c/123"
    assert classroom["id"] == "gc-gc-bio"

    # Defect #26: every card carries a metadata-derived doc_type for its icon.
    assert classroom["doc_type"] == "classroom"
    # This source has no indexed documents yet → neutral folder type.
    assert folder["doc_type"] == "folder"


def test_resources_doc_type_comes_from_authoritative_document_type(
    client: TestClient, db_session: Session
):
    """Defect #26: the card icon follows ``KbDocument.doc_type`` (the real file
    type), not the synthetic card kind."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid, name="Papers", enabled=True)
    # Two PDFs vs one markdown → the source's dominant type is "pdf".
    for i in range(2):
        db_session.add(KbDocument(
            user_id=uid, source_id=src.id, path_rel=f"p{i}.pdf",
            title=f"Paper {i}", doc_type="pdf", status="unchanged",
        ))
    db_session.add(KbDocument(
        user_id=uid, source_id=src.id, path_rel="note.md",
        title="Note", doc_type="md", status="unchanged",
    ))
    db_session.commit()

    data = client.get("/api/courses/resources", headers=headers).json()
    folder = next(r for r in data if r["type"] == "folder")
    assert folder["doc_type"] == "pdf"


def test_resources_ignores_deleted_documents_for_doc_type(
    client: TestClient, db_session: Session
):
    """Deleted documents must not drive the card's icon type (defect #26)."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid, name="Mixed", enabled=True)
    for i in range(3):
        db_session.add(KbDocument(
            user_id=uid, source_id=src.id, path_rel=f"old{i}.pdf",
            title=f"Old {i}", doc_type="pdf", status="deleted",
        ))
    db_session.add(KbDocument(
        user_id=uid, source_id=src.id, path_rel="live.md",
        title="Live", doc_type="md", status="unchanged",
    ))
    db_session.commit()

    data = client.get("/api/courses/resources", headers=headers).json()
    folder = next(r for r in data if r["type"] == "folder")
    assert folder["doc_type"] == "md"


def test_resources_fallback_defaults_when_nothing_derived(client: TestClient, db_session: Session):
    token = _signup(client)
    headers = {AUTH: f"Bearer {token}"}

    resp = client.get("/api/courses/resources", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    # Falls back to the static default resource cards.
    assert len(data) == 4
    assert all(r["url"] == "#" for r in data)


def test_sync_kb_works_without_auth(client: TestClient):
    """Single-user app: no token needed to trigger the sync."""
    resp = client.post("/api/courses/sync-kb")
    assert resp.status_code == 200
    assert resp.json()["created"] == 0


def test_derive_reports_rich_summary(client: TestClient, db_session: Session):
    """Sync summary now carries sources/documents/course_tags/errors so the UI
    can explain *why* a sync is empty.
    """
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "01.md")
    tag = _make_tag(db_session, uid, "course:Databases")
    _link(db_session, doc, tag)

    body = client.post("/api/courses/sync-kb", headers=headers).json()
    assert body["sources"] == 1
    assert body["documents"] == 1
    assert body["course_tags"] == 1
    assert body["course_folders"] == 0
    assert body["errors"] == []
    assert body["synced_at"]

    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .first()
    )
    assert course is not None
    assert course.kb_document_count == 1
    assert course.status == "In progress"


def test_sync_status_endpoint_reports_counters(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "01.md")
    tag = _make_tag(db_session, uid, "course:Operating Systems")
    _link(db_session, doc, tag)

    client.post("/api/courses/sync-kb", headers=headers)

    resp = client.get("/api/courses/sync-status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"] == 1
    assert body["documents"] == 1
    assert body["course_tags"] == 1
    assert body["course_folders"] == 0
    assert body["last_sync"] is not None
    assert body["last_sync"]["created"] == 1
    assert body["last_sync"]["errors"] == []
    assert "google" in body
    assert body["google"]["configured"] in (True, False)


def test_sync_status_empty_before_first_sync(client: TestClient, db_session: Session):
    token = _signup(client)
    headers = {AUTH: f"Bearer {token}"}

    resp = client.get("/api/courses/sync-status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"] == 0
    assert body["documents"] == 0
    assert body["course_tags"] == 0
    assert body["course_folders"] == 0
    assert body["last_sync"] is None


def test_tag_create_endpoint_triggers_course_derivation(client: TestClient, db_session: Session):
    """Tagging a note ``course:<name>`` in the KB editor immediately creates
    the course — no manual Courses-page sync needed.
    """
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "01.md")

    resp = client.post(
        f"/api/kb/documents/{doc.id}/tags/create",
        json={"name": "course:Operating Systems"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    applied = {t["name"]: t for t in data["applied"]}
    assert "course:Operating Systems" in applied
    assert applied["course:Operating Systems"]["provenance"] == "manual"

    # Derivation ran as an event hook — the course already exists.
    courses = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .all()
    )
    assert len(courses) == 1
    assert courses[0].title == "Operating Systems"
    assert courses[0].kb_document_count == 1


def test_tag_create_endpoint_is_idempotent(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "02.md")

    for _ in range(2):
        resp = client.post(
            f"/api/kb/documents/{doc.id}/tags/create",
            json={"name": "course:Operating Systems"},
            headers=headers,
        )
        assert resp.status_code == 200

    links = (
        db_session.query(KbDocumentTag)
        .filter(KbDocumentTag.document_id == doc.id)
        .count()
    )
    course_rows = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .count()
    )
    assert links == 1
    assert course_rows == 1


# ---------------------------------------------------------------------------
# Folder derivation (subjects from top-level vault folders, no tagging)
# ---------------------------------------------------------------------------


def test_derive_creates_courses_from_folders(client: TestClient, db_session: Session):
    """Top-level vault folders become subjects automatically.

    Generic containers (``templates``, ``notes``) are skipped and their child
    segment wins, so ``notes/Networks/`` still derives "Networks". Root-level
    files derive nothing.
    """
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Intro", "Operating Systems/intro.md")
    _make_doc(db_session, uid, src.id, "Scheduling", "Operating Systems/sched.md")
    _make_doc(db_session, uid, src.id, "Limits", "Mathematics/limits.md")
    _make_doc(db_session, uid, src.id, "Root", "root.md")  # no folder → no subject
    _make_doc(db_session, uid, src.id, "Tpl", "templates/x.md")  # ignored container
    _make_doc(db_session, uid, src.id, "Nets", "notes/Networks/dhcp.md")  # container skip → Networks

    resp = client.post("/api/courses/sync-kb", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 3
    assert body["course_tags"] == 0
    assert body["course_folders"] == 3

    courses = db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_folder").all()
    by_title = {c.title: c for c in courses}
    assert set(by_title) == {"Operating Systems", "Mathematics", "Networks"}
    assert by_title["Operating Systems"].kb_document_count == 2
    assert by_title["Operating Systems"].total_assignments == 2
    assert by_title["Operating Systems"].status == "In progress"
    assert by_title["Mathematics"].kb_document_count == 1
    assert by_title["Networks"].kb_document_count == 1
    assert all(c.kb_source_id == src.id and c.kb_folder_path for c in courses)


def test_folder_derivation_is_idempotent(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Note", "Operating Systems/01.md")

    first = client.post("/api/courses/sync-kb", headers=headers).json()
    assert first["created"] == 1

    second = client.post("/api/courses/sync-kb", headers=headers).json()
    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["removed"] == 0

    count = db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_folder").count()
    assert count == 1


def test_folder_derivation_removes_stale_subject(client: TestClient, db_session: Session):
    """A folder-derived course disappears once its folder no longer resolves."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Old", "Deprecated/01.md")

    client.post("/api/courses/sync-kb", headers=headers)
    assert db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_folder").count() == 1

    doc.path_rel = "moved-out.md"  # folder no longer exists
    db_session.commit()

    resp = client.post("/api/courses/sync-kb", headers=headers).json()
    assert resp["removed"] == 1
    assert db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_folder").count() == 0


def test_tag_wins_over_folder_title_collision(client: TestClient, db_session: Session):
    """Explicit tagging beats folder derivation: same title → one course."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "Operating Systems/01.md")
    tag = _make_tag(db_session, uid, "course:Operating Systems")
    _link(db_session, doc, tag)

    client.post("/api/courses/sync-kb", headers=headers)

    by_source = {
        c.source_type: c
        for c in db_session.query(Course).filter(Course.user_id == uid).all()
    }
    assert set(by_source) == {"kb_tag"}  # folder skipped, no duplicate
    assert by_source["kb_tag"].title == "Operating Systems"


def test_late_tag_drops_stale_folder_course(client: TestClient, db_session: Session):
    """A folder subject derived first must be replaced when a ``course:`` tag
    with the same title appears later — no duplicate rows.
    """
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "Operating Systems/01.md")

    # Run 1: only folder derivation → kb_folder subject.
    first = client.post("/api/courses/sync-kb", headers=headers).json()
    assert first["created"] == 1
    assert (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_folder")
        .count()
        == 1
    )

    # User tags the document as a course → explicit source appears later.
    tag = _make_tag(db_session, uid, "course:Operating Systems")
    _link(db_session, doc, tag)

    second = client.post("/api/courses/sync-kb", headers=headers).json()
    assert second["created"] == 1  # the tag course is created this run
    assert second["removed"] == 1  # …and the stale folder row is dropped

    courses = db_session.query(Course).filter(Course.user_id == uid).all()
    assert len(courses) == 1  # no duplicate
    assert courses[0].source_type == "kb_tag"
    assert courses[0].title == "Operating Systems"
    assert courses[0].kb_document_count == 1


def test_collision_match_is_case_insensitive(client: TestClient, db_session: Session):
    """A lowercase ``course:`` tag and a title-cased folder dedupe to one row."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "linux/01.md")
    tag = _make_tag(db_session, uid, "course:linux")  # raw title stays lowercase
    _link(db_session, doc, tag)

    client.post("/api/courses/sync-kb", headers=headers)

    rows = db_session.query(Course).filter(Course.user_id == uid).all()
    assert len(rows) == 1  # folder "Linux" vs tag "linux" → one subject
    assert rows[0].source_type == "kb_tag"


def test_folder_index_frontmatter_drives_course_metadata(client: TestClient, db_session: Session):
    """A folder's ``index.md`` frontmatter sets the subject's description,
    status and color instead of the folder-derivation defaults."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Intro", "Operating Systems/intro.md")
    _make_doc(
        db_session,
        uid,
        src.id,
        "Operating Systems Overview",
        "Operating Systems/index.md",
        frontmatter={
            "description": "Processes, memory and scheduling fundamentals.",
            "status": "completed",
            "color": "#8b5cf6",
        },
    )

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db_session.query(Course)
        .filter(
            Course.user_id == uid,
            Course.source_type == "kb_folder",
            Course.title == "Operating Systems",
        )
        .first()
    )
    assert course is not None
    assert course.description == "Processes, memory and scheduling fundamentals."
    assert course.status == "Completed"  # "completed" normalized to canonical
    assert course.color == "#8b5cf6"

    # The API exposes them too.
    data = client.get(f"/api/courses/{course.id}", headers=headers).json()
    assert data["description"] == "Processes, memory and scheduling fundamentals."
    assert data["color"] == "#8b5cf6"
    assert data["status"] == "Completed"


def test_folder_index_frontmatter_variants_and_invalid_values(client: TestClient, db_session: Session):
    """Alias keys (summary/state/colour) work; junk status/color values are
    ignored in favour of the defaults."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Note", "Mathematics/limits.md")
    _make_doc(
        db_session,
        uid,
        src.id,
        "Math Index",
        "Mathematics/_index.md",
        frontmatter={
            "summary": "Calculus and analysis.",
            "state": "done",
            "colour": "emerald",
        },
    )
    # Invalid values must not leak into the UI.
    _make_doc(db_session, uid, src.id, "Note", "Networks/dhcp.md")
    _make_doc(
        db_session,
        uid,
        src.id,
            "Networks Index",
            "Networks/index.md",
            frontmatter={
                "description": "Networking fundamentals.",
                "status": "banana",
                "color": "not-a-color",
            },
    )

    client.post("/api/courses/sync-kb", headers=headers)
    by_title = {
        c.title: c
        for c in db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_folder").all()
    }
    math = by_title["Mathematics"]
    assert math.description == "Calculus and analysis."
    assert math.status == "Completed"  # "done" normalized
    assert math.color == "emerald"

    nets = by_title["Networks"]
    assert nets.description == "Networking fundamentals."
    assert nets.status == "In progress"  # unknown status → default
    assert nets.color is None  # invalid color ignored


def test_folder_without_index_keeps_defaults(client: TestClient, db_session: Session):
    """No index.md → default status ``In progress``, no description/color."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Processes", "Operating Systems/processes.md")

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db_session.query(Course)
        .filter(
            Course.user_id == uid,
            Course.source_type == "kb_folder",
            Course.title == "Operating Systems",
        )
        .first()
    )
    assert course is not None
    assert course.status == "In progress"
    assert course.description is None
    assert course.color is None


def test_folder_index_metadata_refreshes_on_resync(client: TestClient, db_session: Session):
    """Editing the index.md frontmatter then resyncing updates the subject row
    (no duplicate, no stale description/color)."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Intro", "Operating Systems/intro.md")
    index = _make_doc(
        db_session,
        uid,
        src.id,
        "OS Index",
        "Operating Systems/index.md",
        frontmatter={"description": "First pass.", "status": "in progress", "color": "#111111"},
    )

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_folder", Course.title == "Operating Systems")
        .first()
    )
    assert course.description == "First pass."
    assert course.color == "#111111"

    # Edit the index file's frontmatter and resync.
    index.frontmatter_json = json.dumps({"description": "Second edition.", "status": "completed", "color": "#22c55e"})
    db_session.commit()
    second = client.post("/api/courses/sync-kb", headers=headers).json()
    assert second["created"] == 0
    assert second["removed"] == 0
    db_session.refresh(course)
    assert course.description == "Second edition."
    assert course.status == "Completed"
    assert course.color == "#22c55e"

    # Removing the index file clears the metadata (defaults return).
    index.status = "deleted"
    db_session.commit()
    client.post("/api/courses/sync-kb", headers=headers)
    db_session.refresh(course)
    assert course.description is None
    assert course.status == "In progress"
    assert course.color is None


def test_folder_index_lookup_escapes_like_wildcards(client: TestClient, db_session: Session):
    """``%`` / ``_`` in a folder name are matched literally.

    The sibling ``50XNotes``'s index.md exists first: without escaping, the
    ``50%_Notes`` lookup pattern ``%/50%_Notes/index.md`` would treat ``_`` as
    a wildcard, match ``50XNotes/index.md`` and steal its metadata. The escape
    prevents that, while a real ``50%_Notes/index.md`` still resolves.
    """
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Note", "50XNotes/01.md")
    _make_doc(
        db_session,
        uid,
        src.id,
        "XNotes Index",
        "50XNotes/index.md",
        frontmatter={"description": "Wrong folder.", "color": "#000000"},
    )
    _make_doc(db_session, uid, src.id, "Note", "50%_Notes/01.md")

    client.post("/api/courses/sync-kb", headers=headers)
    by_title = {
        c.title: c
        for c in db_session.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_folder").all()
    }
    pct = by_title["50% Notes"]  # "50%_Notes" title-cased
    assert pct.description is None  # escaped lookup → no false match
    assert pct.color is None
    sibling = by_title["50XNotes"]
    assert sibling.description == "Wrong folder."  # its own metadata untouched

    # The escaped literal lookup still finds a real ``50%_Notes/index.md``.
    _make_doc(
        db_session,
        uid,
        src.id,
        "Percent Index",
        "50%_Notes/index.md",
        frontmatter={"description": "Percent folder.", "status": "in progress", "color": "#0ea5e9"},
    )
    client.post("/api/courses/sync-kb", headers=headers)
    db_session.refresh(pct)
    assert pct.description == "Percent folder."
    assert pct.color == "#0ea5e9"
    assert pct.status == "In progress"


def test_folder_course_detail_resolves_documents(client: TestClient, db_session: Session):
    """A folder-derived subject's detail page returns exactly its folder docs."""
    token = _signup(client)
    uid = _uid(db_session)
    headers = {AUTH: f"Bearer {token}"}

    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id, "Processes", "Operating Systems/processes.md")
    _make_doc(db_session, uid, src.id, "Memory", "Operating Systems/memory.md")
    _make_doc(db_session, uid, src.id, "Other", "Mathematics/limits.md")

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db_session.query(Course)
        .filter(
            Course.user_id == uid,
            Course.source_type == "kb_folder",
            Course.title == "Operating Systems",
        )
        .first()
    )
    assert course is not None

    data = client.get(f"/api/courses/{course.id}/content", headers=headers).json()
    titles = {d["title"] for d in data["second_brain"]["documents"]}
    assert titles == {"Processes", "Memory"}
    assert data["second_brain"]["document_count"] == 2
