"""Idea 36 — citation registry tests.

Reference-list parsing, ``@cite`` linking, dedupe, BibTeX export, per-user
isolation.
"""
from __future__ import annotations

from app.models import KbCitation
from app.services.kb.citation_registry import (
    add_citation,
    build_bibtex,
    list_citations,
    make_cite_key,
    parse_inline_citations,
    parse_reference_lines,
)


def _signup(client, uname="cite-user", email="cite@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Cite", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


class TestParsing:
    def test_parse_reference_lines(self):
        text = (
            "Some body text here.\n\n"
            "## References\n"
            "1. Smith, J. Quantum mechanics, Nature, 2021.\n"
            "2. Doe, A. arXiv:2301.12345, 2023.\n\n"
            "3. Lee, K. Photon physics, PhysRev, 2020."
        )
        lines = parse_reference_lines(text)
        assert len(lines) >= 2
        assert "Quantum" in lines[0]

    def test_parse_inline_citations(self):
        text = "This result is well known @cite:einstein1905 and also [[cite:planck1900]]."
        keys = parse_inline_citations(text)
        assert "einstein1905" in keys and "planck1900" in keys

    def test_make_cite_key_with_year(self):
        assert make_cite_key("Smith, J. Title, 2021") == "smith2021"


class TestRegistryService:
    def test_add_dedupes_on_key(self, db_session):
        add_citation(db_session, 1, cite_key="smith2021", title="A", raw_text="x")
        add_citation(db_session, 1, cite_key="smith2021", title="B", raw_text="y")
        db_session.commit()
        assert db_session.query(KbCitation).filter_by(cite_key="smith2021").count() == 1
        # First row keeps its metadata; new info is merged, not overwritten.
        row = db_session.query(KbCitation).filter_by(cite_key="smith2021").first()
        assert row.title == "A"

    def test_list_filters_by_year(self, db_session):
        add_citation(db_session, 1, cite_key="a2021", title="A", year=2021)
        add_citation(db_session, 1, cite_key="b2022", title="B", year=2022)
        db_session.commit()
        items = list_citations(db_session, 1, year=2021)
        assert [i["cite_key"] for i in items] == ["a2021"]

    def test_bibtex_export(self, db_session):
        add_citation(db_session, 1, cite_key="einstein1905", title="On the electrodynamics",
                     authors=["Einstein, A."], year=1905, venue="Annalen der Physik",
                     doi="10.1002/andp.19053221004")
        db_session.commit()
        bib = build_bibtex(list_citations(db_session, 1))
        assert "@article{einstein1905," in bib
        assert "title = {On the electrodynamics}" in bib
        assert "author = {Einstein, A.}" in bib
        assert "doi" in bib


class TestCitationEndpoints:
    def test_inline_cite_linked_on_ingest(self, client, db_session):
        token = _signup(client)
        resp = client.post(
            "/api/kb/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (
                "note.md",
                b"# Note\n\nRelativity follows @cite:einstein1905 and [[cite:newton1687]].",
                "test.md",
            )},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]
        r = client.get(
            f"/api/kb/documents/{doc_id}/citations",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200, r.text
        keys = {i["cite_key"] for i in r.json()["items"]}
        assert "einstein1905" in keys and "newton1687" in keys

    def test_export_bibtex_endpoint(self, client, db_session):
        token = _signup(client)
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token)["user_id"]
        add_citation(db_session, user_id, cite_key="demo2024", title="Demo", year=2024)
        db_session.commit()
        r = client.get(
            "/api/kb/citations/export?format=bibtex",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        assert "@misc{demo2024," in r.text

    def test_per_user_isolation(self, client, db_session):
        token_a = _signup(client, "cite-a", "citea@test.com")
        token_b = _signup(client, "cite-b", "citeb@test.com")
        from app.services.security import decode_bearer_token
        user_id = decode_bearer_token(token_a)["user_id"]
        add_citation(db_session, user_id, cite_key="private2024", title="Private")
        db_session.commit()
        r = client.get(
            "/api/kb/citations",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert r.status_code == 200
        assert r.json()["items"] == []
