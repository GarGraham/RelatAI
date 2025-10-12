"""Shared data structures for analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Mapping, Sequence


class ColumnSemanticType(str, Enum):
    """Semantic categories inferred from dataset profiles."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TEXT = "text"


@dataclass(slots=True)
class CorrelationRecord:
    """Summary statistics for a pairwise relationship."""

    variables: tuple[str, str]
    coefficient: float
    p_value: float | None
    sample_size: int
    method: str
    statistic: float | None = None
    extras: Mapping[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ModelSummary:
    """Model-level metrics for multivariate analyses."""

    response: str
    predictors: Sequence[str]
    model_type: str
    metrics: Mapping[str, float]
    sample_size: int | None = None
    notes: Sequence[str] | None = None


@dataclass(slots=True)
class AnalysisResult:
    """Aggregates results from analysis pipelines."""

    correlations: Iterable[CorrelationRecord] | None = None
    models: Iterable[ModelSummary] | None = None
