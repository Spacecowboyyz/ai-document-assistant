from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.core.groq_availability import GroqAvailability
from app.core.groq_chat import GroqChatProvider
from app.core.provider_factory import get_ai_availability, get_chat_provider, get_embedding_provider


@pytest.fixture
def groq_settings(monkeypatch, tmp_path) -> Settings:
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_key")
    monkeypatch.setenv("GROQ_CHAT_MODEL", "llama3-8b-8192")
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only-32bytes-min")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app.config import get_settings

    get_settings.cache_clear()
    return get_settings()


@pytest.mark.asyncio
async def test_groq_availability_requires_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only-32bytes-min")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    from app.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    ai = GroqAvailability(settings)
    await ai.ping_startup()
    assert ai.models_ready is False

    with pytest.raises(HTTPException) as exc:
        await ai.require_available()
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_provider_factory_groq_mode(groq_settings):
    ai = get_ai_availability(groq_settings)
    assert isinstance(ai, GroqAvailability)

    chat = get_chat_provider(groq_settings, ai)
    assert isinstance(chat, GroqChatProvider)

    embed = get_embedding_provider(groq_settings, ai)
    from app.core.sentence_embeddings import SentenceTransformerEmbedding

    assert isinstance(embed, SentenceTransformerEmbedding)


@pytest.mark.asyncio
async def test_groq_chat_streams_tokens(groq_settings):
    ai = GroqAvailability(groq_settings)
    await ai.ping_startup()

    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

    async def fake_stream():
        yield mock_chunk

    mock_create = AsyncMock(return_value=fake_stream())
    mock_client = MagicMock()
    mock_client.chat.completions.create = mock_create

    provider = GroqChatProvider(groq_settings, ai)
    with patch.object(provider, "_get_client", return_value=mock_client):
        tokens = []
        async for token in provider.astream([("human", "Hi")]):
            tokens.append(token)

    assert tokens == ["Hello"]
