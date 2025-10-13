"""Pairwise statistical computations."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from pandas.api import types as ptypes
from scipy import stats

from relat_ai.services.analysis.utils import (
    ANOVAExtras,
    AnalysisResult,
    ChiSquareExtras,
    ColumnSemanticType,
    CorrelationRecord,
    apply_sample_limit,
)
from relat_ai.utils.caching import CacheBackend, InMemoryCache


PAIRWISE_METHODS = {
    "pearson": stats.pearsonr,
    "spearman": stats.spearmanr,
    "kendall": stats.kendalltau,
}

NUMERIC_METHODS = set(PAIRWISE_METHODS.keys())
MIXED_METHODS = {"anova", "point_biserial"}
CATEGORICAL_METHODS = {"chi_square", "cramers_v"}
SUPPORTED_METHODS = NUMERIC_METHODS | MIXED_METHODS | CATEGORICAL_METHODS


@dataclass(slots=True)
class PairwiseAnalysisPlan:
    """Configuration describing which statistics to compute per column type pair."""

    numeric_numeric: Sequence[str] = ("pearson", "spearman", "kendall")
    numeric_categorical: Sequence[str] = ("anova", "point_biserial")
    categorical_categorical: Sequence[str] = ("chi_square", "cramers_v")
    boolean_numeric: Sequence[str] = ("point_biserial",)
    boolean_boolean: Sequence[str] = ("cramers_v",)
    include_methods: frozenset[str] | None = None
    min_samples: int = 3
    max_categories: int = 25
    sample_size_limit: int | None = 5000
    parallelism: int = 1
    random_state: int = 0

    def __post_init__(self) -> None:
        if self.min_samples < 2:
            raise ValueError("min_samples must be at least 2 for pairwise analysis")
        if self.max_categories < 2:
            raise ValueError(
                "max_categories must be at least 2 to compute categorical statistics"
            )
        if self.sample_size_limit is not None and self.sample_size_limit <= 0:
            raise ValueError("sample_size_limit must be a positive integer or None")
        if self.parallelism < 1:
            raise ValueError("parallelism must be at least 1")

    def methods_for_pair(
        self, left: ColumnSemanticType, right: ColumnSemanticType
    ) -> tuple[str, ...]:
        """Return the methods that should be evaluated for a column pair."""

        left, right = _normalize_types(left), _normalize_types(right)
        if left == ColumnSemanticType.NUMERIC and right == ColumnSemanticType.NUMERIC:
            methods: Sequence[str] = self.numeric_numeric
        elif (
            left == ColumnSemanticType.NUMERIC
            and right in {ColumnSemanticType.CATEGORICAL, ColumnSemanticType.BOOLEAN}
        ) or (
            right == ColumnSemanticType.NUMERIC
            and left in {ColumnSemanticType.CATEGORICAL, ColumnSemanticType.BOOLEAN}
        ):
            if ColumnSemanticType.BOOLEAN in {left, right}:
                methods = self.boolean_numeric
            else:
                methods = self.numeric_categorical
        else:
            if ColumnSemanticType.BOOLEAN in {left, right}:
                methods = self.boolean_boolean
            else:
                methods = self.categorical_categorical

        allowed = tuple(methods)
        if self.include_methods is not None:
            allowed = tuple(method for method in allowed if method in self.include_methods)
        return allowed

    def signature(self) -> str:
        """Unique signature for caching derived from plan configuration."""

        def _join(items: Sequence[str]) -> str:
            return ",".join(sorted(items))

        components = [
            _join(self.numeric_numeric),
            _join(self.numeric_categorical),
            _join(self.categorical_categorical),
            _join(self.boolean_numeric),
            _join(self.boolean_boolean),
            str(self.min_samples),
            str(self.max_categories),
            str(self.sample_size_limit),
            str(self.parallelism),
            str(self.random_state),
        ]
        if self.include_methods is not None:
            components.append(_join(tuple(self.include_methods)))
        return "|".join(components)


_PAIRWISE_CACHE: CacheBackend[AnalysisResult] = InMemoryCache()


def compute_pairwise_correlations(
    frame: pd.DataFrame,
    columns: Iterable[str],
    *,
    plan: PairwiseAnalysisPlan | None = None,
    dataset_id: str | None = None,
    cache: CacheBackend[AnalysisResult] | None = None,
) -> AnalysisResult:
    """Compute pairwise relationships according to the configured plan."""

    plan = plan or PairwiseAnalysisPlan()
    requested_columns = list(dict.fromkeys(columns))
    missing_columns = [name for name in requested_columns if name not in frame.columns]
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Columns not found in frame: {missing}")

    column_names = requested_columns
    if len(column_names) < 2:
        raise ValueError("At least two columns are required to compute pairwise correlations")

    invalid_methods = _validate_plan(plan)
    if invalid_methods:
        raise ValueError(f"Unsupported correlation methods requested: {sorted(invalid_methods)}")

    cache_backend: CacheBackend[AnalysisResult] | None = None
    cache_key: str | None = None
    if dataset_id:
        cache_backend = cache or _PAIRWISE_CACHE
        cache_key = _build_pairwise_cache_key(dataset_id, column_names, plan.signature())
        cached_result = cache_backend.get(cache_key)
        if cached_result is not None:
            return cached_result

    column_types = {name: _infer_semantic_type(frame[name]) for name in column_names}
    pair_tasks: list[tuple[str, str, tuple[str, ...]] | None] = []
    for left, right in combinations(column_names, 2):
        methods = plan.methods_for_pair(column_types[left], column_types[right])
        if not methods:
            continue
        pair_tasks.append((left, right, methods))

    if not pair_tasks:
        return AnalysisResult(correlations=[])

    executor = _evaluate_pair if plan.parallelism == 1 else _evaluate_pair_parallel
    records = executor(frame, pair_tasks, plan)

    result = AnalysisResult(correlations=records)
    if cache_backend and cache_key:
        cache_backend.set(cache_key, result)
    return result


def _evaluate_pair(
    frame: pd.DataFrame,
    tasks: Sequence[tuple[str, str, tuple[str, ...]]],
    plan: PairwiseAnalysisPlan,
) -> list[CorrelationRecord]:
    results: list[CorrelationRecord] = []
    for column_a, column_b, methods in tasks:
        pair_records = _compute_pairwise_metrics(frame, column_a, column_b, methods, plan)
        results.extend(pair_records)
    return results


def _evaluate_pair_parallel(
    frame: pd.DataFrame,
    tasks: Sequence[tuple[str, str, tuple[str, ...]]],
    plan: PairwiseAnalysisPlan,
) -> list[CorrelationRecord]:
    parallel = Parallel(n_jobs=plan.parallelism, prefer="threads")
    nested_results = parallel(
        delayed(_compute_pairwise_metrics)(frame, column_a, column_b, methods, plan)
        for column_a, column_b, methods in tasks
    )
    results: list[CorrelationRecord] = []
    for subset in nested_results:
        results.extend(subset)
    return results


def _compute_pairwise_metrics(
    frame: pd.DataFrame,
    column_a: str,
    column_b: str,
    methods: Sequence[str],
    plan: PairwiseAnalysisPlan,
) -> list[CorrelationRecord]:
    subset = frame[[column_a, column_b]].dropna()
    if len(subset.index) < plan.min_samples:
        return []

    subset = apply_sample_limit(
        subset, plan.sample_size_limit, random_state=plan.random_state
    )

    type_a = _infer_semantic_type(frame[column_a])
    type_b = _infer_semantic_type(frame[column_b])
    normalized_a = _normalize_types(type_a)
    normalized_b = _normalize_types(type_b)

    if normalized_a == ColumnSemanticType.NUMERIC and normalized_b == ColumnSemanticType.NUMERIC:
        return _compute_numeric_numeric(subset, column_a, column_b, methods)

    if (
        normalized_a == ColumnSemanticType.NUMERIC
        and normalized_b in {ColumnSemanticType.CATEGORICAL, ColumnSemanticType.BOOLEAN}
    ) or (
        normalized_b == ColumnSemanticType.NUMERIC
        and normalized_a in {ColumnSemanticType.CATEGORICAL, ColumnSemanticType.BOOLEAN}
    ):
        return _compute_mixed_pair(subset, column_a, column_b, methods, plan)

    return _compute_categorical_pair(subset, column_a, column_b, methods, plan)


def _compute_numeric_numeric(
    subset: pd.DataFrame,
    column_a: str,
    column_b: str,
    methods: Sequence[str],
) -> list[CorrelationRecord]:
    results: list[CorrelationRecord] = []
    series_a = pd.to_numeric(subset[column_a], errors="coerce")
    series_b = pd.to_numeric(subset[column_b], errors="coerce")
    clean = pd.concat([series_a, series_b], axis=1).dropna()
    if clean.empty:
        return results

    for method in methods:
        if method not in NUMERIC_METHODS:
            continue
        func = PAIRWISE_METHODS.get(method)
        if func is None:
            continue
        statistic = func(clean.iloc[:, 0], clean.iloc[:, 1])
        coefficient = float(
            statistic.statistic if hasattr(statistic, "statistic") else statistic[0]
        )
        p_value = float(
            statistic.pvalue if hasattr(statistic, "pvalue") else statistic[1]
        )
        test_statistic = None
        if hasattr(statistic, "statistic"):
            test_statistic = float(statistic.statistic)
        elif method == "pearson":
            test_statistic = float(statistic[0])
        results.append(
            CorrelationRecord(
                variables=(column_a, column_b),
                coefficient=coefficient,
                p_value=p_value,
                sample_size=len(clean.index),
                method=method,
                statistic=test_statistic,
            )
        )
    return results


def _compute_mixed_pair(
    subset: pd.DataFrame,
    column_a: str,
    column_b: str,
    methods: Sequence[str],
    plan: PairwiseAnalysisPlan,
) -> list[CorrelationRecord]:
    results: list[CorrelationRecord] = []
    numeric_col, categorical_col = _identify_numeric_categorical(subset, column_a, column_b)
    numeric = pd.to_numeric(subset[numeric_col], errors="coerce")
    categorical = subset[categorical_col]
    clean = pd.concat([numeric, categorical], axis=1).dropna()
    if clean.empty:
        return results

    groups = clean.groupby(categorical_col)
    if len(groups) < 2:
        return results
    if groups.ngroups > plan.max_categories:
        return results

    if "anova" in methods:
        group_values = [group[numeric_col].values for _, group in groups]
        anova = stats.f_oneway(*group_values)
        df_between = groups.ngroups - 1
        df_within = len(clean.index) - groups.ngroups
        eta_squared = 0.0
        if anova.statistic > 0 and df_within > 0:
            numerator = anova.statistic * df_between
            denominator = numerator + df_within
            if denominator > 0:
                eta_squared = float(numerator / denominator)
        results.append(
            CorrelationRecord(
                variables=(numeric_col, categorical_col),
                coefficient=eta_squared,
                p_value=float(anova.pvalue),
                sample_size=len(clean.index),
                method="anova",
                statistic=float(anova.statistic),
                extras=ANOVAExtras(
                    df_between=float(df_between),
                    df_within=float(df_within),
                ),
            )
        )

    if "point_biserial" in methods and groups.ngroups == 2:
        encoded, _ = pd.factorize(clean[categorical_col], sort=True)
        binary = pd.Series(encoded, index=clean.index, dtype=float)
        correlation = stats.pointbiserialr(binary, clean[numeric_col])
        coefficient = float(correlation.statistic)
        p_value = float(correlation.pvalue)
        results.append(
            CorrelationRecord(
                variables=(numeric_col, categorical_col),
                coefficient=coefficient,
                p_value=p_value,
                sample_size=len(clean.index),
                method="point_biserial",
                statistic=float(correlation.statistic),
            )
        )

    return results


def _compute_categorical_pair(
    subset: pd.DataFrame,
    column_a: str,
    column_b: str,
    methods: Sequence[str],
    plan: PairwiseAnalysisPlan,
) -> list[CorrelationRecord]:
    results: list[CorrelationRecord] = []
    contingency = pd.crosstab(subset[column_a], subset[column_b])
    if contingency.size == 0:
        return results
    if contingency.shape[0] > plan.max_categories or contingency.shape[1] > plan.max_categories:
        return results

    chi_square = stats.chi2_contingency(contingency)
    chi2_value = float(chi_square[0])
    p_value = float(chi_square[1])
    dof = float(chi_square[2])
    n = contingency.to_numpy().sum()
    record_extras = ChiSquareExtras(degrees_of_freedom=dof)

    if "chi_square" in methods:
        results.append(
            CorrelationRecord(
                variables=(column_a, column_b),
                coefficient=chi2_value,
                p_value=p_value,
                sample_size=int(n),
                method="chi_square",
                statistic=chi2_value,
                extras=record_extras,
            )
        )

    if "cramers_v" in methods:
        rows, cols = contingency.shape
        if min(rows, cols) > 1 and n > 0:
            phi2 = chi2_value / n
            denom = max(min(cols - 1, rows - 1), 1)
            cramers_v = float(np.sqrt(phi2 / denom))
        else:
            cramers_v = 0.0
        results.append(
            CorrelationRecord(
                variables=(column_a, column_b),
                coefficient=cramers_v,
                p_value=p_value,
                sample_size=int(n),
                method="cramers_v",
                statistic=chi2_value,
                extras=ChiSquareExtras(
                    degrees_of_freedom=record_extras.degrees_of_freedom,
                    chi_square=chi2_value,
                ),
            )
        )

    return results


def _infer_semantic_type(series: pd.Series) -> ColumnSemanticType:
    if ptypes.is_bool_dtype(series):
        return ColumnSemanticType.BOOLEAN
    if ptypes.is_numeric_dtype(series):
        return ColumnSemanticType.NUMERIC
    if ptypes.is_datetime64_any_dtype(series):
        return ColumnSemanticType.DATETIME
    if ptypes.is_string_dtype(series):
        return ColumnSemanticType.TEXT
    return ColumnSemanticType.CATEGORICAL


def _normalize_types(column_type: ColumnSemanticType) -> ColumnSemanticType:
    if column_type in {ColumnSemanticType.TEXT, ColumnSemanticType.DATETIME}:
        return ColumnSemanticType.CATEGORICAL
    return column_type


def _identify_numeric_categorical(
    subset: pd.DataFrame, column_a: str, column_b: str
) -> tuple[str, str]:
    if ptypes.is_numeric_dtype(subset[column_a]):
        return column_a, column_b
    return column_b, column_a


def _validate_plan(plan: PairwiseAnalysisPlan) -> set[str]:
    requested = set().union(
        plan.numeric_numeric,
        plan.numeric_categorical,
        plan.categorical_categorical,
        plan.boolean_numeric,
        plan.boolean_boolean,
    )
    if plan.include_methods is not None:
        requested |= set(plan.include_methods)
    return requested - SUPPORTED_METHODS


def _build_pairwise_cache_key(
    dataset_id: str, columns: Sequence[str], plan_signature: str
) -> str:
    unique_columns = sorted(set(columns))
    pair_tokens = ["~".join(pair) for pair in combinations(unique_columns, 2)]
    pairs_fragment = ",".join(pair_tokens)
    return f"{dataset_id}:{plan_signature}:{pairs_fragment}"
