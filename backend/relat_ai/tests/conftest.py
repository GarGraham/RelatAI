"""Pytest fixtures for backend tests."""

from collections.abc import Iterator

import pytest

try:
    from fastapi.testclient import TestClient
except RuntimeError as exc:  # pragma: no cover - optional dependency guard
    TestClient = None  # type: ignore[assignment]
    _TEST_CLIENT_IMPORT_ERROR = exc
else:
    _TEST_CLIENT_IMPORT_ERROR = None

from relat_ai.api.main import create_app
from relat_ai.core.config import Settings, override_settings
from relat_ai.services.audit_trail import reset_audit_trail
from relat_ai.services.ingestion import reset_registry


@pytest.fixture(autouse=True)
def _reset_registry() -> Iterator[None]:
    """Ensure the dataset registry is cleared between tests."""

    reset_registry()
    reset_audit_trail()
    yield
    reset_registry()
    reset_audit_trail()


@pytest.fixture()
def settings(tmp_path) -> Settings:
    """Provide isolated application settings for tests."""

    uploads_dir = tmp_path / "uploads"
    config = Settings(
        temp_storage_path=uploads_dir,
        max_upload_size_mb=1,
        profile_sample_size=100,
        dataset_registry_state_path=uploads_dir / "registry.json",
        dataset_registry_max_items=10,
    )

    with override_settings(config):
        yield config


@pytest.fixture()
def client(settings: Settings) -> "TestClient":
    """Return a FastAPI test client configured with test settings."""

    if TestClient is None:  # pragma: no cover - optional dependency guard
        pytest.skip(f"httpx is required for API tests: {_TEST_CLIENT_IMPORT_ERROR}")

    app = create_app(settings)
    return TestClient(app)
