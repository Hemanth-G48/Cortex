"""OpenAI-compatible AI client (OmniRoute by default).

Wraps ``POST {AI_BASE_URL}/chat/completions`` with:
- model override + retry across ``AI_MODELS_FALLBACK``
- ``AI_ENABLED=false`` short-circuit so CI/tests never hit the network
- ``extract_json`` — robust JSON-block extraction from model output

Mirrors Shiori-v1's ``utils/ai.js`` + ``utils/gemini.js`` model-retry pattern,
adapted to a server-side FastAPI + httpx architecture.
"""
from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0


def ai_available() -> bool:
    """True when the AI provider is configured and enabled."""
    if not settings.AI_ENABLED:
        return False
    return bool(settings.AI_BASE_URL and settings.AI_MODEL)


def ai_models() -> list[str]:
    """Ordered model list: primary + fallbacks."""
    return list(settings.ai_model_list)


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
    """Send a chat-completions request and return the text, or None on failure.

    Tries ``model`` first, then falls back through ``settings.ai_model_list``.
    Returns None when AI is disabled/unreachable so callers can fall back to
    deterministic local generators.
    """
    if not ai_available():
        return None

    candidates = []
    if model:
        candidates.append(model)
    candidates.extend(ai_models())

    for name in candidates:
        try:
            payload = {
                "model": name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            resp = httpx.post(
                f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.AI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 404 and len(candidates) > 1:
                # Model retired/renamed — try the next one (Shiori pattern).
                continue
            if resp.status_code != 200:
                logger.warning("AI provider returned %s for model %s", resp.status_code, name)
                return None
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if content:
                return str(content).strip()
            return None
        except Exception as exc:  # noqa: BLE001 — network layer, all failures fall through
            logger.warning("AI request failed for model %s: %s", name, exc)
    return None


def generate_json(
    prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.7,
    model: str | None = None,
) -> object | None:
    """Call the model and parse the response as JSON. Returns None on failure."""
    text = generate(prompt, max_tokens=max_tokens, temperature=temperature, model=model)
    return extract_json(text)
