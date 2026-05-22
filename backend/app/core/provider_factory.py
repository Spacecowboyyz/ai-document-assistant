from __future__ import annotations

from app.config import Settings
from app.core.embeddings import LocalEmbeddingService
from app.core.ollama_chat import OllamaChatProvider
from app.core.providers import BaseChatProvider, BaseEmbeddingProvider, OllamaAvailability


def get_embedding_provider(
    settings: Settings,
    ollama: OllamaAvailability,
) -> BaseEmbeddingProvider:
    return LocalEmbeddingService(settings, ollama)


def get_chat_provider(
    settings: Settings,
    ollama: OllamaAvailability,
) -> BaseChatProvider:
    return OllamaChatProvider(settings, ollama)
