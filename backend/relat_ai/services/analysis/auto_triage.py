"""Auto-triage analysis pipeline.

This module bundles unsupervised diagnostics (PCA, clustering, change point
finding, and residual forensics) into a single helper that can be triggered from
the API layer.  The routines favour readability and plentiful commenting so the
intent is crystal clear to stakeholders who may not routinely read Python code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from relat_ai.services.analysis.utils import apply_sample_limit
from relat_ai.services.analysis.change_detection import (
    detect_cusum_change_points,
    detect_pelt_change_points,
)
from relat_ai.services.analysis.confidence_flags import (
    QualityFlag,
    build_quality_flags,
)


# ---------------------------------------------------------------------------
# Dataclasses used to share highly structured payloads with the API layer.
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PCAComponentInsight:
    """Describes one principal component and its strongest contributors."""

    component: int
    explained_variance_ratio: float
    top_contributors: Sequence[tuple[str, float]]


@dataclass(slots=True)
class ChangePointInsight:
    """Container for change-point detections produced by one algorithm."""

    column: str
    method: str
    locations: Sequence[int]


@dataclass(slots=True)
class ClusterInsight:
    """Summaries of unsupervised clustering results."""

    method: str
    cluster_sizes: dict[int, int]


@dataclass(slots=True)
class ResidualBucket:
    """Aggregated residual statistics for an individual bucket."""

    label: str
    average_residual: float
    sample_size: int
    column_residuals: dict[str, float]


@dataclass(slots=True)
class ResidualForensicsInsight:
    """Residual diagnostics grouped by categorical or temporal buckets."""

    grouping: str
    buckets: Sequence[ResidualBucket]


@dataclass(slots=True)
class SuspicionScore:
    """Ranking record indicating where the engine suggests deeper review."""

    target: str
    target_type: str
    score: float
    drivers: Sequence[str]


@dataclass(slots=True)
class AutoTriageResult:
    """Aggregate payload returned by :func:`run_auto_triage`."""

    pca_components: Sequence[PCAComponentInsight]
    change_points: Sequence[ChangePointInsight]
    clusters: Sequence[ClusterInsight]
    residual_forensics: Sequence[ResidualForensicsInsight]
    suspicion_rankings: Sequence[SuspicionScore]
    quality_flags: Sequence[QualityFlag]


@dataclass(slots=True)
class AutoTriageConfig:
    """Configures the auto-triage pipeline."""

    numeric_columns: Sequence[str]
    categorical_columns: Sequence[str] = ()
    datetime_column: str | None = None
    sample_size_limit: int | None = None
    max_components: int = 3
    kmeans_clusters: int = 3
    hierarchical_clusters: int = 3
    change_point_methods: Sequence[str] = ("cusum", "pelt")
    top_component_features: int = 3
    top_residual_buckets: int = 5
    suspicion_top_k: int = 5
    min_sample_warning: int = 50
    high_missing_threshold: float = 0.2
    high_collinearity_threshold: float = 0.95
    random_state: int = 0

    VALID_CHANGE_POINT_METHODS = frozenset({"cusum", "pelt"})

    def __post_init__(self) -> None:
        if not self.numeric_columns:
            raise ValueError("AutoTriageConfig requires at least one numeric column")
        if self.sample_size_limit is not None and self.sample_size_limit <= 0:
            raise ValueError("sample_size_limit must be a positive integer or None")
        if self.kmeans_clusters < 1:
            raise ValueError("kmeans_clusters must be at least 1")
        if self.hierarchical_clusters < 1:
            raise ValueError("hierarchical_clusters must be at least 1")
        if self.max_components < 1:
            raise ValueError("max_components must be at least 1")
        if self.top_component_features < 1:
            raise ValueError("top_component_features must be at least 1")
        if self.top_residual_buckets < 1:
            raise ValueError("top_residual_buckets must be at least 1")
        if self.suspicion_top_k < 1:
            raise ValueError("suspicion_top_k must be at least 1")
        if self.high_missing_threshold < 0 or self.high_missing_threshold > 1:
            raise ValueError("high_missing_threshold must be between 0 and 1")
        if self.high_collinearity_threshold <= 0 or self.high_collinearity_threshold > 1:
            raise ValueError("high_collinearity_threshold must be within (0, 1]")

        invalid_methods = [
            method for method in self.change_point_methods if method not in self.VALID_CHANGE_POINT_METHODS
        ]
        if invalid_methods:
            raise ValueError(
                "Invalid change-point methods: "
                + ", ".join(invalid_methods)
                + ". Supported methods: "
                + ", ".join(sorted(self.VALID_CHANGE_POINT_METHODS))
            )


def run_auto_triage(frame: pd.DataFrame, config: AutoTriageConfig) -> AutoTriageResult:
    """Execute the auto-triage workflow on the provided dataset.

    The analysis follows these broad steps:

    1. Validate inputs and enforce optional sampling limits.
    2. Build a clean numeric matrix (median imputation + scaling) for PCA and
       clustering.
    3. Produce change-point candidates for each numeric series.
    4. Compute residual summaries for the requested categorical/time groupings.
    5. Combine the above diagnostics into suspicion rankings and quality flags.
    """

    _validate_required_columns(frame, config)

    if len(frame.index) == 0:
        raise ValueError("Cannot perform auto-triage on an empty dataset")

    working_frame = frame.copy()
    if config.datetime_column:
        dt_series = pd.to_datetime(working_frame[config.datetime_column], errors="coerce")
        working_frame = working_frame.loc[dt_series.notna()].assign(**{config.datetime_column: dt_series})
        working_frame = working_frame.sort_values(config.datetime_column)

    working_frame = apply_sample_limit(
        working_frame,
        config.sample_size_limit,
        random_state=config.random_state,
    )

    numeric_data, imputation_flags = _prepare_numeric_matrix(working_frame, config)

    pca_insights, pca_component_strength = _run_pca(numeric_data, config)
    change_points = _detect_change_points(working_frame, numeric_data, config)
    cluster_insights = _perform_clustering(numeric_data, config)
    residual_insights = _compute_residual_forensics(working_frame, numeric_data, config)
    suspicion_rankings = _score_suspicion(
        working_frame,
        numeric_data,
        pca_component_strength,
        change_points,
        residual_insights,
        config,
    )
    quality_flags = build_quality_flags(
        working_frame,
        numeric_data,
        imputation_flags,
        change_points,
        config,
    )

    return AutoTriageResult(
        pca_components=pca_insights,
        change_points=change_points,
        clusters=cluster_insights,
        residual_forensics=residual_insights,
        suspicion_rankings=suspicion_rankings,
        quality_flags=quality_flags,
    )


# ---------------------------------------------------------------------------
# Preparation helpers
# ---------------------------------------------------------------------------


def _validate_required_columns(frame: pd.DataFrame, config: AutoTriageConfig) -> None:
    missing = [column for column in config.numeric_columns if column not in frame.columns]
    if missing:
        raise KeyError(f"Missing numeric columns: {', '.join(missing)}")
    for column in config.categorical_columns:
        if column not in frame.columns:
            raise KeyError(f"Missing categorical column: {column}")
    if config.datetime_column and config.datetime_column not in frame.columns:
        raise KeyError(f"Missing datetime column: {config.datetime_column}")


def _prepare_numeric_matrix(
    frame: pd.DataFrame, config: AutoTriageConfig
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Return a numeric matrix with median imputation and scaling applied.

    The returned DataFrame mirrors the input order.  We also compute a dictionary
    detailing the proportion of missing values for each column, allowing the
    calling code to surface data-quality warnings later.
    """

    numeric = frame.loc[:, config.numeric_columns].apply(pd.to_numeric, errors="coerce")

    missing_ratio = numeric.isna().mean().to_dict()

    # Per-column median imputation with fallback to 0 for columns that are entirely NaN
    filled = numeric.apply(lambda col: col.fillna(col.median() if col.notna().any() else 0.0))

    non_constant_columns = [
        column for column in filled.columns if not np.isclose(filled[column].std(ddof=0), 0.0)
    ]
    if not non_constant_columns:
        raise ValueError("All numeric columns are constant; auto-triage requires variability")

    scaled_array = StandardScaler().fit_transform(filled[non_constant_columns])
    scaled = pd.DataFrame(scaled_array, columns=non_constant_columns, index=frame.index)
    return scaled, missing_ratio


# ---------------------------------------------------------------------------
# PCA analysis
# ---------------------------------------------------------------------------


def _run_pca(
    numeric_data: pd.DataFrame, config: AutoTriageConfig
) -> tuple[list[PCAComponentInsight], dict[str, float]]:
    """Perform PCA and capture component strengths per original variable."""

    component_count = min(config.max_components, numeric_data.shape[1])
    pca_model = PCA(n_components=component_count, random_state=config.random_state)
    pca_model.fit(numeric_data)

    components: list[PCAComponentInsight] = []
    strength: dict[str, float] = {column: 0.0 for column in numeric_data.columns}

    for index, variance_ratio in enumerate(pca_model.explained_variance_ratio_):
        loadings = pd.Series(pca_model.components_[index], index=numeric_data.columns)
        ranked = loadings.abs().sort_values(ascending=False)
        top = [
            (feature, float(loadings[feature]))
            for feature in ranked.head(config.top_component_features).index
        ]
        for feature, value in loadings.items():
            strength[feature] = max(strength[feature], abs(value) * float(variance_ratio))
        components.append(
            PCAComponentInsight(
                component=index + 1,
                explained_variance_ratio=float(variance_ratio),
                top_contributors=top,
            )
        )

    return components, strength


# ---------------------------------------------------------------------------
# Change-point detection
# ---------------------------------------------------------------------------


def _detect_change_points(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    config: AutoTriageConfig,
) -> list[ChangePointInsight]:
    """Detect change points for each numeric column using requested methods."""

    change_points: list[ChangePointInsight] = []
    for column in numeric_data.columns:
        series = numeric_data[column]
        for method in config.change_point_methods:
            if method == "cusum":
                locations = detect_cusum_change_points(series)
            elif method == "pelt":
                locations = detect_pelt_change_points(series)
            else:
                continue
            if not locations:
                continue
            change_points.append(
                ChangePointInsight(
                    column=column,
                    method=method,
                    locations=[int(location) for location in locations],
                )
            )
    return change_points

def _apply_clustering_method(
    numeric_data: pd.DataFrame,
    method_name: str,
    n_clusters: int,
    sample_size: int,
    random_state: int | None = None,
) -> ClusterInsight | None:
    """Apply a clustering method and return insight."""

    adjusted_clusters = min(n_clusters, sample_size)
    if adjusted_clusters <= 1:
        return None

    if method_name == "kmeans":
        model = KMeans(n_clusters=adjusted_clusters, random_state=random_state, n_init=10)
    elif method_name == "hierarchical":
        # Agglomerative clustering with ward linkage is deterministic and does not expose random_state.
        model = AgglomerativeClustering(n_clusters=adjusted_clusters)
    else:
        return None

    labels = model.fit_predict(numeric_data)
    return ClusterInsight(method=method_name, cluster_sizes=_count_labels(labels))


def _perform_clustering(
    numeric_data: pd.DataFrame, config: AutoTriageConfig
) -> list[ClusterInsight]:
    """Run K-Means and hierarchical clustering as requested."""

    results: list[ClusterInsight] = []
    sample_size = len(numeric_data.index)
    if sample_size == 0:
        return results

    if insight := _apply_clustering_method(
        numeric_data,
        "kmeans",
        config.kmeans_clusters,
        sample_size,
        config.random_state,
    ):
        results.append(insight)

    if insight := _apply_clustering_method(
        numeric_data,
        "hierarchical",
        config.hierarchical_clusters,
        sample_size,
    ):
        results.append(insight)

    return results


def _count_labels(labels: Iterable[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for label in labels:
        counts[int(label)] = counts.get(int(label), 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Residual forensics
# ---------------------------------------------------------------------------


def _compute_residual_forensics(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    config: AutoTriageConfig,
) -> list[ResidualForensicsInsight]:
    """Summarise average residuals across requested groupings."""

    insights: list[ResidualForensicsInsight] = []
    baseline = numeric_data.mean(axis=0)

    working_frame = frame.copy()
    grouping_columns = list(config.categorical_columns)
    if config.datetime_column:
        time_windows = working_frame[config.datetime_column].dt.to_period("D").astype(str)
        working_frame = working_frame.assign(_auto_triage_window=time_windows)
        grouping_columns.append("_auto_triage_window")

    for column in grouping_columns:
        if column not in working_frame.columns:
            continue
        valid_rows = working_frame[column].notna()
        if not valid_rows.any():
            continue
        buckets = []
        for bucket_value, group in working_frame.loc[valid_rows].groupby(column):
            valid_indices = group.index.intersection(numeric_data.index)
            if len(valid_indices) == 0:
                continue
            matched_numeric = numeric_data.loc[valid_indices]
            residual_frame = (matched_numeric - baseline).abs()
            column_residuals = residual_frame.mean(axis=0).to_dict()
            residual = residual_frame.mean(axis=1)
            buckets.append(
                ResidualBucket(
                    label=str(bucket_value),
                    average_residual=float(residual.mean()),
                    sample_size=int(len(valid_indices)),
                    column_residuals={key: float(value) for key, value in column_residuals.items()},
                )
            )
        buckets.sort(key=lambda item: item.average_residual, reverse=True)
        insights.append(
            ResidualForensicsInsight(
                grouping="time_window" if column == "_auto_triage_window" else column,
                buckets=buckets[: config.top_residual_buckets],
            )
        )

    return insights


# ---------------------------------------------------------------------------
# Suspicion scoring
# ---------------------------------------------------------------------------


def _suspicion_score_key(entry: SuspicionScore) -> float:
    """Sort key for suspicion scores (higher is more suspicious)."""

    return entry.score


def _score_suspicion(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    pca_strength: dict[str, float],
    change_points: Sequence[ChangePointInsight],
    residuals: Sequence[ResidualForensicsInsight],
    config: AutoTriageConfig,
) -> list[SuspicionScore]:
    """Blend PCA, change-point, and residual signals into rankings."""

    per_column_change_counts: dict[str, int] = {column: 0 for column in numeric_data.columns}
    for insight in change_points:
        per_column_change_counts[insight.column] = per_column_change_counts.get(insight.column, 0) + len(insight.locations)

    per_column_residual = {column: 0.0 for column in numeric_data.columns}
    for insight in residuals:
        for bucket in insight.buckets:
            for column, value in bucket.column_residuals.items():
                per_column_residual[column] = per_column_residual.get(column, 0.0) + float(value)

    suspicion_entries: list[SuspicionScore] = []
    for column in numeric_data.columns:
        variability = float(pca_strength.get(column, 0.0))
        change_signal = per_column_change_counts.get(column, 0) / max(len(frame.index), 1)
        series = numeric_data[column]
        std = series.std(ddof=0) + 1e-6
        dispersion = float(np.mean(np.abs(series - series.mean())) / std)
        residual_signal = per_column_residual.get(column, 0.0) / max(len(residuals), 1)
        score = variability + change_signal + dispersion + residual_signal
        drivers = []
        if variability > 0:
            drivers.append("high PCA loading")
        if per_column_change_counts.get(column, 0):
            drivers.append("change points")
        if dispersion > 1:
            drivers.append("wide dispersion")
        if residual_signal > 0:
            drivers.append("residual spikes")

        suspicion_entries.append(
            SuspicionScore(
                target=column,
                target_type="variable",
                score=float(score),
                drivers=tuple(drivers),
            )
        )

    suspicion_entries.sort(key=_suspicion_score_key, reverse=True)
    suspicion_entries = suspicion_entries[: config.suspicion_top_k]

    if config.datetime_column:
        time_scores = _score_time_windows(frame, change_points, config)
        suspicion_entries.extend(time_scores)

    return suspicion_entries


def _score_time_windows(
    frame: pd.DataFrame,
    change_points: Sequence[ChangePointInsight],
    config: AutoTriageConfig,
) -> list[SuspicionScore]:
    """Translate change-point indices into time-window suspicion scores."""

    if not config.datetime_column or not change_points:
        return []

    datetime_index = frame[config.datetime_column]
    index_counts: dict[int, int] = {}
    for insight in change_points:
        for location in insight.locations:
            index_counts[location] = index_counts.get(location, 0) + 1

    scored: list[SuspicionScore] = []
    for location, count in index_counts.items():
        if location >= len(datetime_index):
            continue
        timestamp = datetime_index.iloc[location]
        scored.append(
            SuspicionScore(
                target=str(timestamp),
                target_type="time_window",
                score=float(count),
                drivers=("multiple change points",),
            )
        )
    scored.sort(key=_suspicion_score_key, reverse=True)
    return scored[: config.suspicion_top_k]


__all__ = [
    "AutoTriageConfig",
    "AutoTriageResult",
    "ChangePointInsight",
    "ClusterInsight",
    "PCAComponentInsight",
    "QualityFlag",
    "ResidualBucket",
    "ResidualForensicsInsight",
    "SuspicionScore",
    "run_auto_triage",
]

