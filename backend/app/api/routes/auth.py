from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    return auth_service.register_user(db, body)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return auth_service.login_user(db, body)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return auth_service.refresh_tokens(db, body)


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse(
        user_id=current_user.id,
        email=current_user.email,
        created_at=current_user.created_at,
    )
