from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    app_version: str = "1.0.0"
    cors_origins: str = "*"
    host: str = "0.0.0.0"
    port: int = 8000

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3"
    ollama_embed_model: str = "nomic-embed-text"

    chroma_db_path: str = "./chroma_db"
    uploads_dir: str = "./uploads"
    max_upload_size_mb: int = 50

    secret_key: str = "change-this-to-a-64-char-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    database_url: str = "sqlite:///./data/app.db"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def strip_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_db_path)

    @property
    def uploads_path(self) -> Path:
        return Path(self.uploads_dir)

    @property
    def data_path(self) -> Path:
        if self.database_url.startswith("sqlite:///"):
            db_file = self.database_url.replace("sqlite:///", "", 1)
            return Path(db_file).parent
        return Path("./data")


@lru_cache
def get_settings() -> Settings:
    return Settings()
