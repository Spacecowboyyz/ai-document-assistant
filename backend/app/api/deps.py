from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.security import http_bearer
from app.config import Settings, get_settings
from app.core.memory import MemoryManager
from app.core.providers import AIAvailability
from app.db.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_from_access_token
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService

def get_app_settings() -> Settings:
    return get_settings()


def get_ai_availability(request: Request) -> AIAvailability:
    return request.app.state.ai_availability


def get_ollama(request: Request) -> AIAvailability:
    """Backward-compatible alias used by route dependencies."""
    return get_ai_availability(request)


def get_memory_manager(request: Request) -> MemoryManager:
    return request.app.state.memory_manager


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return get_user_from_access_token(db, credentials.credentials)


def get_document_service(
    request: Request,
    db: Session = Depends(get_db),
) -> DocumentService:
    settings = get_settings()
    ai = get_ai_availability(request)
    return DocumentService(settings, ai, db)


def get_chat_service(
    request: Request,
    db: Session = Depends(get_db),
) -> ChatService:
    settings = get_settings()
    ai = get_ai_availability(request)
    memory = get_memory_manager(request)
    return ChatService(settings, ai, memory, db)
