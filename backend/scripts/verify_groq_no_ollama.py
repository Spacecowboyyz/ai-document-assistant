"""Verify Groq mode does not call Ollama HTTP endpoints."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Configure before imports
os.environ["AI_PROVIDER"] = "groq"
os.environ["GROQ_API_KEY"] = "gsk_test_key"
os.environ["GROQ_CHAT_MODEL"] = "llama3-8b-8192"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:19999"
os.environ["CHROMA_DB_PATH"] = "./verify_data/chroma_groq_check"
os.environ["UPLOADS_DIR"] = "./verify_data/uploads_groq_check"
os.environ["DATABASE_URL"] = "sqlite:///./verify_data/groq_check.db"

from app.config import get_settings
from app.core.groq_availability import GroqAvailability
from app.core.provider_factory import get_ai_availability, get_chat_provider, get_embedding_provider


async def main() -> int:
    get_settings.cache_clear()
    settings = get_settings()

    ollama_calls: list[str] = []

    async def track_get(self, url, *args, **kwargs):
        ollama_calls.append(str(url))
        raise RuntimeError("Ollama should not be called in groq mode")

    with patch("httpx.AsyncClient.get", new=track_get):
        ai = get_ai_availability(settings)
        assert isinstance(ai, GroqAvailability)
        await ai.ping_startup()
        snapshot = ai.get_status_snapshot()
        assert snapshot["ai_provider"] == "groq"
        assert snapshot["models_ready"] is True

        chat = get_chat_provider(settings, ai)
        embed = get_embedding_provider(settings, ai)

        # Lazy-load sentence model (no Ollama)
        vectors = await embed.embed_query("hello world")
        assert len(vectors) == 384

    if ollama_calls:
        print("FAIL: Ollama HTTP calls detected:", ollama_calls)
        return 1

    print("OK: Groq mode status + embeddings without Ollama HTTP")
    print("OK: chat provider", type(chat).__name__)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
