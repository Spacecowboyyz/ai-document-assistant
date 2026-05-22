from __future__ import annotations

import asyncio
import logging
from typing import List

from fastapi import HTTPException
from langchain_community.embeddings import OllamaEmbeddings

from app.config import Settings
from app.core.providers import (
    BaseEmbeddingProvider,
    OllamaAvailability,
    build_ollama_unavailable_detail,
)

logger = logging.getLogger(__name__)


class LocalEmbeddingService(BaseEmbeddingProvider):
    def __init__(self, settings: Settings, ollama: OllamaAvailability) -> None:
        self._settings = settings
        self._ollama = ollama
        self._embeddings = OllamaEmbeddings(
            model=settings.ollama_embed_model,
            base_url=settings.ollama_base_url,
        )

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        await self._ollama.require_available()
        try:
            return await asyncio.to_thread(self._embeddings.embed_documents, texts)
        except Exception as exc:
            logger.warning("Embedding documents failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_ollama_unavailable_detail(self._settings),
            ) from exc

    async def embed_query(self, text: str) -> List[float]:
        await self._ollama.require_available()
        try:
            return await asyncio.to_thread(self._embeddings.embed_query, text)
        except Exception as exc:
            logger.warning("Embedding query failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_ollama_unavailable_detail(self._settings),
            ) from exc
