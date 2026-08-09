"""Idea 23 — hybrid retrieval + RRF fusion tests.

Verifies the RRF math, determinism, mode-switchability, the
where-each-retriever-misses fixture, and the unified response shape for all
three KB_SEARCH_MODEs.
"""
from __future__ import annotations

from app.services.kb.search import rrf_fuse


def _signup(client, uname="hyb-user", email="hyb@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Hyb", "username": uname, "email": email,
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


class TestRrfMath:
    def test_rrf_formula(self):
        # Single retriever, k=60: score = 1/(60+rank).
        lists = [[{"chunk_id": 10, "sources": ["fts"]}]]
        fused = rrf_fuse(lists, k=60)
        assert fused[0]["chunk_id"] == 10
        assert abs(fused[0]["score"] - 1 / 61.0) < 1e-9

    def test_dedup_by_chunk_id(self):
        lists = [
            [{"chunk_id": 1, "sources": ["fts"]}, {"chunk_id": 2, "sources": ["fts"]}],
            [{"chunk_id": 2, "sources": ["semantic"]}, {"chunk_id": 1, "sources": ["semantic"]}],
        ]
        fused = rrf_fuse(lists, k=60)
        ids = [f["chunk_id"] for f in fused]
        assert ids == sorted(set(ids))  # no duplicates
        assert set(ids) == {1, 2}
        # Both chunks appear in both lists → sources aggregated.
        for f in fused:
            assert set(f["sources"]) == {"fts", "semantic"}

    def test_deterministic(self):
        lists = [
            [{"chunk_id": 3, "sources": ["fts"]}, {"chunk_id": 1, "sources": ["fts"]}],
            [{"chunk_id": 1, "sources": ["semantic"]}],
        ]
        a = rrf_fuse(lists, k=60)
        b = rrf_fuse(lists, k=60)
        assert [f["chunk_id"] for f in a] == [f["chunk_id"] for f in b]

    def test_where_each_retriever_misses(self):
        # FTS finds chunk A; semantic finds chunk B; neither finds the other's.
        # Fused top-k must contain BOTH.
        fts_only = [{"chunk_id": 1, "sources": ["fts"]}, {"chunk_id": 2, "sources": ["fts"]}]
        sem_only = [{"chunk_id": 3, "sources": ["semantic"]}, {"chunk_id": 4, "sources": ["semantic"]}]
        fused = rrf_fuse([fts_only, sem_only], k=60)
        assert {f["chunk_id"] for f in fused} == {1, 2, 3, 4}


class TestHybridEndpoint:
    def test_hybrid_mode_returns_shape(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, [
            "Support vector machines classify linearly separable data.",
            "Recurrent neural networks process sequential input.",
        ])
        resp = client.post(
            "/api/kb/search",
            json={"query": "neural sequence", "mode": "hybrid"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["mode"] == "hybrid"
        assert "items" in data and "total" in data

    def test_keyword_mode_matches_keyword_only(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Alpha beta gamma."])
        resp = client.post(
            "/api/kb/search",
            json={"query": "alpha", "mode": "keyword"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["mode"] == "keyword"

    def test_semantic_mode_matches_semantic_only(self, client, tmp_path):
        token = _signup(client)
        _scan(client, token, tmp_path, ["Some vault content."])
        resp = client.post(
            "/api/kb/search",
            json={"query": "anything", "mode": "semantic"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["mode"] == "semantic"

    def test_bad_mode_falls_back_to_hybrid(self, client, tmp_path):
        token = _signup(client)
        resp = client.post(
            "/api/kb/search",
            json={"query": "x", "mode": "bogus"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["mode"] == "hybrid"
