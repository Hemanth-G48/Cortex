"""Configurable AI provider registry (local-first, single-user).

The application talks to a *provider abstraction* instead of a hard-coded
model endpoint. Providers are stored in a local JSON file
(``app/data/ai_providers.json`` — git-ignored) and edited through
``/api/ai/providers`` endpoints or by hand. The legacy environment
configuration (``AI_BASE_URL`` / ``AI_API_KEY`` / ``AI_MODEL``) remains the
implicit *default* provider when no JSON-configured provider is active, so
existing installs keep working with zero migration.

Supported provider types (all OpenAI-compatible except Anthropic/Google):

- ``custom``   — any OpenAI-compatible endpoint (self-hosted, proxies, gateways)
- ``openai``   — OpenAI API
- ``ollama``   — Ollama's OpenAI-compatible server (``http://localhost:11434/v1``)
- ``lmstudio`` — LM Studio (``http://localhost:1234/v1``)
- ``anthropic``— Anthropic Messages API (``/v1/messages``)
- ``google``   — Google Gemini (``:generateContent``)

Security: API keys live only in the local JSON file and are never returned by
the API (responses expose ``has_api_key`` + a masked preview), and are never
logged.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0
TEST_TIMEOUT = 8.0

# Provider types that are inherently local (run on the user's machine).
LOCAL_TYPES = ("ollama", "lmstudio")
# Known default base URLs per provider type (prefill convenience).
DEFAULT_BASE_URLS = {
    "custom": "http://localhost:11434/v1",
    "openai": "https://api.openai.com/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
    "anthropic": "https://api.anthropic.com",
    "google": "https://generativelanguage.googleapis.com",
}
# Curated model lists for providers without a public model-list endpoint.
KNOWN_MODELS = {
    "anthropic": [
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-haiku-20240307",
    ],
    "google": [
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ],
}


def _env_providers_file() -> Path:
    """Resolve the providers JSON path (env override → package data dir).

    Resolved relative to this package (``backend/app/data/ai_providers.json``)
    so the app works regardless of the CWD the server is started from.
    """
    override = (settings.AI_PROVIDERS_FILE or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "data" / "ai_providers.json"


# ---------------------------------------------------------------------------
# Config model
# ---------------------------------------------------------------------------


@dataclass
class ProviderConfig:
    id: str
    name: str
    provider_type: str  # custom | openai | ollama | lmstudio | anthropic | google
    base_url: str = ""
    api_key: str | None = None
    model: str | None = None
    models: list[str] = field(default_factory=list)
    enabled: bool = True
    is_default: bool = False

    @property
    def is_local(self) -> bool:
        """True for local runners or any base URL pointing at loopback/private hosts."""
        if self.provider_type in LOCAL_TYPES:
            return True
        host = _url_host(self.base_url or "")
        if not host:
            return False
        return _host_is_local(host)

    @property
    def api_key_preview(self) -> str | None:
        if not self.api_key:
            return None
        if len(self.api_key) <= 4:
            return "****"
        return f"{self.api_key[:3]}…{self.api_key[-4:]}"


def _url_host(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url if "://" in url else f"http://{url}")
        return (parsed.hostname or "").lower()
    except Exception:  # noqa: BLE001
        return ""


def _host_is_local(host: str) -> bool:
    if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


class AIProvider(Protocol):
    config: ProviderConfig

    def list_models(self) -> list[str]: ...
    def generate(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        model: str | None = None,
    ) -> str | None: ...
    def test_connection(self) -> dict: ...


def _client(config: ProviderConfig, timeout: float = DEFAULT_TIMEOUT) -> httpx.Client:
    return httpx.Client(base_url=config.base_url.rstrip("/") if config.base_url else "", timeout=timeout)


# ---------------------------------------------------------------------------
# OpenAI-compatible provider (custom / openai / ollama / lmstudio)
# ---------------------------------------------------------------------------


class OpenAICompatProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    def list_models(self) -> list[str]:
        """GET {base_url}/models — supported by OpenAI, Ollama, LM Studio,
        and most OpenAI-compatible gateways. Never raises: a unreachable or
        non-compliant server yields an empty list (callers degrade gracefully)."""
        if not self.config.base_url:
            return []
        try:
            with _client(self.config, timeout=TEST_TIMEOUT) as client:
                resp = client.get("/models", headers=self._headers())
                if resp.status_code != 200:
                    logger.warning("model list failed (%s): %s", resp.status_code, resp.text[:120])
                    return []
                data = resp.json()
                if isinstance(data, list):
                    return [str(m) for m in data]
                items = data.get("data") if isinstance(data, dict) else None
                if isinstance(items, list):
                    out: list[str] = []
                    for item in items:
                        name = item.get("id") if isinstance(item, dict) else item
                        if name:
                            out.append(str(name))
                    return out
                return []
        except Exception as exc:  # noqa: BLE001 — network layer, never raise
            logger.warning("model list request failed (%s): %s", self.config.name, exc)
            return []

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str | None:
        if not self.config.base_url:
            return None
        name = model or self.config.model
        if not name:
            return None
        payload = {
            "model": name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            # Some OpenAI-compatible gateways (OmniRoute) default to SSE
            # streaming; the client parses a single JSON body, so force
            # non-streamed completions.
            "stream": False,
        }
        try:
            with _client(self.config) as client:
                resp = client.post("/chat/completions", headers=self._headers(), json=payload)
                if resp.status_code != 200:
                    logger.warning(
                        "OpenAI-compatible %s returned %s for %s",
                        self.config.name, resp.status_code, name,
                    )
                    return None
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                return str(content).strip() if content else None
        except Exception as exc:  # noqa: BLE001 — network layer
            logger.warning("OpenAI-compatible request failed (%s): %s", self.config.name, exc)
            return None

    def test_connection(self) -> dict:
        start = time.monotonic()
        try:
            models = self.list_models()
            latency_ms = round((time.monotonic() - start) * 1000)
            if models:
                return {
                    "ok": True,
                    "message": f"Connected — {len(models)} models available",
                    "latency_ms": latency_ms,
                    "models": models,
                }
            # Some custom gateways don't implement /models but accept
            # completions. Do a minimal 1-token probe when the model is set.
            if self.config.model:
                text = self.generate("ping", max_tokens=1, temperature=0)
                latency_ms = round((time.monotonic() - start) * 1000)
                if text is not None:
                    return {
                        "ok": True,
                        "message": f"Connected — model '{self.config.model}' responds",
                        "latency_ms": latency_ms,
                        "models": [self.config.model],
                    }
            # Neither /models nor a completion probe answered: either the
            # server is unreachable or the base URL path is wrong.
            return {
                "ok": False,
                "message": "Connection failed — the server did not respond. Check that it is running and the base URL path is right (many local servers expect /v1).",
                "latency_ms": latency_ms,
                "models": [],
            }
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.monotonic() - start) * 1000)
            return {"ok": False, "message": f"Connection failed: {exc}", "latency_ms": latency_ms, "models": []}


# ---------------------------------------------------------------------------
# Anthropic provider
# ---------------------------------------------------------------------------


class AnthropicProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    def list_models(self) -> list[str]:
        # Anthropic has no public free model-list endpoint — curated list.
        return list(KNOWN_MODELS["anthropic"])

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str | None:
        name = model or self.config.model
        if not name:
            return None
        headers = {
            "x-api-key": self.config.api_key or "",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": name,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            with _client(self.config) as client:
                resp = client.post("/v1/messages", headers=headers, json=payload)
                if resp.status_code != 200:
                    logger.warning("Anthropic returned %s for %s", resp.status_code, name)
                    return None
                data = resp.json()
                blocks = data.get("content") or []
                text = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
                return text.strip() or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Anthropic request failed (%s): %s", self.config.name, exc)
            return None

    def test_connection(self) -> dict:
        if not self.config.api_key:
            return {"ok": False, "message": "Anthropic requires an API key.", "models": list(KNOWN_MODELS["anthropic"])}
        start = time.monotonic()
        try:
            with _client(self.config, timeout=TEST_TIMEOUT) as client:
                # A 1-token request validates the key + model without cost.
                resp = client.post(
                    "/v1/messages",
                    headers={
                        "x-api-key": self.config.api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model or KNOWN_MODELS["anthropic"][0],
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "ping"}],
                    },
                )
                latency_ms = round((time.monotonic() - start) * 1000)
                if resp.status_code in (200, 201):
                    return {"ok": True, "message": "Connected — API key valid", "latency_ms": latency_ms, "models": list(KNOWN_MODELS["anthropic"])}
                body = (resp.text or "")[:160]
                return {"ok": False, "message": f"Anthropic error {resp.status_code}: {body}", "latency_ms": latency_ms, "models": []}
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.monotonic() - start) * 1000)
            return {"ok": False, "message": f"Connection failed: {exc}", "latency_ms": latency_ms, "models": []}


# ---------------------------------------------------------------------------
# Google Gemini provider
# ---------------------------------------------------------------------------


class GoogleProvider:
    def __init__(self, config: ProviderConfig):
        self.config = config

    def list_models(self) -> list[str]:
        if not self.config.api_key:
            return list(KNOWN_MODELS["google"])
        try:
            with _client(self.config, timeout=TEST_TIMEOUT) as client:
                resp = client.get("/v1beta/models", params={"key": self.config.api_key})
                if resp.status_code == 200:
                    data = resp.json()
                    models = [
                        m.get("name", "").replace("models/", "")
                        for m in data.get("models", [])
                        if isinstance(m, dict) and m.get("name")
                    ]
                    if models:
                        return models
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google model list failed: %s", exc)
        return list(KNOWN_MODELS["google"])

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str | None:
        name = model or self.config.model
        if not name or not self.config.api_key:
            return None
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
        try:
            with _client(self.config) as client:
                resp = client.post(
                    f"/v1beta/models/{urllib.parse.quote(name)}:generateContent",
                    params={"key": self.config.api_key},
                    json=payload,
                )
                if resp.status_code != 200:
                    logger.warning("Google returned %s for %s", resp.status_code, name)
                    return None
                data = resp.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    return None
                parts = candidates[0].get("content", {}).get("parts") or []
                text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
                return text.strip() or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("Google request failed (%s): %s", self.config.name, exc)
            return None

    def test_connection(self) -> dict:
        start = time.monotonic()
        models = self.list_models()
        latency_ms = round((time.monotonic() - start) * 1000)
        if self.config.api_key and models:
            return {"ok": True, "message": f"Connected — {len(models)} models available", "latency_ms": latency_ms, "models": models}
        if not self.config.api_key:
            return {"ok": False, "message": "Google Gemini requires an API key.", "latency_ms": latency_ms, "models": models}
        return {"ok": False, "message": "Could not reach the Gemini API.", "latency_ms": latency_ms, "models": models}


def build_provider(config: ProviderConfig) -> AIProvider:
    if config.provider_type == "anthropic":
        return AnthropicProvider(config)
    if config.provider_type == "google":
        return GoogleProvider(config)
    return OpenAICompatProvider(config)


# ---------------------------------------------------------------------------
# Registry + JSON persistence
# ---------------------------------------------------------------------------


class ProviderRegistry:
    """Loads providers from JSON, exposes CRUD, and resolves the active one.

    The legacy environment configuration acts as the implicit default
    provider when no JSON provider is enabled.
    """

    def __init__(self, path: Path | None = None):
        self._path = path or _env_providers_file()
        self._lock = threading.RLock()
        self._providers: list[ProviderConfig] = []
        self._load()

    # ---- persistence ------------------------------------------------------

    def _load(self) -> None:
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                items = raw.get("providers", []) if isinstance(raw, dict) else raw
                self._providers = [self._coerce(p) for p in items if isinstance(p, dict)]
        except Exception as exc:  # noqa: BLE001 — a corrupt file must not crash the app
            logger.error("Failed to load AI providers from %s: %s", self._path, exc)
            self._providers = []

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({"providers": [self._to_dict(p) for p in self._providers]}, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save AI providers to %s: %s", self._path, exc)

    @staticmethod
    def _as_bool(value, default: bool) -> bool:
        """Lenient bool parse — hand-edited JSON may store "true"/"false" strings."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(value, (int, float)):
            return value != 0
        return default

    @staticmethod
    def _coerce(raw: dict) -> ProviderConfig:
        ptype = str(raw.get("provider_type") or "custom")
        base_url = str(raw.get("base_url") or DEFAULT_BASE_URLS.get(ptype, ""))
        if base_url and "://" not in base_url:
            base_url = f"http://{base_url}"
        return ProviderConfig(
            id=str(raw.get("id") or raw.get("name") or "provider"),
            name=str(raw.get("name") or raw.get("id") or "Provider"),
            provider_type=ptype,
            base_url=base_url,
            api_key=raw.get("api_key") or None,
            model=raw.get("model") or None,
            models=[str(m) for m in (raw.get("models") or [])],
            enabled=ProviderRegistry._as_bool(raw.get("enabled"), True),
            is_default=ProviderRegistry._as_bool(raw.get("is_default"), False),
        )

    @staticmethod
    def _to_dict(p: ProviderConfig) -> dict:
        return {
            "id": p.id,
            "name": p.name,
            "provider_type": p.provider_type,
            "base_url": p.base_url,
            "api_key": p.api_key,
            "model": p.model,
            "models": p.models,
            "enabled": p.enabled,
            "is_default": p.is_default,
        }

    # ---- query ------------------------------------------------------------

    def all(self) -> list[ProviderConfig]:
        with self._lock:
            return [ProviderConfig(**vars(p)) for p in self._providers]

    def get(self, provider_id: str) -> ProviderConfig | None:
        with self._lock:
            for p in self._providers:
                if p.id == provider_id:
                    return ProviderConfig(**vars(p))
            return None

    def active(self) -> ProviderConfig | None:
        """The default → first enabled JSON provider, else the env provider."""
        with self._lock:
            for p in self._providers:
                if p.enabled and p.is_default:
                    return ProviderConfig(**vars(p))
            for p in self._providers:
                if p.enabled:
                    return ProviderConfig(**vars(p))
        if settings.AI_ENABLED and settings.AI_BASE_URL and settings.AI_MODEL:
            return ProviderConfig(
                id="env",
                name="Environment (legacy)",
                provider_type="custom",
                base_url=settings.AI_BASE_URL,
                api_key=settings.AI_API_KEY or None,
                model=settings.AI_MODEL,
                models=settings.ai_model_list,
                enabled=True,
                is_default=True,
            )
        return None

    def active_provider(self) -> AIProvider | None:
        config = self.active()
        return build_provider(config) if config else None

    # ---- CRUD -------------------------------------------------------------

    def create(self, name: str, provider_type: str, base_url: str | None = None,
               api_key: str | None = None, model: str | None = None,
               enabled: bool = True, is_default: bool = False) -> ProviderConfig:
        with self._lock:
            provider_id = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower()).strip("-") or "provider"
            base = provider_id
            n = 2
            while any(p.id == provider_id for p in self._providers):
                provider_id = f"{base}-{n}"
                n += 1
            ptype = provider_type if provider_type in DEFAULT_BASE_URLS else "custom"
            url = (base_url or "").strip() or DEFAULT_BASE_URLS[ptype]
            if url and "://" not in url:
                url = f"http://{url}"
            config = ProviderConfig(
                id=provider_id,
                name=name.strip() or provider_id,
                provider_type=ptype,
                base_url=url,
                api_key=(api_key or "").strip() or None,
                model=(model or "").strip() or None,
                enabled=enabled,
                is_default=is_default,
            )
            if is_default:
                for p in self._providers:
                    p.is_default = False
            self._providers.append(config)
            self._save()
            return ProviderConfig(**vars(config))

    def update(self, provider_id: str, **changes) -> ProviderConfig | None:
        with self._lock:
            for p in self._providers:
                if p.id != provider_id:
                    continue
                if "name" in changes and changes["name"] is not None:
                    p.name = str(changes["name"]).strip() or p.name
                if "provider_type" in changes and changes["provider_type"]:
                    p.provider_type = changes["provider_type"]
                if "base_url" in changes and changes["base_url"] is not None:
                    url = str(changes["base_url"]).strip()
                    if url:
                        if "://" not in url:
                            url = f"http://{url}"
                        p.base_url = url
                # api_key=None means "leave unchanged" (write-only field).
                if "api_key" in changes and changes["api_key"] not in (None, ""):
                    p.api_key = str(changes["api_key"]).strip()
                if "model" in changes and changes["model"] is not None:
                    p.model = str(changes["model"]).strip() or None
                if "models" in changes and isinstance(changes["models"], list):
                    p.models = [str(m) for m in changes["models"]]
                if "enabled" in changes:
                    p.enabled = bool(changes["enabled"])
                # is_default=True asserts this provider as the single default;
                # is_default=False explicitly clears it (the edit form lets the
                # user uncheck "Use as default").
                if "is_default" in changes:
                    if changes["is_default"]:
                        for other in self._providers:
                            other.is_default = False
                        p.is_default = True
                    else:
                        p.is_default = False
                self._save()
                return ProviderConfig(**vars(p))
            return None

    def remove(self, provider_id: str) -> bool:
        with self._lock:
            before = len(self._providers)
            self._providers = [p for p in self._providers if p.id != provider_id]
            if len(self._providers) != before:
                self._save()
                return True
            return False

    def set_default(self, provider_id: str) -> ProviderConfig | None:
        return self.update(provider_id, is_default=True)

    def refresh_models(self, provider_id: str) -> ProviderConfig | None:
        """Fetch the live model list from the provider and persist it."""
        config = self.get(provider_id)
        if config is None:
            return None
        provider = build_provider(config)
        models = provider.list_models()
        if models:
            self.update(provider_id, models=models)
            if config.model is None or config.model not in models:
                self.update(provider_id, model=models[0])
        return self.get(provider_id)

    def test(self, provider_id: str) -> dict:
        config = self.get(provider_id)
        if config is None:
            return {"ok": False, "message": "Provider not found", "models": []}
        return build_provider(config).test_connection()

    # ---- generation facade ------------------------------------------------

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        model: str | None = None,
    ) -> str | None:
        config = self.active()
        if config is None:
            return None
        provider = build_provider(config)
        # Explicit model → configured model → first known model.
        candidates = [m for m in (model, config.model) if m]
        for name in candidates:
            text = provider.generate(prompt, max_tokens=max_tokens, temperature=temperature, model=name)
            if text:
                return text
        # Last resort: the legacy env fallback list — only meaningful when the
        # active provider IS the env provider (it owns those model names).
        if config.id == "env":
            for name in settings.ai_model_list:
                if name in candidates:
                    continue
                text = provider.generate(prompt, max_tokens=max_tokens, temperature=temperature, model=name)
                if text:
                    return text
        return None

    def models(self) -> list[str]:
        config = self.active()
        if config is None:
            return []
        if config.models:
            return list(config.models)
        return list(settings.ai_model_list)


# Module-level singleton — reloaded on writes so the router always sees the
# latest persisted state without re-importing.
_registry: ProviderRegistry | None = None
_registry_lock = threading.Lock()


def get_registry() -> ProviderRegistry:
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ProviderRegistry()
        return _registry


def reload_registry() -> ProviderRegistry:
    """Re-read the JSON file from disk (used after external edits / tests)."""
    global _registry
    with _registry_lock:
        _registry = ProviderRegistry()
        return _registry


def active_endpoint() -> tuple[str, str | None] | None:
    """(base_url, api_key) of the active provider when it exposes an
    OpenAI-compatible ``/embeddings`` endpoint, else None.

    Anthropic/Google use their own protocols and don't expose OpenAI-style
    embeddings — callers keep their env fallback for those. This is what
    ``services.embeddings`` uses so embeddings follow the selected provider
    instead of always hitting the legacy ``AI_BASE_URL``.
    """
    config = get_registry().active()
    if config is None or not config.base_url:
        return None
    if config.provider_type in ("anthropic", "google"):
        return None
    return config.base_url, config.api_key


def mask_config(p: ProviderConfig) -> dict:
    """Public API shape — never exposes the raw API key."""
    return {
        "id": p.id,
        "name": p.name,
        "provider_type": p.provider_type,
        "is_local": p.is_local,
        "base_url": p.base_url,
        "has_api_key": bool(p.api_key),
        "api_key_preview": p.api_key_preview,
        "model": p.model,
        "models": p.models,
        "enabled": p.enabled,
        "is_default": p.is_default,
    }
