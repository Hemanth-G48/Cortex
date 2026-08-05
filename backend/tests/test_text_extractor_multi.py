"""Tests for extract_multiple in text_extractor service."""
from __future__ import annotations

import os
import tempfile

from app.services.text_extractor import extract_multiple


def _write_tmp(content: bytes, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    f.write(content)
    f.close()
    return f.name


def test_extract_multiple_two_txt_files():
    p1 = _write_tmp(b"First file content.", ".txt")
    p2 = _write_tmp(b"Second file content.", ".txt")
    try:
        result = extract_multiple([(p1, "txt"), (p2, "txt")])
    finally:
        os.unlink(p1)
        os.unlink(p2)
    assert "First file content" in result
    assert "Second file content" in result
    # Each file should have a header
    assert "--- " in result


def test_extract_multiple_skips_unsupported_file():
    p_txt = _write_tmp(b"Only this should appear.", ".txt")
    p_zip = _write_tmp(b"binary zip data", ".zip")
    try:
        result = extract_multiple([(p_txt, "txt"), (p_zip, "zip")])
    finally:
        os.unlink(p_txt)
        os.unlink(p_zip)
    assert "Only this should appear" in result
    assert "binary zip data" not in result


def test_extract_multiple_empty_result():
    p_zip = _write_tmp(b"garbage", ".zip")
    try:
        result = extract_multiple([(p_zip, "zip")])
    finally:
        os.unlink(p_zip)
    assert result == ""


def test_extract_multiple_with_docx():
    from docx import Document

    doc = Document()
    doc.add_paragraph("DOCX paragraph text.")
    p_docx = _write_tmp(b"", ".docx")
    doc.save(p_docx)
    p_txt = _write_tmp(b"TXT file text.", ".txt")
    try:
        result = extract_multiple([(p_txt, "txt"), (p_docx, "docx")])
    finally:
        os.unlink(p_txt)
        os.unlink(p_docx)
    assert "TXT file text" in result
    assert "DOCX paragraph text" in result
