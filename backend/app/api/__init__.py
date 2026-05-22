from fastapi import APIRouter

from app.api.routes import auth, chat, documents, health, models

api_router = APIRouter()
api_router.include_router(health.router)

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth.router, prefix="/auth")
v1_router.include_router(models.router)
v1_router.include_router(documents.router)
v1_router.include_router(chat.router)
api_router.include_router(v1_router)
