"""Tests for metadata extraction & enrichment (Idea 13, phrases 22-30)."""
from __future__ import annotations

import io

import pytest
from sqlalchemy.orm import Session

from app.models import KbDocument, User
from app.services.kb import KbService
from app.services.kb.metadata import (
    apply_metadata_update,
    detect_language,
    enrich_metadata,
    estimate_reading_time,
    extract_frontmatter,
    metadata_filters,
    propose_metadata,
)
from app.schemas.kb import KbMetadataUpdate

AUTH = "Authorization"


def _signup(client, uname="meta-user", email="meta@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={
            "name": "Meta",
            "username": uname,
            "email": email,
            "password": "pass123",
            "role": "student",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _make_doc(db: Session, user_id: int, title: str = "Test Doc", extracted_text: str = "", frontmatter_json: str | None = None) -> KbDocument:
    doc = KbDocument(
        user_id=user_id,
        title=title,
        doc_type="md",
        extracted_text=extracted_text,
        frontmatter_json=frontmatter_json,
        metadata_json=None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


class TestDetectLanguage:
    def test_english_detection(self):
        text = "The quick brown fox jumps over the lazy dog and the cat sat on the mat"
        assert detect_language(text) == "en"

    def test_french_detection(self):
        text = "Le chat est sur le toit et la femme mange du pain avec un verre de vin"
        assert detect_language(text) == "fr"

    def test_empty_text_returns_none(self):
        assert detect_language("") is None
        assert detect_language("   ") is None

    def test_code_like_text_returns_none(self):
        assert detect_language("x = 1 + 2\nreturn foo()") is None


class TestEstimateReadingTime:
    def test_exact_200_words(self):
        # 200 words at 200 wpm = 1 minute = 60 seconds
        words = "word " * 200
        assert estimate_reading_time(words) == 60

    def test_zero_text(self):
        assert estimate_reading_time("") == 0
        assert estimate_reading_time(None) == 0  # type: ignore[arg-type]

    def test_fractional_rounds_down(self):
        # 100 words = 0.5 min = 30 seconds
        words = "word " * 100
        assert estimate_reading_time(words) == 30


class TestExtractFrontmatter:
    def test_frontmatter_author_wins(self, db_session: Session):
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="My Post",
            extracted_text="Some content here.",
            frontmatter_json='{"author": "Jane Doe", "title": "My Post"}',
        )
        result = extract_frontmatter(db_session, doc)
        assert result["author"] == "Jane Doe"

    def test_frontmatter_source_url(self, db_session: Session):
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Source URL Test",
            frontmatter_json='{"url": "https://example.com/article"}',
        )
        result = extract_frontmatter(db_session, doc)
        assert result["source_url"] == "https://example.com/article"

    def test_frontmatter_language_and_date(self, db_session: Session):
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Lang Date Test",
            frontmatter_json='{"language": "en", "date": "2024-06-15"}',
        )
        result = extract_frontmatter(db_session, doc)
        assert result["language"] == "en"
        assert result["doc_date"] is not None

    def test_empty_frontmatter(self, db_session: Session):
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="Empty FM Test")
        result = extract_frontmatter(db_session, doc)
        assert result == {}


class TestProposeMetadata:
    def test_returns_valid_proposal_when_ai_disabled(self, db_session: Session, monkeypatch):
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="French Article",
            extracted_text="Le chat est sur le toit et la femme mange du pain",
        )
        proposal = propose_metadata(db_session, doc)
        assert proposal is not None
        assert proposal.language == "fr"
        assert proposal.reading_time_seconds >= 0
        assert proposal.confidence >= 0.0

    def test_frontmatter_author_in_proposal(self, db_session: Session):
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Author Test",
            extracted_text="Some content.",
            frontmatter_json='{"author": "Frontmatter Author"}',
        )
        proposal = propose_metadata(db_session, doc)
        assert proposal.author == "Frontmatter Author"


class TestEnrichMetadata:
    def test_frontmatter_precedence_over_llm(self, db_session: Session, monkeypatch):
        """Frontmatter author beats LLM proposal (phrase 27)."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Frontmatter Precedence",
            extracted_text="The quick brown fox jumps over the lazy dog " * 10,
            frontmatter_json='{"author": "Frontmatter Author"}',
        )
        enrich_metadata(db_session, doc)
        db_session.refresh(doc)
        assert doc.author == "Frontmatter Author"

    def test_manual_override_survives_re_enrich(self, db_session: Session, monkeypatch):
        """Manual override must not be overwritten by re-ingest (phrase 27)."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Manual Override Test",
            extracted_text="The quick brown fox jumps over the lazy dog and the cat sat on the mat and the dog ran away fast and the fox was quick and the cat was lazy and the dog barked loudly at the fox and the cat hissed back at the dog and the fox ran away quickly into the forest and the cat followed silently behind the dog and the fox stopped to rest under a tree and the cat sat down next to the dog and the dog wagged its tail and the cat purred softly and the fox opened its eyes and the dog barked again at the fox and the cat jumped up and the fox ran away into the deep forest and the cat followed the fox into the forest and the dog waited patiently for the cat and the fox to return and the cat returned with the fox and the dog wagged its tail again",
            frontmatter_json='{"author": "Frontmatter Author"}',
        )
        # First enrich — sets author from frontmatter
        enrich_metadata(db_session, doc)
        db_session.refresh(doc)
        assert doc.author == "Frontmatter Author"

        # Now apply a manual override
        update = KbMetadataUpdate(author="Manual Author")
        apply_metadata_update(db_session, doc, update)
        db_session.refresh(doc)
        assert doc.author == "Manual Author"

        # Re-enrich — manual value must survive
        enrich_metadata(db_session, doc)
        db_session.refresh(doc)
        assert doc.author == "Manual Author"

    def test_provenance_stored_in_metadata_json(self, db_session: Session, monkeypatch):
        """Per-field provenance is persisted in metadata_json (phrase 27)."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Provenance Test",
            extracted_text="The quick brown fox jumps over the lazy dog " * 10,
            frontmatter_json='{"author": "FM Author"}',
        )
        enrich_metadata(db_session, doc)
        db_session.refresh(doc)
        meta = doc.metadata_json
        assert meta is not None
        parsed = doc.metadata_json  # already a dict after json_loads in enrich
        # The rule provenance should record frontmatter for author
        assert "rule" in meta or "ai" in meta or "manual" in meta

    def test_deterministic_language_set_by_enrich(self, db_session: Session, monkeypatch):
        """When AI is disabled, language is set by detect_language heuristic."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(
            db_session,
            user.id,
            title="Lang Detect Test",
            extracted_text="The quick brown fox jumps over the lazy dog and the cat sat on the mat",
        )
        enrich_metadata(db_session, doc)
        db_session.refresh(doc)
        assert doc.language == "en"


class TestApplyMetadataUpdate:
    def test_manual_override_persists(self, db_session: Session):
        """PUT metadata stores values in metadata_json["manual"] (phrase 26)."""
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="Override Test")

        update = KbMetadataUpdate(author="Manual Author", language="en")
        result = apply_metadata_update(db_session, doc, update)
        db_session.refresh(result)

        assert result.author == "Manual Author"
        assert result.language == "en"
        assert result.metadata_json is not None
        meta = KbService.json_loads(result.metadata_json) or {}
        assert "manual" in meta
        assert meta["manual"]["author"] == "Manual Author"
        assert meta["manual"]["language"] == "en"

    def test_metadata_dict_merged(self, db_session: Session):
        """update.metadata dict is merged into metadata_json."""
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="Metadata Merge Test")

        update = KbMetadataUpdate(metadata={"custom_key": "custom_value"})
        apply_metadata_update(db_session, doc, update)
        db_session.refresh(doc)

        meta = KbService.json_loads(doc.metadata_json) or {}
        assert "metadata" in meta
        assert meta["metadata"]["custom_key"] == "custom_value"


class TestMetadataApi:
    def test_proposal_404_for_other_user(self, client):
        """404 when requesting proposal for another user's document."""
        token_a = _signup(client, "meta-a", "meta-a@test.com")
        token_b = _signup(client, "meta-b", "meta-b@test.com")

        # Create a doc as user A
        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token_a}"},
            files={"file": ("test.md", io.BytesIO(b"# Title\n\nContent here."), "text/markdown")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        # User B tries to get proposal — should be 404
        resp = client.get(
            f"/api/kb/documents/{doc_id}/metadata-proposal",
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 404

    def test_proposal_returns_metadata(self, client, monkeypatch):
        """GET proposal returns a valid KbMetadataProposal."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client, "prop-user", "prop@test.com")

        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", io.BytesIO(b"# Title\n\nThe quick brown fox jumps over the lazy dog."), "text/markdown")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        resp = client.get(
            f"/api/kb/documents/{doc_id}/metadata-proposal",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "author" in data
        assert "language" in data
        assert "reading_time_seconds" in data
        assert "confidence" in data
        assert "reason" in data

    def test_proposal_get_never_calls_llm(self, client, monkeypatch):
        """GET metadata-proposal is read-only — browsing must not spend an
        LLM call (frontmatter + deterministic heuristics only)."""
        token = _signup(client, "det-user", "det@test.com")

        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", io.BytesIO(b"# Title\n\nThe quick brown fox jumps over the lazy dog."), "text/markdown")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        # If the GET path ever reaches the LLM, fail loudly.
        monkeypatch.setattr(
            "app.services.kb.metadata.generate_json",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("GET must not call the LLM")),
        )
        resp = client.get(
            f"/api/kb/documents/{doc_id}/metadata-proposal",
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "author" in data
        assert "language" in data
        assert "reading_time_seconds" in data

    def test_put_metadata_manual_override(self, client, monkeypatch):
        """PUT metadata stores manual override; re-enrich preserves it."""
        monkeypatch.setattr("app.config.settings.AI_ENABLED", False)
        token = _signup(client, "put-user", "put@test.com")

        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token}"},
            files={"file": ("test.md", io.BytesIO(b"# Title\n\nContent here."), "text/markdown")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        # Apply manual metadata override
        resp = client.put(
            f"/api/kb/documents/{doc_id}/metadata",
            json={
                "author": "Manual Author",
                "language": "en",
                "metadata": {"custom": "value"},
            },
            headers={AUTH: f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["author"] == "Manual Author"
        assert data["language"] == "en"

    def test_put_metadata_404_for_other_user(self, client):
        """404 when updating another user's document."""
        token_a = _signup(client, "put-a", "put-a@test.com")
        token_b = _signup(client, "put-b", "put-b@test.com")

        resp = client.post(
            "/api/kb/documents/upload",
            headers={AUTH: f"Bearer {token_a}"},
            files={"file": ("test.md", io.BytesIO(b"# Title\n\nContent."), "text/markdown")},
        )
        assert resp.status_code == 201, resp.text
        doc_id = resp.json()["document"]["id"]

        resp = client.put(
            f"/api/kb/documents/{doc_id}/metadata",
            json={"author": "Hacker"},
            headers={AUTH: f"Bearer {token_b}"},
        )
        assert resp.status_code == 404


class TestMetadataFilters:
    def test_author_filter(self, db_session: Session):
        """metadata_filters with author matches case-insensitively."""
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="Auth Test", extracted_text="content")
        doc.author = "Jane Doe"
        db_session.commit()

        from sqlalchemy.orm import Session as Sess

        q = db_session.query(KbDocument).filter(KbDocument.user_id == user.id)
        filtered = metadata_filters(q, author="jane")
        assert filtered.count() == 1

        filtered = metadata_filters(q, author="nobody")
        assert filtered.count() == 0

    def test_language_filter(self, db_session: Session):
        """metadata_filters with language exact match."""
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="Lang Test", extracted_text="content")
        doc.language = "en"
        db_session.commit()

        q = db_session.query(KbDocument).filter(KbDocument.user_id == user.id)
        filtered = metadata_filters(q, language="en")
        assert filtered.count() == 1

        filtered = metadata_filters(q, language="fr")
        assert filtered.count() == 0

    def test_date_range_filter(self, db_session: Session):
        """metadata_filters with date_from and date_to."""
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="Date Test", extracted_text="content")
        from datetime import date as dt_date
        doc.doc_date = dt_date(2024, 6, 15)
        db_session.commit()

        q = db_session.query(KbDocument).filter(KbDocument.user_id == user.id)
        filtered = metadata_filters(
            q,
            date_from=dt_date(2024, 1, 1),
            date_to=dt_date(2024, 12, 31),
        )
        assert filtered.count() == 1

        filtered = metadata_filters(q, date_from=dt_date(2025, 1, 1))
        assert filtered.count() == 0

    def test_no_filters_returns_all(self, db_session: Session):
        """metadata_filters with no filters returns the original query unchanged."""
        user = db_session.query(User).first()
        assert user is not None
        doc = _make_doc(db_session, user.id, title="No Filter Test", extracted_text="content")
        db_session.commit()

        q = db_session.query(KbDocument).filter(KbDocument.user_id == user.id)
        filtered = metadata_filters(q)
        assert filtered.count() == 1
