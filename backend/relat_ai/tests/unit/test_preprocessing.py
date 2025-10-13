"""Tests for preprocessing utilities and audit trail integration."""

import numpy as np
import pandas as pd

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
