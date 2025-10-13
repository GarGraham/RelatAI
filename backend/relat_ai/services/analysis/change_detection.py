"""Change-point detection algorithms used by auto-triage analysis."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def detect_cusum_change_points(
    series: pd.Series,
    threshold_multiplier: float = 5.0,
) -> list[int]:
    """CUSUM implementation detecting mean shifts in a 1D series."""

    values = series.to_numpy()
    if values.size < 5:
        return []
    mean = values.mean()
    std = values.std(ddof=0)
    threshold = threshold_multiplier * std if std > 0 else 0.0
    if threshold == 0.0:
        return []

    s_pos = 0.0
    s_neg = 0.0
    locations: list[int] = []
    for index, value in enumerate(values):
        deviation = value - mean
        s_pos = max(0.0, s_pos + deviation)
        s_neg = min(0.0, s_neg + deviation)
        if s_pos > threshold or abs(s_neg) > threshold:
            locations.append(index)
            s_pos = 0.0
            s_neg = 0.0
    return locations


def detect_pelt_change_points(
    series: pd.Series,
    penalty_multiplier: float = 3.0,
) -> list[int]:
    """Simplified PELT algorithm for detecting mean shifts."""

    values = series.to_numpy()
    n = len(values)
    if n < 5:
        return []

    penalty = penalty_multiplier * np.log(n)
    cumulative_sum = np.cumsum(np.insert(values, 0, 0.0))
    cumulative_sum_sq = np.cumsum(np.insert(values**2, 0, 0.0))

    def cost(start: int, end: int) -> float:
        length = end - start
        if length <= 1:
            return 0.0
        segment_sum = cumulative_sum[end] - cumulative_sum[start]
        segment_sq_sum = cumulative_sum_sq[end] - cumulative_sum_sq[start]
        mean = segment_sum / length
        return segment_sq_sum - 2 * mean * segment_sum + length * mean**2

    best_cost = np.zeros(n + 1)
    best_cost[0] = -penalty
    change_points: list[list[int]] = [[] for _ in range(n + 1)]
    candidate_indices: list[int] = [0]

    for end in range(1, n + 1):
        scores: list[tuple[float, int]] = []
        for start in candidate_indices:
            score = best_cost[start] + cost(start, end) + penalty
            scores.append((score, start))
        best_score, best_start = min(scores, key=lambda item: item[0])
        best_cost[end] = best_score
        change_points[end] = change_points[best_start] + [best_start]
        candidate_indices = [
            start
            for _, start in scores
            if best_cost[start] + cost(start, end) <= best_score + penalty
        ]

    final_points = [point for point in change_points[n] if point not in (0, n)]
    return final_points


__all__: Sequence[str] = [
    "detect_cusum_change_points",
    "detect_pelt_change_points",
]
