from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings, get_ollama
from app.config import Settings
from app.core.providers import OllamaAvailability
from app.schemas.models import ModelsStatusResponse
from app.services import models_service

router = APIRouter(tags=["models"])


@router.get("/models/status", response_model=ModelsStatusResponse)
async def models_status(
    ollama: OllamaAvailability = Depends(get_ollama),
    settings: Settings = Depends(get_app_settings),
) -> ModelsStatusResponse:
    return await models_service.get_models_status(ollama, settings)
