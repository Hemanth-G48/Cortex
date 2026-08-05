"""Tests for ingestion error handling (empty/unsupported content)."""
from __future__ import annotations

import io

import pytest
from fastapi import status

from app.services.text_extractor import NoExtractableTextError


def test_no_extractable_text_error_for_unsupported_type():
    """NoExtractableTextError is raised for unsupported file types."""
    with pytest.raises(NoExtractableTextError):
        from app.services.text_extractor import extract
        extract("/tmp/fake.xyz", "xyz")


def test_no_extractable_text_error_for_empty_txt():
    """NoExtractableTextError is raised for empty txt content."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as f:
        f.write("")
        fname = f.name
    try:
        from app.services.text_extractor import extract
        with pytest.raises(NoExtractableTextError):
            extract(fname, "txt")
    finally:
        os.unlink(fname)


def test_text_for_material_returns_empty_on_unsupported_type():
    """text_for_material returns empty string when extraction fails."""
    from unittest.mock import MagicMock
    from app.services.ingestion import text_for_material

    material = MagicMock()
    material.extracted_text = None
    material.file_path_on_disk.return_value = "/tmp/fake.xyz"
    material.file_type = "xyz"

    result = text_for_material(MagicMock(), material)
    assert result == ""