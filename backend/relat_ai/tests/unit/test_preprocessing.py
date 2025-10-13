"""Tests for preprocessing utilities and audit trail integration."""

import numpy as np
import pandas as pd
import pytest

from relat_ai.services.audit_trail import get_audit_log, initialise_audit_log
from relat_ai.services.preprocessing import PreprocessingConfig, preprocess_frame


def test_preprocess_frame_applies_strategies_and_logs_actions() -> None:
    """Preprocessing should impute, clip outliers, scale, and log actions."""

    frame = pd.DataFrame(
        {
            "num": pd.Series([1.0, 2.5, np.nan, 100.0, -120.0], dtype=float),
            "category": pd.Series(["a", "b", None, "b", "c"], dtype="category"),
        }
    )
    dataset_id = "dataset-test"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="sample.csv",
        dataset_hash="hash",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig()
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    assert processed["num"].isna().sum() == 0
    assert processed["category"].isna().sum() == 0

    log = get_audit_log(dataset_id)
    assert log is not None
    action_types = [action.action_type for action in log.actions]

    assert action_types.count("missing_imputation") == 2
    assert "outlier_clipping" in action_types
    assert "scaling" in action_types

    # Robust scaling should centre the data at approximately zero median.
    scaled_median = float(processed["num"].median())
    assert abs(scaled_median) < 1e-9


def test_preprocess_frame_handles_all_missing_column() -> None:
    """Preprocessing should handle columns with all missing values gracefully."""

    frame = pd.DataFrame(
        {
            "all_missing_num": pd.Series([np.nan, np.nan, np.nan], dtype=float),
            "all_missing_cat": pd.Series([None, None, None], dtype=object),
            "valid_num": pd.Series([1.0, 2.0, 3.0], dtype=float),
        }
    )
    dataset_id = "dataset-all-missing"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="all_missing.csv",
        dataset_hash="hash123",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig()
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # All-missing numeric column should be filled with 0.0 (fallback)
    assert processed["all_missing_num"].isna().sum() == 0
    assert (processed["all_missing_num"] == 0.0).all()

    # All-missing categorical column should be filled with constant
    assert processed["all_missing_cat"].isna().sum() == 0
    assert (processed["all_missing_cat"] == "Unknown").all()

    # Valid column should still be processed
    assert processed["valid_num"].isna().sum() == 0


def test_preprocess_frame_handles_empty_dataframe() -> None:
    """Preprocessing should handle empty dataframes without errors."""

    frame = pd.DataFrame({"num": pd.Series([], dtype=float), "cat": pd.Series([], dtype=object)})
    dataset_id = "dataset-empty"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="empty.csv",
        dataset_hash="hash456",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig()
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Should return empty dataframe without errors
    assert len(processed.index) == 0
    assert len(processed.columns) == 2

    # Should not log any preprocessing actions (no data to process)
    log = get_audit_log(dataset_id)
    assert log is not None
    assert len(log.actions) == 0


def test_preprocess_frame_handles_single_value_column() -> None:
    """Preprocessing should handle columns with a single repeated value (zero variance)."""

    frame = pd.DataFrame(
        {
            "constant_num": pd.Series([5.0, 5.0, 5.0, 5.0], dtype=float),
            "constant_cat": pd.Series(["A", "A", "A", "A"], dtype=object),
            "variable_num": pd.Series([1.0, 2.0, 3.0, 4.0], dtype=float),
        }
    )
    dataset_id = "dataset-constant"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="constant.csv",
        dataset_hash="hash789",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig()
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Constant numeric column should not be scaled (IQR = 0)
    assert (processed["constant_num"] == 5.0).all()

    # Variable column should still be processed
    assert processed["variable_num"].isna().sum() == 0

    log = get_audit_log(dataset_id)
    assert log is not None
    # Constant column should not have outlier clipping or scaling actions
    constant_num_actions = [
        action for action in log.actions if action.column == "constant_num"
    ]
    # Should not have scaling or outlier actions for zero-variance column
    action_types = [action.action_type for action in constant_num_actions]
    assert "scaling" not in action_types
    assert "outlier_clipping" not in action_types


def test_preprocess_frame_handles_all_unique_categorical() -> None:
    """Preprocessing should handle categorical columns where all values are unique (no mode)."""

    frame = pd.DataFrame(
        {
            "unique_cat": pd.Series(["A", "B", None, "D"], dtype=object),
            "num": pd.Series([1.0, 2.0, 3.0, 4.0], dtype=float),
        }
    )
    dataset_id = "dataset-unique-cat"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="unique_cat.csv",
        dataset_hash="hash_abc",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(missing_categorical="mode")
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Missing value should be filled with first mode (or fallback to constant)
    assert processed["unique_cat"].isna().sum() == 0

    log = get_audit_log(dataset_id)
    assert log is not None
    unique_cat_actions = [action for action in log.actions if action.column == "unique_cat"]
    assert len(unique_cat_actions) == 1
    assert unique_cat_actions[0].action_type == "missing_imputation"


def test_preprocessing_config_validation() -> None:
    """PreprocessingConfig should validate configuration values."""

    # Valid configurations should not raise
    PreprocessingConfig(missing_numeric="median")
    PreprocessingConfig(missing_categorical="mode")
    PreprocessingConfig(outlier_strategy="none")
    PreprocessingConfig(scaling_strategy="robust")

    # Invalid configurations should raise ValueError
    with pytest.raises(ValueError, match="Unsupported numeric imputation strategy"):
        PreprocessingConfig(missing_numeric="invalid")

    with pytest.raises(ValueError, match="Unsupported categorical imputation strategy"):
        PreprocessingConfig(missing_categorical="invalid")

    with pytest.raises(ValueError, match="Unsupported outlier strategy"):
        PreprocessingConfig(outlier_strategy="invalid")

    with pytest.raises(ValueError, match="Unsupported scaling strategy"):
        PreprocessingConfig(scaling_strategy="invalid")


def test_preprocessing_strategies_mean_imputation() -> None:
    """Test mean imputation strategy for numeric columns."""

    frame = pd.DataFrame({"num": pd.Series([1.0, 2.0, np.nan, 4.0], dtype=float)})
    dataset_id = "dataset-mean"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="mean.csv",
        dataset_hash="hash_mean",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(missing_numeric="mean", outlier_strategy="none", scaling_strategy="none")
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Mean of [1, 2, 4] = 2.333...
    expected_mean = (1.0 + 2.0 + 4.0) / 3
    assert processed["num"].isna().sum() == 0
    assert abs(processed["num"].iloc[2] - expected_mean) < 1e-9


def test_preprocessing_strategies_zero_imputation() -> None:
    """Test zero imputation strategy for numeric columns."""

    frame = pd.DataFrame({"num": pd.Series([1.0, np.nan, 3.0], dtype=float)})
    dataset_id = "dataset-zero"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="zero.csv",
        dataset_hash="hash_zero",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(missing_numeric="zero", outlier_strategy="none", scaling_strategy="none")
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    assert processed["num"].isna().sum() == 0
    assert processed["num"].iloc[1] == 0.0


def test_preprocessing_strategies_constant_imputation() -> None:
    """Test constant imputation strategy for categorical columns."""

    frame = pd.DataFrame({"cat": pd.Series(["A", None, "B"], dtype=object)})
    dataset_id = "dataset-constant-cat"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="constant_cat.csv",
        dataset_hash="hash_const",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(
        missing_categorical="constant", 
        missing_constant_value="MISSING",
        outlier_strategy="none",
        scaling_strategy="none"
    )
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    assert processed["cat"].isna().sum() == 0
    assert processed["cat"].iloc[1] == "MISSING"


def test_preprocessing_strategies_no_outlier_handling() -> None:
    """Test that outlier_strategy='none' skips outlier clipping."""

    frame = pd.DataFrame({"num": pd.Series([1.0, 2.0, 100.0, -100.0], dtype=float)})
    dataset_id = "dataset-no-outlier"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="no_outlier.csv",
        dataset_hash="hash_no_out",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(outlier_strategy="none", scaling_strategy="none")
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Outliers should remain unchanged
    assert processed["num"].iloc[2] == 100.0
    assert processed["num"].iloc[3] == -100.0

    log = get_audit_log(dataset_id)
    assert log is not None
    action_types = [action.action_type for action in log.actions]
    assert "outlier_clipping" not in action_types


def test_preprocessing_strategies_no_scaling() -> None:
    """Test that scaling_strategy='none' skips scaling."""

    frame = pd.DataFrame({"num": pd.Series([1.0, 2.0, 3.0, 4.0], dtype=float)})
    dataset_id = "dataset-no-scale"

    initialise_audit_log(
        dataset_id=dataset_id,
        dataset_name="no_scale.csv",
        dataset_hash="hash_no_scale",
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )

    config = PreprocessingConfig(scaling_strategy="none", outlier_strategy="none")
    processed = preprocess_frame(frame, dataset_id=dataset_id, config=config)

    # Values should remain unchanged
    assert (processed["num"] == frame["num"]).all()

    log = get_audit_log(dataset_id)
    assert log is not None
    action_types = [action.action_type for action in log.actions]
    assert "scaling" not in action_types

