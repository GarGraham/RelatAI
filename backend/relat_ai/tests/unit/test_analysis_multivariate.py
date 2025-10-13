"""Tests for multivariate analysis utilities."""

from __future__ import annotations

import pandas as pd

from relat_ai.services.analysis.multivariate import (
    ANOVAConfig,
    PartialCorrelationRequest,
    RegressionPlan,
    build_multivariate_models,
)


def test_regression_plan_honors_anchor_and_max_predictors() -> None:
    """Regression plan should expand to combinations respecting anchors and limits."""

    plan = RegressionPlan(
        response="y",
        candidate_predictors=["x1", "x2", "x3"],
        anchor_predictors=["x1"],
        max_predictors=2,
    )

    configs = plan.build_configs()
    predictor_sets = {tuple(config.predictors) for config in configs}

    assert ("x1",) in predictor_sets
    assert ("x1", "x2") in predictor_sets
    assert ("x1", "x3") in predictor_sets
    assert all(len(predictors) <= 2 for predictors in predictor_sets)


def test_multivariate_pipeline_runs_regression_anova_and_partial() -> None:
    """Multivariate pipeline should aggregate regression, ANOVA, and partial correlations."""

    frame = pd.DataFrame(
        {
            "y": [10, 12, 13, 15, 16, 18, 19, 21],
            "x1": [1, 2, 3, 4, 5, 6, 7, 8],
            "x2": [2, 1, 2, 3, 3, 4, 4, 5],
            "segment": ["A", "A", "B", "B", "A", "A", "B", "B"],
        }
    )

    regression_plan = RegressionPlan(
        response="y",
        candidate_predictors=["x1", "x2"],
        anchor_predictors=["x1"],
        max_predictors=2,
        interaction_depth=2,
    )
    anova_configs = [ANOVAConfig(response="y", factor="segment")]
    partial_request = PartialCorrelationRequest(
        target="y",
        candidates=["x2"],
        controls=["x1"],
    )

    result = build_multivariate_models(
        frame,
        regression_plan,
        anova=anova_configs,
        partial=partial_request,
    )

    assert result.models
    assert any(model.model_type == "regression" for model in result.models)
    assert any(model.model_type == "anova" for model in result.models)
    regression = next(model for model in result.models if model.model_type == "regression")
    assert regression.metrics.r_squared is not None

    assert result.correlations
    partial = next(record for record in result.correlations if record.method == "partial_correlation")
    assert -1.0 <= partial.coefficient <= 1.0


def test_partial_correlation_skips_when_sample_size_too_small() -> None:
    """Partial correlations should be skipped instead of raising when insufficient data remains."""

    frame = pd.DataFrame(
        {
            "target": [1.0],
            "candidate": [2.0],
            "control": [3.0],
        }
    )

    request = PartialCorrelationRequest(
        target="target",
        candidates=["candidate"],
        controls=["control"],
        sample_size_limit=1,
    )

    result = build_multivariate_models(frame, None, partial=request)

    assert list(result.correlations) == []
