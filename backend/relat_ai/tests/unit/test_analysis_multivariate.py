"""Tests for multivariate analysis utilities."""

from __future__ import annotations

import math

import pandas as pd

from relat_ai.services.analysis.multivariate import (
    ANOVAConfig,
    PartialCorrelationRequest,
    RegressionPlan,
    _augment_interactions,
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


def test_regression_metrics_include_effect_size_and_vif() -> None:
    """Regression models should expose effect sizes and VIF diagnostics."""

    frame = pd.DataFrame(
        {
            "y": [5.1, 7.3, 8.9, 11.4, 13.1, 14.8],
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "x2": [2.0, 2.4, 3.4, 4.5, 5.4, 6.3],
        }
    )

    plan = RegressionPlan(
        response="y",
        candidate_predictors=["x1", "x2"],
        max_predictors=2,
        interaction_depth=2,
        max_interactions=1,
    )

    result = build_multivariate_models(frame, plan)

    regression = next(
        model
        for model in result.models
        if model.model_type == "regression" and set(model.predictors) == {"x1", "x2"}
    )
    assert regression.metrics.cohen_f2 is not None
    assert regression.diagnostics is not None
    vif = regression.diagnostics.variance_inflation_factors
    assert {"x1", "x2"}.issubset(vif)
    assert all(value >= 1.0 for value in vif.values())


def test_pls_regression_generates_summary() -> None:
    """PLS regression requests should return metrics with adjusted R² computed."""

    frame = pd.DataFrame(
        {
            "y": [10.0, 11.0, 13.0, 14.0, 16.0, 18.0, 19.0, 21.0],
            "x1": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
            "x2": [1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2, 2.4],
            "x3": [2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7],
        }
    )

    plan = RegressionPlan(
        response="y",
        candidate_predictors=["x1", "x2", "x3"],
        max_predictors=3,
        solver="pls",
        pls_components=2,
    )

    result = build_multivariate_models(frame, plan)

    regression = next(
        model
        for model in result.models
        if model.model_type == "regression_pls" and set(model.predictors) == {"x1", "x2", "x3"}
    )
    assert regression.metrics.r_squared > 0
    assert regression.metrics.cohen_f2 is not None
    assert not math.isnan(regression.metrics.adjusted_r_squared)
    assert regression.diagnostics is not None
    assert regression.notes == ["n_components=2"]


def test_anova_effect_size_present() -> None:
    """ANOVA summaries should include partial eta squared effect sizes."""

    frame = pd.DataFrame(
        {
            "y": [10, 12, 13, 15, 16, 18, 19, 21],
            "segment": ["A", "A", "B", "B", "A", "A", "B", "B"],
        }
    )

    configs = [ANOVAConfig(response="y", factor="segment")]
    result = build_multivariate_models(frame, None, anova=configs)

    anova = next(model for model in result.models if model.model_type == "anova")
    assert anova.metrics.effect_size is not None


def test_augment_interactions_respects_max_terms() -> None:
    """Interaction helper should honor the configured maximum number of generated terms."""

    predictors = pd.DataFrame(
        {
            "x1": [1.0, 2.0, 3.0],
            "x2": [0.5, 1.5, 2.5],
            "x3": [2.0, 2.5, 3.0],
        }
    )

    augmented = _augment_interactions(predictors, depth=3, max_terms=1)

    interaction_columns = [column for column in augmented.columns if ":" in column]
    assert len(interaction_columns) == 1


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
