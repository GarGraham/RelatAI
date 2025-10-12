"""Tests for the pairwise analysis engine."""

from __future__ import annotations

import pandas as pd

from relat_ai.services.analysis.pairwise import (
    PairwiseAnalysisPlan,
    compute_pairwise_correlations,
)


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
    assert "chi_square" in cramers.extras
