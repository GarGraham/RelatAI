"""Pairwise statistical computations."""

from collections.abc import Iterable

import pandas as pd
from scipy import stats

from relat_ai.services.analysis.utils import AnalysisResult, CorrelationRecord
from relat_ai.utils.caching import CacheBackend, InMemoryCache


PAIRWISE_METHODS = {
    "pearson": stats.pearsonr,
    "spearman": stats.spearmanr,
    "kendall": stats.kendalltau,
}

_PAIRWISE_CACHE: CacheBackend[AnalysisResult] = InMemoryCache()


def compute_pairwise_correlations(
    frame: pd.DataFrame,
    columns: Iterable[str],
    method: str = "pearson",
    *,
    dataset_id: str | None = None,
    cache: CacheBackend[AnalysisResult] | None = None,
) -> AnalysisResult:
    """Compute pairwise correlations for the specified columns."""

    if method not in PAIRWISE_METHODS:
        raise ValueError(f"Unsupported correlation method: {method}")

    column_names = list(columns)
    if len(column_names) < 2:
        return AnalysisResult(correlations=[])

    cache_backend: CacheBackend[AnalysisResult] | None = None
    cache_key: str | None = None
    if dataset_id:
        cache_backend = cache or _PAIRWISE_CACHE
        cache_key = _build_pairwise_cache_key(dataset_id, column_names, method)
        cached_result = cache_backend.get(cache_key)
        if cached_result is not None:
            return cached_result

    results: list[CorrelationRecord] = []
    for idx, column_a in enumerate(column_names):
        for column_b in column_names[idx + 1 :]:
            series_a = frame[column_a].dropna()
            series_b = frame[column_b].dropna()

            if series_a.empty or series_b.empty:
                continue

            common = pd.concat([series_a, series_b], axis=1, join="inner").dropna()
            if common.empty:
                continue

            values = PAIRWISE_METHODS[method](common.iloc[:, 0], common.iloc[:, 1])
            coefficient = float(values.statistic if hasattr(values, "statistic") else values[0])
            p_value = float(values.pvalue if hasattr(values, "pvalue") else values[1])

            results.append(
                CorrelationRecord(
                    variables=(column_a, column_b),
                    coefficient=coefficient,
                    p_value=p_value,
                    sample_size=len(common.index),
                    method=method,
                )
            )

    result = AnalysisResult(correlations=results)
    if cache_backend and cache_key:
        cache_backend.set(cache_key, result)
    return result


def _build_pairwise_cache_key(
    dataset_id: str, columns: list[str], method: str
) -> str:
    sorted_columns = ",".join(sorted(columns))
    return f"{dataset_id}:{method}:{sorted_columns}"
