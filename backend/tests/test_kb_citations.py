"""Idea 25 — citation-aware result cards tests.

Verifies snippet markers, page/heading resolution, open-in-vault path
building, and the PDF vs markdown variants of the citation resolver.
"""
from __future__ import annotations

from app.services.kb import citations


def _signup(client, uname="cit-user", email="cit@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Cit", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _scan(client, token, root, texts):
    for i, text in enumerate(texts):
        (root / f"d{i}.md").write_text(text)
    r = client.post(
        "/api/kb/sources",
        json={"name": "V", "root_path": str(root)},
        headers={"Authorization": f"Bearer {token}"},
    )
    src = r.json()
    client.post(f"/api/kb/sources/{src['id']}/scan",
                headers={"Authorization": f"Bearer {token}"})


class TestCitationResolver:
    def test_page_resolution_pdf(self):
        # char 6200 with 3000-char pages → page 3.
        assert citations.resolve_page("pdf", 6200) == 3
        assert citations.resolve_page("md", 6200) is None

    def test_page_resolution_with_boundaries(self):
        bounds = [(0, 1000), (1000, 2000), (2000, 3000)]
        assert citations.resolve_page("pdf", 1500, bounds) == 2

    def test_open_in_vault_uri(self):
        target = citations.open_in_vault_target("notes/math.md", "vault_folder")
        assert target and target.startswith("obsidian://")
        assert "notes/math.md" in target

    def test_open_in_vault_plain_path(self):
        assert citations.open_in_vault_target("notes/math.md", "local_dir") == "notes/math.md"
        assert citations.open_in_vault_target(None, "local_dir") is None

    def test_build_citation_shape(self):
        item = {
            "chunk_id": 1,
            "document_id": 2,
            "title": "T",
            "snippet": "…<mark>foo</mark>…",
            "score": 0.9,
            "mode": "keyword",
            "source_path": "a/b.md",
            "heading_path": "Intro",
            "doc_type": "md",
            "char_start": 10,
            "char_end": 50,
        }
        c = citations.build_citation(item, "vault_folder")
        assert c["heading"] == "Intro"
        assert c["source_path"] == "a/b.md"
        assert c["open_in_vault"].startswith("obsidian://")
        assert c["page"] is None  # md has no page


class TestCitationEndpoint:
    def test_search_results_carry_citation_fields(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, [
            "## Intro\n\nCitations make retrieval trustworthy.",
        ])
        resp = client.post(
            "/api/kb/search",
            json={"query": "citation", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert {"document_id", "source_path", "doc_type", "char_start"} <= set(item)

    def test_snippet_markers_present(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["A note about quantum entanglement."])
        resp = client.post(
            "/api/kb/search",
            json={"query": "quantum", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert any("<mark>" in i["snippet"] for i in resp.json()["items"])
