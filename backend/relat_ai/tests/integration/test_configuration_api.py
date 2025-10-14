"""Integration tests for the configuration management API."""

from __future__ import annotations

from io import BytesIO

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient


def _upload_dataset(client: TestClient) -> str:
    csv_bytes = b"Region,Value\nEurope,1\nAsia,2\nEurope,3\n"
    response = client.post(
        "/datasets/upload",
        files={"file": ("config.csv", BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 201
    return response.json()["metadata"]["dataset_id"]


def test_configuration_defaults_after_upload(client: TestClient) -> None:
    dataset_id = _upload_dataset(client)

    response = client.get(f"/datasets/{dataset_id}/configuration")
    assert response.status_code == 200
    payload = response.json()

    assert payload["selected_columns"] == ["Region", "Value"]
    assert payload["analysis_mode"] == "correlation"


def test_configuration_update_and_preview(client: TestClient) -> None:
    dataset_id = _upload_dataset(client)

    update_response = client.patch(
        f"/datasets/{dataset_id}/configuration",
        json={"filters": {"Region": ["Europe"]}, "selected_columns": ["Region", "Value"]},
    )
    assert update_response.status_code == 200

    preview = client.get(
        f"/datasets/{dataset_id}/configuration/preview",
        params={"limit": 5},
    )
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["row_count"] == 2
    assert preview_payload["columns"] == ["Region", "Value"]
    assert all(row["Region"] == "Europe" for row in preview_payload["preview"])


def test_configuration_template_round_trip(client: TestClient) -> None:
    dataset_id = _upload_dataset(client)

    client.patch(
        f"/datasets/{dataset_id}/configuration",
        json={
            "selected_columns": ["Region"],
            "anchor_columns": ["Region"],
            "filters": {"Region": ["Europe"]},
            "max_variables": 1,
        },
    )

    create_response = client.post(
        f"/datasets/{dataset_id}/templates",
        json={"name": "eu-template", "description": "Region filter"},
    )
    assert create_response.status_code == 201
    template_id = create_response.json()["template_id"]

    # Change configuration to demonstrate template application restores previous settings.
    client.patch(
        f"/datasets/{dataset_id}/configuration",
        json={"selected_columns": ["Value"], "filters": {}},
    )

    apply_response = client.post(
        f"/datasets/{dataset_id}/templates/{template_id}/apply"
    )
    assert apply_response.status_code == 200
    applied = apply_response.json()
    assert applied["selected_columns"] == ["Region"]
    assert applied["filters"] == {"Region": ["Europe"]}

    templates_list = client.get(f"/datasets/{dataset_id}/templates")
    assert templates_list.status_code == 200
    assert len(templates_list.json()) == 1


def test_configuration_update_rejects_unknown_column(client: TestClient) -> None:
    dataset_id = _upload_dataset(client)

    response = client.patch(
        f"/datasets/{dataset_id}/configuration",
        json={"selected_columns": ["missing"]},
    )
    assert response.status_code == 422
