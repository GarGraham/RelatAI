"""Integration tests for audit trail API endpoints."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient


def test_audit_log_available_after_dataset_upload(client: TestClient) -> None:
    """Uploading a dataset should register an audit log retrievable via the API."""

    frame = pd.DataFrame({"num": [1.0, None, 250.0], "cat": ["a", "b", None]})
    csv_bytes = frame.to_csv(index=False).encode()

    response = client.post(
        "/datasets/upload",
        files={"file": ("audit.csv", BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 201
    dataset_id = response.json()["metadata"]["dataset_id"]

    log_response = client.get(f"/audit/{dataset_id}")
    assert log_response.status_code == 200
    log_payload = log_response.json()
    assert log_payload["dataset_id"] == dataset_id
    assert log_payload["dataset_hash"]
    assert any(action["action_type"] == "missing_imputation" for action in log_payload["actions"])

    list_response = client.get("/audit")
    assert list_response.status_code == 200
    dataset_ids = {entry["dataset_id"] for entry in list_response.json()}
    assert dataset_id in dataset_ids


def test_audit_list_pagination(client: TestClient) -> None:
    """Audit log list endpoint should support pagination parameters."""

    # Upload multiple datasets to create audit logs
    for i in range(5):
        frame = pd.DataFrame({"col": [1.0, 2.0, None]})
        csv_bytes = frame.to_csv(index=False).encode()
        response = client.post(
            "/datasets/upload",
            files={"file": (f"test_{i}.csv", BytesIO(csv_bytes), "text/csv")},
        )
        assert response.status_code == 201

    # Test default pagination (skip=0, limit=50)
    response = client.get("/audit")
    assert response.status_code == 200
    all_logs = response.json()
    assert len(all_logs) >= 5

    # Test skip parameter
    response = client.get("/audit?skip=2")
    assert response.status_code == 200
    skipped_logs = response.json()
    assert len(skipped_logs) == len(all_logs) - 2
    # Should skip first 2 (newest)
    assert skipped_logs[0]["dataset_id"] == all_logs[2]["dataset_id"]

    # Test limit parameter
    response = client.get("/audit?limit=2")
    assert response.status_code == 200
    limited_logs = response.json()
    assert len(limited_logs) == 2
    # Should return 2 newest logs
    assert limited_logs[0]["dataset_id"] == all_logs[0]["dataset_id"]
    assert limited_logs[1]["dataset_id"] == all_logs[1]["dataset_id"]

    # Test skip + limit combination
    response = client.get("/audit?skip=1&limit=2")
    assert response.status_code == 200
    paginated_logs = response.json()
    assert len(paginated_logs) == 2
    assert paginated_logs[0]["dataset_id"] == all_logs[1]["dataset_id"]
    assert paginated_logs[1]["dataset_id"] == all_logs[2]["dataset_id"]


def test_audit_list_pagination_validation(client: TestClient) -> None:
    """Audit list endpoint should validate pagination parameters."""

    # Test skip < 0 (should fail)
    response = client.get("/audit?skip=-1")
    assert response.status_code == 422  # Unprocessable Entity

    # Test limit < 1 (should fail)
    response = client.get("/audit?limit=0")
    assert response.status_code == 422

    # Test limit > 100 (should fail)
    response = client.get("/audit?limit=101")
    assert response.status_code == 422

    # Test valid boundary values
    response = client.get("/audit?skip=0&limit=1")
    assert response.status_code == 200

    response = client.get("/audit?skip=0&limit=100")
    assert response.status_code == 200
