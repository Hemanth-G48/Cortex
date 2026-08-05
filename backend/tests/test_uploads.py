"""Tests for the multipart upload infrastructure (Phase 5)."""
from __future__ import annotations

import io
import os
import tempfile

import pytest

from app.config import settings


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

SAMPLE_PDF = b"%PDF-1.4 fake pdf content"
SAMPLE_PNG = b"\x89PNG\r\n\x1a\n fake png content"
SAMPLE_TXT = b"hello world"


def _upload(client, filename: str, content: bytes, content_type: str = "", kind: str = "attachment"):
    """Helper: POST a multipart file and return the response."""
    files = {"file": (filename, io.BytesIO(content), content_type or "application/octet-stream")}
    data = {"kind": kind}
    return client.post("/api/uploads", files=files, data=data)


# ---------------------------------------------------------------------------
# happy path
# ---------------------------------------------------------------------------

def test_upload_pdf_returns_201_and_url(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        resp = _upload(client, "report.pdf", SAMPLE_PDF, "application/pdf")
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"].startswith("/uploads/")
    assert data["filename"] == "report.pdf"
    assert data["size"] == len(SAMPLE_PDF)
    assert data["kind"] == "attachment"


def test_upload_png_returns_201(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        resp = _upload(client, "image.png", SAMPLE_PNG, "image/png")
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"].startswith("/uploads/")


def test_upload_txt_returns_201(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        resp = _upload(client, "note.txt", SAMPLE_TXT, "text/plain")
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"].startswith("/uploads/")


def test_upload_serves_static_file(client):
    """Static serving works: upload into the real UPLOAD_DIR then GET it."""
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    stored_name = "test_static_file.pdf"
    dest = os.path.join(settings.UPLOAD_DIR, stored_name)
    try:
        with open(dest, "wb") as f:
            f.write(SAMPLE_PDF)
        resp = client.get(f"/uploads/{stored_name}")
        assert resp.status_code == 200
        assert resp.content == SAMPLE_PDF
    finally:
        if os.path.exists(dest):
            os.remove(dest)


def test_upload_kind_form_field_passed_through(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        # OOXML files are zip containers (PK magic) — matches the Phase 86 sniff.
        sample_pptx = b"PK\x03\x04 pptx content"
        resp = _upload(client, "slide.pptx", sample_pptx, "application/vnd.ms-powerpoint", kind="assignment")
    assert resp.status_code == 201
    assert resp.json()["kind"] == "assignment"


# ---------------------------------------------------------------------------
# validation: missing file
# ---------------------------------------------------------------------------

def test_upload_no_file_returns_422(client):
    """FastAPI rejects a missing required UploadFile with 422."""
    resp = client.post("/api/uploads", data={"kind": "attachment"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# validation: disallowed extension
# ---------------------------------------------------------------------------

def test_upload_exe_returns_400(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        resp = _upload(client, "malware.exe", b"fake exe", "application/x-msdownload")
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "File type not allowed"


def test_upload_shell_script_returns_400(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        resp = _upload(client, "script.sh", b"#!/bin/bash", "application/x-sh")
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "File type not allowed"


# ---------------------------------------------------------------------------
# validation: oversized file
# ---------------------------------------------------------------------------

def test_upload_oversized_returns_413(client, monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setattr(settings, "UPLOAD_DIR", tmp)
        oversized = b"x" * (10 * 1024 * 1024 + 1)  # 1 byte over 10 MB default
        resp = _upload(client, "huge.pdf", oversized, "application/pdf")
    assert resp.status_code == 413
    assert resp.json()["detail"]["error"] == "File too large"
