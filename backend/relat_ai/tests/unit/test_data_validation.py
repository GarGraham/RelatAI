from __future__ import annotations

import math

import pytest

from relat_ai.core.results import RankedInsightModel, SerializedAnalysisResult
from relat_ai.utils.data_validation import DataValidationError, validate_serialized_result


def test_validate_serialized_result_rejects_nan() -> None:
    insight = RankedInsightModel.model_construct(
        label="test",
        score=math.nan,
        drivers=["a"],
        category="auto_triage",
        method="variable",
    )
    payload = SerializedAnalysisResult.model_construct(
        dataset_id="ds",
        dataset_hash="hash",
        analysis_mode="correlation",
        configuration_signature="sig",
        filters_signature="filters",
        ranked_insights=[insight],
    )

    with pytest.raises(DataValidationError):
        validate_serialized_result(payload)
