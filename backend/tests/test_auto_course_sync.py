"""Auto course-sync job tests (Second Brain dynamic courses, Phase 9)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Course, KbDocument, KbDocumentTag, KbSource, KbTag, User
from app.services.kb.auto_course_sync import run
from app.services.kb.automation import JOBS, _load_features

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "course-auto", email: str = "courseauto@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Course Auto",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "courseauto@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_source(db: Session, user_id: int, name: str = "Notes") -> KbSource:
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


def _make_doc(db: Session, user_id: int, source_id: int, title: str, path: str) -> KbDocument:
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


def _make_tag(db: Session, user_id: int, name: str) -> KbTag:
    tag = KbTag(user_id=user_id, name=name, kind="manual")
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def _link(db: Session, doc: KbDocument, tag: KbTag) -> None:
    db.add(KbDocumentTag(user_id=doc.user_id, document_id=doc.id, tag_id=tag.id, provenance="manual"))
    db.commit()


def test_job_is_registered_and_gated():
    _load_features()
    assert "auto_course_sync" in JOBS
    spec = JOBS["auto_course_sync"]
    assert spec.toggle == "KB_AUTO_COURSE_SYNC_ENABLED"
    # Safe/idempotent job — on by default.
    assert getattr(settings, spec.toggle) is True


def test_job_derives_courses(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "01.md")
    tag = _make_tag(db_session, uid, "course:Operating Systems")
    _link(db_session, doc, tag)

    summary = run(db_session, uid)
    assert summary["processed"] == 1
    assert summary["created"] == 1

    courses = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .all()
    )
    assert len(courses) == 1
    assert courses[0].title == "Operating Systems"
    assert courses[0].kb_document_count == 1


def test_job_is_idempotent(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "02.md")
    tag = _make_tag(db_session, uid, "course:OS")
    _link(db_session, doc, tag)

    first = run(db_session, uid)
    second = run(db_session, uid)
    assert first["created"] == 1
    assert second["created"] == 0
    assert second["updated"] == 1
    assert (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .count()
        == 1
    )


def test_job_ignores_non_course_tags(client: TestClient, db_session: Session):
    token = _signup(client)
    uid = _uid(db_session)
    src = _make_source(db_session, uid)
    doc = _make_doc(db_session, uid, src.id, "Note", "01.md")
    tag = _make_tag(db_session, uid, "python")
    _link(db_session, doc, tag)

    summary = run(db_session, uid)
    assert summary["processed"] == 0
    assert summary["created"] == 0
    assert (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_tag")
        .count()
        == 0
    )
