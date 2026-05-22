from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api.security import http_bearer
from app.config import Settings, get_settings
from app.core.memory import MemoryManager
from app.core.providers import OllamaAvailability
from app.db.database import get_db
from app.models.user import User
from app.services.auth_service import get_user_from_access_token
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService

def get_app_settings() -> Settings:
    return get_settings()


def get_ollama(request: Request) -> OllamaAvailability:
    return request.app.state.ollama_availability


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
    ollama = get_ollama(request)
    return DocumentService(settings, ollama, db)


def get_chat_service(
    request: Request,
    db: Session = Depends(get_db),
) -> ChatService:
    settings = get_settings()
    ollama = get_ollama(request)
    memory = get_memory_manager(request)
    return ChatService(settings, ollama, memory, db)
