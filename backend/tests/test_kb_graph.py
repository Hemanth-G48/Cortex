"""Idea 16, Group 6 (phrases 51-60) — knowledge graph nodes & edges tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import (
    KbChunk,
    KbConcept,
    KbDocument,
    KbDocumentTag,
    KbEdge,
    KbSource,
    KbTag,
    User,
)
from app.services.kb.graph import (
    add_edge,
    build_graph,
    build_wikilink_edges,
    cooccurrence_edges,
    concepts_of,
    link_mentions_edges,
    neighbors,
    parse_wikilinks,
    related_docs,
)
from main import app

USER_A = dict(name="Graph A", username="graph-a", email="graph-a@test.com", role="student")
USER_B = dict(name="Graph B", username="graph-b", email="graph-b@test.com", role="student")


# ---------------------------------------------------------------------------
# Direct-db fixtures for service-level tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def graph_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def graph_session(graph_engine):
    Session = sessionmaker(bind=graph_engine)
    session = Session()
    yield session
    session.close()


def _user(session, **kwargs) -> User:
    user = User(**kwargs)
    session.add(user)
    session.flush()
    return user


def _doc(session, user, path="notes/hello.md", title="Hello", content_hash=None, extracted_text="", source_id=None) -> KbDocument:
    doc = KbDocument(
        user_id=user.id,
        source_id=source_id,
        path_rel=path,
        title=title,
        doc_type="md",
        content_hash=content_hash,
        status="unchanged",
        extracted_text=extracted_text,
    )
    session.add(doc)
    session.flush()
    return doc


# ---------------------------------------------------------------------------
# API fixtures
# ---------------------------------------------------------------------------

AUTH = "Authorization"


def _signup(client, uname="graph-user", email="graph@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Graph",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


# ===========================================================================
# parse_wikilinks
# ===========================================================================

class TestParseWikilinks:
    def test_simple_name(self):
        assert parse_wikilinks("[[Note name]]") == ["Note name"]

    def test_folder_path(self):
        assert parse_wikilinks("[[Folder/Note]]") == ["Folder/Note"]

    def test_section_anchor(self):
        assert parse_wikilinks("[[Note#Section]]") == ["Note"]

    def test_display_alias(self):
        assert parse_wikilinks("[[Note|Alias]]") == ["Note"]

    def test_section_and_alias(self):
        assert parse_wikilinks("[[Note#Sec|Alias]]") == ["Note"]

    def test_multiple_links(self):
        text = "[[First]] and [[Second#Intro|Show]]"
        assert parse_wikilinks(text) == ["First", "Second"]

    def test_empty_returns_nothing(self):
        assert parse_wikilinks("no links here") == []

    def test_strips_whitespace(self):
        assert parse_wikilinks("[[  spaced  ]]") == ["spaced"]


# ===========================================================================
# add_edge — dedupe, overwrite, threshold
# ===========================================================================

class TestAddEdge:
    def test_insert_new_edge(self, graph_session):
        u = _user(graph_session, **USER_A)
        d = _doc(graph_session, u, path="a.md")
        edge = add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.5)
        assert edge is not None
        assert edge.weight == 0.5
        assert edge.provenance == "auto"

    def test_below_threshold_returns_none(self, graph_session):
        u = _user(graph_session, **USER_A)
        d = _doc(graph_session, u, path="a.md")
        edge = add_edge(graph_session, u.id, d.id, target_document_id=d.id, weight=0.1)
        assert edge is None

    def test_no_target_returns_none(self, graph_session):
        u = _user(graph_session, **USER_A)
        d = _doc(graph_session, u, path="a.md")
        edge = add_edge(graph_session, u.id, d.id, weight=0.5)
        assert edge is None

    def test_dedupe_same_key(self, graph_session):
        u = _user(graph_session, **USER_A)
        d = _doc(graph_session, u, path="a.md")
        add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.5)
        edge2 = add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.8)
        # Without overwrite, second insert creates a duplicate (dedupe key allows it).
        # With overwrite=True (default), it updates the existing row.
        edges = (
            graph_session.query(KbEdge)
            .filter(KbEdge.user_id == u.id, KbEdge.source_document_id == d.id)
            .all()
        )
        assert len(edges) == 1
        assert edges[0].weight == 0.8

    def test_overwrite_updates_weight_and_provenance(self, graph_session):
        u = _user(graph_session, **USER_A)
        d = _doc(graph_session, u, path="a.md")
        add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.5, provenance="auto")
        edge = add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.9, provenance="manual", overwrite=True)
        assert edge is not None
        assert edge.weight == 0.9
        assert edge.provenance == "manual"

    def test_no_overwrite_returns_existing(self, graph_session):
        u = _user(graph_session, **USER_A)
        d = _doc(graph_session, u, path="a.md")
        edge1 = add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.5, overwrite=False)
        edge2 = add_edge(graph_session, u.id, d.id, target_document_id=d.id, relation="RELATED", weight=0.8, overwrite=False)
        # Both calls return the same row; no duplicate is inserted.
        assert edge1 is not None
        assert edge2 is not None
        assert edge1.id == edge2.id
        edges = (
            graph_session.query(KbEdge)
            .filter(KbEdge.user_id == u.id, KbEdge.source_document_id == d.id)
            .all()
        )
        assert len(edges) == 1

    def test_per_user_isolation(self, graph_session):
        ua = _user(graph_session, **USER_A)
        ub = _user(graph_session, **USER_B)
        da = _doc(graph_session, ua, path="a.md")
        db_doc = _doc(graph_session, ub, path="b.md")
        add_edge(graph_session, ua.id, da.id, target_document_id=db_doc.id, relation="RELATED", weight=0.5)
        edges = (
            graph_session.query(KbEdge)
            .filter(KbEdge.user_id == ub.id, KbEdge.source_document_id == db_doc.id)
            .all()
        )
        assert len(edges) == 0


# ===========================================================================
# build_wikilink_edges
# ===========================================================================

class TestBuildWikilinkEdges:
    def test_creates_wikilink_and_backlink(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = _doc(graph_session, u, path="notes/hello.md", title="Hello", extracted_text="See [[Notes/World]] for details.")
        tgt = _doc(graph_session, u, path="notes/world.md", title="World", extracted_text="Back to hello.")
        graph_session.commit()

        edges = build_wikilink_edges(graph_session, u.id, src)
        assert len(edges) == 2
        wikilink = [e for e in edges if e.relation == "WIKILINK"]
        backlink = [e for e in edges if e.relation == "BACKLINK"]
        assert len(wikilink) == 1
        assert len(backlink) == 1
        assert wikilink[0].source_document_id == src.id
        assert wikilink[0].target_document_id == tgt.id
        assert wikilink[0].provenance == "rule"
        assert backlink[0].source_document_id == tgt.id
        assert backlink[0].target_document_id == src.id
        assert backlink[0].provenance == "rule"

    def test_resolves_by_path_rel(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="[[b]]")
        tgt = _doc(graph_session, u, path="notes/b.md", title="B", extracted_text="")
        graph_session.commit()

        edges = build_wikilink_edges(graph_session, u.id, src)
        assert len(edges) == 2
        assert edges[0].target_document_id == tgt.id

    def test_resolves_by_title_fallback(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="[[B]]")
        tgt = _doc(graph_session, u, path="notes/b.md", title="B", extracted_text="")
        graph_session.commit()

        edges = build_wikilink_edges(graph_session, u.id, src)
        assert len(edges) == 2
        assert edges[0].target_document_id == tgt.id

    def test_self_link_skipped(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="[[A]]")
        graph_session.commit()

        edges = build_wikilink_edges(graph_session, u.id, src)
        assert len(edges) == 0

    def test_backlinks_false_omits_reverse(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="[[b]]")
        tgt = _doc(graph_session, u, path="notes/b.md", title="B", extracted_text="")
        graph_session.commit()

        edges = build_wikilink_edges(graph_session, u.id, src, backlinks=False)
        assert len(edges) == 1
        assert edges[0].relation == "WIKILINK"

    def test_no_extracted_text_returns_empty(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="")
        graph_session.commit()
        edges = build_wikilink_edges(graph_session, u.id, src)
        assert edges == []


# ===========================================================================
# link_mentions_edges
# ===========================================================================

class TestLinkMentionsEdges:
    def test_creates_mentions_edges(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept = KbConcept(user_id=u.id, canonical_name="Quantum Mechanics", aliases='["QM", "quantum"]')
        graph_session.add(concept)
        graph_session.flush()

        doc = _doc(graph_session, u, path="notes/physics.md", title="Physics", extracted_text="Quantum Mechanics is a field. QM is weird.")
        graph_session.commit()

        edges = link_mentions_edges(graph_session, u.id, doc)
        assert len(edges) == 1
        assert edges[0].relation == "MENTIONS"
        assert edges[0].target_type == "concept"
        assert edges[0].target_concept_id == concept.id
        assert edges[0].weight > 0

    def test_no_matching_concepts(self, graph_session):
        u = _user(graph_session, **USER_A)
        doc = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="Nothing relevant here.")
        graph_session.commit()
        edges = link_mentions_edges(graph_session, u.id, doc)
        assert edges == []

    def test_weight_is_relative_frequency(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept = KbConcept(user_id=u.id, canonical_name="Energy")
        graph_session.add(concept)
        graph_session.flush()

        doc = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="Energy energy energy matter.")
        graph_session.commit()

        edges = link_mentions_edges(graph_session, u.id, doc)
        assert len(edges) == 1
        # "Energy" appears 3 times out of 4 words (roughly)
        assert edges[0].weight > 0.5

    def test_idempotent(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept = KbConcept(user_id=u.id, canonical_name="Force")
        graph_session.add(concept)
        graph_session.flush()

        doc = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="Force is force.")
        graph_session.commit()

        link_mentions_edges(graph_session, u.id, doc)
        count_before = graph_session.query(KbEdge).filter(KbEdge.source_document_id == doc.id, KbEdge.relation == "MENTIONS").count()
        link_mentions_edges(graph_session, u.id, doc)
        count_after = graph_session.query(KbEdge).filter(KbEdge.source_document_id == doc.id, KbEdge.relation == "MENTIONS").count()
        assert count_before == count_after


# ===========================================================================
# cooccurrence_edges
# ===========================================================================

class TestCooccurrenceEdges:
    def test_shares_concept_edge(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept = KbConcept(user_id=u.id, canonical_name="Gravity")
        graph_session.add(concept)
        graph_session.flush()

        doc_a = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="Gravity is real.")
        doc_b = _doc(graph_session, u, path="notes/b.md", title="B", extracted_text="Gravity pulls things.")
        graph_session.commit()

        # Create MENTIONS edges for both docs to the same concept.
        add_edge(graph_session, u.id, doc_a.id, target_concept_id=concept.id, relation="MENTIONS", weight=1.0, provenance="rule", target_type="concept", overwrite=True)
        add_edge(graph_session, u.id, doc_b.id, target_concept_id=concept.id, relation="MENTIONS", weight=1.0, provenance="rule", target_type="concept", overwrite=True)
        graph_session.commit()

        edges = cooccurrence_edges(graph_session, u.id)
        assert len(edges) >= 1
        shares = [e for e in edges if e.relation == "SHARES_CONCEPT"]
        assert len(shares) >= 1

    def test_no_mentions_no_edges(self, graph_session):
        u = _user(graph_session, **USER_A)
        _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="Hello")
        _doc(graph_session, u, path="notes/b.md", title="B", extracted_text="World")
        graph_session.commit()
        edges = cooccurrence_edges(graph_session, u.id)
        assert edges == []

    def test_below_threshold_not_created(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept_a = KbConcept(user_id=u.id, canonical_name="Alpha")
        concept_b = KbConcept(user_id=u.id, canonical_name="Beta")
        graph_session.add_all([concept_a, concept_b])
        graph_session.flush()

        doc_a = _doc(graph_session, u, path="notes/a.md", title="A", extracted_text="Alpha here.")
        doc_b = _doc(graph_session, u, path="notes/b.md", title="B", extracted_text="Beta there.")
        graph_session.commit()

        add_edge(graph_session, u.id, doc_a.id, target_concept_id=concept_a.id, relation="MENTIONS", weight=1.0, provenance="rule", target_type="concept", overwrite=True)
        add_edge(graph_session, u.id, doc_b.id, target_concept_id=concept_b.id, relation="MENTIONS", weight=1.0, provenance="rule", target_type="concept", overwrite=True)
        graph_session.commit()

        edges = cooccurrence_edges(graph_session, u.id)
        shares = [e for e in edges if e.relation == "SHARES_CONCEPT"]
        assert len(shares) == 0  # no shared concepts → Jaccard = 0


# ===========================================================================
# neighbors
# ===========================================================================

class TestNeighbors:
    def test_outbound_and_inbound(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        add_edge(graph_session, u.id, b.id, target_document_id=a.id, relation="BACKLINK", weight=0.6, provenance="rule", overwrite=True)
        graph_session.commit()

        result = neighbors(graph_session, u.id, a.id)
        assert len(result) == 2
        assert all(r["direction"] in ("outbound", "inbound") for r in result)
        # Outbound: A→B, Inbound: B→A
        outbound = [r for r in result if r["direction"] == "outbound"]
        inbound = [r for r in result if r["direction"] == "inbound"]
        assert len(outbound) == 1
        assert len(inbound) == 1
        assert outbound[0]["relation"] == "WIKILINK"
        assert inbound[0]["relation"] == "BACKLINK"

    def test_ordered_by_weight_desc(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        c = _doc(graph_session, u, path="c.md", title="C")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="RELATED", weight=0.3, provenance="rule", overwrite=True)
        add_edge(graph_session, u.id, a.id, target_document_id=c.id, relation="RELATED", weight=0.9, provenance="rule", overwrite=True)
        graph_session.commit()

        result = neighbors(graph_session, u.id, a.id)
        assert result[0]["weight"] == 0.9
        assert result[1]["weight"] == 0.3

    def test_relation_filter(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="CITES", weight=0.5, provenance="rule", overwrite=True)
        graph_session.commit()

        result = neighbors(graph_session, u.id, a.id, relation="WIKILINK")
        assert len(result) == 1
        assert result[0]["relation"] == "WIKILINK"


# ===========================================================================
# related_docs
# ===========================================================================

class TestRelatedDocs:
    def test_returns_doc_targets(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        graph_session.commit()

        result = related_docs(graph_session, u.id, a.id)
        assert len(result) == 1
        assert result[0]["id"] == b.id
        assert result[0]["relation"] == "WIKILINK"
        assert result[0]["weight"] == 0.8

    def test_filters_by_min_weight(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="RELATED", weight=0.2, provenance="rule", overwrite=True)
        graph_session.commit()

        result = related_docs(graph_session, u.id, a.id)
        assert len(result) == 0  # below KB_EDGE_MIN_WEIGHT (0.3)


# ===========================================================================
# concepts_of
# ===========================================================================

class TestConceptsOf:
    def test_returns_mention_concepts(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept = KbConcept(user_id=u.id, canonical_name="Entropy")
        graph_session.add(concept)
        graph_session.flush()

        doc = _doc(graph_session, u, path="a.md", title="A", extracted_text="Entropy increases.")
        graph_session.commit()

        add_edge(graph_session, u.id, doc.id, target_concept_id=concept.id, relation="MENTIONS", weight=0.7, provenance="rule", target_type="concept", overwrite=True)
        graph_session.commit()

        result = concepts_of(graph_session, u.id, doc.id)
        assert len(result) == 1
        assert result[0]["name"] == "Entropy"
        assert result[0]["weight"] == 0.7


# ===========================================================================
# build_graph
# ===========================================================================

class TestBuildGraph:
    def test_node_id_format(self, graph_session):
        u = _user(graph_session, **USER_A)
        doc = _doc(graph_session, u, path="a.md", title="My Doc")
        concept = KbConcept(user_id=u.id, canonical_name="My Concept")
        graph_session.add(concept)
        graph_session.commit()

        add_edge(graph_session, u.id, doc.id, target_concept_id=concept.id, relation="MENTIONS", weight=0.5, provenance="rule", target_type="concept", overwrite=True)
        graph_session.commit()

        result = build_graph(graph_session, u.id)
        node_ids = {n["id"] for n in result["nodes"]}
        assert f"doc:{doc.id}" in node_ids
        assert f"concept:{concept.id}" in node_ids

    def test_edge_source_target_format(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        graph_session.commit()

        result = build_graph(graph_session, u.id)
        edges = result["edges"]
        assert len(edges) >= 1
        assert edges[0]["source"] == f"doc:{a.id}"
        assert edges[0]["target"] == f"doc:{b.id}"

    def test_weight_filtering(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="RELATED", weight=0.2, provenance="rule", overwrite=True)
        graph_session.commit()

        result = build_graph(graph_session, u.id)
        edge_weights = [e["weight"] for e in result["edges"]]
        assert all(w >= settings.KB_EDGE_MIN_WEIGHT for w in edge_weights)
        assert 0.2 not in edge_weights

    def test_relation_filter(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="CITES", weight=0.5, provenance="rule", overwrite=True)
        graph_session.commit()

        result = build_graph(graph_session, u.id, relation="WIKILINK")
        relations = {e["relation"] for e in result["edges"]}
        assert relations == {"WIKILINK"}

    def test_truncation_flag(self, graph_session):
        u = _user(graph_session, **USER_A)
        # Create more docs than the default limit of 200
        for i in range(5):
            _doc(graph_session, u, path=f"notes/{i}.md", title=f"Doc {i}")
        graph_session.commit()

        result = build_graph(graph_session, u.id, limit=2)
        assert result["truncated"] is True
        assert result["total_nodes"] == 5
        assert len(result["nodes"]) <= 2

    def test_no_truncation_when_under_limit(self, graph_session):
        u = _user(graph_session, **USER_A)
        _doc(graph_session, u, path="a.md", title="A")
        _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        result = build_graph(graph_session, u.id, limit=10)
        assert result["truncated"] is False
        assert result["total_nodes"] == 2

    def test_source_filter(self, graph_session):
        u = _user(graph_session, **USER_A)
        src = KbSource(user_id=u.id, name="Vault", source_type="vault_folder", root_path="/tmp")
        graph_session.add(src)
        graph_session.flush()

        d1 = _doc(graph_session, u, path="a.md", title="A", source_id=src.id)
        d2 = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        result = build_graph(graph_session, u.id, source=str(src.id))
        node_labels = {n["label"] for n in result["nodes"]}
        assert "A" in node_labels
        assert "B" not in node_labels

    def test_tag_filter(self, graph_session):
        u = _user(graph_session, **USER_A)
        tag = KbTag(user_id=u.id, name="math", kind="inline")
        graph_session.add(tag)
        graph_session.flush()

        d1 = _doc(graph_session, u, path="a.md", title="Algebra")
        d2 = _doc(graph_session, u, path="b.md", title="History")
        graph_session.commit()

        graph_session.add(KbDocumentTag(user_id=u.id, document_id=d1.id, tag_id=tag.id, provenance="rule"))
        graph_session.commit()

        result = build_graph(graph_session, u.id, tag="math")
        node_labels = {n["label"] for n in result["nodes"]}
        assert "Algebra" in node_labels
        assert "History" not in node_labels

    def test_concept_filter(self, graph_session):
        u = _user(graph_session, **USER_A)
        concept = KbConcept(user_id=u.id, canonical_name="Quantum")
        graph_session.add(concept)
        graph_session.flush()

        d1 = _doc(graph_session, u, path="a.md", title="Physics", extracted_text="Quantum theory")
        d2 = _doc(graph_session, u, path="b.md", title="Biology", extracted_text="Cells divide")
        graph_session.commit()

        add_edge(graph_session, u.id, d1.id, target_concept_id=concept.id, relation="MENTIONS", weight=0.5, provenance="rule", target_type="concept", overwrite=True)
        graph_session.commit()

        result = build_graph(graph_session, u.id, concept="Quantum")
        node_labels = {n["label"] for n in result["nodes"]}
        assert "Physics" in node_labels
        assert "Biology" not in node_labels

    def test_per_user_isolation(self, graph_session):
        ua = _user(graph_session, **USER_A)
        ub = _user(graph_session, **USER_B)
        da = _doc(graph_session, ua, path="a.md", title="A")
        db_doc = _doc(graph_session, ub, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, ua.id, da.id, target_document_id=db_doc.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        graph_session.commit()

        result_a = build_graph(graph_session, ua.id)
        result_b = build_graph(graph_session, ub.id)

        # User A's graph has the edge
        assert len(result_a["edges"]) >= 1
        # User B's graph has no nodes from user A
        a_node_ids = {n["id"] for n in result_b["nodes"]}
        assert f"doc:{da.id}" not in a_node_ids

    def test_total_counts(self, graph_session):
        u = _user(graph_session, **USER_A)
        a = _doc(graph_session, u, path="a.md", title="A")
        b = _doc(graph_session, u, path="b.md", title="B")
        graph_session.commit()

        add_edge(graph_session, u.id, a.id, target_document_id=b.id, relation="WIKILINK", weight=0.8, provenance="rule", overwrite=True)
        graph_session.commit()

        result = build_graph(graph_session, u.id)
        assert result["total_nodes"] == 2
        assert result["total_edges"] >= 1


# ===========================================================================
# API-level tests
# ===========================================================================

class TestGraphApi:
    def test_get_graph_endpoint(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "a.md").write_text("[[b]]")
        (tmp_path / "b.md").write_text("[[a]]")

        src_resp = client.post(
            "/api/kb/sources",
            json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token}"},
        )
        assert src_resp.status_code == 201
        source_id = src_resp.json()["id"]

        scan_resp = client.post(
            f"/api/kb/sources/{source_id}/scan",
            headers={AUTH: f"Bearer {token}"},
        )
        assert scan_resp.status_code == 200

        graph_resp = client.get(
            "/api/kb/graph",
            headers={AUTH: f"Bearer {token}"},
        )
        assert graph_resp.status_code == 200
        data = graph_resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert "truncated" in data
        assert "total_nodes" in data
        assert "total_edges" in data

    def test_graph_per_user_isolation(self, client, tmp_path):
        token_a = _signup(client, "graph-iso-a", "iso-a@test.com")
        token_b = _signup(client, "graph-iso-b", "iso-b@test.com")

        # User A creates a source with a wikilink document
        (tmp_path / "a.md").write_text("[[b]]")
        (tmp_path / "b.md").write_text("[[a]]")
        src_a = client.post(
            "/api/kb/sources",
            json={"name": "Vault A", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token_a}"},
        ).json()

        client.post(
            f"/api/kb/sources/{src_a['id']}/scan",
            headers={AUTH: f"Bearer {token_a}"},
        )

        # User B has no documents
        graph_b = client.get(
            "/api/kb/graph",
            headers={AUTH: f"Bearer {token_b}"},
        ).json()
        assert graph_b["total_nodes"] == 0

    def test_get_neighbors_endpoint(self, client, tmp_path):
        token = _signup(client)
        (tmp_path / "a.md").write_text("[[b]]")
        (tmp_path / "b.md").write_text("[[a]]")

        src_resp = client.post(
            "/api/kb/sources",
            json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token}"},
        )
        assert src_resp.status_code == 201
        source_id = src_resp.json()["id"]

        scan_resp = client.post(
            f"/api/kb/sources/{source_id}/scan",
            headers={AUTH: f"Bearer {token}"},
        )
        assert scan_resp.status_code == 200

        # Get the first document's ID
        docs_resp = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token}"}).json()
        assert docs_resp["total"] >= 1
        doc_id = docs_resp["items"][0]["id"]

        neighbors_resp = client.get(
            f"/api/kb/documents/{doc_id}/neighbors",
            headers={AUTH: f"Bearer {token}"},
        )
        assert neighbors_resp.status_code == 200
        neighbors_data = neighbors_resp.json()
        assert isinstance(neighbors_data, list)

    def test_neighbors_404_for_nonexistent_doc(self, client, tmp_path):
        token = _signup(client)
        resp = client.get(
            "/api/kb/documents/99999/neighbors",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_neighbors_404_for_other_users_doc(self, client, tmp_path):
        token_a = _signup(client, "neighbor-a", "na@test.com")
        token_b = _signup(client, "neighbor-b", "nb@test.com")

        (tmp_path / "a.md").write_text("content")
        src_resp = client.post(
            "/api/kb/sources",
            json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token_a}"},
        )
        assert src_resp.status_code == 201
        source_id = src_resp.json()["id"]

        scan_resp = client.post(
            f"/api/kb/sources/{source_id}/scan",
            headers={AUTH: f"Bearer {token_a}"},
        )
        assert scan_resp.status_code == 200

        docs_resp = client.get("/api/kb/documents", headers={AUTH: f"Bearer {token_a}"}).json()
        doc_id = docs_resp["items"][0]["id"]

        # User B tries to access user A's document neighbors
        resp = client.get(
            f"/api/kb/documents/{doc_id}/neighbors",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    def test_graph_limit_param(self, client, tmp_path):
        token = _signup(client)
        # Distinct content so each file becomes its own document (content-hash
        # dedup would otherwise collapse identical files into one document).
        (tmp_path / "a.md").write_text("alpha content")
        (tmp_path / "b.md").write_text("beta content")
        (tmp_path / "c.md").write_text("gamma content")

        src_resp = client.post(
            "/api/kb/sources",
            json={"name": "Vault", "source_type": "vault_folder", "root_path": str(tmp_path)},
            headers={AUTH: f"Bearer {token}"},
        )
        assert src_resp.status_code == 201
        source_id = src_resp.json()["id"]

        client.post(
            f"/api/kb/sources/{source_id}/scan",
            headers={AUTH: f"Bearer {token}"},
        )

        resp = client.get(
            "/api/kb/graph?limit=1",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["truncated"] is True
        assert len(data["nodes"]) <= 1
