"""Idea 38 — mind-map tests.

Tree building from outline, concept attachment, markdown/OPML export, heading
fallback.
"""
from __future__ import annotations

from app.models import KbConcept, KbDocument, KbEdge
from app.services.kb.graph import add_edge
from app.services.kb.mindmap import (
    build_tree,
    export_markdown,
    export_opml,
)


def _signup(client, uname="mm-user", email="mm@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mm", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _upload(client, token, name="note.md", content=None, mime="test/markdown"):
    content = content or b"# Intro\n\nText.\n\n## Part One\n\nMore text.\n\n### Sub A\n\nDeeper."
    resp = client.post(
        "/api/kb/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (name, content, mime)},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["document"]["id"]


class TestMindmapEndpoint:
    def test_tree_from_outline(self, client):
        token = _signup(client)
        doc_id = _upload(client, token, "note.md")
        r = client.get(
            f"/api/kb/documents/{doc_id}/mindmap",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        tree = r.json()
        assert tree["label"] == "note"
        labels = [n["label"] for n in _flatten(tree["children"])]
        assert "Intro" in labels
        assert "Part One" in labels
        assert "Sub A" in labels

    def test_markdown_export(self, client):
        token = _signup(client)
        doc_id = _upload(client, token, "note.md")
        r = client.get(
            f"/api/kb/documents/{doc_id}/mindmap?format=markdown",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/markdown")
        assert "# " in r.text

    def test_opml_export(self, client):
        token = _signup(client)
        doc_id = _upload(client, token, "note.md")
        r = client.get(
            f"/api/kb/documents/{doc_id}/mindmap?format=opml",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "<opml" in r.text
        assert "<outline" in r.text

    def test_heading_fallback_for_txt(self, client):
        token = _signup(client)
        # A .txt doc has no markdown outline — the tree must still build.
        doc_id = _upload(
            client, token, "plain.txt",
            content=b"Section One\n\nSection Two\n\nMore body text here.",
            mime="text/plain",
        )
        r = client.get(
            f"/api/kb/documents/{doc_id}/mindmap",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "children" in r.json()

    def test_per_user_isolation(self, client):
        token_a = _signup(client, "mm-a", "mma@test.com")
        token_b = _signup(client, "mm-b", "mmb@test.com")
        doc_id = _upload(client, token_a, "note.md")
        r = client.get(
            f"/api/kb/documents/{doc_id}/mindmap",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r.status_code == 404


class TestMindmapService:
    def test_concept_attachment(self, db_session, client):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_id = _upload(client, token, "note.md")
        concept = KbConcept(user_id=user_id, canonical_name="text")
        db_session.add(concept)
        db_session.commit()
        add_edge(db_session, user_id, doc_id, target_concept_id=concept.id,
                 relation="MENTIONS", target_type="concept", weight=0.9)
        db_session.commit()

        doc = db_session.query(KbDocument).get(doc_id)
        tree = build_tree(db_session, user_id, doc)
        all_nodes = [tree] + _flatten(tree["children"])
        assert any("text" in (n["concepts"] or []) for n in all_nodes)


def _flatten(nodes):
    out = []
    for n in nodes:
        out.append(n)
        out.extend(_flatten(n["children"]))
    return out
