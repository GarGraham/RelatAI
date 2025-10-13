"""Dataset preprocessing utilities with audit trail integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from relat_ai.services.audit_trail import record_preprocessing_action


MissingNumericStrategy = Literal["median", "mean", "zero"]
MissingCategoricalStrategy = Literal["mode", "constant"]
OutlierStrategy = Literal["none", "iqr_clip"]
ScalingStrategy = Literal["none", "robust"]


@dataclass(slots=True)
class PreprocessingConfig:
    """Configuration options controlling preprocessing behaviour."""

    missing_numeric: MissingNumericStrategy = "median"
    missing_categorical: MissingCategoricalStrategy = "mode"
    missing_constant_value: str = "Unknown"
    outlier_strategy: OutlierStrategy = "iqr_clip"
    scaling_strategy: ScalingStrategy = "robust"

    def __post_init__(self) -> None:
        if self.missing_numeric not in {"median", "mean", "zero"}:
            raise ValueError(f"Unsupported numeric imputation strategy: {self.missing_numeric}")
        if self.missing_categorical not in {"mode", "constant"}:
            raise ValueError(
                f"Unsupported categorical imputation strategy: {self.missing_categorical}"
            )
        if self.outlier_strategy not in {"none", "iqr_clip"}:
            raise ValueError(f"Unsupported outlier strategy: {self.outlier_strategy}")
        if self.scaling_strategy not in {"none", "robust"}:
            raise ValueError(f"Unsupported scaling strategy: {self.scaling_strategy}")

    @classmethod
    def from_settings(cls, settings: object) -> "PreprocessingConfig":
        """Create a configuration from a settings object."""

        attrs = {
            "missing_numeric": getattr(settings, "preprocessing_missing_numeric", "median"),
            "missing_categorical": getattr(
                settings, "preprocessing_missing_categorical", "mode"
            ),
            "missing_constant_value": getattr(
                settings, "preprocessing_missing_constant", "Unknown"
            ),
            "outlier_strategy": getattr(settings, "preprocessing_outlier_strategy", "iqr_clip"),
            "scaling_strategy": getattr(settings, "preprocessing_scaling_strategy", "robust"),
        }
        return cls(**attrs)


def preprocess_frame(
    frame: pd.DataFrame,
    *,
    dataset_id: str,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    """Apply preprocessing steps to a dataframe while logging actions."""

    processed = frame.copy(deep=True)

    _handle_missing_numeric(processed, dataset_id, config)
    _handle_missing_categorical(processed, dataset_id, config)
    _handle_outliers(processed, dataset_id, config)
    _apply_scaling(processed, dataset_id, config)

    return processed


def _handle_missing_numeric(
    frame: pd.DataFrame, dataset_id: str, config: PreprocessingConfig
) -> None:
    numeric_columns = frame.select_dtypes(include=[np.number]).columns
    for column in numeric_columns:
        series = frame[column]
        missing_mask = series.isna()
        missing_count = int(missing_mask.sum())
        if missing_count == 0:
            continue

        if config.missing_numeric == "median":
            fill_value = float(series.median(skipna=True)) if not series.dropna().empty else 0.0
        elif config.missing_numeric == "mean":
            fill_value = float(series.mean(skipna=True)) if not series.dropna().empty else 0.0
        else:  # "zero"
            fill_value = 0.0

        frame[column] = series.fillna(fill_value)
        record_preprocessing_action(
            dataset_id,
            action_type="missing_imputation",
            column=column,
            details={
                "strategy": config.missing_numeric,
                "fill_value": fill_value,
                "imputed_count": missing_count,
            },
        )


def _handle_missing_categorical(
    frame: pd.DataFrame, dataset_id: str, config: PreprocessingConfig
) -> None:
    categorical_columns = frame.select_dtypes(include=["object", "category"]).columns
    for column in categorical_columns:
        series = frame[column]
        missing_mask = series.isna()
        missing_count = int(missing_mask.sum())
        if missing_count == 0:
            continue

        if config.missing_categorical == "mode":
            mode = series.mode(dropna=True)
            fill_value = mode.iloc[0] if not mode.empty else config.missing_constant_value
        else:
            fill_value = config.missing_constant_value

        frame[column] = series.fillna(fill_value)
        record_preprocessing_action(
            dataset_id,
            action_type="missing_imputation",
            column=column,
            details={
                "strategy": config.missing_categorical,
                "fill_value": fill_value,
                "imputed_count": missing_count,
            },
        )


def _handle_outliers(frame: pd.DataFrame, dataset_id: str, config: PreprocessingConfig) -> None:
    if config.outlier_strategy != "iqr_clip":
        return

    numeric_columns = frame.select_dtypes(include=[np.number]).columns
    for column in numeric_columns:
        series = frame[column]
        clean = series.dropna()
        if clean.empty:
            continue

        q1 = clean.quantile(0.25)
        q3 = clean.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        clipped = series.clip(lower=lower_bound, upper=upper_bound)
        clipped_count = int((clipped != series).sum())
        if clipped_count == 0:
            continue

        frame[column] = clipped
        record_preprocessing_action(
            dataset_id,
            action_type="outlier_clipping",
            column=column,
            details={
                "strategy": config.outlier_strategy,
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "clipped_count": clipped_count,
            },
        )


def _apply_scaling(frame: pd.DataFrame, dataset_id: str, config: PreprocessingConfig) -> None:
    if config.scaling_strategy != "robust":
        return

    numeric_columns = frame.select_dtypes(include=[np.number]).columns
    for column in numeric_columns:
        series = frame[column]
        clean = series.dropna()
        if clean.empty:
            continue

        median = float(clean.median())
        iqr = float(clean.quantile(0.75) - clean.quantile(0.25))
        if iqr == 0:
            continue

        scaled = (series - median) / iqr
        frame[column] = scaled
        record_preprocessing_action(
            dataset_id,
            action_type="scaling",
            column=column,
            details={
                "strategy": config.scaling_strategy,
                "median": median,
                "iqr": iqr,
            },
        )

