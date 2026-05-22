from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import Settings, get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    user_id: UUID,
    email: str,
    settings: Settings | None = None,
) -> str:
    resolved = settings or get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=resolved.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, resolved.secret_key, algorithm=resolved.algorithm)


def decode_access_token(
    token: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    resolved = settings or get_settings()
    return jwt.decode(
        token,
        resolved.secret_key,
        algorithms=[resolved.algorithm],
    )


def create_refresh_token_value() -> str:
    return secrets.token_urlsafe(48)
