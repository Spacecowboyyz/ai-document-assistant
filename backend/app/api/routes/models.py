from fastapi import APIRouter, Depends

from app.api.deps import get_ai_availability, get_app_settings
from app.config import Settings
from app.core.providers import AIAvailability
from app.schemas.models import ModelsStatusResponse
from app.services import models_service

router = APIRouter(tags=["models"])


@router.get("/models/status", response_model=ModelsStatusResponse)
async def models_status(
    ai: AIAvailability = Depends(get_ai_availability),
    settings: Settings = Depends(get_app_settings),
) -> ModelsStatusResponse:
    return await models_service.get_models_status(ai, settings)
