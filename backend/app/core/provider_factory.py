from __future__ import annotations

from app.config import Settings
from app.core.embeddings import LocalEmbeddingService
from app.core.ollama_chat import OllamaChatProvider
from app.core.providers import (
    AIAvailability,
    BaseChatProvider,
    BaseEmbeddingProvider,
    OllamaAvailability,
)


def get_ai_availability(settings: Settings) -> AIAvailability:
    if settings.is_groq_mode:
        from app.core.groq_availability import GroqAvailability

        return GroqAvailability(settings)
    return OllamaAvailability(settings)


def get_embedding_provider(
    settings: Settings,
    ai: AIAvailability,
) -> BaseEmbeddingProvider:
    if settings.is_groq_mode:
        from app.core.sentence_embeddings import SentenceTransformerEmbedding

        return SentenceTransformerEmbedding(settings)
    if not isinstance(ai, OllamaAvailability):
        ai = OllamaAvailability(settings)
    return LocalEmbeddingService(settings, ai)


def get_chat_provider(
    settings: Settings,
    ai: AIAvailability,
) -> BaseChatProvider:
    if settings.is_groq_mode:
        from app.core.groq_availability import GroqAvailability
        from app.core.groq_chat import GroqChatProvider

        if not isinstance(ai, GroqAvailability):
            ai = GroqAvailability(settings)
        return GroqChatProvider(settings, ai)
    if not isinstance(ai, OllamaAvailability):
        ai = OllamaAvailability(settings)
    return OllamaChatProvider(settings, ai)
