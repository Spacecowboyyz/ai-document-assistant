from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import (
    create_access_token,
    create_refresh_token_value,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import Settings, get_settings
from app.models.token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse


def normalize_email(email: str) -> str:
    return email.strip().lower()


def register_user(db: Session, payload: RegisterRequest) -> UserResponse:
    email = normalize_email(payload.email)
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(user_id=user.id, email=user.email, created_at=user.created_at)


def login_user(db: Session, payload: LoginRequest) -> TokenResponse:
    email = normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found",
        )
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password incorrect",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return _issue_tokens(db, user)


def refresh_tokens(db: Session, payload: RefreshRequest) -> TokenResponse:
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token == payload.refresh_token)
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    if row.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked",
        )
    now = datetime.now(timezone.utc)
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    row.is_revoked = True
    db.commit()
    return _issue_tokens(db, user)


def get_user_response(db: Session, user_id: UUID) -> UserResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return UserResponse(user_id=user.id, email=user.email, created_at=user.created_at)


def get_user_from_access_token(db: Session, token: str) -> User:
    settings = get_settings()
    try:
        payload = decode_access_token(token, settings)
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    try:
        user_id = UUID(sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return user


def _issue_tokens(db: Session, user: User) -> TokenResponse:
    settings = get_settings()
    access_token = create_access_token(user.id, user.email, settings)
    refresh_value = create_refresh_token_value()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    db.add(
        RefreshToken(
            token=refresh_value,
            user_id=user.id,
            expires_at=expires_at,
        )
    )
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_value,
    )
