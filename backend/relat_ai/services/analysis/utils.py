"""Shared data structures for analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(slots=True)
class CorrelationRecord:
    """Summary statistics for a pairwise correlation."""

    variables: tuple[str, str]
    coefficient: float
    p_value: float
    sample_size: int
    method: str


@dataclass(slots=True)
class ModelSummary:
    """Model-level metrics for multivariate analyses."""

    response: str
    predictors: Sequence[str]
    r_squared: float
    adjusted_r_squared: float
    aic: float
    bic: float


@dataclass(slots=True)
class AnalysisResult:
    """Aggregates results from analysis pipelines."""

    correlations: Iterable[CorrelationRecord] | None = None
    models: Iterable[ModelSummary] | None = None
