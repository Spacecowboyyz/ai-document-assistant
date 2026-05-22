from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List
from urllib.parse import urljoin

import httpx
from fastapi import HTTPException

from app.config import Settings

logger = logging.getLogger(__name__)

NOMIC_EMBED_DIMENSION = 768


def build_ollama_unavailable_detail(settings: Settings) -> str:
    return (
        "Local AI models unavailable. "
        "Start Ollama with: ollama serve\n"
        "Then pull models:\n"
        f"ollama pull {settings.ollama_chat_model}\n"
        f"ollama pull {settings.ollama_embed_model}"
    )


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        ...


class BaseChatProvider(ABC):
    @abstractmethod
    async def astream(self, messages: Any) -> AsyncGenerator[str, None]:
        ...


class OllamaAvailability:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._online = False
        self._models_ready = False
        self._available_models: set[str] = set()
        self._client: httpx.AsyncClient | None = None

    @property
    def online(self) -> bool:
        return self._online

    @property
    def models_ready(self) -> bool:
        return self._models_ready

    def _tags_url(self) -> str:
        base = self._settings.ollama_base_url.rstrip("/")
        return f"{base}/api/tags"

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=5.0)
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def ping_startup(self) -> None:
        try:
            await self.refresh()
        except Exception as exc:
            logger.warning("Ollama unreachable at startup: %s", exc)
            self._online = False
            self._models_ready = False
            self._available_models = set()

    async def refresh(self) -> None:
        client = await self._get_client()
        response = await client.get(self._tags_url())
        response.raise_for_status()
        payload = response.json()
        models: set[str] = set()
        for entry in payload.get("models", []):
            name = entry.get("name", "")
            if name:
                models.add(name.split(":")[0])
                models.add(name)
        self._available_models = models
        self._online = True
        chat = self._settings.ollama_chat_model
        embed = self._settings.ollama_embed_model
        self._models_ready = self._has_model(chat) and self._has_model(embed)

    def _has_model(self, model_name: str) -> bool:
        if model_name in self._available_models:
            return True
        return any(
            name == model_name or name.startswith(f"{model_name}:")
            for name in self._available_models
        )

    def get_status_snapshot(self) -> dict[str, Any]:
        return {
            "ollama": "online" if self._online else "offline",
            "chat_model": self._settings.ollama_chat_model,
            "embed_model": self._settings.ollama_embed_model,
            "models_ready": self._models_ready,
        }

    async def require_available(self) -> None:
        try:
            await self.refresh()
        except Exception as exc:
            logger.warning("Ollama unavailable: %s", exc)
            self._online = False
            self._models_ready = False
            raise HTTPException(
                status_code=503,
                detail=build_ollama_unavailable_detail(self._settings),
            ) from exc

        if not self._online or not self._models_ready:
            logger.warning(
                "Ollama online=%s models_ready=%s available=%s",
                self._online,
                self._models_ready,
                sorted(self._available_models),
            )
            raise HTTPException(
                status_code=503,
                detail=build_ollama_unavailable_detail(self._settings),
            )
