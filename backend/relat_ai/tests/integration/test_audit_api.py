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
