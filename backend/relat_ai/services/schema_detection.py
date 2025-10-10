"""Schema detection utilities for uploaded datasets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class ColumnProfile:
    """Summary statistics for a column used to drive analysis selection."""

    name: str
    dtype: str
    non_null_count: int
    sample_values: list[Any]


@dataclass(slots=True)
class DatasetProfile:
    """Aggregated dataset profile information."""

    row_count: int
    column_count: int
    columns: list[ColumnProfile]


NUMERIC_KINDS = {"i", "u", "f"}
DATETIME_KINDS = {"M"}


def profile_frame(frame: pd.DataFrame) -> DatasetProfile:
    """Generate a dataset profile used for UI defaults and analysis configuration."""

    column_profiles = [profile_column(frame[column]) for column in frame.columns]
    return DatasetProfile(
        row_count=len(frame.index),
        column_count=len(frame.columns),
        columns=column_profiles,
    )


def profile_column(series: pd.Series) -> ColumnProfile:
    """Profile an individual Pandas Series."""

    dtype_kind = series.dtype.kind
    if dtype_kind in NUMERIC_KINDS:
        logical_type = "numeric"
    elif dtype_kind in DATETIME_KINDS:
        logical_type = "datetime"
    elif dtype_kind == "b":
        logical_type = "boolean"
    else:
        logical_type = "categorical"

    non_null = int(series.notna().sum())
    samples = series.dropna().head(5).tolist()

    return ColumnProfile(
        name=str(series.name),
        dtype=logical_type,
        non_null_count=non_null,
        sample_values=samples,
    )
