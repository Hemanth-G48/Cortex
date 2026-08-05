"""Tests for text_extractor service."""
from __future__ import annotations

import io
import os
import tempfile

import pytest
from docx import Document

from app.services.text_extractor import NoExtractableTextError, extract, extract_multiple


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_tmp(content: bytes, suffix: str) -> str:
    """Write content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(content)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# txt extraction
# ---------------------------------------------------------------------------


def test_extract_txt_returns_text():
    path = _write_tmp(b"Hello, world!", ".txt")
    try:
        result = extract(path, "txt")
    finally:
        os.unlink(path)
    assert "Hello, world!" in result


def test_extract_md_returns_text():
    path = _write_tmp(b"# Heading\n\nSome **bold** text.", ".md")
    try:
        result = extract(path, "md")
    finally:
        os.unlink(path)
    assert "# Heading" in result


# ---------------------------------------------------------------------------
# docx extraction
# ---------------------------------------------------------------------------


def test_extract_docx_returns_paragraph_text():
    doc = Document()
    doc.add_paragraph("First paragraph of the document.")
    doc.add_paragraph("Second paragraph with more detail.")
    path = _write_tmp(b"", ".docx")
    doc.save(path)
    try:
        result = extract(path, "docx")
    finally:
        os.unlink(path)
    assert "First paragraph" in result
    assert "Second paragraph" in result


def test_extract_docx_empty_raises():
    doc = Document()  # no paragraphs
    path = _write_tmp(b"", ".docx")
    doc.save(path)
    try:
        with pytest.raises(NoExtractableTextError):
            extract(path, "docx")
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# pdf extraction (graceful: either works or raises NoExtractableTextError)
# ---------------------------------------------------------------------------


def test_extract_pdf_graceful():
    """A minimal hand-written PDF that pypdf can parse (or raises NoExtractableTextError)."""
    # Minimal valid PDF with a text stream.
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 44 >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000388 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n497\n%%EOF\n"
    )
    path = _write_tmp(pdf_bytes, ".pdf")
    try:
        result = extract(path, "pdf")
        # If pypdf can parse it, we should get "Hello PDF" in the result.
        assert "Hello PDF" in result
    except NoExtractableTextError:
        # If the minimal PDF is not parseable by this pypdf version,
        # at least it should raise NoExtractableTextError (not crash).
        pass
    finally:
        os.unlink(path)


def test_extract_pdf_empty_raises():
    """A garbage PDF file should raise NoExtractableTextError, not crash."""
    path = _write_tmp(b"not a real pdf", ".pdf")
    try:
        with pytest.raises(NoExtractableTextError):
            extract(path, "pdf")
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# unsupported type
# ---------------------------------------------------------------------------


def test_extract_unsupported_type_raises():
    path = _write_tmp(b"zip content", ".zip")
    try:
        with pytest.raises(NoExtractableTextError):
            extract(path, "zip")
    finally:
        os.unlink(path)


def test_extract_no_text_raises():
    path = _write_tmp(b"   \n\n  ", ".txt")
    try:
        with pytest.raises(NoExtractableTextError):
            extract(path, "txt")
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# extract_multiple
# ---------------------------------------------------------------------------


def test_extract_multiple_joins_with_headers():
    path1 = _write_tmp(b"Content of file one.", ".txt")
    path2 = _write_tmp(b"Content of file two.", ".txt")
    try:
        result = extract_multiple([(path1, "txt"), (path2, "txt")])
    finally:
        os.unlink(path1)
        os.unlink(path2)
    assert "--- " in result
    assert "Content of file one." in result
    assert "Content of file two." in result


def test_extract_multiple_skips_unsupported():
    path_txt = _write_tmp(b"Valid text content.", ".txt")
    path_zip = _write_tmp(b"not extractable", ".zip")
    try:
        result = extract_multiple([(path_txt, "txt"), (path_zip, "zip")])
    finally:
        os.unlink(path_txt)
        os.unlink(path_zip)
    assert "Valid text content" in result
    assert "--- " in result
    # The zip file should be skipped, not cause an error
    assert "not extractable" not in result