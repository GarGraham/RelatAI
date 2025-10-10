"""Unit tests for analysis utilities."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import pytest

from relat_ai.services.analysis.multivariate import (
    RegressionConfig,
    build_multivariate_models,
)
from relat_ai.services.analysis.pairwise import compute_pairwise_correlations


def _iter_columns(columns: Iterable[str]):
    """Yield columns lazily to simulate generator usage."""

    for column in columns:
        yield column


def test_compute_pairwise_correlations_accepts_generators() -> None:
    """The correlation routine should consume generator inputs only once."""

    frame = pd.DataFrame({"x": [1, 2, 3], "y": [3, 4, 5], "z": [5, 6, 7]})
    columns = _iter_columns(["x", "y", "z"])

    result = compute_pairwise_correlations(frame, columns)
    pairs = {record.variables for record in result.correlations}

    assert pairs == {("x", "y"), ("x", "z"), ("y", "z")}


def test_build_multivariate_models_skips_invalid_configs(caplog: pytest.LogCaptureFixture) -> None:
    """Configurations with missing data or singular matrices should be skipped safely."""

    frame = pd.DataFrame(
        {
            "y": [1.0, 2.0, 3.0],
            "x1": [1.0, 1.0, 1.0],  # singular when combined with intercept
            "x2": [0.0, 1.0, 2.0],
        }
    )
    configs = [
        RegressionConfig(response="y", predictors=["missing"]),
        RegressionConfig(response="y", predictors=["x1"]),
        RegressionConfig(response="y", predictors=["x2"]),
    ]

    with caplog.at_level("WARNING"):
        result = build_multivariate_models(frame, configs)

    models = list(result.models or [])
    assert len(models) == 1
    assert models[0].predictors == ["x2"]
    warnings = [record.message for record in caplog.records]
    assert any("missing columns" in message for message in warnings)
    assert any("fitting error" in message for message in warnings)
