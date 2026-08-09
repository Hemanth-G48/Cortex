"""Tests for the configurable AI provider registry (local-first providers).

Hermetic: all provider I/O goes through ``httpx.MockTransport``; the registry
JSON lives in a temp file so tests never touch ``app/data/``.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import httpx
import pytest

from app.services import ai_client, ai_providers


def _handler(json_response: dict, status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=json_response)
    return handler


def make_registry(tmp_path: Path, providers: list[dict] | None = None) -> ai_providers.ProviderRegistry:
    path = tmp_path / f"providers-{uuid.uuid4().hex[:8]}.json"
    reg = ai_providers.ProviderRegistry(path=path)
    for p in providers or []:
        reg.create(**p)
    return reg


# ---------------------------------------------------------------------------
# Registry + persistence
# ---------------------------------------------------------------------------


def test_create_persists_to_json(tmp_path):
    reg = make_registry(tmp_path)
    config = reg.create(
        name="Ollama", provider_type="ollama", base_url="http://localhost:11434/v1", model="llama3"
    )
    assert config.id == "ollama"
    # Reload from disk — the data survived.
    reg2 = ai_providers.ProviderRegistry(path=reg._path)
    assert [p.name for p in reg2.all()] == ["Ollama"]


def test_create_dedupes_ids_and_sanitises_base_url(tmp_path):
    reg = make_registry(tmp_path)
    reg.create(name="My Provider", provider_type="custom", base_url="localhost:1234/v1", model="m1")
    reg.create(name="My Provider", provider_type="custom", base_url="localhost:1234/v1", model="m2")
    ids = [p.id for p in reg.all()]
    assert ids == ["my-provider", "my-provider-2"]
    # base_url gets the http:// scheme when missing.
    assert reg.all()[0].base_url.startswith("http://")


def test_update_keeps_key_when_blank(tmp_path):
    reg = make_registry(tmp_path)
    reg.create(name="OpenAI", provider_type="openai", api_key="sk-secret", model="gpt-4o")
    reg.update("openai", api_key="")  # blank → unchanged
    assert reg.get("openai").api_key == "sk-secret"
    reg.update("openai", api_key="new-key")
    assert reg.get("openai").api_key == "new-key"


def test_default_and_active_resolution(tmp_path):
    reg = make_registry(tmp_path)
    reg.create(name="A", provider_type="custom", base_url="http://a/v1")
    reg.create(name="B", provider_type="custom", base_url="http://b/v1", enabled=False)
    assert reg.active().name == "A"  # first enabled
    reg.set_default("a") if reg.get("a") else None
    # only one default at a time
    reg.create(name="C", provider_type="custom", base_url="http://c/v1", is_default=True)
    defaults = [p.name for p in reg.all() if p.is_default]
    assert defaults == ["C"]


# ---------------------------------------------------------------------------
# Local vs cloud detection + masking
# ---------------------------------------------------------------------------


def test_is_local_detection(tmp_path):
    reg = make_registry(tmp_path)
    reg.create(name="Ollama", provider_type="ollama", base_url="http://localhost:11434/v1")
    reg.create(name="Cloud", provider_type="openai", base_url="https://api.openai.com/v1")
    reg.create(name="CustomLocal", provider_type="custom", base_url="http://127.0.0.1:8080/v1")
    reg.create(name="CustomRemote", provider_type="custom", base_url="https://gateway.example.com/v1")
    by_name = {p.name: p for p in reg.all()}
    assert by_name["Ollama"].is_local is True
    assert by_name["CustomLocal"].is_local is True
    assert by_name["Cloud"].is_local is False
    assert by_name["CustomRemote"].is_local is False


def test_mask_config_never_exposes_key(tmp_path):
    reg = make_registry(tmp_path)
    reg.create(name="OpenAI", provider_type="openai", api_key="sk-abcdef123456", model="gpt-4o")
    masked = ai_providers.mask_config(reg.get("openai"))
    assert masked["has_api_key"] is True
    assert masked["api_key_preview"] == "sk-…3456"
    assert "sk-abcdef123456" not in json.dumps(masked)


# ---------------------------------------------------------------------------
# Provider implementations (MockTransport)
# ---------------------------------------------------------------------------


def mock_client(monkeypatch, handler):
    """Point the module-level ``_client`` at a MockTransport for this test."""
    def _client(cfg, timeout=ai_providers.DEFAULT_TIMEOUT):
        return httpx.Client(base_url=cfg.base_url.rstrip("/"), timeout=timeout, transport=httpx.MockTransport(handler))
    monkeypatch.setattr(ai_providers, "_client", _client)


def test_openai_compat_list_models(tmp_path, monkeypatch):
    reg = make_registry(tmp_path)
    reg.create(name="LM Studio", provider_type="lmstudio", base_url="http://localhost:1234/v1")
    config = reg.get("lm-studio")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/models")
        return httpx.Response(200, json={"data": [{"id": "local-model"}, {"id": "qwen2.5"}]})

    mock_client(monkeypatch, handler)
    assert ai_providers.build_provider(config).list_models() == ["local-model", "qwen2.5"]


def test_openai_compat_generate(tmp_path, monkeypatch):
    reg = make_registry(tmp_path)
    reg.create(name="Custom", provider_type="custom", base_url="http://localhost:11434/v1", model="llama3")
    config = reg.get("custom")

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "llama3"
        assert str(request.url).endswith("/chat/completions")
        return httpx.Response(200, json={"choices": [{"message": {"content": "hi from llama3"}}]})

    mock_client(monkeypatch, handler)
    text = ai_providers.build_provider(config).generate("hello")
    assert text == "hi from llama3"


def test_anthropic_generate_uses_messages_api(tmp_path, monkeypatch):
    reg = make_registry(tmp_path)
    reg.create(name="Anthropic", provider_type="anthropic", api_key="sk-ant-x", model="claude-3-5-sonnet-20241022")
    config = reg.get("anthropic")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).endswith("/v1/messages")
        assert request.headers.get("x-api-key") == "sk-ant-x"
        body = json.loads(request.content)
        assert body["model"] == "claude-3-5-sonnet-20241022"
        return httpx.Response(200, json={"content": [{"type": "text", "text": "claude says hi"}]})

    mock_client(monkeypatch, handler)
    text = ai_providers.build_provider(config).generate("hello")
    assert text == "claude says hi"


def test_google_generate_uses_generatecontent(tmp_path, monkeypatch):
    reg = make_registry(tmp_path)
    reg.create(name="Google", provider_type="google", api_key="g-key", model="gemini-2.5-flash")
    config = reg.get("google")

    def handler(request: httpx.Request) -> httpx.Response:
        assert ":generateContent" in str(request.url)
        assert request.url.params.get("key") == "g-key"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "gemini here"}]}}]})

    mock_client(monkeypatch, handler)
    text = ai_providers.build_provider(config).generate("hello")
    assert text == "gemini here"


# ---------------------------------------------------------------------------
# Connection testing
# ---------------------------------------------------------------------------


def test_test_connection_success_lists_models(tmp_path, monkeypatch):
    reg = make_registry(tmp_path)
    reg.create(name="Ollama", provider_type="ollama", base_url="http://localhost:11434/v1")
    config = reg.get("ollama")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "llama3"}, {"id": "qwen"}]})

    mock_client(monkeypatch, handler)
    result = reg.test("ollama")
    assert result["ok"] is True
    assert result["models"] == ["llama3", "qwen"]


def test_test_connection_failure(tmp_path, monkeypatch):
    reg = make_registry(tmp_path)
    reg.create(name="Dead", provider_type="custom", base_url="http://localhost:9999/v1", model="x")
    config = reg.get("dead")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    mock_client(monkeypatch, handler)
    result = reg.test("dead")
    assert result["ok"] is False
    assert "Connection failed" in result["message"]


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


def test_providers_api_crud(client, tmp_path, monkeypatch):
    path = tmp_path / "api-providers.json"
    reg = ai_providers.ProviderRegistry(path=path)
    monkeypatch.setattr(ai_providers, "get_registry", lambda: reg)

    # Create
    r = client.post("/api/ai/providers", json={"name": "Ollama", "provider_type": "ollama", "model": "llama3"})
    assert r.status_code == 201
    created = r.json()
    assert created["id"] == "ollama"
    assert created["is_local"] is True
    assert "api_key" not in created  # never raw

    # List
    listed = client.get("/api/ai/providers").json()
    assert listed["active_id"] == "ollama"
    assert len(listed["providers"]) == 1

    # Test connection (mock)
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "llama3"}]})

    mock_client(monkeypatch, handler)
    t = client.post("/api/ai/providers/ollama/test").json()
    assert t["ok"] is True

    # Refresh models
    rm = client.post("/api/ai/providers/ollama/refresh-models").json()
    assert rm["models"] == ["llama3"]

    # Update
    up = client.put("/api/ai/providers/ollama", json={"model": "qwen2.5"}).json()
    assert up["model"] == "qwen2.5"

    # Set default + delete
    client.post("/api/ai/providers/ollama/default")
    d = client.delete("/api/ai/providers/ollama").json()
    assert d["ok"] is True
    assert len(client.get("/api/ai/providers").json()["providers"]) == 0


def test_providers_api_404(client, tmp_path, monkeypatch):
    path = tmp_path / "api-providers.json"
    reg = ai_providers.ProviderRegistry(path=path)
    monkeypatch.setattr(ai_providers, "get_registry", lambda: reg)
    assert client.delete("/api/ai/providers/nope").status_code == 404
    assert client.put("/api/ai/providers/nope", json={}).status_code == 404


def test_health_reports_active_provider(client, tmp_path, monkeypatch):
    path = tmp_path / "api-providers.json"
    reg = ai_providers.ProviderRegistry(path=path)
    reg.create(name="LM Studio", provider_type="lmstudio", base_url="http://localhost:1234/v1", model="local-model")
    monkeypatch.setattr(ai_providers, "get_registry", lambda: reg)

    health = client.get("/api/ai/health").json()
    assert health["active_provider"]["id"] == "lm-studio"
    assert health["active_provider"]["is_local"] is True
    assert health["model"] == "local-model"
    assert health["providers_count"] == 1

    models = client.get("/api/ai/models").json()
    assert models["active_provider"]["id"] == "lm-studio"
    assert len(models["providers"]) == 1


# ---------------------------------------------------------------------------
# Reviewer-fix regressions: graceful refresh, default unset, strict
# availability, embeddings endpoint routing, robust bool parsing
# ---------------------------------------------------------------------------


def test_refresh_models_never_raises_on_unreachable(tmp_path, monkeypatch):
    """list_models must swallow network errors (was an unhandled 500 crash)."""
    reg = make_registry(tmp_path)
    reg.create(name="Dead", provider_type="custom", base_url="http://localhost:9999/v1", model="x")

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    mock_client(monkeypatch, handler)
    config = reg.refresh_models("dead")  # must not raise
    assert config is not None
    assert config.models == []  # unchanged, graceful empty


def test_update_can_explicitly_unset_default(tmp_path):
    reg = make_registry(tmp_path)
    reg.create(name="A", provider_type="custom", base_url="http://a/v1", model="m", is_default=True)
    reg.create(name="B", provider_type="custom", base_url="http://b/v1", model="m")
    assert reg.get("a").is_default is True

    # Explicitly clear the default flag on A (edit-form uncheck behavior).
    reg.update("a", is_default=False)
    assert reg.get("a").is_default is False
    # With no default, the first enabled provider becomes active.
    assert reg.active().name == "A"


def test_ai_available_requires_base_url_and_model(tmp_path, monkeypatch):
    """Enabled-but-incomplete providers must not report AI as available."""
    path = tmp_path / "avail.json"
    reg = ai_providers.ProviderRegistry(path=path)
    monkeypatch.setattr(ai_providers, "get_registry", lambda: reg)

    # No providers → env legacy config decides (defaults on in tests are
    # AI_ENABLED=True with a configured AI_MODEL, so available).
    # First: simulate a JSON provider being active with no base URL.
    reg.create(name="Incomplete", provider_type="custom", base_url="", model="m")
    # create() fills the default base URL when blank — simulate a hand-edited
    # file with empty base_url by coercing directly.
    reg._providers[0].base_url = ""
    reg._providers[0].is_default = True
    assert ai_client.ai_available() is False

    reg._providers[0].base_url = "http://localhost:11434/v1"
    reg._providers[0].model = None
    assert ai_client.ai_available() is False  # no model → still unavailable

    reg._providers[0].model = "llama3"
    assert ai_client.ai_available() is True


def test_active_endpoint_routes_embeddings_through_provider(tmp_path):
    """Embeddings resolve the active provider's base URL + key."""
    reg = make_registry(tmp_path)
    reg.create(
        name="Ollama", provider_type="ollama",
        base_url="http://localhost:11434/v1", model="llama3",
    )
    # Patch the singleton used by active_endpoint.
    ai_providers._registry = reg
    try:
        assert ai_providers.active_endpoint() == ("http://localhost:11434/v1", None)
    finally:
        ai_providers._registry = None

    # Anthropic/Google don't expose OpenAI-compatible embeddings → None.
    reg2 = make_registry(tmp_path)
    reg2.create(name="Anthropic", provider_type="anthropic", api_key="sk-x", model="claude")
    ai_providers._registry = reg2
    try:
        assert ai_providers.active_endpoint() is None
    finally:
        ai_providers._registry = None


def test_coerce_handles_string_bools(tmp_path):
    """Hand-edited JSON with "true"/"false" strings must parse correctly."""
    path = tmp_path / "bools.json"
    path.write_text(
        json.dumps({
            "providers": [
                {"id": "p", "name": "P", "provider_type": "custom", "enabled": "true", "is_default": "false"}
            ]
        })
    )
    reg = ai_providers.ProviderRegistry(path=path)
    p = reg.get("p")
    assert p.enabled is True
    assert p.is_default is False
