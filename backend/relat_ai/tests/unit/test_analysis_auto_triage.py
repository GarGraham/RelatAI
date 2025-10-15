"""Unit tests for the auto-triage analysis pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd

import pytest

from relat_ai.services.analysis import AutoTriageConfig, run_auto_triage


def _build_sample_frame() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = 120
    dates = pd.date_range("2024-01-01", periods=rows, freq="D")
    metric_a = rng.normal(0, 1, size=rows)
    metric_b = np.concatenate([rng.normal(0, 1, size=60), rng.normal(5, 1, size=60)])
    metric_c = 0.5 * metric_a + rng.normal(0, 0.2, size=rows)

    frame = pd.DataFrame(
        {
            "timestamp": dates,
            "metric_a": metric_a,
            "metric_b": metric_b,
            "metric_c": metric_c,
            "instrument": ["A" if index % 2 == 0 else "B" for index in range(rows)],
            "lot": [f"L{index % 5}" for index in range(rows)],
        }
    )

    frame.loc[::15, "metric_a"] = np.nan
    frame.loc[::22, "metric_c"] = np.nan

    return frame


def test_auto_triage_pipeline_produces_expected_sections() -> None:
    frame = _build_sample_frame()
    config = AutoTriageConfig(
        numeric_columns=["metric_a", "metric_b", "metric_c"],
        categorical_columns=["instrument", "lot"],
        datetime_column="timestamp",
        kmeans_clusters=3,
        hierarchical_clusters=3,
        max_components=2,
        suspicion_top_k=3,
        random_state=7,
    )

    result = run_auto_triage(frame, config)

    assert len(result.pca_components) == 2
    assert any(component.top_contributors for component in result.pca_components)

    metric_b_changes = [
        insight
        for insight in result.change_points
        if insight.column == "metric_b"
    ]
    assert metric_b_changes, "Expected change points for metric_b"

    assert result.clusters, "Clustering insights should not be empty"
    assert result.residual_forensics, "Residual forensics should be populated"

    assert result.suspicion_rankings, "Suspicion ranking should highlight drivers"
    assert any(
        entry.target == "metric_b" and entry.target_type == "variable"
        for entry in result.suspicion_rankings
    )

    assert result.quality_flags is not None

    if result.suspicion_items:
        for item in result.suspicion_items:
            assert "timestamps" not in (item.raw_stats or {}), "PII timestamps should be removed"


def test_auto_triage_rejects_empty_dataset() -> None:
    frame = pd.DataFrame(columns=["timestamp", "metric_a", "metric_b", "metric_c"])
    config = AutoTriageConfig(
        numeric_columns=["metric_a", "metric_b", "metric_c"],
        datetime_column="timestamp",
    )

    with pytest.raises(ValueError, match="empty dataset"):
        run_auto_triage(frame, config)


def test_auto_triage_config_validates_change_point_methods() -> None:
    with pytest.raises(ValueError, match="Invalid change-point methods"):
        AutoTriageConfig(
            numeric_columns=["metric_a"],
            change_point_methods=("cusum", "invalid"),
        )
