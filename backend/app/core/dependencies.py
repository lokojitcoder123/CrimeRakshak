"""FastAPI dependencies for authentication and RBAC authorization.

This is the enforcement layer:

  - ``get_current_user``     validates the bearer access token → User
  - ``get_current_active_user`` additionally requires the account be enabled
  - ``require_roles(...)``   dependency factory gating on role membership
  - ``require_permissions(...)`` dependency factory gating on permission codes

Superusers bypass role/permission checks.
"""
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.core.database import get_db
from app.models.rbac import User
from app.services import auth_service

# ``tokenUrl`` is what Swagger's "Authorize" button posts to.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    scheme_name="OAuth2PasswordBearer",
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    except JWTError:
        raise UnauthorizedError("could not validate credentials")

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("could not validate credentials")

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise UnauthorizedError("could not validate credentials")

    user = auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError("user not found")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise ForbiddenError("inactive account")
    if current_user.is_locked:
        raise ForbiddenError("account is locked")
    return current_user


def require_roles(*required: str, require_all: bool = False) -> Callable:
    """Dependency factory: caller must have (any|all of) the given roles.

    Usage::

        @router.get("/x", dependencies=[Depends(require_roles("admin"))])
    """

    def _dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.is_superuser:
            return current_user
        held = current_user.role_names
        needed = set(required)
        ok = needed.issubset(held) if require_all else bool(needed & held)
        if not ok:
            raise ForbiddenError(
                f"requires role(s): {', '.join(sorted(needed))}"
            )
        return current_user

    return _dependency


def require_permissions(*required: str, require_all: bool = True) -> Callable:
    """Dependency factory: caller must hold the given permission code(s).

    Defaults to ``require_all=True`` (must hold every listed permission).
    """

    def _dependency(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.is_superuser:
            return current_user
        held = current_user.permission_codes
        needed = set(required)
        ok = needed.issubset(held) if require_all else bool(needed & held)
        if not ok:
            raise ForbiddenError(
                f"requires permission(s): {', '.join(sorted(needed))}"
            )
        return current_user

    return _dependency


def get_client_ip(request: Request) -> str | None:
    """Best-effort client IP, honoring a single proxy hop via X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
