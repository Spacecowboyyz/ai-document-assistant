from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture
def test_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_models_status_offline(test_client, offline_ollama):
    app.state.ai_availability = offline_ollama
    app.state.ollama_availability = offline_ollama
    get_settings.cache_clear()

    async with test_client as client:
        response = await client.get("/api/v1/models/status")

    assert response.status_code == 200
    data = response.json()
    assert data["ollama"] == "offline"
    assert data["models_ready"] is False
    assert data["chat_model"] == "llama3"
    assert data["embed_model"] == "nomic-embed-text"


@pytest.mark.asyncio
async def test_models_status_online(mock_ollama_availability, monkeypatch):
    mock_ollama_availability.refresh = AsyncMock()
    mock_ollama_availability._online = True
    mock_ollama_availability._models_ready = True
    app.state.ai_availability = mock_ollama_availability
    app.state.ollama_availability = mock_ollama_availability

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/models/status")

    assert response.status_code == 200
    data = response.json()
    assert data["ollama"] == "online"
    assert data["models_ready"] is True


@pytest.mark.asyncio
async def test_health_200_when_ollama_offline(offline_ollama):
    app.state.ai_availability = offline_ollama
    app.state.ollama_availability = offline_ollama

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
