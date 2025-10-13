"""Shared data structures for analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

import pandas as pd


class ColumnSemanticType(str, Enum):
    """Semantic categories inferred from dataset profiles."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"


@dataclass(slots=True)
class RegressionMetrics:
    """Core goodness-of-fit statistics for linear regression models."""

    r_squared: float
    adjusted_r_squared: float
    aic: float
    bic: float


@dataclass(slots=True)
class ANOVAMetrics:
    """Summary statistics for one-way ANOVA models."""

    f_statistic: float
    p_value: float
    df_factor: float
    df_residual: float


@dataclass(slots=True)
class ANOVAExtras:
    """Additional descriptive statistics for ANOVA-style correlations."""

    df_between: float
    df_within: float


@dataclass(slots=True)
class ChiSquareExtras:
    """Additional descriptive statistics for chi-square style correlations."""

    degrees_of_freedom: float
    chi_square: float | None = None


CorrelationExtras = ANOVAExtras | ChiSquareExtras | None
ModelMetrics = RegressionMetrics | ANOVAMetrics


@dataclass(slots=True)
class CorrelationRecord:
    """Summary statistics for a pairwise relationship."""

    variables: tuple[str, str]
    coefficient: float
    p_value: float | None
    sample_size: int
    method: str
    statistic: float | None = None
    extras: CorrelationExtras = None


@dataclass(slots=True)
class ModelSummary:
    """Model-level metrics for multivariate analyses."""

    response: str
    predictors: Sequence[str]
    model_type: str
    metrics: ModelMetrics
    sample_size: int | None = None
    notes: Sequence[str] | None = None


@dataclass(slots=True)
class AnalysisResult:
    """Aggregates results from analysis pipelines."""

    correlations: Iterable[CorrelationRecord] | None = None
    models: Iterable[ModelSummary] | None = None


def apply_sample_limit(
    frame: pd.DataFrame,
    limit: int | None,
    *,
    random_state: int | None = None,
) -> pd.DataFrame:
    """Return a sampled frame when a positive sample size limit is configured."""

    if limit is None:
        return frame
    if limit <= 0:
        raise ValueError("sample_size_limit must be a positive integer when provided")
    if len(frame.index) <= limit:
        return frame
    return frame.sample(limit, random_state=random_state)
