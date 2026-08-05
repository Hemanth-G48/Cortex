"""Auth router: signup, login (legacy + credential), me, logout."""

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse, UserSignup, UserLogin, EnrollmentUpdate
from app.services.security import (
    hash_password,
    verify_password,
    create_bearer_token,
    get_current_user,
    require_teacher,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Phase 87: basic brute-force protection (in-memory, per client IP)
# ---------------------------------------------------------------------------
# Only *credential* logins are counted; the legacy no-body login (used by the
# single-user boot flow and tests) is exempt so it stays frictionless. A
# successful login resets the failure budget for that IP.

_LOGIN_WINDOW_SECONDS = 60.0
_LOGIN_MAX_FAILURES = 10
# Hard cap on tracked client IPs so an IP-rotation attack cannot grow the
# in-memory table without bound. Overflowing simply drops all counts (worst
# case: a fresh failure budget).
_MAX_TRACKED_CLIENTS = 10_000

_failed_logins: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Single-process local app: `request.client.host` is sufficient. If this is
    # ever deployed behind a reverse proxy, switch to the (trusted) forwarded
    # header, otherwise every user shares one IP and 10 failures lock out all.
    return request.client.host if request.client else "unknown"


def _prune_failures(client_ip: str) -> None:
    now = time.time()
    dq = _failed_logins[client_ip]
    while dq and now - dq[0] > _LOGIN_WINDOW_SECONDS:
        dq.popleft()


def reset_login_failures() -> None:
    """Clear all tracked failure state (used by tests and ops tooling)."""
    _failed_logins.clear()


def _check_login_lockout(client_ip: str) -> None:
    """Raise 429 when the client has exhausted its failure budget."""
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

    # Only compare non-empty identifiers: comparing against NULL columns
    # (``username IS NULL``) would match every seed/legacy user and block signup.
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

    # Credential-based login: identifier is username or email.
    try:
        login_data = UserLogin(**body)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid login payload",
        )

    # Phase 87: throttle repeated failures per client IP before the lookup.
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
def me(current_user: User = Depends(get_current_user)):
    return {"user": UserResponse.model_validate(current_user).model_dump(exclude_none=True)}


@router.post("/logout", response_model=dict)
def logout(current_user: User = Depends(get_current_user)):
    return {"ok": True}


@router.put("/enrollment", response_model=dict)
def update_enrollment(
    body: EnrollmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate institution exists and is active (Institution model).
    from app.models import Institution, CurriculumCourse

    inst = db.query(Institution).filter(Institution.id == body.institution_id).first()
    if inst is None or not inst.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution {body.institution_id} not found or not active",
        )

    program = db.query(CurriculumCourse).filter(
        CurriculumCourse.id == body.program_id,
        CurriculumCourse.institution_id == body.institution_id,
        CurriculumCourse.is_active == True,  # noqa: E712
    ).first()
    if program is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Program {body.program_id} not found, not active, or does not belong to institution {body.institution_id}",
        )

    current_user.institution_id = body.institution_id
    current_user.program_id = body.program_id
    db.commit()
    db.refresh(current_user)

    return {
        "user": UserResponse.model_validate(current_user).model_dump(exclude_none=True),
    }