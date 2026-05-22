from __future__ import annotations

import json
from pathlib import Path
from typing import AsyncGenerator, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config import Settings, get_settings
from app.core.providers import (
    BaseChatProvider,
    BaseEmbeddingProvider,
    NOMIC_EMBED_DIMENSION,
    OllamaAvailability,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES_DIR / "sample.pdf"


def _ensure_sample_pdf() -> Path:
    if not SAMPLE_PDF.exists():
        import subprocess
        import sys

        script = Path(__file__).resolve().parent.parent / "scripts" / "generate_sample_pdf.py"
        subprocess.run([sys.executable, str(script)], check=True)
    return SAMPLE_PDF


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    return _ensure_sample_pdf()


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def init_app_state(mock_ollama_availability):
    from app.core.memory import MemoryManager

    app = __import__("app.main", fromlist=["app"]).app
    app.state.ollama_availability = mock_ollama_availability
    app.state.memory_manager = MemoryManager()
    yield


@pytest.fixture
def mock_settings(tmp_path, monkeypatch) -> Settings:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "llama3")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    monkeypatch.setenv("CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("UPLOADS_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "50")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-pytest-only-32bytes-min")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    get_settings.cache_clear()
    from app.db.database import reset_engine

    reset_engine()
    return get_settings()


@pytest.fixture
def db_session(mock_settings, tmp_path):
    from app.db.base import Base
    from app.db.database import get_engine, reset_engine

    reset_engine()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    from app.db.database import get_session_factory

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        reset_engine()


class MockEmbeddingProvider(BaseEmbeddingProvider):
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * NOMIC_EMBED_DIMENSION for _ in texts]

    async def embed_query(self, text: str) -> List[float]:
        return [0.1] * NOMIC_EMBED_DIMENSION


class MockChatProvider(BaseChatProvider):
    async def astream(self, messages) -> AsyncGenerator[str, None]:
        for token in ["Hello", " ", "world"]:
            yield token


@pytest.fixture
def mock_embedding_service() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()


@pytest.fixture
def mock_llm_stream() -> MockChatProvider:
    return MockChatProvider()


@pytest.fixture
def mock_ollama_availability(mock_settings: Settings) -> OllamaAvailability:
    ollama = OllamaAvailability(mock_settings)
    ollama._online = True
    ollama._models_ready = True
    ollama._available_models = {
        mock_settings.ollama_chat_model,
        mock_settings.ollama_embed_model,
    }
    ollama.refresh = AsyncMock()
    ollama.ping_startup = AsyncMock()
    ollama.require_available = AsyncMock()
    return ollama


@pytest.fixture
def offline_ollama(mock_settings: Settings) -> OllamaAvailability:
    ollama = OllamaAvailability(mock_settings)
    ollama._online = False
    ollama._models_ready = False

    async def _require():
        from fastapi import HTTPException
        from app.core.providers import build_ollama_unavailable_detail

        raise HTTPException(
            status_code=503,
            detail=build_ollama_unavailable_detail(mock_settings),
        )

    ollama.refresh = AsyncMock()
    ollama.require_available = _require
    return ollama
