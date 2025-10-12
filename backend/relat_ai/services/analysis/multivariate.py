"""Multivariate modeling utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from numpy.linalg import LinAlgError
from scipy import stats
from statsmodels.stats.anova import anova_lm
from statsmodels.tools.sm_exceptions import PerfectSeparationError

from relat_ai.services.analysis.utils import (
    AnalysisResult,
    CorrelationRecord,
    ModelSummary,
)


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RegressionConfig:
    """Configuration for regression modeling."""

    response: str
    predictors: Sequence[str]
    add_intercept: bool = True
    interaction_depth: int = 1
    sample_size_limit: int | None = None
    min_variance: float = 1e-12
    random_state: int = 0


@dataclass(slots=True)
class RegressionPlan:
    """Declarative plan describing regression generation rules."""

    response: str
    candidate_predictors: Sequence[str]
    max_predictors: int = 3
    anchor_predictors: Sequence[str] = ()
    interaction_depth: int = 1
    sample_size_limit: int | None = None
    add_intercept: bool = True
    min_variance: float = 1e-12
    random_state: int = 0

    def build_configs(self) -> list[RegressionConfig]:
        """Expand the declarative plan into explicit regression configs."""

        anchors = list(dict.fromkeys(self.anchor_predictors))
        if len(anchors) > self.max_predictors:
            LOGGER.warning(
                "Anchor predictors (%s) exceed configured max_predictors (%d); proceeding with anchors only.",
                ", ".join(anchors),
                self.max_predictors,
            )
        optional = [
            predictor
            for predictor in self.candidate_predictors
            if predictor not in anchors and predictor != self.response
        ]
        max_optional = max(self.max_predictors - len(anchors), 0)
        configs: list[RegressionConfig] = []
        for count in range(0, min(len(optional), max_optional) + 1):
            for combo in combinations(optional, count):
                predictors = anchors + list(combo)
                if not predictors:
                    continue
                configs.append(
                    RegressionConfig(
                        response=self.response,
                        predictors=predictors,
                        add_intercept=self.add_intercept,
                        interaction_depth=self.interaction_depth,
                        sample_size_limit=self.sample_size_limit,
                        min_variance=self.min_variance,
                        random_state=self.random_state,
                    )
                )
        if not configs and anchors:
            configs.append(
                RegressionConfig(
                    response=self.response,
                    predictors=anchors,
                    add_intercept=self.add_intercept,
                    interaction_depth=self.interaction_depth,
                    sample_size_limit=self.sample_size_limit,
                    min_variance=self.min_variance,
                    random_state=self.random_state,
                )
            )
        return configs


@dataclass(slots=True)
class ANOVAConfig:
    """Configuration for one-way ANOVA models."""

    response: str
    factor: str
    sample_size_limit: int | None = None


@dataclass(slots=True)
class PartialCorrelationRequest:
    """Specification for partial correlation computations."""

    target: str
    candidates: Sequence[str]
    controls: Sequence[str]
    sample_size_limit: int | None = None
    random_state: int = 0


def build_multivariate_models(
    frame: pd.DataFrame,
    configs: Iterable[RegressionConfig] | RegressionPlan | None,
    *,
    anova: Iterable[ANOVAConfig] | None = None,
    partial: PartialCorrelationRequest | None = None,
) -> AnalysisResult:
    """Fit regression, ANOVA, and partial correlation models as requested."""

    regression_configs = _prepare_regression_configs(configs)
    regression_models = _fit_regressions(frame, regression_configs)

    anova_models: list[ModelSummary] = []
    if anova:
        anova_models = _fit_anova_models(frame, anova)

    partial_correlations: list[CorrelationRecord] = []
    if partial:
        partial_correlations = _compute_partial_correlations(frame, partial)

    models = regression_models + anova_models
    correlations = partial_correlations
    return AnalysisResult(
        correlations=correlations,
        models=models,
    )


def _prepare_regression_configs(
    configs: Iterable[RegressionConfig] | RegressionPlan | None,
) -> list[RegressionConfig]:
    if configs is None:
        return []
    if isinstance(configs, RegressionPlan):
        return configs.build_configs()
    return list(configs)


def _fit_regressions(
    frame: pd.DataFrame, configs: Iterable[RegressionConfig]
) -> list[ModelSummary]:
    summaries: list[ModelSummary] = []
    for config in configs:
        required_columns = [config.response, *config.predictors]
        missing_columns = [column for column in required_columns if column not in frame.columns]
        if missing_columns:
            LOGGER.warning(
                "Skipping regression for response '%s' due to missing columns: %s",
                config.response,
                ", ".join(missing_columns),
            )
            continue

        design = frame.loc[:, required_columns].dropna()
        if config.sample_size_limit and len(design.index) > config.sample_size_limit:
            design = design.sample(config.sample_size_limit, random_state=config.random_state)
        if design.empty:
            continue

        y = design.pop(config.response)
        predictors = design.loc[:, config.predictors].copy()
        predictors = _augment_interactions(predictors, config.interaction_depth)
        predictors = _drop_low_variance(predictors, config.min_variance)
        if predictors.empty:
            LOGGER.warning(
                "Skipping regression for response '%s' due to insufficient variance in predictors.",
                config.response,
            )
            continue

        if config.add_intercept:
            predictors = sm.add_constant(predictors, prepend=True, has_constant="add")

        try:
            if np.linalg.matrix_rank(predictors) < predictors.shape[1]:
                LOGGER.warning(
                    "Skipping regression for response '%s' due to singular design matrix (fitting error)",
                    config.response,
                )
                continue
            model = sm.OLS(y, predictors).fit()
        except (ValueError, LinAlgError, PerfectSeparationError) as exc:
            LOGGER.warning(
                "Skipping regression for response '%s' due to model fitting error: %s",
                config.response,
                exc,
            )
            continue

        summaries.append(
            ModelSummary(
                response=config.response,
                predictors=list(config.predictors),
                model_type="regression",
                metrics={
                    "r_squared": float(model.rsquared),
                    "adjusted_r_squared": float(model.rsquared_adj),
                    "aic": float(model.aic),
                    "bic": float(model.bic),
                },
                sample_size=len(design.index),
            )
        )

    return summaries


def _fit_anova_models(
    frame: pd.DataFrame, configs: Iterable[ANOVAConfig]
) -> list[ModelSummary]:
    summaries: list[ModelSummary] = []
    for config in configs:
        required_columns = [config.response, config.factor]
        missing_columns = [column for column in required_columns if column not in frame.columns]
        if missing_columns:
            LOGGER.warning(
                "Skipping ANOVA for response '%s' due to missing columns: %s",
                config.response,
                ", ".join(missing_columns),
            )
            continue

        design = frame.loc[:, required_columns].dropna()
        if config.sample_size_limit and len(design.index) > config.sample_size_limit:
            design = design.sample(config.sample_size_limit, random_state=0)
        if design.empty:
            continue

        try:
            model = smf.ols(
                f"{config.response} ~ C({config.factor})",
                data=design,
            ).fit()
            table = anova_lm(model, typ=2)
        except (ValueError, LinAlgError, PerfectSeparationError) as exc:
            LOGGER.warning(
                "Skipping ANOVA for response '%s' due to model fitting error: %s",
                config.response,
                exc,
            )
            continue

        factor_label = f"C({config.factor})"
        if factor_label not in table.index or "Residual" not in table.index:
            continue

        row = table.loc[factor_label]
        residual = table.loc["Residual"]
        summaries.append(
            ModelSummary(
                response=config.response,
                predictors=[config.factor],
                model_type="anova",
                metrics={
                    "f_statistic": float(row.get("F", np.nan)),
                    "p_value": float(row.get("PR(>F)", np.nan)),
                    "df_factor": float(row.get("df", np.nan)),
                    "df_residual": float(residual.get("df", np.nan)),
                },
                sample_size=len(design.index),
            )
        )

    return summaries


def _compute_partial_correlations(
    frame: pd.DataFrame, request: PartialCorrelationRequest
) -> list[CorrelationRecord]:
    results: list[CorrelationRecord] = []
    controls = list(request.controls)
    for candidate in request.candidates:
        required = [request.target, candidate, *controls]
        missing_columns = [column for column in required if column not in frame.columns]
        if missing_columns:
            LOGGER.warning(
                "Skipping partial correlation for '%s' due to missing columns: %s",
                candidate,
                ", ".join(missing_columns),
            )
            continue

        design = frame.loc[:, required].dropna()
        if request.sample_size_limit and len(design.index) > request.sample_size_limit:
            design = design.sample(request.sample_size_limit, random_state=request.random_state)
        if design.empty:
            continue

        if controls:
            target_residual = _residualize(design[request.target], design[controls])
            candidate_residual = _residualize(design[candidate], design[controls])
        else:
            target_residual = design[request.target]
            candidate_residual = design[candidate]

        correlation = stats.pearsonr(target_residual, candidate_residual)
        coefficient = float(
            correlation.statistic if hasattr(correlation, "statistic") else correlation[0]
        )
        p_value = float(
            correlation.pvalue if hasattr(correlation, "pvalue") else correlation[1]
        )
        results.append(
            CorrelationRecord(
                variables=(request.target, candidate),
                coefficient=coefficient,
                p_value=p_value,
                sample_size=len(target_residual.index),
                method="partial_correlation",
            )
        )

    return results


def _augment_interactions(predictors: pd.DataFrame, depth: int) -> pd.DataFrame:
    if depth <= 1:
        return predictors
    augmented = predictors.copy()
    numeric_columns = [
        column for column in predictors.columns if pd.api.types.is_numeric_dtype(predictors[column])
    ]
    for level in range(2, depth + 1):
        for combo in combinations(numeric_columns, level):
            name = ":".join(combo)
            augmented[name] = predictors.loc[:, combo].prod(axis=1)
    return augmented


def _drop_low_variance(matrix: pd.DataFrame, threshold: float) -> pd.DataFrame:
    if matrix.empty:
        return matrix
    variances = matrix.var(axis=0, ddof=0)
    keep_columns = variances[variances > threshold].index
    return matrix.loc[:, keep_columns]


def _residualize(series: pd.Series, controls: pd.DataFrame) -> pd.Series:
    if controls.empty:
        return series - series.mean()
    controls_with_const = sm.add_constant(controls, prepend=True, has_constant="add")
    model = sm.OLS(series, controls_with_const).fit()
    return series - model.predict(controls_with_const)
