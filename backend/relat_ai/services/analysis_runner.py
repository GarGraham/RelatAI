"""Orchestrate execution of statistical analyses exposed via the API layer."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from pydantic import ValidationError

from relat_ai.config import (
    get_auto_triage_suspicion_top_k,
)
from relat_ai.core.config import get_settings
from relat_ai.core.models import DatasetConfiguration
from relat_ai.core.results import (
    AnalysisParameterOverrides,
    AnalysisResultResponse,
    AnalysisRunRequest,
    SerializedAnalysisResult,
)
from relat_ai.services.analysis import (
    AutoTriageConfig,
    RegressionPlan,
    compute_pairwise_correlations,
    build_multivariate_models,
    run_auto_triage,
)
from relat_ai.services.audit_trail import get_audit_log, record_guardrail_override
from relat_ai.services.configuration import (
    ConfigurationValidator,
    apply_configuration_to_frame,
    get_configuration,
    initialise_configuration,
    normalise_configuration,
)
from relat_ai.services.ingestion import DatasetRecord, get_registry, load_frame
from relat_ai.services.results import (
    ResultKey,
    ResultStorage,
    SignatureBuilder,
    create_serialized_result,
)
from relat_ai.services.summarization import SummarizationService
from relat_ai.utils.data_validation import DataValidationError, validate_serialized_result


class DatasetNotFoundError(LookupError):
    """Raised when an analysis is requested for an unknown dataset."""


class AnalysisExecutionError(ValueError):
    """Raised when an analysis cannot be executed with the provided inputs."""


_RESULT_STORAGE: ResultStorage | None = None
_SUMMARIZER: SummarizationService | None = None


def get_result_storage() -> ResultStorage:
    """Return the process-wide analysis result cache."""

    global _RESULT_STORAGE
    if _RESULT_STORAGE is None:
        _RESULT_STORAGE = ResultStorage()
    return _RESULT_STORAGE


def get_summarizer() -> SummarizationService:
    """Return a lazily-instantiated summarization service."""

    global _SUMMARIZER
    if _SUMMARIZER is None:
        _SUMMARIZER = SummarizationService()
    return _SUMMARIZER


def execute_analysis(
    dataset_id: str,
    request: AnalysisRunRequest | None = None,
) -> AnalysisResultResponse:
    """Execute the requested analysis and return a structured response."""

    payload = request or AnalysisRunRequest()
    record = _get_dataset_record(dataset_id)

    configuration = _resolve_configuration(dataset_id, record)
    if payload.parameters is not None:
        configuration = _apply_overrides(configuration, payload.parameters, record)
    if payload.mode is not None:
        configuration.analysis_mode = payload.mode

    try:
        configuration = normalise_configuration(dataset_id, configuration, record.profile)
    except ValidationError as exc:
        raise AnalysisExecutionError(_format_validation_error(exc)) from exc
    except ValueError as exc:
        raise AnalysisExecutionError(str(exc)) from exc

    frame = load_frame(record.metadata.path)
    filtered = apply_configuration_to_frame(frame, configuration)
    if filtered.empty:
        raise AnalysisExecutionError(
            "Configuration filters removed all rows; unable to execute analysis."
        )

    dataset_hash = _resolve_dataset_hash(dataset_id, record.metadata.path)
    parameters_payload = (
        payload.parameters.model_dump(exclude_none=True) if payload.parameters else None
    )

    cache_key = _build_cache_key(configuration, dataset_id, dataset_hash, parameters_payload)
    storage = get_result_storage()
    cached = storage.get(cache_key)
    if cached is not None:
        return AnalysisResultResponse(
            dataset_id=dataset_id,
            analysis_id=_build_analysis_id(cache_key),
            analysis_mode=configuration.analysis_mode,
            configuration=configuration,
            cached=True,
            result=cached,
        )

    serialized = _run_analysis_pipeline(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        configuration=configuration,
        filtered=filtered,
        parameters=parameters_payload,
        record=record,
    )

    try:
        validate_serialized_result(serialized)
    except DataValidationError as exc:
        raise AnalysisExecutionError(str(exc)) from exc

    storage.store(cache_key, serialized)
    return AnalysisResultResponse(
        dataset_id=dataset_id,
        analysis_id=_build_analysis_id(cache_key),
        analysis_mode=configuration.analysis_mode,
        configuration=configuration,
        cached=False,
        result=serialized,
    )


def _get_dataset_record(dataset_id: str) -> DatasetRecord:
    record = get_registry().get(dataset_id)
    if record is None:
        raise DatasetNotFoundError(f"Dataset '{dataset_id}' was not found")
    return record


def _resolve_configuration(
    dataset_id: str, record: DatasetRecord
) -> DatasetConfiguration:
    configuration = get_configuration(dataset_id)
    if configuration is None:
        configuration = initialise_configuration(dataset_id, record.profile)
    else:
        configuration = configuration.model_copy(deep=True)
    return configuration


def _apply_overrides(
    configuration: DatasetConfiguration,
    overrides: AnalysisParameterOverrides,
    record: DatasetRecord,
) -> DatasetConfiguration:
    validator = ConfigurationValidator(record.profile)
    updated = configuration.model_copy(deep=True)

    if overrides.selected_columns is not None:
        updated.selected_columns = validator.ensure_selected_columns(overrides.selected_columns)
        updated.anchor_columns = validator.prune_missing_anchors(
            updated.anchor_columns, updated.selected_columns
        )
        if updated.max_variables > len(updated.selected_columns):
            updated.max_variables = len(updated.selected_columns)

    if overrides.anchor_columns is not None:
        updated.anchor_columns = validator.validate_anchor_columns(
            overrides.anchor_columns, updated.selected_columns
        )

    if overrides.max_variables is not None:
        max_variables = validator.validate_max_variables(
            overrides.max_variables, len(updated.selected_columns)
        )
        if max_variables is not None:
            updated.max_variables = max_variables

    if overrides.interaction_depth is not None:
        interaction_depth = validator.validate_interaction_depth(overrides.interaction_depth)
        if interaction_depth is not None:
            updated.interaction_depth = interaction_depth

    if overrides.include_interactions is not None:
        updated.include_interactions = overrides.include_interactions

    if overrides.filters is not None:
        if not overrides.filters:
            updated.filters = {}
        else:
            validated_filters = validator.validate_filters(overrides.filters)
            for column in list(updated.filters.keys()):
                if column in overrides.filters and column not in validated_filters:
                    updated.filters.pop(column, None)
            updated.filters.update(validated_filters)

    return DatasetConfiguration.model_validate(updated.model_dump())


def _build_cache_key(
    configuration: DatasetConfiguration,
    dataset_id: str,
    dataset_hash: str,
    parameters: Mapping[str, object] | None,
) -> ResultKey:
    return ResultKey(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        analysis_mode=configuration.analysis_mode,
        configuration_signature=SignatureBuilder.for_configuration(configuration),
        filters_signature=SignatureBuilder.for_filters(configuration.filters),
        parameters_signature=SignatureBuilder.for_parameters(parameters),
    )


def _build_analysis_id(key: ResultKey) -> str:
    joined = "|".join(key.as_tuple())
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def _resolve_dataset_hash(dataset_id: str, path: Path) -> str:
    log = get_audit_log(dataset_id)
    if log is not None:
        return log.dataset_hash

    digest = hashlib.sha256()
    with path.open("rb") as buffer:
        for chunk in iter(lambda: buffer.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_analysis_pipeline(
    *,
    dataset_id: str,
    dataset_hash: str,
    configuration: DatasetConfiguration,
    filtered: pd.DataFrame,
    parameters: Mapping[str, object] | None,
    record: DatasetRecord,
) -> SerializedAnalysisResult:
    mode = configuration.analysis_mode

    if mode == "correlation":
        return _run_correlation(dataset_id, dataset_hash, configuration, filtered, parameters)
    if mode == "multivariate":
        return _run_multivariate(dataset_id, dataset_hash, configuration, filtered, parameters)
    if mode == "auto_triage":
        return _run_auto_triage(dataset_id, dataset_hash, configuration, filtered, parameters, record)

    raise AnalysisExecutionError(f"Unsupported analysis mode: {mode}")


def _run_correlation(
    dataset_id: str,
    dataset_hash: str,
    configuration: DatasetConfiguration,
    filtered: pd.DataFrame,
    parameters: Mapping[str, object] | None,
) -> SerializedAnalysisResult:
    columns = configuration.selected_columns or list(filtered.columns)
    if len(columns) < 2:
        raise AnalysisExecutionError(
            "Correlation analysis requires at least two selected columns."
        )

    result = compute_pairwise_correlations(
        filtered,
        columns,
        dataset_id=dataset_id,
    )
    summary = get_summarizer().summarize(result)

    return create_serialized_result(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        configuration=configuration,
        analysis_mode="correlation",
        result=result,
        filters=configuration.filters,
        parameters=parameters,
        ai_summary_text=summary,
    )


def _run_multivariate(
    dataset_id: str,
    dataset_hash: str,
    configuration: DatasetConfiguration,
    filtered: pd.DataFrame,
    parameters: Mapping[str, object] | None,
) -> SerializedAnalysisResult:
    columns = configuration.selected_columns
    if len(columns) < 2:
        raise AnalysisExecutionError(
            "Multivariate analysis requires at least one response and one predictor column."
        )

    responses = configuration.anchor_columns or [columns[0]]
    regression_configs: list = []
    interaction_depth = configuration.interaction_depth if configuration.include_interactions else 1

    for response in responses:
        if response not in columns:
            continue
        predictors = [column for column in columns if column != response]
        if not predictors:
            continue
        max_predictors = max(1, min(configuration.max_variables, len(predictors)))
        plan = RegressionPlan(
            response=response,
            candidate_predictors=predictors,
            anchor_predictors=[anchor for anchor in responses if anchor != response and anchor in predictors],
            max_predictors=max_predictors,
            interaction_depth=interaction_depth,
        )
        regression_configs.extend(plan.build_configs())

    if not regression_configs:
        raise AnalysisExecutionError(
            "Unable to construct regression models with the provided configuration."
        )

    result = build_multivariate_models(filtered, regression_configs)
    summary = get_summarizer().summarize(result)

    return create_serialized_result(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        configuration=configuration,
        analysis_mode="multivariate",
        result=result,
        filters=configuration.filters,
        parameters=parameters,
        ai_summary_text=summary,
    )


def _run_auto_triage(
    dataset_id: str,
    dataset_hash: str,
    configuration: DatasetConfiguration,
    filtered: pd.DataFrame,
    parameters: Mapping[str, object] | None,
    record: DatasetRecord,
) -> SerializedAnalysisResult:
    selected = configuration.selected_columns or list(filtered.columns)
    numeric, categorical, datetime_column = _partition_columns(record, selected)
    if not numeric:
        raise AnalysisExecutionError(
            "Auto-triage analysis requires at least one numeric column."
        )

    settings = get_settings()
    auto_config = AutoTriageConfig(
        numeric_columns=numeric,
        categorical_columns=categorical,
        datetime_column=datetime_column,
        suspicion_top_k=get_auto_triage_suspicion_top_k(),
        emit_structured_payloads=settings.auto_triage_explainability,
    )
    _apply_auto_triage_guardrails(dataset_id, auto_config)
    result = run_auto_triage(filtered, auto_config)

    return create_serialized_result(
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        configuration=configuration,
        analysis_mode="auto_triage",
        result=result,
        filters=configuration.filters,
        parameters=parameters,
    )


def _partition_columns(
    record: DatasetRecord, selected: Sequence[str]
) -> tuple[list[str], list[str], str | None]:
    column_types = {column.name: column.logical_type for column in record.profile.columns}

    numeric: list[str] = []
    categorical: list[str] = []
    datetime_column: str | None = None

    for column in selected:
        logical_type = column_types.get(column)
        if logical_type == "numeric":
            numeric.append(column)
        elif logical_type in {"categorical", "boolean"}:
            categorical.append(column)
        elif logical_type == "datetime" and datetime_column is None:
            datetime_column = column

    return numeric, categorical, datetime_column


__all__ = [
    "AnalysisExecutionError",
    "AnalysisResultResponse",
    "DatasetNotFoundError",
    "execute_analysis",
    "get_result_storage",
]


def _apply_auto_triage_guardrails(dataset_id: str, config: AutoTriageConfig) -> None:
    """Enforce upper bounds on clustering and PCA settings."""

    overrides: list[tuple[str, int, int]] = []
    max_clusters = 12
    max_components = 8

    if config.kmeans_clusters > max_clusters:
        overrides.append(("kmeans_clusters", config.kmeans_clusters, max_clusters))
        config.kmeans_clusters = max_clusters
    if config.hierarchical_clusters > max_clusters:
        overrides.append(("hierarchical_clusters", config.hierarchical_clusters, max_clusters))
        config.hierarchical_clusters = max_clusters
    if config.max_components > max_components:
        overrides.append(("max_components", config.max_components, max_components))
        config.max_components = max_components

    for field, original, enforced in overrides:
        record_guardrail_override(
            dataset_id,
            guardrail=field,
            original_value=original,
            enforced_value=enforced,
        )


def _format_validation_error(error: ValidationError) -> str:
    """Return a concise, actionable error message from a validation error."""

    segments = []
    for entry in error.errors():
        location = " -> ".join(str(part) for part in entry.get("loc", ()) if part is not None)
        message = entry.get("msg", "Invalid value")
        if location:
            segments.append(f"{location}: {message}")
        else:
            segments.append(message)
    formatted = "; ".join(segments)
    return f"Configuration validation failed: {formatted}" if formatted else str(error)

