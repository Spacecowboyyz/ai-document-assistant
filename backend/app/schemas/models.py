from typing import Literal

from pydantic import BaseModel


class ModelsStatusResponse(BaseModel):
    ai_provider: Literal["ollama", "groq"] = "ollama"
    ollama: Literal["online", "offline"]
    chat_model: str
    embed_model: str
    models_ready: bool
