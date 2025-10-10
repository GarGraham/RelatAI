"""Pairwise statistical computations."""

from collections.abc import Iterable
import pandas as pd
from scipy import stats

from relat_ai.services.analysis.utils import AnalysisResult, CorrelationRecord


PAIRWISE_METHODS = {
    "pearson": stats.pearsonr,
    "spearman": stats.spearmanr,
    "kendall": stats.kendalltau,
}


def compute_pairwise_correlations(
    frame: pd.DataFrame,
    columns: Iterable[str],
    method: str = "pearson",
) -> AnalysisResult:
    """Compute pairwise correlations for the specified columns."""

    if method not in PAIRWISE_METHODS:
        raise ValueError(f"Unsupported correlation method: {method}")

    column_names = list(columns)
    if len(column_names) < 2:
        return AnalysisResult(correlations=[])

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

    return AnalysisResult(correlations=results)
