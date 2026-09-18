"""Tests for the Subject Details content pipeline:

- ``GET /api/courses/{id}/content`` — Second Brain documents, nested topics
  with their documents, related concepts, subject-scoped knowledge graph,
  and Classroom assignment payload.
- ``GET /api/courses/{id}/gaps`` — topic coverage gaps + scoped concept gaps.
- ``POST /api/courses/{id}/resync`` — idempotent KB derivation + classroom
  merge, returns refreshed content.
"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Course,
    CourseGapAnalysis,
    KbConcept,
    KbDocument,
    KbDocumentTag,
    KbEdge,
    KbSource,
    KbTag,
    User,
)

AUTH = "Authorization"


def _signup(client: TestClient, uname: str = "sb-content", email: str = "sb-content@test.com") -> str:
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "SB Content",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db: Session, email: str = "sb-content@test.com") -> int:
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _make_source(db: Session, user_id: int, name: str = "Notes") -> KbSource:
    src = KbSource(user_id=user_id, name=name, source_type="local_dir", root_path=f"/tmp/{name}")
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
    outline: list[dict] | None = None,
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
    if outline is not None:
        doc.outline_json = json.dumps(outline)
    doc.metadata_json = json.dumps({"tags": ["course:Operating Systems"], "wikilinks": ["Other"]})
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


def _make_concept(db: Session, user_id: int, name: str) -> KbConcept:
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


def _build_course(client: TestClient, db: Session) -> tuple[int, dict[str, str]]:
    """Seed a kb_tag course with 2 docs (shared + unique headings) and a concept."""
    token = _signup(client)
    uid = _uid(db)
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db, uid)

    doc_a = _make_doc(
        db, uid, src.id, "Processes", "os/processes.md",
        outline=[
            {"level": 1, "text": "Scheduling", "char_start": 0},
            {"level": 2, "text": "Round Robin", "char_start": 10},
            {"level": 1, "text": "Memory", "char_start": 40},
        ],
    )
    doc_b = _make_doc(
        db, uid, src.id, "Threads", "os/threads.md",
        outline=[
            {"level": 1, "text": "Scheduling", "char_start": 0},
            {"level": 2, "text": "Priority Queues", "char_start": 8},
        ],
    )
    # Thin topic: appears in only 1 of 3 outlined docs → below the 50% bar.
    doc_c = _make_doc(
        db, uid, src.id, "Virtualization", "os/virt.md",
        outline=[{"level": 1, "text": "Virtualization", "char_start": 0}],
    )
    doc_flat = _make_doc(db, uid, src.id, "Cheat Sheet", "os/cheat.md")  # no outline

    tag = _make_tag(db, uid, "course:Operating Systems")
    _link(db, doc_a, tag)
    _link(db, doc_b, tag)
    _link(db, doc_c, tag)
    _link(db, doc_flat, tag)

    concept = _make_concept(db, uid, "scheduling")
    _mention(db, uid, doc_a.id, concept.id)

    resp = client.post("/api/courses/sync-kb", headers=headers)
    assert resp.status_code == 200
    course = db.query(Course).filter(Course.user_id == uid, Course.source_type == "kb_tag").first()
    assert course is not None
    return course.id, headers


def test_content_returns_documents_with_outline_and_metadata(client: TestClient, db_session: Session):
    course_id, headers = _build_course(client, db_session)
    resp = client.get(f"/api/courses/{course_id}/content", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["course"]["title"] == "Operating Systems"
    sb = data["second_brain"]
    assert sb["document_count"] == 4
    assert {d["title"] for d in sb["documents"]} == {"Processes", "Threads", "Virtualization", "Cheat Sheet"}
    first = next(d for d in sb["documents"] if d["title"] == "Processes")
    # Outline + metadata survive the JSON-column round trip (regression: the
    # old payload builder read doc.outline/doc.metadata and crashed).
    assert first["outline"] and first["outline"][0]["text"] == "Scheduling"
    assert first["tags"] == ["course:Operating Systems"]
    assert first["wikilinks"] == ["Other"]


def _build_folder_course(
    client: TestClient, db: Session, email: str = "sb-folder-topics@test.com"
) -> tuple[int, dict[str, str]]:
    """Seed a kb_folder course with nested folder docs (no tagging needed)."""
    token = _signup(client, uname="sb-foldertopics", email=email)
    uid = _uid(db, email=email)
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db, uid)

    _make_doc(db, uid, src.id, "Intro", "Operating Systems/intro.md",
              outline=[{"level": 1, "text": "Overview", "char_start": 0}])
    # Nested folders → topics under the subject.
    _make_doc(db, uid, src.id, "Paging", "Operating Systems/Memory/paging.md",
              outline=[{"level": 1, "text": "Page Tables", "char_start": 0}])
    _make_doc(db, uid, src.id, "Heap", "Operating Systems/Memory/heap.md")  # no outline, in folder
    _make_doc(db, uid, src.id, "RR", "Operating Systems/Scheduling/rr.md",
              outline=[{"level": 1, "text": "Round Robin", "char_start": 0}])
    # Deep nesting: Memory/Virtual Memory/01.md
    _make_doc(db, uid, src.id, "VM", "Operating Systems/Memory/Virtual Memory/vm.md",
              outline=[{"level": 1, "text": "TLB", "char_start": 0}])

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_folder", Course.title == "Operating Systems")
        .first()
    )
    assert course is not None
    return course.id, headers


def test_folder_subject_nested_folders_become_topics(client: TestClient, db_session: Session):
    """Folder-derived subjects reflect their vault structure: nested folders
    become topics/subtopics, each carrying the documents inside them."""
    course_id, headers = _build_folder_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/content", headers=headers).json()
    topics = data["second_brain"]["topics"]

    by_name = {t["name"]: t for t in topics}
    # Root-level doc keeps its heading topic.
    assert "Overview" in by_name
    # Nested folders become topics.
    assert "Memory" in by_name
    assert "Scheduling" in by_name

    memory = by_name["Memory"]
    assert memory["level"] == 1
    # Folder-derived topics are marked so the UI can show a folder breadcrumb.
    assert memory["origin"] == "folder"
    # The folder topic carries every doc under it (incl. no-outline heap.md,
    # now organized under its folder instead of unorganized, and the deeply
    # nested VM doc, which also passes through the Memory level).
    assert {d["title"] for d in memory["documents"]} == {"Paging", "Heap", "VM"}
    child_names = {c["name"] for c in memory["children"]}
    assert "Page Tables" in child_names
    # Deep nesting: Virtual Memory is a subtopic of Memory, TLB under it.
    vm = next(c for c in memory["children"] if c["name"] == "Virtual Memory")
    assert vm["level"] == 2
    assert vm["origin"] == "folder"
    assert {c["name"] for c in vm["children"]} == {"TLB"}
    assert {d["title"] for d in vm["documents"]} == {"VM"}

    # Root heading topics (not folders) carry the heading origin.
    assert by_name["Overview"]["origin"] == "heading"

    scheduling = by_name["Scheduling"]
    assert {d["title"] for d in scheduling["documents"]} == {"RR"}
    assert {c["name"] for c in scheduling["children"]} == {"Round Robin"}

    # All 5 docs are now organized (folders + headings) — nothing unorganized.
    assert data["second_brain"]["unorganized_documents"] == []


def test_folder_subject_root_docs_without_folders_remain_unorganized(client: TestClient, db_session: Session):
    """Docs directly in the subject root without headings stay unorganized;
    folder-nested docs without headings do NOT."""
    token = _signup(client, uname="sb-folderflat", email="sb-folderflat@test.com")
    uid = _uid(db_session, email="sb-folderflat@test.com")
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db_session, uid)
    _make_doc(db_session, uid, src.id,    "Flat Root", "Operating Systems/flat.md", outline=None)  # no outline, at root
    _make_doc(db_session, uid, src.id, "Nested Flat", "Operating Systems/Memory/note.md", outline=None)  # no outline, in folder

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_folder", Course.title == "Operating Systems")
        .first()
    )
    data = client.get(f"/api/courses/{course.id}/content", headers=headers).json()

    unorganized = {d["title"] for d in data["second_brain"]["unorganized_documents"]}
    assert unorganized == {"Flat Root"}  # root + no headings → unorganized
    topics = data["second_brain"]["topics"]
    memory = next(t for t in topics if t["name"] == "Memory")
    assert {d["title"] for d in memory["documents"]} == {"Nested Flat"}


def test_folder_subject_gap_topics_include_folder_topics(client: TestClient, db_session: Session):
    """Folder-derived subjects surface their vault folders as gap-analysis
    knowledge targets: the topic-coverage list AND the actionable engine treat
    nested folders as topics (mirroring the topic tree), with coverage equal to
    the share of subject documents inside each folder."""
    course_id, headers = _build_folder_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()

    assert data["cached"] is False
    assert data["document_count"] == 5

    # Folder topics are coverage targets, with the documents inside them counted.
    by_name = {g["normalized"]: g for g in data["topics"]}
    memory = by_name["memory"]
    assert memory["topic"] == "Memory"
    assert memory["documents"] == 3  # paging.md + heap.md + vm.md
    assert memory["coverage"] == 0.6  # 3 of 5 effective-outlined docs
    assert memory["is_gap"] is False

    # Thin folder topics are flagged as gaps — they surface as targets.
    assert by_name["scheduling"]["is_gap"] is True
    assert by_name["scheduling"]["documents"] == 1
    assert by_name["virtual memory"]["is_gap"] is True
    assert by_name["virtual memory"]["documents"] == 1
    assert "overview" in by_name  # root heading still listed

    # The actionable engine also sees folder topics as knowledge targets with
    # document-presence evidence (Memory has 3 docs → never "Not Found").
    engine_names = {g["name"] for g in data["gaps"]}
    engine_names |= {s["name"] for s in data["strengths"]}
    engine_names |= {p["name"] for ph in data["path"] for p in ph["items"]}
    assert "Memory" in engine_names
    # The fixture has no MENTIONS edges, so the folder topic's only evidence is
    # the doc_hints seeding (documents=1, heading_docs=3) → classified Weak,
    # never "Not Found". This pins the folder-topic→evidence behaviour.
    memory_gap = next((g for g in data["gaps"] if g["name"] == "Memory"), None)
    assert memory_gap is not None
    assert memory_gap["level"] == "Weak"


def test_folder_topic_wins_over_same_named_root_heading(client: TestClient, db_session: Session):
    """A topic that exists BOTH as a root heading and as a vault folder is
    treated as a folder topic (origin 'folder') — the folder reading wins, so
    the UI shows the folder breadcrumb on it. Headings under it stay headings.
    """
    token = _signup(client, uname="sb-folder-merge", email="sb-folder-merge@test.com")
    uid = _uid(db_session, email="sb-folder-merge@test.com")
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db_session, uid)
    # Root doc: heading "Memory" (no folder).
    _make_doc(db_session, uid, src.id, "Root", "Operating Systems/root.md",
              outline=[{"level": 1, "text": "Memory", "char_start": 0}])
    # Nested doc: folder "Memory" (level 1) with heading "Paging".
    _make_doc(db_session, uid, src.id, "Paging", "Operating Systems/Memory/paging.md",
              outline=[{"level": 1, "text": "Paging", "char_start": 0}])

    client.post("/api/courses/sync-kb", headers=headers)
    course = (
        db_session.query(Course)
        .filter(Course.user_id == uid, Course.source_type == "kb_folder", Course.title == "Operating Systems")
        .first()
    )
    data = client.get(f"/api/courses/{course.id}/content", headers=headers).json()
    topics = {t["name"]: t for t in data["second_brain"]["topics"]}

    # The merged node (heading + folder) is a folder topic.
    assert topics["Memory"]["origin"] == "folder"
    assert topics["Memory"]["level"] == 1
    # Both documents land under it; the heading child stays a heading.
    assert {d["title"] for d in topics["Memory"]["documents"]} == {"Root", "Paging"}
    paging = next(c for c in topics["Memory"]["children"] if c["name"] == "Paging")
    assert paging["origin"] == "heading"


def test_folder_segments_edge_cases(client: TestClient, db_session: Session):
    """Paths equal to the root, trailing slashes, and backslash separators are
    handled without deriving bogus topics."""
    from app.services.course_content import _folder_segments

    assert _folder_segments("Operating Systems", "Operating Systems") == []
    assert _folder_segments("Operating Systems/intro.md", "Operating Systems") == []
    assert _folder_segments("Operating Systems/", "Operating Systems") == []
    assert _folder_segments("Operating Systems/Memory/01.md", "Operating Systems") == ["Memory"]
    assert _folder_segments("Operating Systems/notes/Memory/01.md", "Operating Systems") == ["Memory"]
    # A path under a *different* root is not this subject's document.
    assert _folder_segments("Networks/01.md", "Operating Systems") == []
    # None / empty paths never crash.
    assert _folder_segments(None, "Operating Systems") == []
    assert _folder_segments("", "Operating Systems") == []


def test_tag_course_includes_docs_from_matching_folder(client: TestClient, db_session: Session):
    """A course derived from a ``course:*`` tag ALSO shows documents that live
    under a vault folder whose name matches the course — nested domain
    subfolders included — because the tag and the folder are the same subject.
    The folder's subfolders surface as folder topics, and documents under
    unrelated folders stay out."""
    token = _signup(client, uname="sb-tagfolder", email="sb-tagfolder@test.com")
    uid = _uid(db_session, email="sb-tagfolder@test.com")
    headers = {AUTH: f"Bearer {token}"}
    src = _make_source(db_session, uid)

    tagged = _make_doc(
        db_session, uid, src.id, "Tagged Note", "Cybersecurity/root.md",
        outline=[{"level": 1, "text": "Intro", "char_start": 0}],
    )
    # Untagged folder docs — including nested domain subfolders — must appear.
    _make_doc(db_session, uid, src.id, "Firewall", "Cybersecurity/Network Security/firewall.md")
    _make_doc(db_session, uid, src.id, "Hashing", "Cybersecurity/cryptography/hashes.md")
    # A document under an unrelated folder must NOT leak into the course.
    _make_doc(db_session, uid, src.id, "Routing", "Networks/routing.md")

    tag = _make_tag(db_session, uid, "course:Cybersecurity")
    _link(db_session, tagged, tag)

    client.post("/api/courses/sync-kb", headers=headers)
    # The tag wins over the folder course (title collision) — one row only.
    cyber = db_session.query(Course).filter(Course.user_id == uid, Course.title == "Cybersecurity").all()
    assert len(cyber) == 1
    assert cyber[0].source_type == "kb_tag"

    data = client.get(f"/api/courses/{cyber[0].id}/content", headers=headers).json()
    titles = {d["title"] for d in data["second_brain"]["documents"]}
    assert titles == {"Tagged Note", "Firewall", "Hashing"}
    assert "Routing" not in titles

    # The matching folder's nested domain folders become topics.
    topics = {t["name"]: t for t in data["second_brain"]["topics"]}
    assert topics["Network Security"]["origin"] == "folder"
    assert {d["title"] for d in topics["Network Security"]["documents"]} == {"Firewall"}
    assert "Cryptography" in topics

    # Folder-nested docs without headings are organized — not unorganized.
    unorganized = {d["title"] for d in data["second_brain"]["unorganized_documents"]}
    assert "Firewall" not in unorganized
    assert "Hashing" not in unorganized


def test_content_topics_are_nested_and_carry_their_documents(client: TestClient, db_session: Session):
    course_id, headers = _build_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/content", headers=headers).json()
    topics = data["second_brain"]["topics"]

    names = {t["name"]: t for t in topics}
    assert "Scheduling" in names
    assert "Memory" in names

    scheduling = names["Scheduling"]
    # Heading-built topics carry the heading origin (no folder breadcrumb).
    assert scheduling["origin"] == "heading"
    # Merged across both documents (deduped per topic).
    assert {d["title"] for d in scheduling["documents"]} == {"Processes", "Threads"}
    subtopic_names = {c["name"] for c in scheduling["children"]}
    assert "Round Robin" in subtopic_names
    assert "Priority Queues" in subtopic_names

    # Documents without outlines are excluded from the tree but listed.
    assert {d["title"] for d in data["second_brain"]["unorganized_documents"]} == {"Cheat Sheet"}


def test_content_related_concepts_from_mentions(client: TestClient, db_session: Session):
    course_id, headers = _build_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/content", headers=headers).json()
    concepts = data["second_brain"]["concepts"]
    assert any(c["name"] == "scheduling" for c in concepts)
    scheduling = next(c for c in concepts if c["name"] == "scheduling")
    assert scheduling["mentions"] == 1
    assert scheduling["document_count"] == 1
    assert scheduling["sources"][0]["title"] == "Processes"


def test_content_graph_is_scoped_to_subject_documents(client: TestClient, db_session: Session):
    course_id, headers = _build_course(client, db_session)
    data = client.get(f"/api/courses/{course_id}/content", headers=headers).json()
    graph = data["second_brain"]["graph"]

    doc_ids = {d["id"] for d in data["second_brain"]["documents"]}
    node_ids = {n["id"] for n in graph["nodes"]}
    # Only subject documents appear as doc nodes.
    for nid in node_ids:
        if nid.startswith("doc:"):
            assert int(nid.split(":")[1]) in doc_ids
    assert any(n["kind"] == "concept" and n["label"] == "scheduling" for n in graph["nodes"])
    # Every edge touches a returned node.
    node_set = set(node_ids)
    for e in graph["edges"]:
        assert e["source"] in node_set and e["target"] in node_set


def test_gaps_report_topic_and_concept_gaps(client: TestClient, db_session: Session):
    course_id, headers = _build_course(client, db_session)
    resp = client.get(f"/api/courses/{course_id}/gaps", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # First call computes and stores the analysis (not cached).
    assert data.get("cached") is False
    assert data.get("analyzed_at")

    assert data["document_count"] == 4
    # "Scheduling" appears in 2 of 3 outlined docs → NOT a gap; the thin
    # "Virtualization" heading (1 of 3) IS a gap.
    by_name = {g["normalized"]: g for g in data["topics"]}
    assert by_name["scheduling"]["is_gap"] is False
    assert by_name["virtualization"]["is_gap"] is True

    assert any(c["concept"] == "scheduling" for c in data["concepts"])
    assert data["classroom"]["total"] == 0

    # ── New actionable gap engine payload ──
    assert data["domain"] == "Operating Systems"  # course title → curated domain
    assert isinstance(data["summary"], dict) and data["summary"]["text"]
    assert isinstance(data["strengths"], list)
    assert isinstance(data["gaps"], list)
    assert data["path"] and data["path"][0]["items"]
    assert data["next"] is not None
    assert data["coverage"]["total"] > 0
    # The subject's mentioned concept (1 doc, 1 mention) is Weak — evidence,
    # not knowledge.
    scheduling = next(g for g in data["gaps"] if g["name"] == "Scheduling")
    assert scheduling["level"] == "Weak"
    assert scheduling["sources"][0]["title"] == "Processes"
    # Every gap is actionable: why + prerequisites + learn + practice.
    for g in data["gaps"]:
        assert g["why"]
        assert isinstance(g["prerequisites"], list)
        assert isinstance(g["learn"], list) and g["learn"]
        assert isinstance(g["practice"], list) and g["practice"]


def test_gaps_on_subject_with_no_documents_returns_no_global_concept_gaps(client: TestClient, db_session: Session):
    """A subject with no KB docs must not score the user's whole concept vault.

    Regression: ``course_gaps`` used to fall back to ``concept_ids or None``,
    which made ``concept_gaps`` score EVERY vault concept (an N+1 query per
    concept) — the endpoint timed out on manual/empty subjects, and whole-vault
    gaps are not the subject's gaps anyway.
    """
    token = _signup(client, uname="sb-gapempty", email="sb-gapempty@test.com")
    uid = _uid(db_session, email="sb-gapempty@test.com")
    headers = {AUTH: f"Bearer {token}"}

    course = Course(
        title="Manual Subject", source_type="manual", user_id=uid, status="In progress"
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    # A concept exists in the vault but is NOT mentioned by any subject doc.
    _make_concept(db_session, uid, "unrelated-concept")

    resp = client.get(f"/api/courses/{course.id}/gaps", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_count"] == 0
    assert data["concepts"] == []  # never leaks global vault concepts
    # The actionable engine degrades gracefully to an empty analysis.
    assert data["gaps"] == []
    assert data["strengths"] == []
    assert data["coverage"]["total"] == 0


def test_gaps_are_saved_and_reused_until_explicit_reanalyze(client: TestClient, db_session: Session):
    """The analysis is computed once, saved, and reused on later GETs;
    only the explicit analyze endpoint recomputes."""
    course_id, headers = _build_course(client, db_session)

    first = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert first["cached"] is False
    assert first["document_count"] == 4
    assert first["analyzed_at"]

    # The stored row exists.
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.course_id == course_id)
        .count()
        == 1
    )

    # A later GET returns the SAME saved payload — cached, not recomputed.
    second = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert second["cached"] is True
    assert second["document_count"] == first["document_count"]
    assert second["analyzed_at"] == first["analyzed_at"]
    assert second["summary"]["text"] == first["summary"]["text"]

    # The explicit analyze endpoint recomputes and refreshes the saved copy.
    third = client.post(f"/api/courses/{course_id}/gaps/analyze", headers=headers).json()
    assert third["cached"] is False
    # Fresh timestamp: the re-analysis happened strictly after the cached copy.
    assert third["analyzed_at"] != second["analyzed_at"]
    assert third["document_count"] == 4

    # After analyze, GET now serves the refreshed copy as cached.
    fourth = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert fourth["cached"] is True
    assert fourth["analyzed_at"] == third["analyzed_at"]
    # Exactly one saved row per course (upsert, never duplicate).
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.course_id == course_id)
        .count()
        == 1
    )


def test_gaps_cache_invalidated_by_resync(client: TestClient, db_session: Session):
    """A resync drops the saved analysis so the next gaps request recomputes."""
    course_id, headers = _build_course(client, db_session)

    first = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert first["cached"] is False

    # Resync invalidates the cache (data may have changed).
    resp = client.post(f"/api/courses/{course_id}/resync", headers=headers)
    assert resp.status_code == 200
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.course_id == course_id)
        .count()
        == 0
    )

    # Next GET recomputes (cached: false again, fresh timestamp).
    after = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert after["cached"] is False
    assert after["document_count"] == 4


def test_gaps_saved_per_course_and_per_user(client: TestClient, db_session: Session):
    """Each course (and user) keeps its own saved analysis."""
    course_id, headers = _build_course(client, db_session)
    client.get(f"/api/courses/{course_id}/gaps", headers=headers)

    # A second course for the same user gets its own row.
    token2 = _signup(client, uname="sb-content2", email="sb-content2@test.com")
    uid2 = _uid(db_session, email="sb-content2@test.com")
    headers2 = {AUTH: f"Bearer {token2}"}
    src2 = _make_source(db_session, uid2)
    doc2 = _make_doc(db_session, uid2, src2.id, "Note", "math/01.md")
    tag2 = _make_tag(db_session, uid2, "course:Math")
    _link(db_session, doc2, tag2)
    client.post("/api/courses/sync-kb", headers=headers2)
    course2 = (
        db_session.query(Course)
        .filter(Course.user_id == uid2, Course.source_type == "kb_tag")
        .first()
    )
    client.get(f"/api/courses/{course2.id}/gaps", headers=headers2)

    rows = db_session.query(CourseGapAnalysis).all()
    # One row per (user, course): user1+course, user2+course2.
    assert len(rows) == 2
    keys = {(r.user_id, r.course_id) for r in rows}
    assert (db_session.query(User).filter(User.email == "sb-content@test.com").first().id, course_id) in keys
    assert (uid2, course2.id) in keys

    # Cached for user 1's course only.
    cached = client.get(f"/api/courses/{course_id}/gaps", headers=headers).json()
    assert cached["cached"] is True

    # User 2 has no access to user 1's course.
    resp = client.get(f"/api/courses/{course_id}/gaps", headers=headers2)
    assert resp.status_code == 404


def test_gaps_cache_cleaned_up_when_course_deleted(client: TestClient, db_session: Session):
    """Deleting a course (or having it removed by a sync) also removes its
    saved analysis — no orphaned rows."""
    course_id, headers = _build_course(client, db_session)
    client.get(f"/api/courses/{course_id}/gaps", headers=headers)
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.course_id == course_id)
        .count()
        == 1
    )

    # Manual delete clears the saved analysis.
    resp = client.delete(f"/api/courses/{course_id}", headers=headers)
    assert resp.status_code == 200
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.course_id == course_id)
        .count()
        == 0
    )

    # Stale-tag removal also clears it: fresh user, analyze, then remove the
    # tag so the next sync drops the course.
    token2 = _signup(client, uname="sb-del2", email="sb-del2@test.com")
    uid2 = _uid(db_session, email="sb-del2@test.com")
    headers2 = {AUTH: f"Bearer {token2}"}
    src2 = _make_source(db_session, uid2)
    doc2 = _make_doc(db_session, uid2, src2.id, "Note", "os/01.md")
    tag2 = _make_tag(db_session, uid2, "course:Networks")
    _link(db_session, doc2, tag2)
    client.post("/api/courses/sync-kb", headers=headers2)
    course2 = (
        db_session.query(Course)
        .filter(Course.user_id == uid2, Course.source_type == "kb_tag")
        .first()
    )
    client.get(f"/api/courses/{course2.id}/gaps", headers=headers2)
    db_session.query(KbTag).filter(KbTag.id == tag2.id).delete()
    db_session.commit()
    client.post("/api/courses/sync-kb", headers=headers2)
    assert (
        db_session.query(CourseGapAnalysis)
        .filter(CourseGapAnalysis.course_id == course2.id)
        .count()
        == 0
    )


def test_resync_is_idempotent_and_returns_content(client: TestClient, db_session: Session):
    course_id, headers = _build_course(client, db_session)
    before = db_session.query(Course).filter(Course.source_type == "kb_tag").count()

    for _ in range(2):
        resp = client.post(f"/api/courses/{course_id}/resync", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["kb"]["created"] == 0
        assert body["content"] is not None
        assert len(body["content"]["second_brain"]["documents"]) == 4

    after = db_session.query(Course).filter(Course.source_type == "kb_tag").count()
    assert after == before  # no duplicates


def test_resync_classroom_course_merges_by_google_id(client: TestClient, db_session: Session):
    token = _signup(client, uname="sb-class", email="sb-class@test.com")
    uid = _uid(db_session, email="sb-class@test.com")
    headers = {AUTH: f"Bearer {token}"}

    course = Course(
        title="QRA", source_type="classroom", google_id="gc-qra",
        classroom_url="https://classroom.google.com/c/1", user_id=uid, status="In progress",
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    resp = client.post(f"/api/courses/{course.id}/resync", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    # Not connected in the test env → labelled mock, nothing persisted.
    assert body["classroom"] is not None
    assert body["content"]["classroom"]["linked"] is True
    count = db_session.query(Course).filter(Course.user_id == uid).count()
    assert count == 1  # idempotent — the resync did not create a duplicate row
