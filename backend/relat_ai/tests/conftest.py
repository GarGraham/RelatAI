"""Pytest fixtures for backend tests."""

import pytest
from fastapi.testclient import TestClient

from relat_ai.api.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """Return a FastAPI test client."""

    app = create_app()
    return TestClient(app)
