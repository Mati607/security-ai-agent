from __future__ import annotations

import time
from dataclasses import dataclass

import jwt

from app.config import Settings


class TokenDecodeError(Exception):
    """Invalid, expired, or malformed bearer token."""


@dataclass(frozen=True)
class AccessClaims:
    sub: str


def create_access_token(user_id: str, settings: Settings) -> tuple[str, int]:
    """Return (jwt, expires_in_seconds)."""

    now = int(time.time())
    ttl = max(60, settings.jwt_expire_minutes * 60)
    exp = now + ttl
    payload = {"sub": user_id, "iat": now, "exp": exp}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")
    if isinstance(token, bytes):
        token = token.decode("ascii")
    return token, ttl


def decode_access_token(token: str, settings: Settings) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as e:
        raise TokenDecodeError(str(e)) from e
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise TokenDecodeError("missing subject")
    return AccessClaims(sub=sub)
