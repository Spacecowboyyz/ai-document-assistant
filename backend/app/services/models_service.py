from __future__ import annotations

from app.config import Settings
from app.core.providers import AIAvailability
from app.schemas.models import ModelsStatusResponse


async def get_models_status(
    ai: AIAvailability,
    settings: Settings,
) -> ModelsStatusResponse:
    try:
        await ai.refresh()
    except Exception:
        pass

    snapshot = ai.get_status_snapshot()
    return ModelsStatusResponse(
        ai_provider=snapshot.get("ai_provider", settings.ai_provider),
        ollama=snapshot["ollama"],
        chat_model=snapshot["chat_model"],
        embed_model=snapshot["embed_model"],
        models_ready=snapshot["models_ready"],
    )
