import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api.security import http_bearer
from app.api import api_router
from app.config import get_settings
from app.core.memory import MemoryManager
from app.core.provider_factory import get_ai_availability
from app.core.providers import AIAvailability

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    settings = get_settings()
    settings.data_path.mkdir(parents=True, exist_ok=True)
    alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.uploads_path.mkdir(parents=True, exist_ok=True)
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    settings.data_path.mkdir(parents=True, exist_ok=True)

    run_migrations()

    ai: AIAvailability = get_ai_availability(settings)
    await ai.ping_startup()
    if not ai.models_ready:
        if settings.is_groq_mode:
            logger.warning(
                "Groq not configured at startup; AI endpoints will return 503 until GROQ_API_KEY is set"
            )
        else:
            logger.warning(
                "Ollama unreachable at startup; AI endpoints will return 503 until available"
            )

    app.state.ai_availability = ai
    app.state.ollama_availability = ai
    app.state.memory_manager = MemoryManager()

    yield

    await ai.close()


def _path_requires_bearer(path: str) -> bool:
    if path == "/api/v1/auth/me":
        return True
    if path == "/api/v1/upload":
        return True
    if path == "/api/v1/documents":
        return True
    return path.startswith("/api/v1/chat/")


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="AI Document Assistant API",
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000",
        "https://ai-document-assistant-pearl.vercel.app",
        "https://ai-document-assistant-ddjnjdzx3-spacecowboyyzs-projects.vercel.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)

    def custom_openapi():
        if application.openapi_schema:
            return application.openapi_schema

        openapi_schema = get_openapi(
            title=application.title,
            version=application.version,
            description="AI Document Assistant API",
            routes=application.routes,
        )
        openapi_schema.setdefault("components", {}).setdefault(
            "securitySchemes",
            {},
        )["HTTPBearer"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste access token from POST /api/v1/auth/login",
        }

        for path, path_item in openapi_schema.get("paths", {}).items():
            if not _path_requires_bearer(path):
                continue
            for method, operation in path_item.items():
                if method in ("get", "post", "put", "delete", "patch", "options", "head"):
                    if isinstance(operation, dict):
                        operation["security"] = [{"HTTPBearer": []}]

        application.openapi_schema = openapi_schema
        return application.openapi_schema

    application.openapi = custom_openapi
    return application


app = create_app()
