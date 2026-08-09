"""Idea 37 — concept-linking UI tests.

Manual edge create/delete, validation (self-edge, bad target), auto-edge
removal, links panel, per-user isolation.
"""
from __future__ import annotations

from app.models import KbConcept, KbEdge


def _signup(client, uname="edge-user", email="edge@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Edge", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _upload(client, token, name="note.md"):
    # Unique content per filename so the content-hash dedupe never collapses
    # two uploads into one document.
    content = (f"# Title\n\n{name} " + "word " * 60).encode()
    resp = client.post(
        "/api/kb/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (name, content, "test.md")},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["document"]["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class TestManualEdges:
    def test_create_and_list_links(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_a = _upload(client, token, "a.md")
        doc_b = _upload(client, token, "b.md")

        r = client.post(
            "/api/kb/edges",
            json={"source_document_id": doc_a, "target_id": doc_b,
                  "relation": "RELATED", "target_type": "document"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        edge_id = r.json()["id"]

        edge = db_session.query(KbEdge).get(edge_id)
        assert edge.provenance == "manual" and edge.weight == 1.0

        links = client.get(
            f"/api/kb/documents/{doc_a}/links",
            headers=_auth(token),
        ).json()
        assert len(links["related"]) == 1
        assert links["related"][0]["relation"] == "RELATED"

    def test_link_to_concept(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc = _upload(client, token)
        concept = KbConcept(user_id=user_id, canonical_name="thermodynamics")
        db_session.add(concept)
        db_session.commit()

        r = client.post(
            "/api/kb/edges",
            json={"source_document_id": doc, "target_id": concept.id,
                  "relation": "MENTIONS", "target_type": "concept"},
            headers=_auth(token),
        )
        assert r.status_code == 200, r.text
        links = client.get(
            f"/api/kb/documents/{doc}/links", headers=_auth(token)
        ).json()
        assert links["concepts"][0]["name"] == "thermodynamics"

    def test_self_edge_rejected(self, client):
        token = _signup(client)
        doc = _upload(client, token)
        r = client.post(
            "/api/kb/edges",
            json={"source_document_id": doc, "target_id": doc,
                  "relation": "RELATED", "target_type": "document"},
            headers=_auth(token),
        )
        assert r.status_code == 400

    def test_bad_target_404(self, client):
        token = _signup(client)
        doc = _upload(client, token)
        r = client.post(
            "/api/kb/edges",
            json={"source_document_id": doc, "target_id": 99999,
                  "relation": "RELATED", "target_type": "document"},
            headers=_auth(token),
        )
        assert r.status_code == 404

    def test_delete_edge(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        doc_a = _upload(client, token, "a.md")
        doc_b = _upload(client, token, "b.md")
        edge = KbEdge(user_id=user_id, source_document_id=doc_a,
                      target_document_id=doc_b, relation="RELATED",
                      provenance="auto")
        db_session.add(edge)
        db_session.commit()

        r = client.delete(f"/api/kb/edges/{edge.id}", headers=_auth(token))
        assert r.status_code == 200
        assert db_session.query(KbEdge).get(edge.id) is None

    def test_per_user_isolation(self, client, db_session):
        token_a = _signup(client, "edge-a", "edgea@test.com")
        token_b = _signup(client, "edge-b", "edgeb@test.com")
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token_a)["user_id"]
        doc_a = _upload(client, token_a, "a.md")
        doc_b = _upload(client, token_a, "b.md")
        edge = KbEdge(user_id=user_id, source_document_id=doc_a,
                      target_document_id=doc_b, relation="RELATED")
        db_session.add(edge)
        db_session.commit()

        # User B cannot delete user A's edge.
        r = client.delete(f"/api/kb/edges/{edge.id}", headers=_auth(token_b))
        assert r.status_code == 404

        # User B cannot read user A's links either.
        r2 = client.get(f"/api/kb/documents/{doc_a}/links", headers=_auth(token_b))
        assert r2.status_code == 404
