"""OpenAI-compatible embedding client (Second Brain Phase 2, Idea 11).

Mirrors ``ai_client.py`` for text-embedding models:
- ``POST {AI_BASE_URL}/embeddings`` using the same Bearer auth and the same
  model-fallback list as the chat client.
- ``AI_ENABLED=false`` short-circuit so CI/tests never hit the network.
- Deterministic hash-based local fallback (``local_embed``) so the whole
  Phase 2 pipeline runs offline with stable, content-derived vectors —
  identical inputs always produce identical vectors (hermetic tests).

All provider output is normalized to ``settings.EMBEDDINGS_DIM`` so the
numpy store never sees ragged dimensions (the store requires one dim).
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
from datetime import datetime, timezone

import httpx
import numpy as np

from app.config import settings
from app.models.kb.embedding import KbEmbedding
from app.services import ai_providers

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0

# Marker stored in KbEmbedding.model when the deterministic fallback produced
# the vector. Budget guards treat these as free (cost = money only for real
# provider calls), mirroring the demo-summary exemption.
LOCAL_MODEL = "local"

# Marker stored in KbEmbedding.model when the local fastembed (ONNX) model
# produced the vector. Also budget-exempt — it runs on this machine.
FASTEMBED_MODEL = "fastembed"


def _endpoint() -> tuple[str, str | None] | None:
    """(base_url, api_key) for embeddings — follows the active provider when it
    exposes an OpenAI-compatible endpoint, else falls back to the legacy env
    config (e.g. for Anthropic/Google providers without /embeddings)."""
    ep = ai_providers.active_endpoint()
    if ep:
        return ep
    if settings.AI_BASE_URL:
        return settings.AI_BASE_URL, settings.AI_API_KEY
    return None


def embed_available() -> bool:
    """True when the AI provider is configured and enabled."""
    if not settings.AI_ENABLED:
        return False
    return bool(_endpoint() and settings.EMBEDDINGS_MODEL)


def embed_models() -> list[str]:
    """Ordered model candidates: explicit override, then primary, then fallbacks."""
    candidates = []
    if settings.EMBEDDINGS_MODEL:
        candidates.append(settings.EMBEDDINGS_MODEL)
    candidates.extend(settings.ai_model_list)
    seen: set[str] = set()
    deduped: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return deduped


def embedding_hash(text: str) -> str:
    """Stable content hash for embedding de-dup / caching (Idea 11, phrase 6)."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _normalize_dim(vecs: list[list[float]], target: int | None = None) -> list[list[float]]:
    """Truncate/pad every vector to ``target`` (default EMBEDDINGS_DIM)."""
    target = target or settings.EMBEDDINGS_DIM
    out: list[list[float]] = []
    for v in vecs:
        v = list(v)
        if len(v) > target:
            v = v[:target]
        elif len(v) < target:
            v = v + [0.0] * (target - len(v))
        out.append(v)
    return out


def fastembed_available() -> bool:
    """True when the local fastembed model is selectable.

    Requires ``EMBEDDINGS_BACKEND`` to be fastembed/auto and the optional
    ``fastembed`` package to be importable (import-guarded, so tests and
    machines without it keep the hash fallback). Also warns when the
    configured ``EMBEDDINGS_DIM`` doesn't match the model's native dimension
    (cosine survives zero-padding, but storage is wasteful and the ``dim``
    column misleads).
    """
    backend = (settings.EMBEDDINGS_BACKEND or "provider").lower()
    if backend not in ("fastembed", "auto"):
        return False
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return False
    if backend == "fastembed":
        expected = fastembed_dim()
        if expected != settings.EMBEDDINGS_DIM:
            logger.warning(
                "EMBEDDINGS_DIM=%d does not match local model %s (expects %d) "
                "— vectors will be zero-padded/truncated.",
                settings.EMBEDDINGS_DIM,
                settings.EMBEDDINGS_LOCAL_MODEL,
                expected,
            )
    return True


_fastembed_model = None
_fastembed_lock = threading.Lock()
_model_warmed = False


def _preload_nvidia_libs() -> None:
    """Load the pip-shipped CUDA runtime libs so onnxruntime-gpu can use them.

    ``onnxruntime-gpu`` wheels from the NVIDIA CUDA-12 index expect the CUDA
    runtime (cublas/cudnn/cudart/curand/cufft) to be resolvable. The ``nvidia-*-cu12``
    pip packages install them under the venv; preloading with ``RTLD_GLOBAL``
    makes them visible to onnxruntime without touching ``LD_LIBRARY_PATH``.
    Best-effort: if no nvidia libs are present (CPU onnxruntime) this no-ops.
    """
    try:
        import ctypes
        import glob
        import os
        import sys

        # Find site-packages dirs on sys.path (handles lib/ and lib64/, venv
        # and base env) and locate any pip-shipped nvidia CUDA runtime libs.
        site_dirs = {
            os.path.abspath(entry)
            for entry in sys.path
            if entry and "site-packages" in entry.replace("\\", "/")
        }
        lib_dirs: list[str] = []
        for site_dir in site_dirs:
            lib_dirs.extend(
                glob.glob(os.path.join(site_dir, "nvidia", "*", "lib"))
            )
        seen: set[str] = set()
        for lib_dir in lib_dirs:
            for lib in sorted(glob.glob(os.path.join(lib_dir, "*.so*"))):
                if lib in seen:
                    continue
                seen.add(lib)
                try:
                    ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
                except Exception:  # noqa: BLE001 — best-effort per lib
                    continue
    except Exception:  # noqa: BLE001 — never break embedding on preload issues
        pass


def _get_fastembed():
    """Lazily load the shared fastembed TextEmbedding model (thread-safe).

    Uses CUDA when available (RTX 3050 + onnxruntime-gpu) with a graceful
    fallback to CPU — fastembed's provider list falls through on failure.
    Optimized for GPU with parallel processing enabled and model warmup.
    """
    global _fastembed_model, _model_warmed
    if _fastembed_model is None:
        with _fastembed_lock:
            if _fastembed_model is None:
                _preload_nvidia_libs()
                from fastembed import TextEmbedding

                _fastembed_model = TextEmbedding(
                    model_name=settings.EMBEDDINGS_LOCAL_MODEL,
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
                    # Enable parallel processing for better GPU utilization
                    n_threads=4,  # Use 4 threads for CPU preprocessing
                    batch_size=256,  # Larger batch size for GPU
                )
                # Warm up the model with a dummy call to avoid first-call latency
                try:
                    list(_fastembed_model.embed(["warmup"]))
                    _model_warmed = True
                except Exception:  # noqa: BLE001
                    pass
    return _fastembed_model


def fastembed_dim() -> int:
    """Expected embedding dimension for the configured local model.

    Currently the only supported model is BAAI/bge-small-en-v1.5 (384); the
    mapping is kept here so the config guard can warn on mismatch.
    """
    name = (settings.EMBEDDINGS_LOCAL_MODEL or "").lower()
    if "bge-small-en" in name or "minilm" in name:
        return 384
    if "bge-base-en" in name or "nomic" in name:
        return 768
    if "bge-m3" in name:
        return 1024
    return settings.EMBEDDINGS_DIM


def local_model_embed(
    texts: list[str], dim: int | None = None
) -> list[list[float]] | None:
    """Embed via the local fastembed ONNX model (never raises, no network).

    Returns ``None`` when fastembed is unavailable or the model fails, so
    callers fall through to the deterministic hash embedder.
    """
    if not texts or not fastembed_available():
        return None
    try:
        model = _get_fastembed()
        vecs = list(model.embed(texts))
        out = [list(v) for v in vecs]
        return _normalize_dim(out, dim)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully
        logger.warning("fastembed local model failed: %s", exc)
        return None


def backend_embed(
    texts: list[str],
    db=None,
    user_id: int | None = None,
    budget_check: bool = True,
    force_local: bool = False,
) -> tuple[list[list[float]], str]:
    """Embed through the active backend chain (provider → fastembed → hash).

    Returns ``(vectors, model_marker)`` where ``model_marker`` is the provider
    model name, ``FASTEMBED_MODEL``, or ``LOCAL_MODEL`` — exactly what should
    be stored in ``KbEmbedding.model``. Never returns None; the hash embedder
    is the last resort. ``budget_check=False`` (search queries) skips the
    per-day provider budget so retrieval never stalls mid-day.
    ``force_local=True`` skips the provider entirely and goes directly to
    local embedding (fastembed → hash).
    """
    backend = (settings.EMBEDDINGS_BACKEND or "provider").lower()
    model_marker = LOCAL_MODEL
    vectors: list[list[float]] | None = None

    if not force_local and backend in ("provider", "auto"):
        use_provider = embed_available() and (
            not budget_check
            or (db is not None and user_id is not None and budget_allows(db, user_id, len(texts)))
        )
        if use_provider:
            vectors = embed_texts(texts)
            if vectors is not None:
                model_marker = settings.EMBEDDINGS_MODEL or "text-embedding-3-small"

    if vectors is None and backend in ("fastembed", "auto"):
        vectors = local_model_embed(texts)
        if vectors is not None:
            model_marker = FASTEMBED_MODEL

    if vectors is None:
        vectors = local_embed(texts, dim=settings.EMBEDDINGS_DIM)
    return vectors, model_marker


def query_embed(text: str) -> list[float]:
    """Embed a single search query through the active backend chain.

    Uses the same chain as document embeddings so query vectors live in the
    same space as the stored rows (required for cosine retrieval). Never
    returns None — the hash embedder guarantees a vector.
    """
    vectors, _ = backend_embed([text], budget_check=False)
    return vectors[0]


def local_embed(texts: list[str], dim: int | None = None) -> list[list[float]]:
    """Deterministic, content-derived vectors — never raises, never hits network.

    Each whitespace token is hashed and scattered into the vector (a sparse
    random-feature map); the result is L2-normalized. Empty text still gets a
    stable (zero-length-hash) vector so downstream code can rely on a constant
    row count. ``model='local'`` in the caller marks rows as budget-exempt.
    """
    dim = dim or settings.EMBEDDINGS_DIM
    out: list[list[float]] = []
    for text in texts:
        vec = np.zeros(dim, dtype=np.float32)
        tokens = re.findall(r"\w+", (text or "").lower())
        if not tokens:
            tokens = list((text or " ")[:64].lower())
        for tok in tokens:
            h = int(hashlib.sha256(tok.encode("utf-8")).hexdigest()[:16], 16)
            idx = h % dim
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        out.append(vec.tolist())
    return out


def embed_texts(
    texts: list[str],
    model: str | None = None,
    dim: int | None = None,
) -> list[list[float]] | None:
    """Embed a batch of texts through the provider.

    Returns ``None`` when the provider is disabled/unreachable or returns a
    malformed payload — callers then fall back to ``local_embed``. Uses the
    configured ``EMBEDDINGS_BATCH_SIZE`` ceiling for a single request.
    """
    if not embed_available():
        return None
    if not texts:
        return []
    if not isinstance(texts, list):
        raise TypeError("texts must be a list of strings")

    candidates = []
    if model:
        candidates.append(model)
    candidates.extend(embed_models())

    endpoint = _endpoint()
    if endpoint is None:
        return None
    base_url, api_key = endpoint

    batch = texts[: settings.EMBEDDINGS_BATCH_SIZE]
    for name in candidates:
        try:
            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            resp = httpx.post(
                f"{base_url.rstrip('/')}/embeddings",
                headers=headers,
                json={"model": name, "input": batch},
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 404 and len(candidates) > 1:
                # Model retired/renamed — try the next one (Shiori pattern).
                continue
            if resp.status_code != 200:
                logger.warning(
                    "AI provider returned %s for model %s", resp.status_code, name
                )
                return None
            data = resp.json()
            rows = data.get("data")
            if not isinstance(rows, list) or not rows:
                logger.warning("Embedding response missing data for model %s", name)
                return None
            rows = sorted(rows, key=lambda e: e.get("index", 0))
            vecs = [e.get("embedding") for e in rows]
            if any(not isinstance(v, list) or not v for v in vecs):
                logger.warning("Embedding response missing vector for model %s", name)
                return None
            return _normalize_dim(vecs)
        except Exception as exc:  # noqa: BLE001 — network layer, all failures fall through
            logger.warning("Embedding request failed for model %s: %s", name, exc)
    return None


def get_embedding(text: str, model: str | None = None) -> list[float] | None:
    """Convenience: embed one text through the provider (or None)."""
    result = embed_texts([text], model=model)
    if result:
        return result[0]
    return None


def embedding_budget(db, user_id: int) -> dict:
    """Per-user daily embedding budget meter (cost guard, Idea 15 / phrase 5).

    Counts KbEmbedding rows created today, mirroring the ``SUMMARY_DAILY_LIMIT``
    pattern. Local-fallback rows (model='local') are excluded because they cost
    nothing — offline use must never hit the cap.
    """
    start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    count = (
        db.query(KbEmbedding)
        .filter(
            KbEmbedding.user_id == user_id,
            ~KbEmbedding.model.in_([LOCAL_MODEL, FASTEMBED_MODEL]),
            KbEmbedding.created_at >= start,
        )
        .count()
    )
    limit = settings.EMBEDDINGS_DAILY_LIMIT
    return {
        "today": count,
        "limit": limit,
        "remaining": max(0, limit - count),
    }


def budget_allows(db, user_id: int, amount: int = 1) -> bool:
    """True when ``amount`` more provider calls fit in the daily budget."""
    return embedding_budget(db, user_id)["remaining"] >= amount
