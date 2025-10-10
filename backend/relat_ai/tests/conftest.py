"""Pytest fixtures for backend tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from relat_ai.api.main import create_app
from relat_ai.core.config import Settings
from relat_ai.services.ingestion import reset_registry


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    """Ensure the dataset registry is cleared between tests."""

    reset_registry()
    yield
    reset_registry()


@pytest.fixture()
def settings(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Provide isolated application settings for tests."""

    uploads_dir = tmp_path / "uploads"
    config = Settings(
        temp_storage_path=uploads_dir,
        max_upload_size_mb=1,
        profile_sample_size=100,
    )

    monkeypatch.setattr("relat_ai.core.config.get_settings", lambda: config)
    return config


@pytest.fixture()
def client(settings: Settings) -> TestClient:
    """Return a FastAPI test client configured with test settings."""

    app = create_app(settings)
    return TestClient(app)
