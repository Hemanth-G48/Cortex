"""Tests for Phase 86: upload security hardening.

Covers the three hardening vectors from the plan:
1. Path-traversal filenames are neutralised (stored under a random name).
2. MIME spoofing — content that does not match its declared extension — is
   rejected with 400 (magic-byte sniffing).
3. The size cap still returns 413.
"""
from __future__ import annotations

import tempfile

from app.config import settings


def _upload(client, filename: str, content: bytes, content_type: str = ""):
    files = {"file": (filename, content, content_type or "application/octet-stream")}
    return client.post("/api/uploads", files=files, data={"kind": "attachment"})


class TestPathTraversal:
    def test_traversal_filename_stored_safely(self, client, monkeypatch):
        """``../../etc/passwd`` is stored under a random name in UPLOAD_DIR."""
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            resp = _upload(client, "../../etc/passwd.pdf", b"%PDF-1.4 ok")
            assert resp.status_code == 201, resp.text
            data = resp.json()
            # The returned URL is a random hex name — never the original path.
            assert data["url"].startswith("/uploads/")
            assert "/etc/" not in data["url"]
            assert ".." not in data["url"]

    def test_upload_rejects_oversized(self, client, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            oversized = b"x" * (10 * 1024 * 1024 + 1)
            resp = _upload(client, "big.pdf", oversized, "application/pdf")
            assert resp.status_code == 413


class TestMimeSniffing:
    def test_pdf_content_with_png_extension_rejected(self, client, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            resp = _upload(client, "fake.png", b"%PDF-1.4 not a png", "image/png")
            assert resp.status_code == 400
            assert "does not match" in resp.json()["detail"]["error"]

    def test_text_content_disguised_as_pdf_rejected(self, client, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            resp = _upload(client, "evil.pdf", b"#!/bin/sh\nrm -rf /", "application/pdf")
            assert resp.status_code == 400
            assert "does not match" in resp.json()["detail"]["error"]

    def test_nul_bytes_disguised_as_txt_rejected(self, client, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            resp = _upload(client, "notes.txt", b"hello\x00world", "text/plain")
            assert resp.status_code == 400
            assert "does not match" in resp.json()["detail"]["error"]

    def test_valid_png_passes_sniff(self, client, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            resp = _upload(
                client,
                "image.png",
                b"\x89PNG\r\n\x1a\n fake png",
                "image/png",
            )
            assert resp.status_code == 201

    def test_valid_docx_passes_sniff(self, client, monkeypatch):
        with tempfile.TemporaryDirectory() as tmp:
            monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
            resp = _upload(
                client,
                "paper.docx",
                b"PK\x03\x04 docx zip content",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            assert resp.status_code == 201
