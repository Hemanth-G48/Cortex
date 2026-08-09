"""AI client facade — provider-agnostic, local-first.

The rest of the application talks to *this* module (``ai_available``,
``ai_models``, ``generate``, ``generate_json``, ``extract_json``). Since the
provider registry refactor, these functions resolve the active provider from
``app.services.ai_providers`` — a local JSON registry of configurable
providers (Ollama, LM Studio, OpenAI, Anthropic, Google, custom OpenAI-
compatible endpoints) with the legacy ``AI_BASE_URL``/``AI_MODEL`` env config
as the implicit default provider.

The public API is unchanged, so every existing caller keeps working:
``AI_ENABLED=false`` short-circuits to deterministic fallbacks, network
failures return ``None``, and ``extract_json`` still robustly parses model
output.
"""
from __future__ import annotations

import json
import logging
import re

from app.config import settings
from app.services import ai_providers

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0


def ai_available() -> bool:
    """True when an AI provider is configured, enabled, and reachable.

    Preserves the legacy strictness (a base URL AND a model are required, the
    same way the old env check required ``AI_BASE_URL and AI_MODEL``): an
    enabled-but-incomplete registry entry (empty base URL, or no model and no
    known models) must not report AI as available — ``generate`` would fail.
    The legacy env fallback model list only counts for the env provider, which
    always carries ``AI_MODEL`` as its configured model.
    """
    if not settings.AI_ENABLED:
        return False
    active = ai_providers.get_registry().active()
    if active is None:
        return False
    return bool(active.base_url and (active.model or active.models))


def ai_models() -> list[str]:
    """Ordered model list of the active provider (or env fallbacks)."""
    if not settings.AI_ENABLED:
        return list(settings.ai_model_list)
    return ai_providers.get_registry().models() or list(settings.ai_model_list)


def extract_json(text: str | None) -> object | None:
    """Extract a JSON value (object or array) from model output.

    Handles ```json fences, plain JSON, leading prose and trailing prose.
    Port of Shiori's ``parseJSONBlock`` with extra resilience.
    """
    if not text:
        return None

    stripped = text.strip()

    # Direct parse first (fast path).
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences.
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # First complete {...} or [...] block.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(stripped[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def generate(
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    model: str | None = None,
) -> str | None:
    """Send a request to the active provider and return text, or None on failure.

    Callers fall back to deterministic local generators when this returns
    None (AI disabled or unreachable).
    """
    if not ai_available():
        return None
    try:
        return ai_providers.get_registry().generate(
            prompt, max_tokens=max_tokens, temperature=temperature, model=model
        )
    except Exception as exc:  # noqa: BLE001 — registry must never raise
        logger.warning("AI generate failed: %s", exc)
        return None


def generate_json(
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    model: str | None = None,
) -> object | None:
    """Call the active provider and parse the response as JSON. None on failure."""
    text = generate(prompt, max_tokens=max_tokens, temperature=temperature, model=model)
    return extract_json(text)
