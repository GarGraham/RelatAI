"""Multivariate modeling utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Literal, Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from numpy.linalg import LinAlgError
from scipy import stats
from statsmodels.stats.anova import anova_lm
from statsmodels.tools.sm_exceptions import PerfectSeparationError

from relat_ai.services.analysis.utils import (
    ANOVAMetrics,
    AnalysisResult,
    CorrelationRecord,
    ModelSummary,
    RegressionDiagnostics,
    RegressionMetrics,
    apply_sample_limit,
)
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import KFold, cross_val_score
from statsmodels.stats.outliers_influence import variance_inflation_factor


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
    solver: Literal["ols", "pls"] = "ols"
    pls_components: int | None = None
    max_interactions: int | None = None

    def __post_init__(self) -> None:
        if not self.predictors:
            raise ValueError("RegressionConfig requires at least one predictor")
        if self.interaction_depth < 1:
            raise ValueError("interaction_depth must be at least 1")
        if self.sample_size_limit is not None and self.sample_size_limit <= 0:
            raise ValueError("sample_size_limit must be a positive integer or None")
        if self.min_variance < 0:
            raise ValueError("min_variance must be non-negative")
        if self.max_interactions is not None and self.max_interactions <= 0:
            raise ValueError("max_interactions must be a positive integer when provided")
        if self.solver not in {"ols", "pls"}:
            raise ValueError("solver must be either 'ols' or 'pls'")
        if self.pls_components is not None and self.pls_components <= 0:
            raise ValueError("pls_components must be a positive integer when provided")
        if self.solver != "pls" and self.pls_components is not None:
            LOGGER.warning(
                "Ignoring pls_components for solver '%s'; parameter is only applicable to PLS regression.",
                self.solver,
            )


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
    solver: Literal["ols", "pls"] = "ols"
    pls_components: int | None = None
    max_interactions: int | None = None

    def __post_init__(self) -> None:
        if self.max_predictors < 1:
            raise ValueError("max_predictors must be at least 1")
        if self.interaction_depth < 1:
            raise ValueError("interaction_depth must be at least 1")
        if self.sample_size_limit is not None and self.sample_size_limit <= 0:
            raise ValueError("sample_size_limit must be a positive integer or None")
        if self.min_variance < 0:
            raise ValueError("min_variance must be non-negative")
        if self.max_interactions is not None and self.max_interactions <= 0:
            raise ValueError("max_interactions must be a positive integer when provided")
        if self.solver not in {"ols", "pls"}:
            raise ValueError("solver must be either 'ols' or 'pls'")
        if self.pls_components is not None and self.pls_components <= 0:
            raise ValueError("pls_components must be a positive integer when provided")

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
                        solver=self.solver,
                        pls_components=self.pls_components,
                        max_interactions=self.max_interactions,
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
                    solver=self.solver,
                    pls_components=self.pls_components,
                    max_interactions=self.max_interactions,
                )
            )
        return configs


@dataclass(slots=True)
class ANOVAConfig:
    """Configuration for one-way ANOVA models."""

    response: str
    factor: str
    sample_size_limit: int | None = None
    random_state: int = 0

    def __post_init__(self) -> None:
        if self.sample_size_limit is not None and self.sample_size_limit <= 0:
            raise ValueError("sample_size_limit must be a positive integer or None")


@dataclass(slots=True)
class PartialCorrelationRequest:
    """Specification for partial correlation computations."""

    target: str
    candidates: Sequence[str]
    controls: Sequence[str]
    sample_size_limit: int | None = None
    random_state: int = 0

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError("PartialCorrelationRequest requires at least one candidate")
        if self.sample_size_limit is not None and self.sample_size_limit <= 0:
            raise ValueError("sample_size_limit must be a positive integer or None")
        if self.target in self.controls:
            raise ValueError("target column cannot be part of the control set")


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
        design = apply_sample_limit(
            design, config.sample_size_limit, random_state=config.random_state
        )
        if design.empty:
            continue

        y = design.pop(config.response)
        predictors = design.loc[:, config.predictors].copy()
        predictors = _augment_interactions(
            predictors,
            config.interaction_depth,
            max_terms=config.max_interactions,
        )
        predictors = _drop_low_variance(predictors, config.min_variance)
        if predictors.empty:
            LOGGER.warning(
                "Skipping regression for response '%s' due to insufficient variance in predictors.",
                config.response,
            )
            continue

        vif = _compute_vif(predictors)

        if config.solver == "ols":
            if config.add_intercept:
                predictors_with_const = sm.add_constant(predictors, prepend=True, has_constant="add")
            else:
                predictors_with_const = predictors

            try:
                if np.linalg.matrix_rank(predictors_with_const) < predictors_with_const.shape[1]:
                    LOGGER.warning(
                        "Skipping regression for response '%s' due to singular design matrix (fitting error)",
                        config.response,
                    )
                    continue
                model = sm.OLS(y, predictors_with_const).fit()
            except (ValueError, LinAlgError, PerfectSeparationError) as exc:
                LOGGER.warning(
                    "Skipping regression for response '%s' due to model fitting error: %s",
                    config.response,
                    exc,
                )
                continue

            cohen_f2 = _cohen_f2(float(model.rsquared))
            summaries.append(
                ModelSummary(
                    response=config.response,
                    predictors=list(config.predictors),
                    model_type="regression",
                    metrics=RegressionMetrics(
                        r_squared=float(model.rsquared),
                        adjusted_r_squared=float(model.rsquared_adj),
                        aic=float(model.aic),
                        bic=float(model.bic),
                        cohen_f2=cohen_f2,
                    ),
                    sample_size=len(design.index),
                    diagnostics=RegressionDiagnostics(variance_inflation_factors=vif),
                )
            )
            continue

        if config.solver == "pls":
            summary = _fit_pls_regression(
                predictors,
                y,
                config,
                vif=vif,
            )
            if summary is not None:
                summaries.append(summary)
            continue

        LOGGER.warning("Unsupported regression solver '%s' requested; skipping.", config.solver)

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
        design = apply_sample_limit(
            design, config.sample_size_limit, random_state=config.random_state
        )
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
        effect_size = _partial_eta_squared(row.get("sum_sq", np.nan), residual.get("sum_sq", np.nan))
        summaries.append(
            ModelSummary(
                response=config.response,
                predictors=[config.factor],
                model_type="anova",
                metrics=ANOVAMetrics(
                    f_statistic=float(row.get("F", np.nan)),
                    p_value=float(row.get("PR(>F)", np.nan)),
                    df_factor=float(row.get("df", np.nan)),
                    df_residual=float(residual.get("df", np.nan)),
                    effect_size=effect_size,
                ),
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
        design = apply_sample_limit(
            design, request.sample_size_limit, random_state=request.random_state
        )
        if design.empty:
            continue

        if controls:
            target_residual = _residualize(design[request.target], design[controls])
            candidate_residual = _residualize(design[candidate], design[controls])
        else:
            target_residual = design[request.target]
            candidate_residual = design[candidate]

        sample_size = len(target_residual.index)
        if sample_size < 2:
            LOGGER.warning(
                "Skipping partial correlation for '%s' due to insufficient samples (%d)",
                candidate,
                sample_size,
            )
            continue

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
                sample_size=sample_size,
                method="partial_correlation",
            )
        )

    return results


def _fit_pls_regression(
    predictors: pd.DataFrame,
    response: pd.Series,
    config: RegressionConfig,
    *,
    vif: dict[str, float],
) -> ModelSummary | None:
    n_samples = len(predictors.index)
    n_features = predictors.shape[1]
    max_components = max(min(n_features, n_samples - 1), 1)

    if max_components < 1:
        LOGGER.warning(
            "Skipping PLS regression for response '%s' due to insufficient samples (%d)",
            config.response,
            n_samples,
        )
        return None

    if config.pls_components is not None:
        n_components = min(config.pls_components, max_components)
    else:
        n_components = _select_optimal_pls_components(
            predictors,
            response,
            max_components,
            random_state=config.random_state,
        )

    if n_components < 1:
        LOGGER.warning(
            "Skipping PLS regression for response '%s' due to insufficient samples (%d)",
            config.response,
            n_samples,
        )
        return None

    try:
        model = PLSRegression(n_components=n_components, scale=True)
        model.fit(predictors, response)
    except ValueError as exc:
        LOGGER.warning(
            "Skipping PLS regression for response '%s' due to model fitting error: %s",
            config.response,
            exc,
        )
        return None

    predictions = model.predict(predictors)
    if predictions.ndim > 1:
        predictions = predictions.ravel()
    r_squared = float(r2_score(response, predictions))
    adjusted_r_squared = _adjusted_r_squared(r_squared, n_samples, n_components)
    cohen_f2 = _cohen_f2(r_squared)

    return ModelSummary(
        response=config.response,
        predictors=list(config.predictors),
        model_type="regression_pls",
        metrics=RegressionMetrics(
            r_squared=r_squared,
            adjusted_r_squared=adjusted_r_squared,
            aic=float("nan"),
            bic=float("nan"),
            cohen_f2=cohen_f2,
        ),
        sample_size=n_samples,
        notes=[f"n_components={n_components}"],
        diagnostics=RegressionDiagnostics(variance_inflation_factors=vif),
    )


def _select_optimal_pls_components(
    predictors: pd.DataFrame,
    response: pd.Series,
    max_components: int,
    *,
    random_state: int,
) -> int:
    if max_components <= 1:
        return max_components

    n_samples = len(predictors.index)
    if n_samples < 3:
        return min(max_components, 1)

    n_splits = min(5, n_samples)
    if n_splits < 2:
        return min(max_components, 1)

    kfold = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    best_components = 1
    best_score = -np.inf

    y_array = response.to_numpy()

    for n_components in range(1, max_components + 1):
        model = PLSRegression(n_components=n_components, scale=True)
        try:
            scores = cross_val_score(model, predictors, y_array, cv=kfold, scoring="r2")
        except ValueError:
            continue
        mean_score = float(np.mean(scores))
        if mean_score > best_score + np.finfo(float).eps:
            best_score = mean_score
            best_components = n_components

    return best_components


def _augment_interactions(
    predictors: pd.DataFrame,
    depth: int,
    *,
    max_terms: int | None = None,
) -> pd.DataFrame:
    if depth <= 1:
        return predictors
    augmented = predictors.copy()
    numeric_columns = [
        column for column in predictors.columns if pd.api.types.is_numeric_dtype(predictors[column])
    ]
    generated: list[tuple[str, pd.Series, float]] = []
    for level in range(2, depth + 1):
        for combo in combinations(numeric_columns, level):
            name = ":".join(combo)
            values = predictors.loc[:, combo].prod(axis=1)
            variance = float(values.var(ddof=0))
            generated.append((name, values, variance))

    if max_terms is not None and len(generated) > max_terms:
        generated.sort(key=lambda item: item[2], reverse=True)
        generated = generated[:max_terms]

    for name, values, _ in generated:
        augmented[name] = values
    return augmented


def _compute_vif(predictors: pd.DataFrame) -> dict[str, float]:
    if predictors.empty:
        return {}

    numeric = predictors.select_dtypes(include=[np.number])
    if numeric.shape[1] < 2:
        return {}

    matrix = numeric.to_numpy()
    vif: dict[str, float] = {}
    for index, column in enumerate(numeric.columns):
        try:
            with np.errstate(divide="ignore", invalid="ignore"):
                value = float(variance_inflation_factor(matrix, index))
        except (LinAlgError, ValueError):
            LOGGER.debug("Unable to compute VIF for column '%s' due to singular matrix.", column)
            continue
        if not np.isfinite(value):
            LOGGER.debug("VIF for column '%s' is non-finite; reporting as infinity.", column)
            value = float("inf")
        vif[column] = value
    return vif


def _cohen_f2(r_squared: float) -> float | None:
    if not np.isfinite(r_squared) or r_squared <= 0.0 or r_squared >= 1.0:
        return None
    return r_squared / (1.0 - r_squared)


def _adjusted_r_squared(r_squared: float, n_samples: int, predictors: int) -> float:
    if n_samples <= predictors + 1 or not np.isfinite(r_squared):
        return float("nan")
    return 1.0 - (1.0 - r_squared) * (n_samples - 1) / (n_samples - predictors - 1)


def _partial_eta_squared(ss_factor: float, ss_residual: float) -> float | None:
    if not np.isfinite(ss_factor) or not np.isfinite(ss_residual):
        return None
    denominator = ss_factor + ss_residual
    if denominator <= 0:
        return None
    return ss_factor / denominator


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
