"""Tests for schema detection heuristics."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from relat_ai.services import schema_detection


def test_profile_frame_infers_column_types():
    """Profile generation should infer logical types and dataset stats."""

    frame = pd.DataFrame(
        {
            "numeric": [1, 2, 3, 4],
            "category": ["A", "A", "B", "B"],
            "boolean": [True, False, True, False],
            "timestamp": pd.to_datetime(
                [
                    datetime(2024, 1, 1),
                    datetime(2024, 1, 2),
                    datetime(2024, 1, 3),
                    datetime(2024, 1, 4),
                ],
                utc=True,
            ),
            "text": ["short", "a" * 200, "b" * 210, "c" * 190],
        }
    )

    profile = schema_detection.profile_frame(
        frame,
        dataset_id="test-id",
        dataset_name="demo.csv",
        sample_size=2,
    )

    assert profile.dataset_id == "test-id"
    assert profile.name == "demo.csv"
    assert profile.row_count == 4
    assert profile.missing_cell_count == 0

    columns = {column.name: column for column in profile.columns}
    assert columns["numeric"].logical_type == "numeric"
    assert columns["category"].logical_type == "categorical"
    assert columns["boolean"].stats["true"] == 2
    assert columns["timestamp"].logical_type == "datetime"
    assert columns["text"].logical_type == "text"


def test_to_model_serializes_profile():
    """Profiles should convert to pydantic models for API responses."""

    frame = pd.DataFrame({"value": [1, 2, 3]})
    profile = schema_detection.profile_frame(
        frame,
        dataset_id="abc",
        dataset_name="values.csv",
        sample_size=None,
    )

    model = schema_detection.to_model(profile)

    assert model.dataset_id == "abc"
    assert model.name == "values.csv"
    assert model.row_count == 3
    assert model.columns[0].stats["min"] == 1.0
