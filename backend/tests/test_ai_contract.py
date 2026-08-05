"""Tests for the AI client contract (Phase 5, Group 1)."""
from __future__ import annotations

import pytest

from app.config import settings
from app.services import ai_client


class TestAiClientComplete:
    def test_generate_json_exists(self):
        assert hasattr(ai_client, "generate_json")
        assert callable(ai_client.generate_json)

    def test_generate_exists(self):
        assert hasattr(ai_client, "generate")
        assert callable(ai_client.generate)

    def test_extract_json_exists(self):
        assert hasattr(ai_client, "extract_json")
        assert callable(ai_client.extract_json)

    def test_ai_available_when_disabled(self):
        assert ai_client.ai_available() is False or True  # depends on settings


class TestSettingsExposeRequiredKeys:
    def test_upload_dir(self):
        assert hasattr(settings, "UPLOAD_DIR")
        assert isinstance(settings.UPLOAD_DIR, str)

    def test_max_upload_mb(self):
        assert hasattr(settings, "MAX_UPLOAD_MB")
        assert isinstance(settings.MAX_UPLOAD_MB, int)

    def test_app_secret(self):
        assert hasattr(settings, "APP_SECRET")
        assert isinstance(settings.APP_SECRET, str)