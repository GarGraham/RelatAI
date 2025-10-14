"""Unit tests for result serialization and storage helpers."""

from __future__ import annotations

import time

import pandas as pd
import pytest

from relat_ai.core.models import DatasetConfiguration
from relat_ai.core.results import RankedInsightModel, SerializedAnalysisResult
from relat_ai.services.analysis.utils import AnalysisResult, CorrelationRecord
from relat_ai.services.results import (
    ResultKey,
    ResultStorage,
    SignatureBuilder,
    create_serialized_result,
    export_reduced_dataset,
    serialize_correlation_table,
)


def test_serialize_correlation_table_generates_ranked_insights() -> None:
    """Correlation serialization should produce ranked insights with metadata."""

    result = AnalysisResult(
        correlations=[
            CorrelationRecord(
                variables=("temperature", "pressure"),
                coefficient=0.82,
                p_value=0.001,
                sample_size=120,
                method="pearson",
            ),
            CorrelationRecord(
                variables=("temperature", "humidity"),
                coefficient=-0.45,
                p_value=0.02,
                sample_size=110,
                method="spearman",
            ),
        ]
    )

    table, ranked = serialize_correlation_table(result)

    assert len(table.records) == 2
    assert table.records[0].variables == ("temperature", "pressure")
    assert [insight.label for insight in ranked] == [
        "temperature vs pressure",
        "temperature vs humidity",
    ]
    assert all(insight.category == "correlation" for insight in ranked)
    assert ranked[0].score >= ranked[1].score


def test_result_storage_uses_dataset_hash_in_key() -> None:
    """Result storage should distinguish entries by dataset hash and configuration."""

    configuration = DatasetConfiguration(dataset_id="dataset", selected_columns=["a", "b"])
    config_signature = SignatureBuilder.for_configuration(configuration)
    filters_signature = SignatureBuilder.for_filters(configuration.filters)

    base_result = create_serialized_result(
        dataset_id="dataset",
        dataset_hash="hash-1",
        configuration=configuration,
        analysis_mode="correlation",
    )

    storage = ResultStorage()
    key = ResultKey(
        dataset_id="dataset",
        dataset_hash="hash-1",
        analysis_mode="correlation",
        configuration_signature=config_signature,
        filters_signature=filters_signature,
    )
    storage.store(key, base_result)

    assert storage.get(key) is base_result

    different_hash_key = ResultKey(
        dataset_id="dataset",
        dataset_hash="hash-2",
        analysis_mode="correlation",
        configuration_signature=config_signature,
        filters_signature=filters_signature,
    )
    assert storage.get(different_hash_key) is None


def test_result_storage_invalidation_and_dataset_clear() -> None:
    """Result storage should support targeted and dataset-wide invalidation."""

    configuration = DatasetConfiguration(dataset_id="dataset", selected_columns=["a", "b"])
    config_signature = SignatureBuilder.for_configuration(configuration)
    filters_signature = SignatureBuilder.for_filters(configuration.filters)

    base_result = create_serialized_result(
        dataset_id="dataset",
        dataset_hash="hash-1",
        configuration=configuration,
        analysis_mode="correlation",
    )

    storage = ResultStorage()
    first_key = ResultKey(
        dataset_id="dataset",
        dataset_hash="hash-1",
        analysis_mode="correlation",
        configuration_signature=config_signature,
        filters_signature=filters_signature,
    )
    second_key = ResultKey(
        dataset_id="dataset",
        dataset_hash="hash-2",
        analysis_mode="correlation",
        configuration_signature=config_signature,
        filters_signature=filters_signature,
    )

    storage.store(first_key, base_result)
    storage.store(second_key, base_result)

    assert storage.size() == 2
    assert set(storage.keys()) == {first_key, second_key}
    assert storage.invalidate(first_key) is True
    assert storage.invalidate(first_key) is False
    assert storage.size() == 1
    assert storage.invalidate_dataset("dataset") == 1
    assert storage.size() == 0


def test_result_storage_respects_ttl() -> None:
    """Entries should expire once their TTL has elapsed."""

    configuration = DatasetConfiguration(dataset_id="dataset", selected_columns=["a", "b"])
    config_signature = SignatureBuilder.for_configuration(configuration)
    filters_signature = SignatureBuilder.for_filters(configuration.filters)

    result = create_serialized_result(
        dataset_id="dataset",
        dataset_hash="hash-ttl",
        configuration=configuration,
        analysis_mode="correlation",
    )

    storage = ResultStorage(ttl_seconds=0.001)
    key = ResultKey(
        dataset_id="dataset",
        dataset_hash="hash-ttl",
        analysis_mode="correlation",
        configuration_signature=config_signature,
        filters_signature=filters_signature,
    )
    storage.store(key, result)
    time.sleep(0.002)

    assert storage.get(key) is None
    assert storage.size() == 0


def test_export_reduced_dataset_respects_ranked_insights() -> None:
    """Reduced dataset export should include top-N driver columns."""

    frame = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "temperature": [70, 72, 68],
            "pressure": [30, 29, 31],
            "humidity": [0.5, 0.55, 0.6],
        }
    )

    ranked = [
        RankedInsightModel(label="temperature vs pressure", score=0.9, drivers=["temperature", "pressure"]),
        RankedInsightModel(label="humidity", score=0.4, drivers=["humidity"]),
    ]

    serialized = SerializedAnalysisResult(
        dataset_id="dataset",
        dataset_hash="hash-1",
        analysis_mode="correlation",
        configuration_signature="config",
        filters_signature="filters",
        ranked_insights=ranked,
    )

    reduced = export_reduced_dataset(frame, serialized, top_n=2, include_columns=["id"])

    assert list(reduced.columns) == ["id", "temperature", "pressure"]


def test_export_reduced_dataset_accepts_ranked_sequence() -> None:
    """Callers can pass ranked insights directly without wrapping in result."""

    frame = pd.DataFrame(
        {
            "temperature": [70, 72, 68],
            "pressure": [30, 29, 31],
            "humidity": [0.5, 0.55, 0.6],
        }
    )

    ranked = [
        RankedInsightModel(label="temperature vs pressure", score=0.9, drivers=["temperature", "pressure"]),
        RankedInsightModel(label="humidity", score=0.4, drivers=["humidity"]),
    ]

    reduced = export_reduced_dataset(frame, ranked, top_n=2)

    assert list(reduced.columns) == ["temperature", "pressure"]


def test_export_reduced_dataset_requires_ranked_or_columns() -> None:
    """Meaningful error should be raised when no columns can be determined."""

    frame = pd.DataFrame({"temperature": [70, 72], "pressure": [30, 29]})

    with pytest.raises(ValueError, match="no ranked insights available"):
        export_reduced_dataset(frame, [], top_n=1)
