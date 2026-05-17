import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health_returns_ok(test_env):
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
        "environment": "test",
    }


@pytest.mark.asyncio
async def test_health_uses_environment_from_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_VERSION", "2.0.0")
    get_settings.cache_clear()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["environment"] == "staging"
    assert data["version"] == "2.0.0"
    assert data["status"] == "ok"

    os.environ.pop("ENVIRONMENT", None)
    os.environ.pop("APP_VERSION", None)
    get_settings.cache_clear()
