from __future__ import annotations

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.models import TokenResponse, UserPublic, UserRegister
from app.auth.tokens import create_access_token
from app.cases.store import CaseStore, CaseStoreError
from app.config import Settings


def create_auth_router(
    store_getter: Callable[[], CaseStore],
    settings: Settings,
    current_user_dep: Callable[..., UserPublic],
) -> APIRouter:
    router = APIRouter()

    @router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
    def register(body: UserRegister) -> UserPublic:
        try:
            return store_getter().create_user(
                body.username,
                body.password,
                display_name=body.display_name,
            )
        except CaseStoreError as e:
            if "username already" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username already registered",
                ) from e
            raise HTTPException(status_code=400, detail=str(e)) from e

    @router.post("/token", response_model=TokenResponse)
    def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
        user = store_getter().authenticate_user(form.username, form.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token, ttl = create_access_token(user.id, settings)
        return TokenResponse(access_token=token, expires_in=ttl)

    @router.get("/me", response_model=UserPublic)
    def me(*, current_user: UserPublic = Depends(current_user_dep)) -> UserPublic:
        return current_user

    return router
