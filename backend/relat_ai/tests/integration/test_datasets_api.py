"""Integration tests for dataset upload API endpoints."""

from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient


def test_dataset_upload_and_retrieve(client: TestClient) -> None:
    """Uploading a dataset should return metadata that can be retrieved later."""

    csv_bytes = b"feature,target\n1,2\n3,4\n"
    response = client.post(
        "/datasets/upload",
        files={"file": ("train.csv", BytesIO(csv_bytes), "text/csv")},
    )

    assert response.status_code == 201
    payload = response.json()
    dataset_id = payload["metadata"]["dataset_id"]
    assert "path" not in payload["metadata"]

    follow_up = client.get(f"/datasets/{dataset_id}")
    assert follow_up.status_code == 200
    retrieved = follow_up.json()
    assert retrieved["metadata"]["dataset_id"] == dataset_id
    assert "path" not in retrieved["metadata"]
    assert retrieved["profile"]["row_count"] == 2
