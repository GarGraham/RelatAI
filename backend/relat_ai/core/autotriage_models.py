"""Typed payloads for the auto-triage explainability layer.

The :mod:`backend.relat_ai.services.analysis.auto_triage` module still
returns the legacy dataclass flavoured response, but the new explainability
features described in ``docs/DataUnderstanding_v2.md`` require a richer and
type-safe schema.  These Pydantic models formalise that contract so that the
API, caching layer and frontend consumers all share a consistent view of the
payload.

Only the backend deliverables are implemented in this task, therefore the
models focus on validation and serialisation requirements needed by the new
services (suspicion scoring, cluster profiling, PCA narratives and change
point reporting).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


class SignalDetail(BaseModel):
    """Individual signal contributing to suspicion score."""

    kind: Literal["pca_loading", "changepoint", "cluster", "residual", "dispersion"]
    weight: float = Field(ge=0.0, le=1.0, description="Normalised contribution (0-1)")
    detail: str = Field(min_length=1, description="Human readable explanation")
    link: Optional[Dict[str, Any]] = Field(
        default=None, description="UI navigation hints (tab, target, etc.)"
    )

    model_config = ConfigDict(frozen=True)


class SuspicionItemModel(BaseModel):
    """Enhanced suspicion ranking with contribution breakdown and evidence."""

    target: str = Field(min_length=1, description="Variable or feature name")
    score: float = Field(ge=0.0, le=1.0, description="Normalised suspicion score")
    contrib: Dict[str, float] = Field(description="Contribution by signal type")
    top_signals: list[SignalDetail] = Field(
        max_length=4, description="Top evidence bullets sorted by weight"
    )
    links: Dict[str, str] = Field(
        default_factory=dict, description="Navigation targets (tab payloads)"
    )
    flags: list[str] = Field(
        default_factory=list, description="Quality codes (collinearity, low_n, …)"
    )
    raw_stats: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None, description="Underlying statistics for drill downs"
    )

    @field_validator("contrib")
    @classmethod
    def contributions_sum_to_one(cls, value: Dict[str, float]) -> Dict[str, float]:
        total = sum(value.values())
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Contributions must sum to ~1.0, got {total:.3f}")
        if total == 0:
            return value
        normaliser = 1.0 / total
        return {key: round(weight * normaliser, 4) for key, weight in value.items()}

    @field_validator("top_signals")
    @classmethod
    def signals_sorted_by_weight(cls, value: list[SignalDetail]) -> list[SignalDetail]:
        weights = [signal.weight for signal in value]
        if weights != sorted(weights, reverse=True):
            raise ValueError("Signals must be sorted by weight descending")
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> "SuspicionItemModel":
        contrib_keys = set(self.contrib.keys())
        signal_kinds = {signal.kind for signal in self.top_signals}
        if not signal_kinds.issubset(contrib_keys):
            missing = signal_kinds - contrib_keys
            raise ValueError(f"Signals reference missing contrib keys: {missing}")
        return self


class ClusterFeatureStats(BaseModel):
    """Per-feature statistics for a single cluster."""

    mean: float
    median: float
    std: float
    iqr: float
    n: int = Field(gt=0, description="Non-NaN sample count")


class ClusterProfileModel(BaseModel):
    """Enhanced cluster information with profiling statistics."""

    method: Literal["kmeans", "hierarchical"]
    k: int = Field(gt=0, description="Number of clusters")
    sizes: list[dict[str, Any]] = Field(
        description="[{id:0, n:850, pct:0.471}, …]"
    )
    top_diff_features: list[dict[str, Any]] = Field(
        max_length=15,
        description="Features with strongest between-cluster differences",
    )
    feature_importance: list[dict[str, Any]] = Field(
        max_length=15,
        description="Tree based importance scores for cluster prediction",
    )
    medoids: Dict[str, list[int]] = Field(
        description="Representative sample indices per cluster"
    )
    per_feature_stats: Dict[str, Dict[str, ClusterFeatureStats]] = Field(
        description="Statistics by cluster: {cluster_id: {feature: stats}}"
    )
    by_time: Optional[list[dict[str, Any]]] = Field(
        default=None, description="Temporal distribution if datetime column present"
    )


class PCAExplainModel(BaseModel):
    """PCA results with narrative explanations and sorted loadings."""

    variance: list[Dict[str, Any]]  # Contains {"pc": str, "ratio": float}
    loadings: Dict[str, list[tuple[str, float]]]  # PC name -> [(feature, loading), ...]
    narrative: list[str]
    cumulative_variance: float = Field(ge=0.0, le=1.0)


class SegmentSummary(BaseModel):
    """Statistical summary for a time series segment between change points."""

    start: int = Field(ge=0, description="Start index (inclusive)")
    end: int = Field(ge=0, description="End index (inclusive)")
    mean: float
    std: float
    n: int = Field(gt=0)
    pct: float = Field(ge=0.0, le=1.0, description="Percentage of total rows")

    @field_validator("end")
    @classmethod
    def end_after_start(cls, value: int, info: FieldValidationInfo) -> int:
        start = info.data.get("start")
        if start is not None and value < int(start):
            raise ValueError("end must be >= start")
        return value


class ChangePointContext(BaseModel):
    """Contextual information around a change point."""

    index: int = Field(ge=0)
    timestamp: Optional[str] = None
    cluster_shift: Optional[dict[str, int]] = None
    batch_info: Optional[str] = None


class ChangePointReportModel(BaseModel):
    """Enhanced change-point detection with segment summaries and context."""

    column: str
    method: Literal["pelt", "cusum"]
    n: int = Field(ge=0, description="Number of change points detected")
    indices: list[int] = Field(description="Change point locations (sorted)")
    segments: list[SegmentSummary]
    strength: list[float]
    context: list[ChangePointContext] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    """Aggregated narratives returned by the evidence builder service."""

    suspicion_items: list[SuspicionItemModel]
    pca: Optional[PCAExplainModel]
    change_points: list[ChangePointReportModel]
    clusters: Optional[ClusterProfileModel]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

