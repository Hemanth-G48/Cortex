"""Idea 6 — OCR tests: monkeypatched pytesseract/pdf2image, merged output,
ocr_used flag, and graceful degradation when the binary/deps are missing.
"""
from __future__ import annotations

import sys

from app.config import settings
from app.models import KbDocument, User
from app.services.kb import ocr
from app.services.kb.pipeline import ingest_document


class FakeImg:
    pass


class FakePytesseract:
    class _inner:
        tesseract_cmd = ""

    pytesseract = _inner()

    @staticmethod
    def image_to_string(_img):
        return "FAKE OCR TEXT"

    @staticmethod
    def get_tesseract_version():
        return "5.0.0"


class FakePdf2Image:
    @staticmethod
    def convert_from_path(_path):
        return [FakeImg(), FakeImg()]


def _fake_ocr_deps(monkeypatch):
    monkeypatch.setattr(ocr, "_imports_ok", lambda: True)
    monkeypatch.setattr(ocr, "_tesseract_ok", lambda: True)
    monkeypatch.setitem(sys.modules, "pytesseract", FakePytesseract)
    monkeypatch.setitem(sys.modules, "pdf2image", FakePdf2Image)


def _doc(db_session, tmp_path, needs_ocr=True):
    user = User(name="Ocr", username="ocr-user", email="ocr@test.com", role="student")
    db_session.add(user)
    db_session.flush()
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake bytes")
    doc = KbDocument(
        user_id=user.id,
        title="Scanned PDF",
        doc_type="pdf",
        file_path=str(pdf_path),
        content_hash="abc123",
        status="new",
        needs_ocr=needs_ocr,
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc


class TestOcrPipeline:
    def test_ocr_runs_merges_and_flags(self, db_session, tmp_path, monkeypatch):
        _fake_ocr_deps(monkeypatch)
        monkeypatch.setattr(settings, "KB_OCR_ENABLED", True)
        # Empty extracted pages → needs_ocr triggered by the low-text check.
        monkeypatch.setattr(
            "app.services.kb.pipeline.extract_pdf_pages", lambda _p: ["", ""]
        )

        doc = _doc(db_session, tmp_path)
        result = ingest_document(db_session, doc)
        assert result["status"] == "ok"
        db_session.expire_all()
        assert doc.ocr_used is True
        assert "FAKE OCR TEXT" in doc.extracted_text
        assert doc.status == "unchanged"
        assert doc.char_count > 0

    def test_needs_ocr_flag_heuristic(self):
        long_page = "word " * 30  # > 50 chars → text page, no OCR
        assert ocr.needs_ocr([long_page] * 3) is False
        assert ocr.needs_ocr(["tiny"]) is True
        assert ocr.needs_ocr([]) is False

    def test_graceful_degradation_when_ocr_unavailable(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "KB_OCR_ENABLED", True)
        monkeypatch.setattr(ocr, "_imports_ok", lambda: False)
        monkeypatch.setattr(
            "app.services.kb.pipeline.extract_pdf_pages", lambda _p: ["", ""]
        )

        doc = _doc(db_session, tmp_path)
        result = ingest_document(db_session, doc)
        # Missing deps → status=failed, never a crash (phrase 56).
        assert result["status"] == "failed"
        db_session.expire_all()
        assert doc.status == "failed"

    def test_ocr_disabled_leaves_doc_alone(self, db_session, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "KB_OCR_ENABLED", False)
        monkeypatch.setattr(
            "app.services.kb.pipeline.extract_pdf_pages", lambda _p: ["", ""]
        )
        doc = _doc(db_session, tmp_path)
        # Even though the doc needs OCR, with OCR disabled we just ingest the
        # (empty) text rather than failing.
        result = ingest_document(db_session, doc)
        assert result["status"] == "failed"  # no extractable text at all
        db_session.expire_all()
        assert doc.needs_ocr is True
