"""Helpers for generating quality/confidence flags shared across analyses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping, Sequence

import numpy as np
import pandas as pd

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from .auto_triage import AutoTriageConfig, ChangePointInsight


@dataclass(slots=True)
class QualityFlag:
    """Confidence or data-quality indicator surfaced during an analysis run."""

    code: str
    message: str
    severity: str


class QualityFlagBuilder:
    """Factory for common quality flag patterns."""

    @staticmethod
    def low_sample_size(sample_size: int, min_threshold: int) -> QualityFlag | None:
        if sample_size < min_threshold:
            return QualityFlag(
                code="low_sample_size",
                message=(
                    "Fewer than %d records were available; findings may be unstable." % min_threshold
                ),
                severity="warning",
            )
        return None

    @staticmethod
    def high_missing_rate(column: str, ratio: float, threshold: float) -> QualityFlag | None:
        if ratio >= threshold:
            return QualityFlag(
                code=f"missing_{column}",
                message=(
                    f"Column '{column}' had {ratio:.0%} missing values; interpretations require caution."
                ),
                severity="warning",
            )
        return None

    @staticmethod
    def high_collinearity(max_corr: float, threshold: float) -> QualityFlag | None:
        if max_corr >= threshold:
            return QualityFlag(
                code="collinearity",
                message=(
                    "Strong collinearity detected between numeric columns; PCA components may overlap drivers."
                ),
                severity="info",
            )
        return None

    @staticmethod
    def no_change_points_detected(has_change_points: bool) -> QualityFlag | None:
        if not has_change_points:
            return QualityFlag(
                code="no_change_points",
                message="Change-point detectors did not identify strong shifts in the monitored period.",
                severity="info",
            )
        return None


def build_quality_flags(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    missing_ratio: Mapping[str, float],
    change_points: Sequence["ChangePointInsight"],
    config: "AutoTriageConfig",
) -> list[QualityFlag]:
    """Create confidence warnings based on dataset heuristics."""

    flags: list[QualityFlag] = []

    if flag := QualityFlagBuilder.low_sample_size(len(frame.index), config.min_sample_warning):
        flags.append(flag)

    for column, ratio in missing_ratio.items():
        if flag := QualityFlagBuilder.high_missing_rate(column, ratio, config.high_missing_threshold):
            flags.append(flag)

    if not numeric_data.empty:
        correlation_matrix = numeric_data.corr().abs()
        np.fill_diagonal(correlation_matrix.values, 0)
        max_corr = float(correlation_matrix.max().max())
    else:
        max_corr = 0.0
    if flag := QualityFlagBuilder.high_collinearity(max_corr, config.high_collinearity_threshold):
        flags.append(flag)

    has_change_points = any(insight.locations for insight in change_points)
    if flag := QualityFlagBuilder.no_change_points_detected(has_change_points):
        flags.append(flag)

    return flags


__all__ = ["QualityFlag", "QualityFlagBuilder", "build_quality_flags"]
