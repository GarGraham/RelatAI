"""Schema detection utilities for uploaded datasets."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class ColumnProfile(BaseModel):
    """Summary statistics for a column used to drive analysis selection."""

    model_config = ConfigDict(frozen=True)

    name: str
    logical_type: str
    pandas_dtype: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list[Any] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class DatasetProfile(BaseModel):
    """Aggregated dataset profile information."""

    model_config = ConfigDict(frozen=True)

    dataset_id: str
    name: str
    row_count: int
    column_count: int
    missing_cell_count: int
    memory_usage_bytes: int
    columns: list[ColumnProfile]


NUMERIC_KINDS = {"i", "u", "f"}
DATETIME_KINDS = {"M"}


def profile_frame(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    dataset_name: str,
    sample_size: int | None = None,
) -> DatasetProfile:
    """Generate a dataset profile used for UI defaults and analysis configuration."""

    column_profiles = [
        profile_column(frame[column], sample_size=sample_size) for column in frame.columns
    ]
    return DatasetProfile(
        dataset_id=dataset_id,
        name=dataset_name,
        row_count=len(frame.index),
        column_count=len(frame.columns),
        missing_cell_count=int(frame.isna().sum().sum()),
        memory_usage_bytes=int(frame.memory_usage(deep=True).sum()),
        columns=column_profiles,
    )


def profile_column(series: pd.Series, *, sample_size: int | None = None) -> ColumnProfile:
    """Profile an individual Pandas Series."""

    dtype_kind = series.dtype.kind
    logical_type = _resolve_logical_type(series, dtype_kind)

    non_null = int(series.notna().sum())
    null_count = int(len(series.index) - non_null)
    unique_count = int(series.nunique(dropna=True))
    samples = series.dropna().head(5).tolist()

    stats: dict[str, Any]
    if logical_type == "numeric":
        stats = _numeric_stats(series, sample_size)
    elif logical_type == "datetime":
        stats = _datetime_stats(series)
    elif logical_type == "boolean":
        stats = _boolean_stats(series)
    elif logical_type == "text":
        stats = _text_stats(series)
    else:
        stats = _categorical_stats(series)

    return ColumnProfile(
        name=str(series.name),
        logical_type=logical_type,
        pandas_dtype=str(series.dtype),
        non_null_count=non_null,
        null_count=null_count,
        unique_count=unique_count,
        sample_values=samples,
        stats=stats,
    )


def to_model(profile: DatasetProfile):
    """Convert a dataset profile dataclass to the API response model."""

    from relat_ai.core.models import DatasetProfileModel

    return DatasetProfileModel.model_validate(profile.model_dump())


def _resolve_logical_type(series: pd.Series, dtype_kind: str) -> str:
    """Infer a logical type from a pandas dtype and heuristics."""

    if dtype_kind in NUMERIC_KINDS:
        return "numeric"
    if dtype_kind in DATETIME_KINDS:
        return "datetime"
    if dtype_kind == "b":
        return "boolean"

    non_null = series.dropna()
    if non_null.empty:
        return "categorical"

    unique_ratio = len(non_null.unique()) / len(non_null)
    avg_length = non_null.astype(str).str.len().mean()

    if unique_ratio > 0.6 or avg_length > 50:
        return "text"
    return "categorical"


def _numeric_stats(series: pd.Series, sample_size: int | None) -> dict[str, Any]:
    """Return descriptive stats for numeric columns using sampling when needed."""

    clean = _prepare_clean_series(
        series,
        converter=lambda s: pd.to_numeric(s, errors="coerce"),
        sample_size=sample_size,
    )

    if clean.empty:
        return {"min": None, "max": None, "mean": None, "std": None}

    return {
        "min": float(clean.min()),
        "max": float(clean.max()),
        "mean": float(clean.mean()),
        "std": float(clean.std(ddof=0)) if len(clean) > 1 else 0.0,
    }


def _datetime_stats(series: pd.Series) -> dict[str, Any]:
    """Return descriptive stats for datetime columns."""

    clean = _prepare_clean_series(series)
    if clean.empty:
        return {"earliest": None, "latest": None}

    as_datetime = _prepare_clean_series(
        clean, converter=lambda s: pd.to_datetime(s, errors="coerce", utc=True)
    )
    if as_datetime.empty:
        return {"earliest": None, "latest": None}

    return {
        "earliest": as_datetime.min().isoformat(),
        "latest": as_datetime.max().isoformat(),
    }


def _boolean_stats(series: pd.Series) -> dict[str, Any]:
    """Return value counts for boolean columns."""

    true_count = int((series == True).sum())  # noqa: E712
    false_count = int((series == False).sum())  # noqa: E712
    return {"true": true_count, "false": false_count}


def _categorical_stats(series: pd.Series) -> dict[str, Any]:
    """Return top category frequencies for categorical features."""

    clean = _prepare_clean_series(series, converter=lambda s: s.astype(str))
    if clean.empty:
        return {"top_values": []}

    counts = clean.value_counts().head(3)
    return {
        "top_values": [
            {"value": str(index), "count": int(count)} for index, count in counts.items()
        ]
    }


def _text_stats(series: pd.Series) -> dict[str, Any]:
    """Return aggregate metrics for free-text columns."""

    clean = _prepare_clean_series(series, converter=lambda s: s.astype(str))
    if clean.empty:
        return {"avg_length": 0.0, "unique_ratio": 0.0}

    lengths = clean.str.len()
    unique_ratio = len(clean.unique()) / len(clean)
    return {
        "avg_length": float(lengths.mean()),
        "unique_ratio": float(unique_ratio),
    }


def _prepare_clean_series(
    series: pd.Series,
    *,
    converter: Callable[[pd.Series], pd.Series] | None = None,
    sample_size: int | None = None,
) -> pd.Series:
    """Normalise a series before computing statistics.

    The helper consolidates the repeated patterns of dropping missing values,
    applying a conversion, and optionally sampling.
    """

    clean = series.dropna()
    if converter is not None:
        clean = converter(clean)
    if hasattr(clean, "dropna"):
        clean = clean.dropna()
    if sample_size and len(clean) > sample_size:
        clean = clean.sample(sample_size, random_state=0)
    return clean
