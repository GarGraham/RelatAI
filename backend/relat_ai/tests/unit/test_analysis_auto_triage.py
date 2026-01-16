"""Unit tests for the auto-triage analysis pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd

import pytest

from relat_ai.services.analysis import AutoTriageConfig, run_auto_triage
from relat_ai.services.analysis.auto_triage import SignalVector


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


class TestSignalVectorNormalize:
    """Tests for SignalVector.normalize with edge cases."""

    def test_normalize_with_nan_in_population(self) -> None:
        """Normalization should filter out NaN values from population."""
        signal_vec = SignalVector(target="test", raw_signals={"pca_loading": 0.5})
        all_signals = {
            "col1": {"pca_loading": 0.2},
            "col2": {"pca_loading": float("nan")},
            "col3": {"pca_loading": 0.8},
        }

        signal_vec.normalize(all_signals)

        # Should normalize against [0.2, 0.8], ignoring NaN
        assert signal_vec.normalized_signals["pca_loading"] > 0
        assert signal_vec.normalized_signals["pca_loading"] <= 1.0

    def test_normalize_with_inf_in_population(self) -> None:
        """Normalization should filter out Inf values from population."""
        signal_vec = SignalVector(target="test", raw_signals={"cusum_jumps": 3.0})
        all_signals = {
            "col1": {"cusum_jumps": 1.0},
            "col2": {"cusum_jumps": float("inf")},
            "col3": {"cusum_jumps": 5.0},
        }

        signal_vec.normalize(all_signals)

        # Should normalize against [1.0, 5.0], ignoring Inf
        assert signal_vec.normalized_signals["cusum_jumps"] > 0
        assert signal_vec.normalized_signals["cusum_jumps"] <= 1.0

    def test_normalize_with_nan_value(self) -> None:
        """Normalization should return 0 if the value itself is NaN."""
        signal_vec = SignalVector(target="test", raw_signals={"pca_loading": float("nan")})
        all_signals = {
            "col1": {"pca_loading": 0.2},
            "col2": {"pca_loading": 0.5},
        }

        signal_vec.normalize(all_signals)

        assert signal_vec.normalized_signals["pca_loading"] == 0.0

    def test_normalize_all_nan_population(self) -> None:
        """Normalization should return 0 if entire population is NaN/Inf."""
        signal_vec = SignalVector(target="test", raw_signals={"pca_loading": 0.5})
        all_signals = {
            "col1": {"pca_loading": float("nan")},
            "col2": {"pca_loading": float("inf")},
        }

        signal_vec.normalize(all_signals)

        assert signal_vec.normalized_signals["pca_loading"] == 0.0


class TestStrictMissingness:
    """Tests for strict_missingness config option."""

    def test_strict_missingness_false_allows_high_missing(self) -> None:
        """With strict_missingness=False, high missing data emits warnings but proceeds."""
        frame = _build_sample_frame()
        # Inject extra missing values to exceed threshold
        frame.loc[0:35, "metric_a"] = np.nan  # ~30% missing

        config = AutoTriageConfig(
            numeric_columns=["metric_a", "metric_b", "metric_c"],
            categorical_columns=["instrument", "lot"],
            datetime_column="timestamp",
            high_missing_threshold=0.2,
            strict_missingness=False,
        )

        # Should complete without raising
        result = run_auto_triage(frame, config)
        assert result.pca_components is not None

    def test_strict_missingness_true_raises_on_high_missing(self) -> None:
        """With strict_missingness=True, high missing data raises ValueError."""
        frame = _build_sample_frame()
        # Inject extra missing values to exceed threshold
        frame.loc[0:35, "metric_a"] = np.nan  # ~30% missing

        config = AutoTriageConfig(
            numeric_columns=["metric_a", "metric_b", "metric_c"],
            categorical_columns=["instrument", "lot"],
            datetime_column="timestamp",
            high_missing_threshold=0.2,
            strict_missingness=True,
        )

        with pytest.raises(ValueError, match="Data quality failure.*metric_a.*strict mode"):
            run_auto_triage(frame, config)

    def test_strict_missingness_true_passes_below_threshold(self) -> None:
        """With strict_missingness=True, data below threshold proceeds normally."""
        frame = _build_sample_frame()
        # Frame has ~7% missing (15 rows with NaN out of 120) which is below 20%

        config = AutoTriageConfig(
            numeric_columns=["metric_a", "metric_b", "metric_c"],
            categorical_columns=["instrument", "lot"],
            datetime_column="timestamp",
            high_missing_threshold=0.2,
            strict_missingness=True,
        )

        # Should complete without raising
        result = run_auto_triage(frame, config)
        assert result.pca_components is not None
