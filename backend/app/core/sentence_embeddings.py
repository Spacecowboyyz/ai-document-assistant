from __future__ import annotations

import asyncio
import logging
import threading
from typing import List

from fastapi import HTTPException

from app.config import Settings
from app.core.providers import BaseEmbeddingProvider, build_groq_unavailable_detail

logger = logging.getLogger(__name__)

_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_model_lock = threading.Lock()


def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(_MODEL_NAME)


class SentenceTransformerEmbedding(BaseEmbeddingProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _ensure_model(self):
        global _model
        if _model is not None:
            return _model
        with _model_lock:
            if _model is None:
                logger.info("Loading sentence-transformers model: %s", _MODEL_NAME)
                _model = await asyncio.to_thread(_load_model)
        return _model

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = await self._ensure_model()
        try:

            def encode() -> List[List[float]]:
                vectors = model.encode(texts, convert_to_numpy=True)
                return vectors.tolist()

            return await asyncio.to_thread(encode)
        except Exception as exc:
            logger.warning("Sentence-transformer embed_documents failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(self._settings),
            ) from exc

    async def embed_query(self, text: str) -> List[float]:
        model = await self._ensure_model()
        try:

            def encode() -> List[float]:
                vector = model.encode(text, convert_to_numpy=True)
                return vector.tolist()

            return await asyncio.to_thread(encode)
        except Exception as exc:
            logger.warning("Sentence-transformer embed_query failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=build_groq_unavailable_detail(self._settings),
            ) from exc
