"""Configuration management utilities for the RelatAI backend."""

from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
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
    preprocessing_missing_numeric: str = Field(
        default="median", alias="PREPROCESSING_MISSING_NUMERIC"
    )
    preprocessing_missing_categorical: str = Field(
        default="mode", alias="PREPROCESSING_MISSING_CATEGORICAL"
    )
    preprocessing_missing_constant: str = Field(
        default="Unknown", alias="PREPROCESSING_MISSING_CONSTANT"
    )
    preprocessing_outlier_strategy: str = Field(
        default="iqr_clip", alias="PREPROCESSING_OUTLIER_STRATEGY"
    )
    preprocessing_scaling_strategy: str = Field(
        default="robust", alias="PREPROCESSING_SCALING_STRATEGY"
    )

    @property
    def max_upload_size_bytes(self) -> int:
        """Return the configured upload limit in bytes."""

        return self.max_upload_size_mb * 1024 * 1024

_SETTINGS: ContextVar[Settings | None] = ContextVar("relat_ai_settings", default=None)


def get_settings() -> Settings:
    """Return the current application settings instance.

    The first caller lazily creates a :class:`Settings` object which is stored in
    a :class:`~contextvars.ContextVar`.  Tests and application bootstrapping can
    temporarily override the value using :func:`override_settings`, ensuring
    configuration does not leak across requests or worker processes.
    """

    settings = _SETTINGS.get()
    if settings is None:
        settings = Settings()
        _SETTINGS.set(settings)
    return settings


@contextmanager
def override_settings(settings: Settings):
    """Temporarily override the active application settings."""

    token = _SETTINGS.set(settings)
    try:
        yield settings
    finally:
        _SETTINGS.reset(token)


def set_settings(settings: Settings) -> None:
    """Persistently set the active application settings instance."""

    _SETTINGS.set(settings)
