"""Pydantic models describing serialized analysis results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence

from pydantic import BaseModel, Field

from .models import AnalysisMode


def _utcnow() -> datetime:
    """Return the current UTC timestamp."""

    return datetime.now(timezone.utc)


class QualityFlagModel(BaseModel):
    """Confidence or quality indicator associated with an analysis output."""

    code: str
    message: str
    severity: str


class CorrelationExtrasANOVAModel(BaseModel):
    """Additional metrics returned for ANOVA-based correlations."""

    df_between: float
    df_within: float


class CorrelationExtrasChiSquareModel(BaseModel):
    """Additional metrics returned for chi-square style correlations."""

    degrees_of_freedom: float
    chi_square: float | None = None


CorrelationExtrasModel = (
    CorrelationExtrasANOVAModel | CorrelationExtrasChiSquareModel | None
)


class CorrelationRecordModel(BaseModel):
    """Serialized representation of a pairwise correlation record."""

    variables: tuple[str, str]
    coefficient: float
    p_value: float | None = None
    sample_size: int
    method: str
    statistic: float | None = None
    extras: CorrelationExtrasModel = None
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)


class CorrelationTableModel(BaseModel):
    """Container for serialized correlation outputs."""

    records: list[CorrelationRecordModel]
    generated_at: datetime = Field(default_factory=_utcnow)
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)


class RegressionMetricsModel(BaseModel):
    """Regression-specific goodness-of-fit metrics."""

    r_squared: float
    adjusted_r_squared: float
    aic: float
    bic: float
    cohen_f2: float | None = None


class ANOVAMetricsModel(BaseModel):
    """ANOVA model metrics."""

    f_statistic: float
    p_value: float
    df_factor: float
    df_residual: float
    effect_size: float | None = None


ModelMetricsModel = RegressionMetricsModel | ANOVAMetricsModel


class RegressionDiagnosticsModel(BaseModel):
    """Supplementary diagnostic outputs for regression models."""

    variance_inflation_factors: dict[str, float]


class ModelSummaryModel(BaseModel):
    """Serialized representation of a multivariate model summary."""

    response: str
    predictors: list[str]
    model_type: str
    metrics: ModelMetricsModel
    sample_size: int | None = None
    notes: list[str] | None = None
    diagnostics: RegressionDiagnosticsModel | None = None
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)


class MultivariateSummaryModel(BaseModel):
    """Container for serialized multivariate analysis outputs."""

    models: list[ModelSummaryModel]
    generated_at: datetime = Field(default_factory=_utcnow)
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)


class TopContributorModel(BaseModel):
    """Contributor ranking for PCA components."""

    feature: str
    loading: float


class PCAComponentModel(BaseModel):
    """Serialized principal component with variance information."""

    component: int
    explained_variance_ratio: float
    top_contributors: list[TopContributorModel]


class ChangePointModel(BaseModel):
    """Serialized change-point insight."""

    column: str
    method: str
    locations: list[int]


class ClusterModel(BaseModel):
    """Serialized clustering insight."""

    method: str
    cluster_sizes: dict[int, int]


class ResidualBucketModel(BaseModel):
    """Residual statistics for a single bucket."""

    label: str
    average_residual: float
    sample_size: int
    column_residuals: dict[str, float]


class ResidualForensicsModel(BaseModel):
    """Collection of residual buckets grouped by a category."""

    grouping: str
    buckets: list[ResidualBucketModel]


class RankedInsightModel(BaseModel):
    """Generic ranked insight surfaced from an analysis run."""

    label: str
    score: float
    drivers: list[str] = Field(default_factory=list)
    category: str = "general"
    method: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)


class AutoTriageResultModel(BaseModel):
    """Serialized auto-triage analysis output."""

    pca_components: list[PCAComponentModel]
    change_points: list[ChangePointModel]
    clusters: list[ClusterModel]
    residual_forensics: list[ResidualForensicsModel]
    suspicion_rankings: list[RankedInsightModel]
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)


class AISummaryModel(BaseModel):
    """Serialized AI-generated summary of analysis findings."""

    content: str
    generated_at: datetime = Field(default_factory=_utcnow)
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)


class SerializedAnalysisResult(BaseModel):
    """Top-level container for cached analysis results."""

    dataset_id: str
    dataset_hash: str
    analysis_mode: AnalysisMode
    configuration_signature: str
    filters_signature: str
    parameters_signature: str | None = None
    correlation_table: CorrelationTableModel | None = None
    multivariate_summary: MultivariateSummaryModel | None = None
    auto_triage: AutoTriageResultModel | None = None
    ranked_insights: list[RankedInsightModel] = Field(default_factory=list)
    ai_summary: AISummaryModel | None = None
    quality_flags: list[QualityFlagModel] = Field(default_factory=list)
    cached_at: datetime = Field(default_factory=_utcnow)


__all__ = [
    "AISummaryModel",
    "AutoTriageResultModel",
    "ChangePointModel",
    "CorrelationExtrasANOVAModel",
    "CorrelationExtrasChiSquareModel",
    "CorrelationRecordModel",
    "CorrelationTableModel",
    "MultivariateSummaryModel",
    "QualityFlagModel",
    "RankedInsightModel",
    "RegressionDiagnosticsModel",
    "RegressionMetricsModel",
    "ANOVAMetricsModel",
    "ModelSummaryModel",
    "ResidualBucketModel",
    "ResidualForensicsModel",
    "SerializedAnalysisResult",
    "TopContributorModel",
]
