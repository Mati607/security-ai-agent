from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import UserPublic
from app.auth.tokens import TokenDecodeError, decode_access_token
from app.cases.store import CaseStore
from app.config import Settings


def build_get_current_user(
    store_getter: Callable[[], CaseStore],
    settings: Settings,
) -> Callable[..., UserPublic]:
    """Resolve the case store on each request so tests can swap ``_case_store`` on the app module."""

    bearer = HTTPBearer(auto_error=False)

    def get_current_user(
        *,
        creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> UserPublic:
        if creds is None or creds.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=401,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            claims = decode_access_token(creds.credentials, settings)
        except TokenDecodeError:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from None
        user = store_getter().get_user_public(claims.sub)
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    return get_current_user
