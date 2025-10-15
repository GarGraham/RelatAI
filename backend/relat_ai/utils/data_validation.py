"""Data validation helpers ensuring serialized results remain clean."""

from __future__ import annotations

import math
from typing import Any, Iterable, Iterator

import pandas as pd

try:  # pragma: no cover - optional dependency
    import great_expectations as ge
except ImportError:  # pragma: no cover - optional dependency
    ge = None

from relat_ai.core.results import SerializedAnalysisResult


class DataValidationError(RuntimeError):
    """Raised when serialized analysis payloads fail validation checks."""


def _iter_numerics(payload: Any, prefix: tuple[str, ...] = ()) -> Iterator[tuple[str, float]]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            yield from _iter_numerics(value, prefix + (str(key),))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            yield from _iter_numerics(item, prefix + (str(index),))
    elif isinstance(payload, (float, int)):
        yield (" -> ".join(prefix), float(payload))


def _extract_tabular_payloads(result: SerializedAnalysisResult) -> Iterable[pd.DataFrame]:
    tables: list[pd.DataFrame] = []
    if result.ranked_insights:
        tables.append(pd.DataFrame([insight.model_dump() for insight in result.ranked_insights]))
    if result.auto_triage_result and result.auto_triage_result.suspicion_rankings:
        tables.append(
            pd.DataFrame(
                [ranking.model_dump() for ranking in result.auto_triage_result.suspicion_rankings]
            )
        )
    return tables


def validate_serialized_result(result: SerializedAnalysisResult) -> None:
    """Ensure serialized payloads do not contain NaN or infinite numeric values."""

    payload = result.model_dump()
    offenders = [
        location
        for location, value in _iter_numerics(payload)
        if math.isnan(value) or math.isinf(value)
    ]
    if offenders:
        joined = ", ".join(offenders)
        raise DataValidationError(
            f"Serialized analysis result contains invalid numerics at: {joined}"
        )

    if ge is None:
        return

    for table in _extract_tabular_payloads(result):
        if table.empty:
            continue
        dataset = ge.dataset.PandasDataset(table)
        for column in table.columns:
            if table[column].dtype.kind in {"f", "i"}:
                dataset.expect_column_values_to_not_be_null(column)
                dataset.expect_column_values_to_not_be_in_set(column, [math.inf, -math.inf])
        dataset.validate()


__all__ = ["DataValidationError", "validate_serialized_result"]
