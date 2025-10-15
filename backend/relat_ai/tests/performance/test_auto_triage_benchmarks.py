from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pytest_benchmark")

from relat_ai.services.analysis.auto_triage import (
    AutoTriageConfig,
    _detect_change_points,
    _perform_clustering,
    _prepare_numeric_matrix,
    run_auto_triage,
)


def _build_benchmark_frame(rows: int = 1000) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    data = {
        "metric_a": rng.normal(0, 1, size=rows),
        "metric_b": rng.normal(5, 2, size=rows),
        "metric_c": rng.normal(-2, 1, size=rows),
    }
    return pd.DataFrame(data)


def _benchmark_config() -> AutoTriageConfig:
    return AutoTriageConfig(numeric_columns=["metric_a", "metric_b", "metric_c"], max_components=3)


def test_prepare_numeric_matrix_benchmark(benchmark) -> None:
    frame = _build_benchmark_frame()
    config = _benchmark_config()

    def run_prepare() -> None:
        _prepare_numeric_matrix(frame, config)

    benchmark(run_prepare)


def test_clustering_benchmark(benchmark) -> None:
    frame = _build_benchmark_frame()
    config = _benchmark_config()
    numeric_data, _ = _prepare_numeric_matrix(frame, config)

    def run_cluster() -> None:
        _perform_clustering(numeric_data, frame, config)

    benchmark(run_cluster)


def test_change_point_detection_benchmark(benchmark) -> None:
    frame = _build_benchmark_frame()
    config = _benchmark_config()
    numeric_data, _ = _prepare_numeric_matrix(frame, config)

    def run_change_points() -> None:
        _detect_change_points(frame, numeric_data, config)

    benchmark(run_change_points)


def test_end_to_end_auto_triage_benchmark(benchmark) -> None:
    frame = _build_benchmark_frame()
    config = _benchmark_config()

    benchmark(lambda: run_auto_triage(frame, config))
