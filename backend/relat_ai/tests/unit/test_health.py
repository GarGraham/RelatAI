"""Tests for health endpoints."""

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient


def test_healthcheck_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint_exposes_metadata(client: TestClient) -> None:
    response = client.get("/config")
    payload = response.json()
    assert response.status_code == 200
    assert payload["environment"] in {"development", "production", "staging"}
    assert "max_upload_size_mb" in payload
