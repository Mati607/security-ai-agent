from __future__ import annotations

from pydantic import BaseModel, Field


class UserPublic(BaseModel):
    """Authenticated user surfaced to route handlers."""

    id: str
    username: str
    display_name: str | None = None


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_\-]+$")
    password: str = Field(..., min_length=8, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
