"""Serialization helpers and storage for analysis results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

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


def _stable_dumps(payload: Any) -> str:
    """Return a JSON dump with stable key ordering."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _normalise_sequence(values: Sequence[Any]) -> list[str]:
    """Convert a sequence into a list of stringified values preserving order."""

    return [str(value) for value in values]


def build_configuration_signature(configuration: DatasetConfiguration) -> str:
    """Build a deterministic signature for dataset configuration settings."""

    payload = {
        "analysis_mode": configuration.analysis_mode,
        "selected_columns": configuration.selected_columns,
        "anchor_columns": configuration.anchor_columns,
        "include_interactions": configuration.include_interactions,
        "max_variables": configuration.max_variables,
        "interaction_depth": configuration.interaction_depth,
    }
    return _stable_dumps(payload)


def build_filters_signature(filters: Mapping[str, Sequence[Any]]) -> str:
    """Build a deterministic signature for active dataset filters."""

    normalised = {
        column: _normalise_sequence(sorted(values, key=lambda value: str(value)))
        for column, values in sorted(filters.items(), key=lambda item: item[0])
    }
    return _stable_dumps(normalised)


def build_parameters_signature(parameters: Mapping[str, Any] | None) -> str | None:
    """Return a deterministic signature for analysis-specific parameters."""

    if parameters is None:
        return None
    return _stable_dumps(parameters)


def _convert_quality_flags(flags: Sequence[QualityFlag] | None) -> list[QualityFlagModel]:
    """Convert quality flag dataclasses into Pydantic models."""

    if not flags:
        return []
    return [
        QualityFlagModel(code=flag.code, message=flag.message, severity=flag.severity)
        for flag in flags
    ]


def _convert_correlation_extras(extras: Any) -> CorrelationExtrasANOVAModel | CorrelationExtrasChiSquareModel | None:
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


def serialize_correlation_table(
    result: AnalysisResult,
    *,
    table_flags: Sequence[QualityFlag] | None = None,
) -> tuple[CorrelationTableModel, list[RankedInsightModel]]:
    """Serialize correlation records into API-ready models and ranked insights."""

    records: list[CorrelationRecordModel] = []
    ranked: list[RankedInsightModel] = []
    for record in result.correlations or []:
        extras = _convert_correlation_extras(record.extras)
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
        quality_flags=_convert_quality_flags(table_flags),
    )
    return table, ranked


def _convert_diagnostics(diagnostics: RegressionDiagnostics | None) -> RegressionDiagnosticsModel | None:
    if diagnostics is None:
        return None
    return RegressionDiagnosticsModel(
        variance_inflation_factors=dict(diagnostics.variance_inflation_factors)
    )


def serialize_multivariate_summary(
    models: Iterable[ModelSummary],
    *,
    summary_flags: Sequence[QualityFlag] | None = None,
) -> tuple[MultivariateSummaryModel, list[RankedInsightModel]]:
    """Serialize multivariate model summaries."""

    serialised_models: list[ModelSummaryModel] = []
    ranked: list[RankedInsightModel] = []
    for model in models:
        metrics = model.metrics
        if isinstance(metrics, RegressionMetrics):
            metrics_model: RegressionMetricsModel | ANOVAMetricsModel = RegressionMetricsModel(
                r_squared=metrics.r_squared,
                adjusted_r_squared=metrics.adjusted_r_squared,
                aic=metrics.aic,
                bic=metrics.bic,
                cohen_f2=metrics.cohen_f2,
            )
            score = float(metrics.r_squared)
        elif isinstance(metrics, ANOVAMetrics):
            metrics_model = ANOVAMetricsModel(
                f_statistic=metrics.f_statistic,
                p_value=metrics.p_value,
                df_factor=metrics.df_factor,
                df_residual=metrics.df_residual,
                effect_size=metrics.effect_size,
            )
            score = float(metrics.f_statistic)
        else:  # pragma: no cover - defensive fallback
            metrics_model = RegressionMetricsModel.model_validate(metrics)
            score = 0.0

        serialised_models.append(
            ModelSummaryModel(
                response=model.response,
                predictors=list(model.predictors),
                model_type=model.model_type,
                metrics=metrics_model,
                sample_size=model.sample_size,
                notes=list(model.notes) if model.notes else None,
                diagnostics=_convert_diagnostics(model.diagnostics),
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
        quality_flags=_convert_quality_flags(summary_flags),
    )
    return summary, ranked


def _convert_top_contributors(contributors: Sequence[tuple[str, float]]) -> list[TopContributorModel]:
    return [TopContributorModel(feature=feature, loading=value) for feature, value in contributors]


def _convert_residual_buckets(buckets: Sequence[ResidualBucket]) -> list[ResidualBucketModel]:
    return [
        ResidualBucketModel(
            label=bucket.label,
            average_residual=bucket.average_residual,
            sample_size=bucket.sample_size,
            column_residuals=dict(bucket.column_residuals),
        )
        for bucket in buckets
    ]


def _convert_residual_forensics(
    residuals: Sequence[ResidualForensicsInsight],
) -> list[ResidualForensicsModel]:
    return [
        ResidualForensicsModel(
            grouping=insight.grouping,
            buckets=_convert_residual_buckets(insight.buckets),
        )
        for insight in residuals
    ]


def serialize_auto_triage(
    result: AutoTriageResult,
) -> tuple[AutoTriageResultModel, list[RankedInsightModel]]:
    """Serialize an auto-triage analysis result."""

    pca_components = [
        PCAComponentModel(
            component=insight.component,
            explained_variance_ratio=insight.explained_variance_ratio,
            top_contributors=_convert_top_contributors(insight.top_contributors),
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
    residual_forensics = _convert_residual_forensics(result.residual_forensics)

    suspicion_insights: list[RankedInsightModel] = []
    for score in result.suspicion_rankings:
        insight = RankedInsightModel(
            label=score.target,
            score=score.score,
            drivers=list(score.drivers),
            category="auto_triage",
            method=score.target_type,
        )
        suspicion_insights.append(insight)

    suspicion_insights.sort(key=lambda insight: insight.score, reverse=True)
    auto_triage_model = AutoTriageResultModel(
        pca_components=pca_components,
        change_points=change_points,
        clusters=clusters,
        residual_forensics=residual_forensics,
        suspicion_rankings=suspicion_insights,
        quality_flags=_convert_quality_flags(result.quality_flags),
    )
    return auto_triage_model, suspicion_insights


def create_serialized_result(
    *,
    dataset_id: str,
    dataset_hash: str,
    configuration: DatasetConfiguration,
    analysis_mode: AnalysisMode,
    correlation_result: AnalysisResult | None = None,
    multivariate_models: Iterable[ModelSummary] | None = None,
    auto_triage_result: AutoTriageResult | None = None,
    ai_summary_text: str | None = None,
    ai_summary_flags: Sequence[QualityFlag] | None = None,
    parameters_signature: str | None = None,
    quality_flags: Sequence[QualityFlag] | None = None,
) -> SerializedAnalysisResult:
    """Compose a serialized analysis result payload from component outputs."""

    config_signature = build_configuration_signature(configuration)
    filters_signature = build_filters_signature(configuration.filters)

    correlation_table: CorrelationTableModel | None = None
    ranked_insights: list[RankedInsightModel] = []

    if correlation_result is not None:
        correlation_table, ranked = serialize_correlation_table(correlation_result)
        ranked_insights.extend(ranked)

    multivariate_summary: MultivariateSummaryModel | None = None
    if multivariate_models is not None:
        summary, ranked = serialize_multivariate_summary(multivariate_models)
        multivariate_summary = summary
        ranked_insights.extend(ranked)

    auto_triage_model: AutoTriageResultModel | None = None
    if auto_triage_result is not None:
        auto_triage_model, ranked = serialize_auto_triage(auto_triage_result)
        ranked_insights.extend(ranked)

    ai_summary: AISummaryModel | None = None
    if ai_summary_text is not None:
        ai_summary = AISummaryModel(
            content=ai_summary_text,
            generated_at=datetime.now(timezone.utc),
            quality_flags=_convert_quality_flags(ai_summary_flags),
        )

    ranked_insights.sort(key=lambda insight: insight.score, reverse=True)

    return SerializedAnalysisResult(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        analysis_mode=analysis_mode,
        configuration_signature=config_signature,
        filters_signature=filters_signature,
        parameters_signature=parameters_signature,
        correlation_table=correlation_table,
        multivariate_summary=multivariate_summary,
        auto_triage=auto_triage_model,
        ranked_insights=ranked_insights,
        ai_summary=ai_summary,
        quality_flags=_convert_quality_flags(quality_flags),
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

    def __init__(self) -> None:
        self._store: dict[tuple[str, ...], SerializedAnalysisResult] = {}
        self._lock = RLock()

    def store(self, key: ResultKey, result: SerializedAnalysisResult) -> SerializedAnalysisResult:
        """Persist ``result`` under ``key`` and return the stored payload."""

        with self._lock:
            self._store[key.as_tuple()] = result
            return result

    def get(self, key: ResultKey) -> SerializedAnalysisResult | None:
        """Return a cached result if present."""

        with self._lock:
            return self._store.get(key.as_tuple())

    def clear(self) -> None:
        """Remove all cached results (useful for tests)."""

        with self._lock:
            self._store.clear()


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
    result: SerializedAnalysisResult,
    *,
    top_n: int,
    include_columns: Sequence[str] = (),
) -> pd.DataFrame:
    """Return a reduced dataset containing the top-N variables from insights."""

    if top_n <= 0:
        raise ValueError("top_n must be a positive integer")

    ranked_variables = _collect_ranked_variables(result.ranked_insights, top_n)
    columns = list(dict.fromkeys([*include_columns, *ranked_variables]))
    if not columns:
        raise ValueError("No columns available to export")

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
    "build_configuration_signature",
    "build_filters_signature",
    "build_parameters_signature",
    "create_serialized_result",
    "export_reduced_dataset",
    "serialize_auto_triage",
    "serialize_correlation_table",
    "serialize_multivariate_summary",
]
