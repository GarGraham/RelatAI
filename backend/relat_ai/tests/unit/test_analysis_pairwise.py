"""Tests for the pairwise analysis engine."""

from __future__ import annotations

import pandas as pd
import pytest

from relat_ai.services.analysis.pairwise import (
    PairwiseAnalysisPlan,
    compute_pairwise_correlations,
)
from relat_ai.utils.caching import InMemoryCache


def test_compute_pairwise_correlations_produces_expected_methods() -> None:
    """Default plan should evaluate numeric, categorical, and mixed statistics."""

    frame = pd.DataFrame(
        {
            "x": [1, 2, 3, 4, 5, 6],
            "y": [2, 4, 1, 8, 0, 12],
            "category": ["a", "a", "b", "b", "c", "c"],
            "binary": ["yes", "no", "yes", "no", "yes", "no"],
            "group": ["g1", "g2", "g1", "g2", "g1", "g2"],
        }
    )

    plan = PairwiseAnalysisPlan(
        numeric_numeric=("pearson", "spearman"),
        numeric_categorical=("anova", "point_biserial"),
        categorical_categorical=("chi_square", "cramers_v"),
    )

    result = compute_pairwise_correlations(
        frame,
        columns=["x", "y", "category", "binary"],
        plan=plan,
    )

    observed = {
        (tuple(sorted(record.variables)), record.method) for record in result.correlations
    }

    assert (("x", "y"), "pearson") in observed
    assert (("x", "y"), "spearman") in observed
    assert (("binary", "x"), "anova") in observed
    assert (("binary", "x"), "point_biserial") in observed
    assert (("binary", "category"), "chi_square") in observed
    assert (("binary", "category"), "cramers_v") in observed

    cramers = next(
        record for record in result.correlations if record.method == "cramers_v"
    )
    assert 0.0 <= cramers.coefficient <= 1.0
    assert cramers.extras is not None
    assert cramers.extras.chi_square is not None


def test_compute_pairwise_correlations_missing_column_raises() -> None:
    """Requests for unknown columns should surface a clear error."""

    frame = pd.DataFrame({"x": [1, 2, 3], "y": [2, 4, 6]})

    with pytest.raises(ValueError, match="Columns not found"):
        compute_pairwise_correlations(frame, columns=["x", "z"])


def test_pairwise_cache_key_distinguishes_column_subsets() -> None:
    """Caching should return the correct subset of correlations for repeated requests."""

    frame = pd.DataFrame(
        {
            "a": [1, 2, 3, 4],
            "b": [2, 3, 4, 5],
            "c": [4, 5, 6, 7],
        }
    )

    cache = InMemoryCache()
    first = compute_pairwise_correlations(
        frame,
        columns=["a", "b", "c"],
        dataset_id="demo",
        cache=cache,
    )
    assert any(record.variables == ("a", "b") for record in first.correlations)

    second = compute_pairwise_correlations(
        frame,
        columns=["a", "b"],
        dataset_id="demo",
        cache=cache,
    )
    observed_pairs = {record.variables for record in second.correlations}
    assert observed_pairs == {("a", "b")}
