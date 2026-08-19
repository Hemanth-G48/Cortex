"""Test-only auth shim (mounted only under pytest).

Production is single-user and tokenless. This router exists solely so the
legacy test suite's ``_signup`` helpers, no-body ``/api/auth/login`` boot
calls, ``/api/auth/me`` and ``/api/auth/logout`` keep working unchanged.
It is never mounted in production (see ``main.py``).

The dependency below validates the HMAC token minted by
``create_bearer_token`` so tests that exercise per-user isolation still
resolve distinct users. This is test infrastructure, not application auth.
"""

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse, UserSignup, UserLogin
from app.services.security import (
    hash_password,
    verify_password,
    create_bearer_token,
    decode_bearer_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth-test"])

_bearer = HTTPBearer(auto_error=False)

_LOGIN_WINDOW_SECONDS = 60.0
_LOGIN_MAX_FAILURES = 10
_MAX_TRACKED_CLIENTS = 10_000

_failed_logins: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _prune_failures(client_ip: str) -> None:
    now = time.time()
    dq = _failed_logins[client_ip]
    while dq and now - dq[0] > _LOGIN_WINDOW_SECONDS:
        dq.popleft()


def _check_login_lockout(client_ip: str) -> None:
    _prune_failures(client_ip)
    if len(_failed_logins[client_ip]) >= _LOGIN_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )


def _record_login_failure(client_ip: str) -> None:
    _failed_logins[client_ip].append(time.time())
    if len(_failed_logins) > _MAX_TRACKED_CLIENTS:
        _failed_logins.clear()


def _reset_login_failures(client_ip: str) -> None:
    _failed_logins[client_ip].clear()


def _current(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Test-only: resolve the user from a valid bearer token."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_bearer_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == payload["user_id"]).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
def signup(body: UserSignup, db: Session = Depends(get_db)):
    if body.role == "teacher":
        if not settings.TEACHER_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher secret required",
            )
        if body.teacher_secret != settings.TEACHER_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher secret required",
            )

    existing = None
    if body.username:
        existing = db.query(User).filter(User.username == body.username).first()
    if existing is None and body.email:
        existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered",
        )

    user = User(
        name=body.name,
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.flush()
    db.commit()
    db.refresh(user)

    token = create_bearer_token(user.id, user.role)
    return {
        "user": UserResponse.model_validate(user).model_dump(exclude_none=True),
        "token": token,
    }


@router.post("/login", response_model=dict)
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
    except Exception:
        body = {}

    # Legacy no-body login: return the first user with a fresh token.
    if not body:
        user = db.query(User).first()
        if not user:
            return {"user": None}
        token = create_bearer_token(user.id, user.role)
        return {
            "user": UserResponse.model_validate(user).model_dump(exclude_none=True),
            "token": token,
        }

    try:
        login_data = UserLogin(**body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid login payload",
        )

    client_ip = _client_ip(request)
    _check_login_lockout(client_ip)

    user = db.query(User).filter(
        (User.username == login_data.identifier) | (User.email == login_data.identifier)
    ).first()
    if user is None or not verify_password(login_data.password, user.password_hash or ""):
        _record_login_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    _reset_login_failures(client_ip)
    token = create_bearer_token(user.id, user.role)
    return {
        "user": UserResponse.model_validate(user).model_dump(exclude_none=True),
        "token": token,
    }


@router.get("/me", response_model=dict)
def me(current_user: User = Depends(_current)):
    return {"user": UserResponse.model_validate(current_user).model_dump(exclude_none=True)}


@router.post("/logout", response_model=dict)
def logout(current_user: User = Depends(_current)):
    return {"ok": True}
