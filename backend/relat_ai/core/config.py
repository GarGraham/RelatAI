"""Configuration management utilities for the RelatAI backend."""

from functools import lru_cache
from pathlib import Path

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")
    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")
    profile_sample_size: int = Field(default=5000, alias="PROFILE_SAMPLE_SIZE")
    temp_storage_path: Path = Field(default=Path("datasets/uploads"), alias="TEMP_STORAGE_PATH")
    cache_backend: str = Field(default="memory", alias="CACHE_BACKEND")
    dataset_registry_max_items: int | None = Field(
        default=100, alias="DATASET_REGISTRY_MAX_ITEMS"
    )
    dataset_registry_state_path: Path = Field(
        default=Path("datasets/registry.json"), alias="DATASET_REGISTRY_STATE_PATH"
    )

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the configured upload limit in bytes."""

        return self.max_upload_size_mb * 1024 * 1024

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached instance of the application settings."""

    return Settings()
