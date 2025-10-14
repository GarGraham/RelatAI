from __future__ import annotations

from io import BytesIO

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient


def _upload_sample_dataset(client: TestClient) -> str:
    csv_bytes = b"feature_a,feature_b,category\n1,2,A\n2,3,B\n3,4,A\n4,5,B\n"
    response = client.post(
        "/datasets/upload",
        files={"file": ("sample.csv", BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["metadata"]["dataset_id"]


def test_run_correlation_analysis_and_cache_hit(client: TestClient) -> None:
    """Executing correlation analysis should succeed and populate the cache."""

    dataset_id = _upload_sample_dataset(client)

    first = client.post(f"/datasets/{dataset_id}/analyze", json={"mode": "correlation"})
    assert first.status_code == 200
    payload = first.json()
    assert payload["dataset_id"] == dataset_id
    assert payload["analysis_mode"] == "correlation"
    assert payload["cached"] is False
    assert payload["result"]["correlation_table"]["records"]

    second = client.post(f"/datasets/{dataset_id}/analyze", json={"mode": "correlation"})
    assert second.status_code == 200
    cached_payload = second.json()
    assert cached_payload["cached"] is True
    assert cached_payload["analysis_id"] == payload["analysis_id"]


def test_analysis_returns_404_for_unknown_dataset(client: TestClient) -> None:
    """Requests for unknown datasets should surface a 404 response."""

    response = client.post("/datasets/missing/analyze")
    assert response.status_code == 404


def test_analysis_validation_error_for_insufficient_columns(client: TestClient) -> None:
    """Selecting a single column for correlation should produce a validation error."""

    dataset_id = _upload_sample_dataset(client)
    response = client.post(
        f"/datasets/{dataset_id}/analyze",
        json={
            "mode": "correlation",
            "parameters": {"selected_columns": ["feature_a"]},
        },
    )
    assert response.status_code == 422
