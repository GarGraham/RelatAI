"""Serialization helpers and storage for analysis results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from threading import RLock
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence, TypeVar, cast, Literal

import pandas as pd

from pydantic import BaseModel

from relat_ai.core.models import AnalysisMode, DatasetConfiguration
from relat_ai.core.results import (
    AISummaryModel,
    AutoTriageResultModel,
    ChangePointModel,
    ClusterModel,
    CorrelationExtrasANOVAModel,
    CorrelationExtrasChiSquareModel,
    CorrelationRecordModel,
    CorrelationTableModel,
    MultivariateSummaryModel,
    PCAComponentModel,
    QualityFlagModel,
    RankedInsightModel,
    RegressionDiagnosticsModel,
    RegressionMetricsModel,
    ANOVAMetricsModel,
    SerializedAnalysisResult,
    TopContributorModel,
    ModelSummaryModel,
    ResidualBucketModel,
    ResidualForensicsModel,
)
from relat_ai.services.analysis.auto_triage import (
    AutoTriageResult,
    ResidualBucket,
    ResidualForensicsInsight,
)
from relat_ai.services.analysis.confidence_flags import QualityFlag
from relat_ai.services.analysis.utils import (
    ANOVAExtras,
    ANOVAMetrics,
    AnalysisResult,
    ChiSquareExtras,
    CorrelationRecord,
    ModelSummary,
    RegressionDiagnostics,
    RegressionMetrics,
)


TResult = TypeVar("TResult")
TModel = TypeVar("TModel", bound=BaseModel)


class SignatureBuilder:
    """Deterministic signature generation for cache keys."""

    @staticmethod
    def _stable_dumps(payload: Any) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _normalise_sequence(values: Sequence[Any]) -> list[str]:
        return [str(value) for value in values]

    @classmethod
    def for_configuration(cls, configuration: DatasetConfiguration) -> str:
        payload = {
            "analysis_mode": configuration.analysis_mode,
            "selected_columns": configuration.selected_columns,
            "anchor_columns": configuration.anchor_columns,
            "include_interactions": configuration.include_interactions,
            "max_variables": configuration.max_variables,
            "interaction_depth": configuration.interaction_depth,
        }
        return cls._stable_dumps(payload)

    @classmethod
    def for_filters(cls, filters: Mapping[str, Sequence[Any]] | None) -> str:
        ordered_filters = {
            column: cls._normalise_sequence(
                sorted(values, key=lambda value: str(value))
            )
            for column, values in sorted((filters or {}).items(), key=lambda item: item[0])
        }
        return cls._stable_dumps(ordered_filters)

    @classmethod
    def for_parameters(cls, parameters: Mapping[str, Any] | None) -> str | None:
        if parameters is None:
            return None
        return cls._stable_dumps(parameters)


class QualityFlagConverter:
    """Convert domain quality flags into API models."""

    @staticmethod
    def convert(flags: Sequence[QualityFlag] | None) -> list[QualityFlagModel]:
        if not flags:
            return []
        return [
            QualityFlagModel(code=flag.code, message=flag.message, severity=flag.severity)
            for flag in flags
        ]


class CorrelationExtrasConverter:
    """Convert correlation extras into serializable models."""

    @staticmethod
    def convert(
        extras: Any,
    ) -> CorrelationExtrasANOVAModel | CorrelationExtrasChiSquareModel | None:
        if isinstance(extras, ANOVAExtras):
            return CorrelationExtrasANOVAModel(
                df_between=extras.df_between,
                df_within=extras.df_within,
            )
        if isinstance(extras, ChiSquareExtras):
            return CorrelationExtrasChiSquareModel(
                degrees_of_freedom=extras.degrees_of_freedom,
                chi_square=extras.chi_square,
            )
        return None


class RegressionDiagnosticsConverter:
    """Convert regression diagnostics payloads."""

    @staticmethod
    def convert(diagnostics: RegressionDiagnostics | None) -> RegressionDiagnosticsModel | None:
        if diagnostics is None:
            return None
        return RegressionDiagnosticsModel(
            variance_inflation_factors=dict(diagnostics.variance_inflation_factors)
        )


class MultivariateMetricsConverter:
    """Convert multivariate metrics and surface scoring metadata."""

    @staticmethod
    def convert(
        metrics: RegressionMetrics | ANOVAMetrics | Any,
    ) -> tuple[RegressionMetricsModel | ANOVAMetricsModel, float]:
        if isinstance(metrics, RegressionMetrics):
            return (
                RegressionMetricsModel(
                    r_squared=metrics.r_squared,
                    adjusted_r_squared=metrics.adjusted_r_squared,
                    aic=metrics.aic,
                    bic=metrics.bic,
                    cohen_f2=metrics.cohen_f2,
                ),
                float(metrics.r_squared),
            )
        if isinstance(metrics, ANOVAMetrics):
            return (
                ANOVAMetricsModel(
                    f_statistic=metrics.f_statistic,
                    p_value=metrics.p_value,
                    df_factor=metrics.df_factor,
                    df_residual=metrics.df_residual,
                    effect_size=metrics.effect_size,
                ),
                float(metrics.effect_size or 0.0),
            )
        # pragma: no cover - defensive fallback for unexpected metric types
        return RegressionMetricsModel.model_validate(metrics), 0.0


class AutoTriageConverters:
    """Helper routines for auto-triage serialization."""

    @staticmethod
    def top_contributors(contributors: Sequence[tuple[str, float]]) -> list[TopContributorModel]:
        return [
            TopContributorModel(feature=feature, loading=value)
            for feature, value in contributors
        ]

    @staticmethod
    def residual_buckets(buckets: Sequence[ResidualBucket]) -> list[ResidualBucketModel]:
        return [
            ResidualBucketModel(
                label=bucket.label,
                average_residual=bucket.average_residual,
                sample_size=bucket.sample_size,
                column_residuals=dict(bucket.column_residuals),
            )
            for bucket in buckets
        ]

    @classmethod
    def residual_forensics(
        cls, residuals: Sequence[ResidualForensicsInsight]
    ) -> list[ResidualForensicsModel]:
        return [
            ResidualForensicsModel(
                grouping=insight.grouping,
                buckets=cls.residual_buckets(insight.buckets),
            )
            for insight in residuals
        ]

    @staticmethod
    def suspicion_rankings(
        rankings: Sequence[Any],
    ) -> list[RankedInsightModel]:
        suspicion_insights = [
            RankedInsightModel(
                label=score.target,
                score=max(0.0, min(1.0, float(score.score))),
                drivers=list(score.drivers),
                category="auto_triage",
                method=score.target_type,
            )
            for score in rankings
        ]
        suspicion_insights.sort(key=lambda insight: insight.score, reverse=True)
        return suspicion_insights


class AnalysisSerializer(Protocol[TResult, TModel]):
    """Protocol for mode-specific serializers."""

    @staticmethod
    def serialize(result: TResult | None) -> tuple[TModel | None, list[RankedInsightModel]]:
        """Return serialized payload and ranked insights for a mode."""


def serialize_correlation_table(
    result: AnalysisResult,
    *,
    table_flags: Sequence[QualityFlag] | None = None,
) -> tuple[CorrelationTableModel, list[RankedInsightModel]]:
    """Serialize correlation records into API-ready models and ranked insights."""

    records: list[CorrelationRecordModel] = []
    ranked: list[RankedInsightModel] = []
    for record in result.correlations or []:
        extras = CorrelationExtrasConverter.convert(record.extras)
        records.append(
            CorrelationRecordModel(
                variables=record.variables,
                coefficient=record.coefficient,
                p_value=record.p_value,
                sample_size=record.sample_size,
                method=record.method,
                statistic=record.statistic,
                extras=extras,
            )
        )
        ranked.append(
            RankedInsightModel(
                label=f"{record.variables[0]} vs {record.variables[1]}",
                score=abs(record.coefficient),
                drivers=list(record.variables),
                category="correlation",
                method=record.method,
                metadata={"sample_size": record.sample_size},
            )
        )

    ranked.sort(key=lambda insight: insight.score, reverse=True)
    table = CorrelationTableModel(
        records=records,
        quality_flags=QualityFlagConverter.convert(table_flags),
    )
    return table, ranked


def serialize_multivariate_summary(
    models: Iterable[ModelSummary],
    *,
    summary_flags: Sequence[QualityFlag] | None = None,
) -> tuple[MultivariateSummaryModel, list[RankedInsightModel]]:
    """Serialize multivariate model summaries."""

    serialised_models: list[ModelSummaryModel] = []
    ranked: list[RankedInsightModel] = []
    for model in models:
        metrics_model, score = MultivariateMetricsConverter.convert(model.metrics)
        score = max(0.0, min(1.0, score))
        serialised_models.append(
            ModelSummaryModel(
                response=model.response,
                predictors=list(model.predictors),
                model_type=model.model_type,
                metrics=metrics_model,
                sample_size=model.sample_size,
                notes=list(model.notes) if model.notes else None,
                diagnostics=RegressionDiagnosticsConverter.convert(model.diagnostics),
            )
        )
        ranked.append(
            RankedInsightModel(
                label=f"{model.model_type}: {model.response}",
                score=score,
                drivers=list(model.predictors),
                category="multivariate",
                method=model.model_type,
            )
        )

    ranked.sort(key=lambda insight: insight.score, reverse=True)
    summary = MultivariateSummaryModel(
        models=serialised_models,
        quality_flags=QualityFlagConverter.convert(summary_flags),
    )
    return summary, ranked
def serialize_auto_triage(
    result: AutoTriageResult,
) -> tuple[AutoTriageResultModel, list[RankedInsightModel]]:
    """Serialize an auto-triage analysis result."""

    pca_components = [
        PCAComponentModel(
            component=insight.component,
            explained_variance_ratio=insight.explained_variance_ratio,
            top_contributors=AutoTriageConverters.top_contributors(insight.top_contributors),
        )
        for insight in result.pca_components
    ]
    change_points = [
        ChangePointModel(
            column=insight.column,
            method=insight.method,
            locations=list(insight.locations),
        )
        for insight in result.change_points
    ]
    clusters = [
        ClusterModel(method=cluster.method, cluster_sizes=dict(cluster.cluster_sizes))
        for cluster in result.clusters
    ]
    residual_forensics = AutoTriageConverters.residual_forensics(result.residual_forensics)

    suspicion_insights = AutoTriageConverters.suspicion_rankings(result.suspicion_rankings)
    auto_triage_model = AutoTriageResultModel(
        pca_components=pca_components,
        change_points=change_points,
        clusters=clusters,
        residual_forensics=residual_forensics,
        suspicion_rankings=suspicion_insights,
        quality_flags=QualityFlagConverter.convert(result.quality_flags),
    )
    return auto_triage_model, suspicion_insights


class CorrelationResultSerializer:
    """Serializer for correlation analysis outputs."""

    @staticmethod
    def serialize(
        result: AnalysisResult | Sequence[CorrelationRecord] | None,
    ) -> tuple[CorrelationTableModel | None, list[RankedInsightModel]]:
        if result is None:
            return None, []
        payload = result if isinstance(result, AnalysisResult) else AnalysisResult(correlations=result)
        return serialize_correlation_table(payload)


class MultivariateResultSerializer:
    """Serializer for multivariate model summaries."""

    @staticmethod
    def serialize(
        result: AnalysisResult | Iterable[ModelSummary] | None,
    ) -> tuple[MultivariateSummaryModel | None, list[RankedInsightModel]]:
        if result is None:
            return None, []
        models: Iterable[ModelSummary] | None
        if isinstance(result, AnalysisResult):
            models = result.models
        else:
            models = result
        if models is None:
            return None, []
        return serialize_multivariate_summary(models)


class AutoTriageResultSerializer:
    """Serializer for auto-triage mode outputs."""

    @staticmethod
    def serialize(
        result: AutoTriageResult | None,
    ) -> tuple[AutoTriageResultModel | None, list[RankedInsightModel]]:
        if result is None:
            return None, []
        return serialize_auto_triage(result)


SerializerEntry = tuple[
    Callable[[Any], tuple[BaseModel | None, list[RankedInsightModel]]],
    str,
]


SERIALIZERS: dict[AnalysisMode, SerializerEntry] = {
    "correlation": (CorrelationResultSerializer.serialize, "correlation_table"),
    "multivariate": (MultivariateResultSerializer.serialize, "multivariate_summary"),
    "auto_triage": (AutoTriageResultSerializer.serialize, "auto_triage_result"),
}


def create_serialized_result(
    *,
    dataset_id: str,
    dataset_hash: str,
    configuration: DatasetConfiguration,
    analysis_mode: AnalysisMode,
    result: (
        AnalysisResult
        | Iterable[ModelSummary]
        | Sequence[CorrelationRecord]
        | AutoTriageResult
        | None
    ) = None,
    filters: Mapping[str, Sequence[Any]] | None = None,
    parameters: Mapping[str, Any] | None = None,
    ai_summary_text: str | None = None,
    ai_summary_flags: Sequence[QualityFlag] | None = None,
    quality_flags: Sequence[QualityFlag] | None = None,
) -> SerializedAnalysisResult:
    """Compose a serialized analysis result payload from component outputs."""

    config_signature = SignatureBuilder.for_configuration(configuration)
    filters_signature = SignatureBuilder.for_filters(filters or configuration.filters)
    parameters_signature = SignatureBuilder.for_parameters(parameters)

    serializer_entry = SERIALIZERS.get(analysis_mode)
    if serializer_entry is None:
        raise ValueError(f"No serializer registered for analysis mode: {analysis_mode}")

    serializer, attribute = serializer_entry
    mode_output, ranked_insights = serializer(result)

    ai_summary: AISummaryModel | None = None
    if ai_summary_text is not None:
        ai_summary = AISummaryModel(
            content=ai_summary_text,
            generated_at=datetime.now(timezone.utc),
            quality_flags=QualityFlagConverter.convert(ai_summary_flags),
        )

    ranked_insights.sort(key=lambda insight: insight.score, reverse=True)

    correlation_table: CorrelationTableModel | None = None
    multivariate_summary: MultivariateSummaryModel | None = None
    auto_triage_model: AutoTriageResultModel | None = None

    if attribute == "correlation_table":
        correlation_table = cast(CorrelationTableModel | None, mode_output)
    elif attribute == "multivariate_summary":
        multivariate_summary = cast(MultivariateSummaryModel | None, mode_output)
    elif attribute == "auto_triage_result":
        auto_triage_model = cast(AutoTriageResultModel | None, mode_output)

    return SerializedAnalysisResult(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        analysis_mode=analysis_mode,
        configuration_signature=config_signature,
        filters_signature=filters_signature,
        parameters_signature=parameters_signature,
        correlation_table=correlation_table,
        multivariate_summary=multivariate_summary,
        auto_triage_result=auto_triage_model,
        ranked_insights=ranked_insights,
        ai_summary=ai_summary,
        quality_flags=QualityFlagConverter.convert(quality_flags),
    )


@dataclass(frozen=True)
class ResultKey:
    """Key used to store and retrieve cached results."""

    dataset_id: str
    dataset_hash: str
    analysis_mode: AnalysisMode
    configuration_signature: str
    filters_signature: str
    parameters_signature: str | None = None

    def as_tuple(self) -> tuple[str, ...]:
        """Return a tuple representation suitable for dictionary keys."""

        return (
            self.dataset_id,
            self.dataset_hash,
            self.analysis_mode,
            self.configuration_signature,
            self.filters_signature,
            self.parameters_signature or "",
        )


class ResultStorage:
    """Thread-safe in-memory store for serialized analysis results."""

    def __init__(
        self,
        *,
        max_size: int | None = None,
        ttl_seconds: float | None = None,
        eviction_policy: Literal["lru", "fifo"] = "lru",
    ) -> None:
        self._store: dict[tuple[str, ...], _CacheEntry] = {}
        self._lock = RLock()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._eviction_policy = eviction_policy
        self._access_times: dict[tuple[str, ...], float] = {}

    def store(self, key: ResultKey, result: SerializedAnalysisResult) -> SerializedAnalysisResult:
        """Persist ``result`` under ``key`` and return the stored payload."""

        with self._lock:
            self._prune_expired()
            self._evict_if_needed()
            tuple_key = key.as_tuple()
            timestamp = time.time()
            self._store[tuple_key] = _CacheEntry(result=result, stored_at=timestamp)
            self._access_times[tuple_key] = timestamp
            return result

    def get(self, key: ResultKey) -> SerializedAnalysisResult | None:
        """Return a cached result if present and not expired."""

        with self._lock:
            tuple_key = key.as_tuple()
            entry = self._store.get(tuple_key)
            if entry is None:
                return None

            if self._ttl_seconds is not None:
                now = time.time()
                if (now - entry.stored_at) > self._ttl_seconds:
                    del self._store[tuple_key]
                    self._access_times.pop(tuple_key, None)
                    return None
                self._access_times[tuple_key] = now

            return entry.result

    def invalidate(self, key: ResultKey) -> bool:
        """Remove a cached result under ``key``. Returns ``True`` if removed."""

        with self._lock:
            tuple_key = key.as_tuple()
            existed = tuple_key in self._store
            self._store.pop(tuple_key, None)
            self._access_times.pop(tuple_key, None)
            return existed

    def invalidate_dataset(self, dataset_id: str) -> int:
        """Remove all cached results for ``dataset_id``. Returns count removed."""

        with self._lock:
            to_remove = [
                key for key in self._store.keys() if key[0] == dataset_id
            ]
            for tuple_key in to_remove:
                del self._store[tuple_key]
                self._access_times.pop(tuple_key, None)
            return len(to_remove)

    def size(self) -> int:
        """Return the number of cached entries."""

        with self._lock:
            self._prune_expired()
            return len(self._store)

    def keys(self) -> list[ResultKey]:
        """Return cache keys for inspection/debugging."""

        with self._lock:
            return [
                ResultKey(
                    dataset_id=key[0],
                    dataset_hash=key[1],
                    analysis_mode=key[2],
                    configuration_signature=key[3],
                    filters_signature=key[4],
                    parameters_signature=key[5] or None,
                )
                for key in self._store.keys()
            ]

    def clear(self) -> None:
        """Remove all cached results (useful for tests)."""

        with self._lock:
            self._store.clear()
            self._access_times.clear()

    def _prune_expired(self) -> None:
        if self._ttl_seconds is None:
            return
        now = time.time()
        expired = [
            key for key, entry in self._store.items()
            if (now - entry.stored_at) > self._ttl_seconds
        ]
        for tuple_key in expired:
            del self._store[tuple_key]
            self._access_times.pop(tuple_key, None)

    def _evict_if_needed(self) -> None:
        if self._max_size is None or len(self._store) < self._max_size:
            return

        if self._eviction_policy == "fifo":
            oldest_key = min(self._store.items(), key=lambda item: item[1].stored_at)[0]
        else:  # default to LRU
            oldest_key = min(self._access_times.items(), key=lambda item: item[1])[0]

        del self._store[oldest_key]
        self._access_times.pop(oldest_key, None)


@dataclass(frozen=True)
class _CacheEntry:
    """Internal cache entry with metadata for eviction policies."""

    result: SerializedAnalysisResult
    stored_at: float


def _collect_ranked_variables(
    ranked_insights: Sequence[RankedInsightModel],
    limit: int,
) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for insight in ranked_insights:
        for driver in insight.drivers:
            if driver in seen:
                continue
            seen.add(driver)
            ordered.append(driver)
            if len(ordered) >= limit:
                return ordered
    return ordered


def export_reduced_dataset(
    frame: pd.DataFrame,
    ranked_or_result: SerializedAnalysisResult | Sequence[RankedInsightModel],
    *,
    top_n: int,
    include_columns: Sequence[str] = (),
) -> pd.DataFrame:
    """Return a reduced dataset containing the top-N variables from insights."""

    if top_n <= 0:
        raise ValueError("top_n must be a positive integer")

    if isinstance(ranked_or_result, SerializedAnalysisResult):
        ranked_insights = list(ranked_or_result.ranked_insights)
    else:
        ranked_insights = list(ranked_or_result)

    ranked_variables = _collect_ranked_variables(ranked_insights, top_n)
    columns = list(dict.fromkeys([*include_columns, *ranked_variables]))
    if not columns:
        raise ValueError(
            "Cannot export dataset: no ranked insights available and no include_columns provided."
        )

    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"Columns not found in frame: {sorted(missing)!r}")

    return frame.loc[:, columns].copy()


__all__ = [
    "AISummaryModel",
    "AutoTriageResultModel",
    "CorrelationRecordModel",
    "CorrelationTableModel",
    "MultivariateSummaryModel",
    "QualityFlagModel",
    "RankedInsightModel",
    "ResultKey",
    "ResultStorage",
    "SerializedAnalysisResult",
    "SignatureBuilder",
    "CorrelationResultSerializer",
    "MultivariateResultSerializer",
    "AutoTriageResultSerializer",
    "create_serialized_result",
    "export_reduced_dataset",
    "serialize_auto_triage",
    "serialize_correlation_table",
    "serialize_multivariate_summary",
]
