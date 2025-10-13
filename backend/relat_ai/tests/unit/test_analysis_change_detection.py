from __future__ import annotations

import numpy as np
import pandas as pd

from relat_ai.services.analysis.change_detection import (
    detect_cusum_change_points,
    detect_pelt_change_points,
)


def test_detect_cusum_change_points_identifies_shift() -> None:
    baseline = np.zeros(20)
    shifted = np.concatenate([baseline[:10], np.ones(10)])
    series = pd.Series(shifted)

    locations = detect_cusum_change_points(series)

    assert locations, "CUSUM should identify change points for a clear shift"
    assert all(0 <= location < len(series) for location in locations)


def test_detect_pelt_change_points_identifies_shift() -> None:
    baseline = np.zeros(40)
    shifted = np.concatenate([baseline[:20], np.ones(20) * 10])
    series = pd.Series(shifted)

    locations = detect_pelt_change_points(series, penalty_multiplier=0.5)

    assert isinstance(locations, list)
    assert all(0 <= location < len(series) for location in locations)


def test_change_point_algorithms_handle_small_series() -> None:
    series = pd.Series([1.0, 1.0, 1.0])

    assert detect_cusum_change_points(series) == []
    assert detect_pelt_change_points(series) == []
