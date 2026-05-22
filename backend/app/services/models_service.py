from __future__ import annotations

from app.config import Settings
from app.core.providers import OllamaAvailability
from app.schemas.models import ModelsStatusResponse


async def get_models_status(
    ollama: OllamaAvailability,
    settings: Settings,
) -> ModelsStatusResponse:
    try:
        await ollama.refresh()
    except Exception:
        pass

    snapshot = ollama.get_status_snapshot()
    return ModelsStatusResponse(
        ollama=snapshot["ollama"],
        chat_model=settings.ollama_chat_model,
        embed_model=settings.ollama_embed_model,
        models_ready=snapshot["models_ready"],
    )
