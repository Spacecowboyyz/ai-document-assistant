from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from app.config import get_settings, read_groq_api_key
from app.core.providers import build_groq_rate_limit_detail, build_groq_unavailable_detail

logger = logging.getLogger(__name__)


class GroqAvailability:
    """Production AI availability — checks GROQ_API_KEY at request time (no ping)."""

    def __init__(self, settings: Any = None) -> None:
        # settings kept for factory compatibility; key is read fresh per request
        self._settings = settings

    @staticmethod
    def has_api_key() -> bool:
        return bool(read_groq_api_key())

    @property
    def online(self) -> bool:
        return self.has_api_key()

    @property
    def models_ready(self) -> bool:
        return self.has_api_key()

    async def ping_startup(self) -> None:
        if not self.has_api_key():
            logger.warning(
                "GROQ_API_KEY is not set; AI endpoints will return 503 until configured"
            )

    async def refresh(self) -> None:
        return None

    async def close(self) -> None:
        return None

    def get_status_snapshot(self) -> dict[str, Any]:
        settings = get_settings()
        ready = self.has_api_key()
        return {
            "ai_provider": "groq",
            "ollama": "online" if ready else "offline",
            "chat_model": settings.groq_chat_model,
            "embed_model": "all-MiniLM-L6-v2",
            "models_ready": ready,
        }

    async def require_available(self) -> None:
        if not self.has_api_key():
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(get_settings()),
            )

    @staticmethod
    def raise_rate_limited() -> None:
        raise HTTPException(
            status_code=429,
            detail=build_groq_rate_limit_detail(),
        )
