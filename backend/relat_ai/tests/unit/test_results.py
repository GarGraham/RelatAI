"""Unit tests for result serialization and storage helpers."""

from __future__ import annotations

import pandas as pd

from relat_ai.core.models import DatasetConfiguration
from relat_ai.core.results import RankedInsightModel, SerializedAnalysisResult
from relat_ai.services.analysis.utils import AnalysisResult, CorrelationRecord
from relat_ai.services.results import (
    ResultKey,
    ResultStorage,
    build_configuration_signature,
    build_filters_signature,
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
    config_signature = build_configuration_signature(configuration)
    filters_signature = build_filters_signature(configuration.filters)

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
