from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from fastapi import HTTPException
from langchain_community.chat_models import ChatOllama

from app.config import Settings
from app.core.providers import (
    BaseChatProvider,
    OllamaAvailability,
    build_ollama_unavailable_detail,
)

logger = logging.getLogger(__name__)


class OllamaChatProvider(BaseChatProvider):
    def __init__(self, settings: Settings, ollama: OllamaAvailability) -> None:
        self._settings = settings
        self._ollama = ollama
        self._llm = ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            streaming=True,
        )

    async def astream(self, messages: Any) -> AsyncGenerator[str, None]:
        await self._ollama.require_available()
        try:
            async for chunk in self._llm.astream(messages):
                content = chunk.content
                if isinstance(content, str) and content:
                    yield content
                elif content:
                    yield str(content)
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Chat streaming failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_ollama_unavailable_detail(self._settings),
            ) from exc
