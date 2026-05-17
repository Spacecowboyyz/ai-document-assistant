from app.config import Settings, get_settings
from app.schemas.health import HealthResponse


def get_health_status(settings: Settings | None = None) -> HealthResponse:
    resolved = settings or get_settings()
    return HealthResponse(
        status="ok",
        version=resolved.app_version,
        environment=resolved.environment,
    )
