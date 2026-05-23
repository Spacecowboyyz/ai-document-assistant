from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from app.config import Settings
from app.core.providers import build_groq_rate_limit_detail, build_groq_unavailable_detail

logger = logging.getLogger(__name__)


class GroqAvailability:
    """Production AI availability — Groq API key only (no Ollama ping)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._ready = False

    @property
    def online(self) -> bool:
        return self._ready

    @property
    def models_ready(self) -> bool:
        return self._ready

    async def ping_startup(self) -> None:
        self._ready = bool(self._settings.groq_api_key.strip())
        if not self._ready:
            logger.warning(
                "GROQ_API_KEY is not set; AI endpoints will return 503 until configured"
            )

    async def refresh(self) -> None:
        self._ready = bool(self._settings.groq_api_key.strip())

    async def close(self) -> None:
        return None

    def get_status_snapshot(self) -> dict[str, Any]:
        ready = self._ready
        return {
            "ai_provider": "groq",
            "ollama": "online" if ready else "offline",
            "chat_model": self._settings.groq_chat_model,
            "embed_model": "all-MiniLM-L6-v2",
            "models_ready": ready,
        }

    async def require_available(self) -> None:
        await self.refresh()
        if not self._ready:
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(self._settings),
            )

    @staticmethod
    def raise_rate_limited() -> None:
        raise HTTPException(
            status_code=429,
            detail=build_groq_rate_limit_detail(),
        )
