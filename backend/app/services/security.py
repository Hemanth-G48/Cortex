"""Security utilities kept for the pytest test shim.

Production is single-user and tokenless — routers resolve the owner via
``app.services.users.current_user`` and no request is ever rejected for
missing/invalid credentials. The bcrypt password helpers and the HMAC
bearer-token factory/decoder below exist only so the test suite's legacy
``_signup`` helpers, ``create_bearer_token`` calls and
``decode_bearer_token`` lookups keep working. They are never used by the
application itself.
"""

import base64
import hashlib
import hmac
import json
import time

from app.config import settings


# ---------------------------------------------------------------------------
# Password hashing (bcrypt) — test shim only
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    import bcrypt

    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


# ---------------------------------------------------------------------------
# Bearer token (HMAC-SHA256 signed, stateless) — test shim only
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_bearer_token(user_id: int, role: str, expires_in_seconds: int = 3600) -> str:
    payload = {"user_id": user_id, "role": role, "exp": time.time() + expires_in_seconds}
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.APP_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_b64url_encode(signature)}"


def decode_bearer_token(token: str) -> dict:
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = _b64url_decode(sig_b64)
        actual_sig = hmac.new(
            settings.APP_SECRET.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected_sig, actual_sig):
            return {}
        payload = json.loads(_b64url_decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            return {}
        return payload
    except Exception:
        return {}
