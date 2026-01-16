"""Auto-triage analysis pipeline.

This module bundles unsupervised diagnostics (PCA, clustering, change point
finding, and residual forensics) into a single helper that can be triggered from
the API layer.  The routines favour readability and plentiful commenting so the
intent is crystal clear to stakeholders who may not routinely read Python code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

import logging
import math
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from scipy import stats

from relat_ai.services.analysis.utils import apply_sample_limit
from relat_ai.services.analysis.change_detection import (
    detect_cusum_change_points,
    detect_pelt_change_points,
)
from relat_ai.services.analysis.confidence_flags import (
    QualityFlag,
    build_quality_flags,
)

from relat_ai.core.autotriage_models import (
    ChangePointContext,
    ChangePointReportModel,
    ClusterFeatureStats,
    ClusterProfileModel,
    PCAExplainModel,
    SegmentSummary,
    SignalDetail,
    SuspicionItemModel,
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


@dataclass
class SignalVector:
    """Normalized signal contributions for a single target."""

    target: str
    raw_signals: dict[str, float] = field(default_factory=dict)
    normalized_signals: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, dict[str, Any]] = field(default_factory=dict)
    weighted_score: float = 0.0

    def normalize(self, all_signals: dict[str, dict[str, float]]) -> None:
        """Normalize raw signals to percentile ranks within the batch."""

        for signal_kind in {kind for signals in all_signals.values() for kind in signals}:
            value = self.raw_signals.get(signal_kind, 0.0)
            raw_population = np.array([signals.get(signal_kind, 0.0) for signals in all_signals.values()])
            # Filter out NaN and Inf values to prevent searchsorted failures
            population = raw_population[np.isfinite(raw_population)]
            if population.size == 0 or float(population.max()) == 0:
                self.normalized_signals[signal_kind] = 0.0
                continue
            # Handle case where the value itself is non-finite
            if not np.isfinite(value):
                self.normalized_signals[signal_kind] = 0.0
                continue
            rank = np.searchsorted(np.sort(population), value, side="right")
            percentile = rank / population.size
            self.normalized_signals[signal_kind] = float(percentile)

    def compute_weighted_score(self, weights: dict[str, float]) -> float:
        active = {kind: value for kind, value in self.normalized_signals.items() if value > 0}
        if not active:
            self.weighted_score = 0.0
            return 0.0
        weight_subset = {kind: weights.get(kind, 0.0) for kind in active}
        weight_sum = sum(weight_subset.values())
        if weight_sum == 0:
            self.weighted_score = 0.0
            return 0.0
        score = sum(active[kind] * (weight_subset[kind] / weight_sum) for kind in active)
        self.weighted_score = float(score)
        return self.weighted_score

    def build_bullets(self, top_n: int = 4) -> list[SignalDetail]:
        sorted_signals = sorted(
            self.normalized_signals.items(), key=lambda item: item[1], reverse=True
        )
        bullets: list[SignalDetail] = []
        for kind, value in sorted_signals[:top_n]:
            if value <= 0:
                continue
            metadata = self.metadata.get(kind, {})
            bullets.append(
                SignalDetail(
                    kind=kind,
                    weight=round(float(value), 3),
                    detail=_format_signal_detail(kind, value, metadata),
                    link=_build_signal_link(kind, self.target, metadata),
                )
            )
        return bullets

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
    pca_explain: Optional[PCAExplainModel] = None
    cluster_profile: Optional[ClusterProfileModel] = None
    change_point_reports: Sequence[ChangePointReportModel] = ()
    suspicion_items: Sequence[SuspicionItemModel] = ()

# ---------------------------------------------------------------------------
# Migration plan for richer payloads
# ---------------------------------------------------------------------------
#
# ``SuspicionItem`` / ``ClusterProfile`` / ``PCAExplain`` / ``ChangePointReport``
# will eventually replace the light-weight dataclasses above.  To get there
# without breaking consumers that still depend on the legacy shapes:
#
# 1. Introduce parallel dataclasses mirroring the richer schema (e.g.
#    ``SuspicionItemPayload``) and add optional fields for narratives, links, and
#    contribution breakdowns.
# 2. Teach ``run_auto_triage`` to compute those details incrementally while the
#    existing attributes are still populated.  For example, the PCA routine can
#    return both ``PCAComponentInsight`` and a structured ``PCAExplain`` object
#    with variance tables and narrative strings derived from loadings.
# 3. Plumb a feature flag (``emit_structured_payloads``) through
#    ``AutoTriageConfig`` so the service can emit both schemas in parallel during
#    the rollout window.  When the flag is disabled we simply drop the new
#    structures before returning.
# 4. Update helper functions like ``_score_suspicion`` to produce the new
#    ``contrib`` and ``top_signals`` fields, but also aggregate them back into the
#    old ``drivers`` list so nothing is lost for legacy clients.
# 5. Ensure change-point and cluster helpers populate context hooks (segment
#    stats, by-time summaries, medoid indices) behind the flag so downstream
#    components can opt-in tab by tab.
#
# With these steps the backend can emit the richer payloads, cache them, and
# still satisfy historical consumers until the front-end migration is complete.


@dataclass(slots=True)
class AutoTriageConfig:
    """Configures the auto-triage pipeline."""

    numeric_columns: Sequence[str]
    categorical_columns: Sequence[str] = ()
    datetime_column: str | None = None
    batch_column: str | None = None
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
    min_segment_size: int = 30
    emit_structured_payloads: bool = True
    strict_missingness: bool = False  # When True, fail if any column exceeds high_missing_threshold

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
        if self.min_segment_size < 1:
            raise ValueError("min_segment_size must be at least 1")

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

    (
        pca_insights,
        pca_component_strength,
        pca_explain,
    ) = _run_pca(numeric_data, config)

    (
        cluster_insights,
        cluster_labels,
        cluster_profile,
    ) = _perform_clustering(numeric_data, working_frame, config)

    change_points, change_point_reports = _detect_change_points(
        working_frame,
        numeric_data,
        config,
        cluster_labels=cluster_labels,
        cluster_profile=cluster_profile,
    )
    residual_insights = _compute_residual_forensics(working_frame, numeric_data, config)
    suspicion_rankings, suspicion_items = _score_suspicion(
        working_frame,
        numeric_data,
        pca_component_strength,
        change_points,
        residual_insights,
        config,
        cluster_profile=cluster_profile,
        cluster_labels=cluster_labels,
        change_point_reports=change_point_reports,
        imputation_flags=imputation_flags,
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
        pca_explain=pca_explain if config.emit_structured_payloads else None,
        cluster_profile=cluster_profile if config.emit_structured_payloads else None,
        change_point_reports=change_point_reports if config.emit_structured_payloads else (),
        suspicion_items=suspicion_items if config.emit_structured_payloads else (),
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
    if config.batch_column and config.batch_column not in frame.columns:
        raise KeyError(f"Missing batch column: {config.batch_column}")


def _prepare_numeric_matrix(
    frame: pd.DataFrame, config: AutoTriageConfig
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Return a numeric matrix with median imputation and scaling applied.

    The returned DataFrame mirrors the input order.  We also compute a dictionary
    detailing the proportion of missing values for each column, allowing the
    calling code to surface data-quality warnings later.

    When ``config.strict_missingness`` is True, raises ValueError if any column
    exceeds the configured ``high_missing_threshold``.
    """

    numeric = frame.loc[:, config.numeric_columns].apply(pd.to_numeric, errors="coerce")

    missing_ratio = numeric.isna().mean().to_dict()

    # Strict missingness check: fail-fast if critical data quality thresholds are exceeded
    if config.strict_missingness:
        failures = [
            col for col, ratio in missing_ratio.items()
            if ratio > config.high_missing_threshold
        ]
        if failures:
            raise ValueError(
                f"Data quality failure: columns {failures} exceed "
                f"{config.high_missing_threshold:.0%} missingness limit in strict mode."
            )

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
) -> tuple[list[PCAComponentInsight], dict[str, float], Optional[PCAExplainModel]]:
    """Perform PCA and capture component strengths per original variable."""

    component_count = min(config.max_components, numeric_data.shape[1])
    pca_model = PCA(n_components=component_count, random_state=config.random_state)
    pca_model.fit(numeric_data)

    components: list[PCAComponentInsight] = []
    strength: dict[str, float] = {column: 0.0 for column in numeric_data.columns}

    variance_table: list[dict[str, Any]] = []  # Contains {"pc": str, "ratio": float}
    loadings_table: dict[str, list[tuple[str, float]]] = {}

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
        variance_table.append({"pc": f"PC{index + 1}", "ratio": float(variance_ratio)})
        loadings_table[f"PC{index + 1}"] = [
            (feature, float(loadings[feature]))
            for feature in ranked.index[: config.top_component_features]
        ]

    pca_explain: Optional[PCAExplainModel] = None
    if config.emit_structured_payloads:
        narratives = _build_pca_narratives(variance_table, loadings_table)
        cumulative_variance = float(sum(item["ratio"] for item in variance_table))
        pca_explain = PCAExplainModel(
            variance=variance_table,
            loadings=loadings_table,
            narrative=narratives,
            cumulative_variance=cumulative_variance,
        )

    return components, strength, pca_explain


# ---------------------------------------------------------------------------
# PCA narratives
# ---------------------------------------------------------------------------


def _build_pca_narratives(
    variance_table: list[dict[str, Any]],
    loadings_table: dict[str, list[tuple[str, float]]],
    *,
    max_features: int = 3,
) -> list[str]:
    """Generate simple natural language narratives for PCA components."""

    narratives: list[str] = []
    for entry in variance_table:
        pc_name = entry["pc"]
        variance_pct = entry["ratio"] * 100
        contributions = loadings_table.get(pc_name, [])
        if not contributions:
            narratives.append(f"{pc_name} explains {variance_pct:.1f}% of variance.")
            continue

        sorted_contributions = sorted(
            contributions,
            key=lambda item: abs(item[1]),
            reverse=True,
        )
        top_contribs = sorted_contributions[:max_features]
        positive = [name for name, loading in top_contribs if loading > 0]
        negative = [name for name, loading in top_contribs if loading < 0]
        contrib_str = ", ".join(
            f"{name} ({loading:+.2f})" for name, loading in top_contribs
        )
        if positive and negative:
            narrative = (
                f"{pc_name} ({variance_pct:.1f}%) contrasts "
                f"{_describe_feature_group(positive)} versus {_describe_feature_group(negative)}"
                f" with top contributors {contrib_str}."
            )
        else:
            narrative = (
                f"{pc_name} ({variance_pct:.1f}%) captures {_describe_feature_group([name for name, _ in top_contribs])} "
                f"variation led by {contrib_str}."
            )
        narratives.append(narrative)

    return narratives


def _describe_feature_group(feature_names: list[str]) -> str:
    """Heuristic to describe a set of feature names."""

    if not feature_names:
        return "mixed"
    joined = " ".join(feature_names).lower()
    if any(keyword in joined for keyword in ["time", "duration", "date"]):
        return "temporal"
    if any(keyword in joined for keyword in ["mean", "avg", "level"]):
        return "magnitude"
    if any(keyword in joined for keyword in ["std", "var", "spread"]):
        return "variability"
    if any(keyword in joined for keyword in ["max", "min", "peak"]):
        return "extremes"
    if any(keyword in joined for keyword in ["rate", "speed"]):
        return "rate"
    return "composite"


# ---------------------------------------------------------------------------
# Change-point detection
# ---------------------------------------------------------------------------


def _detect_change_points(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    config: AutoTriageConfig,
    *,
    cluster_labels: Optional[np.ndarray] = None,
    cluster_profile: Optional[ClusterProfileModel] = None,
) -> tuple[list[ChangePointInsight], list[ChangePointReportModel]]:
    """Detect change points and build enriched reports."""

    change_points: list[ChangePointInsight] = []
    reports: list[ChangePointReportModel] = []

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
            sorted_locations = sorted(int(location) for location in locations)
            change_points.append(
                ChangePointInsight(
                    column=column,
                    method=method,
                    locations=sorted_locations,
                )
            )
            if config.emit_structured_payloads:
                reports.append(
                    _build_change_point_report(
                        frame=frame,
                        series=series,
                        column=column,
                        method=method,
                        locations=sorted_locations,
                        config=config,
                        cluster_labels=cluster_labels,
                        cluster_profile=cluster_profile,
                    )
                )

    return change_points, reports

def _apply_clustering_method(
    numeric_data: pd.DataFrame,
    method_name: str,
    n_clusters: int,
    sample_size: int,
    random_state: int | None = None,
) -> tuple[ClusterInsight, np.ndarray] | None:
    """Apply a clustering method and return the insight plus labels."""

    adjusted_clusters = min(n_clusters, sample_size)
    if adjusted_clusters <= 1:
        return None

    if method_name == "kmeans":
        model = KMeans(n_clusters=adjusted_clusters, random_state=random_state, n_init=10)
    elif method_name == "hierarchical":
        model = AgglomerativeClustering(n_clusters=adjusted_clusters)
    else:
        return None

    labels = model.fit_predict(numeric_data)
    return ClusterInsight(method=method_name, cluster_sizes=_count_labels(labels)), labels


def _perform_clustering(
    numeric_data: pd.DataFrame,
    frame: pd.DataFrame,
    config: AutoTriageConfig,
) -> tuple[list[ClusterInsight], Optional[np.ndarray], Optional[ClusterProfileModel]]:
    """Run clustering and optionally compute a descriptive profile."""

    results: list[ClusterInsight] = []
    sample_size = len(numeric_data.index)
    if sample_size == 0:
        return results, None, None

    kmeans_labels: Optional[np.ndarray] = None

    kmeans_result = _apply_clustering_method(
        numeric_data,
        "kmeans",
        config.kmeans_clusters,
        sample_size,
        config.random_state,
    )
    if kmeans_result:
        insight, labels = kmeans_result
        results.append(insight)
        kmeans_labels = labels

    hierarchical_result = _apply_clustering_method(
        numeric_data,
        "hierarchical",
        config.hierarchical_clusters,
        sample_size,
    )
    if hierarchical_result:
        insight, _ = hierarchical_result
        results.append(insight)

    profile: Optional[ClusterProfileModel] = None
    if kmeans_labels is not None and config.emit_structured_payloads:
        profile = compute_cluster_profile(
            df=frame,
            features=list(numeric_data.columns),
            cluster_labels=kmeans_labels,
            time_col=config.datetime_column,
            n_medoids=5,
            max_samples_for_distance=min(len(frame), 5000),
        )

    return results, kmeans_labels, profile


def _count_labels(labels: Iterable[int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for label in labels:
        counts[int(label)] = counts.get(int(label), 0) + 1
    return counts


def compute_cluster_profile(
    df: pd.DataFrame,
    features: list[str],
    cluster_labels: np.ndarray,
    *,
    time_col: str | None = None,
    n_medoids: int = 5,
    max_samples_for_distance: int = 5000,
) -> ClusterProfileModel:
    """Compute descriptive statistics and narratives for clusters."""

    numeric_features = df.loc[:, features].apply(pd.to_numeric, errors="coerce")
    numeric_features = numeric_features.dropna(axis=1, how="all")

    unique_labels = np.unique(cluster_labels)
    total = len(cluster_labels)
    sizes = [
        {
            "id": int(label),
            "n": int(np.sum(cluster_labels == label)),
            "pct": round(float(np.sum(cluster_labels == label)) / max(total, 1), 4),
        }
        for label in unique_labels
    ]

    top_diff_features: list[dict[str, Any]] = []
    for feature in numeric_features.columns:
        groups = [
            numeric_features.loc[cluster_labels == label, feature].dropna()
            for label in unique_labels
        ]
        if sum(len(group) for group in groups) <= len(unique_labels):
            continue
        try:
            f_stat, p_value = stats.f_oneway(*groups)
        except ValueError:
            f_stat, p_value = 0.0, 1.0

        overall = pd.concat(groups) if groups else pd.Series(dtype=float)
        overall_mean = overall.mean() if not overall.empty else 0.0
        ss_between = sum(
            len(group) * (group.mean() - overall_mean) ** 2 for group in groups if len(group) > 0
        )
        ss_total = sum(((group - overall_mean) ** 2).sum() for group in groups if len(group) > 0)
        eta_sq = float(ss_between / ss_total) if ss_total else 0.0
        entry = {
            "feature": feature,
            "f_stat": float(f_stat),
            "p": float(p_value),
            "eta_squared": eta_sq,
            "mean_by_cluster": {
                str(int(label)): float(groups[idx].mean()) if len(groups[idx]) else math.nan
                for idx, label in enumerate(unique_labels)
            },
        }
        top_diff_features.append(entry)

    top_diff_features.sort(key=lambda item: (-(item["eta_squared"]), item["p"]))
    top_diff_features = top_diff_features[:15]

    feature_importance: list[dict[str, Any]] = []  # Contains {"feature": str, "importance": float}
    try:
        if numeric_features.shape[1] > 0 and len(np.unique(cluster_labels)) > 1:
            scaler = StandardScaler()
            scaled = scaler.fit_transform(numeric_features.fillna(numeric_features.mean()))
            clf = DecisionTreeClassifier(
                max_depth=4,
                min_samples_leaf=max(5, len(df) // 100),
                random_state=42,
            )
            clf.fit(scaled, cluster_labels)
            importances = clf.feature_importances_
            feature_importance = [
                {"feature": feature, "importance": float(importance)}
                for feature, importance in zip(numeric_features.columns, importances)
                if importance > 0
            ]
            feature_importance.sort(key=lambda item: item["importance"], reverse=True)
            feature_importance = feature_importance[:15]
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.warning("Tree-based importance failed: %s", exc)

    medoids: dict[str, list[int]] = {}
    try:
        if numeric_features.shape[1] > 0:
            scaler = StandardScaler()
            scaled_full = scaler.fit_transform(numeric_features.fillna(numeric_features.mean()))
            rng = np.random.default_rng(42)
            for label in unique_labels:
                indices = np.where(cluster_labels == label)[0]
                if len(indices) == 0:
                    continue
                if len(indices) > max_samples_for_distance:
                    sampled = rng.choice(indices, size=max_samples_for_distance, replace=False)
                else:
                    sampled = indices
                distances = pairwise_distances(scaled_full[sampled], metric="euclidean")
                centre_idx = int(np.argmin(distances.sum(axis=1)))
                distance_to_centre = distances[centre_idx]
                closest = np.argsort(distance_to_centre)[:n_medoids]
                medoids[str(int(label))] = [int(sampled[idx]) for idx in closest]
    except Exception as exc:  # pragma: no cover - defensive logging
        logging.warning("Medoid computation failed: %s", exc)

    per_feature_stats: dict[str, dict[str, ClusterFeatureStats]] = {}
    for label in unique_labels:
        cluster_mask = cluster_labels == label
        stats_for_cluster: dict[str, ClusterFeatureStats] = {}
        for feature in numeric_features.columns:
            values = numeric_features.loc[cluster_mask, feature].dropna()
            if values.empty:
                continue
            q1, q3 = np.percentile(values, [25, 75])
            stats_for_cluster[feature] = ClusterFeatureStats(
                mean=float(values.mean()),
                median=float(values.median()),
                std=float(values.std(ddof=0)),
                iqr=float(q3 - q1),
                n=int(len(values)),
            )
        per_feature_stats[str(int(label))] = stats_for_cluster

    by_time: Optional[list[dict[str, Any]]] = None
    if time_col and time_col in df.columns:
        try:
            temporal = df[[time_col]].copy()
            temporal["cluster"] = cluster_labels
            temporal[time_col] = pd.to_datetime(temporal[time_col], errors="coerce")
            temporal = temporal.dropna(subset=[time_col])
            if not temporal.empty:
                temporal["window"] = temporal[time_col].dt.to_period("W")
                counts = temporal.groupby(["window", "cluster"]).size()
                proportions = counts.groupby(level=0).apply(lambda series: series / series.sum())
                by_time = [
                    {
                        "cluster": int(label),
                        "window": str(period),
                        "pct": round(float(proportion), 4),
                        "n": int(counts.loc[(period, label)]),
                    }
                    for (period, label), proportion in proportions.items()
                ]
        except Exception as exc:  # pragma: no cover - defensive logging
            logging.warning("Temporal cluster profiling failed: %s", exc)

    return ClusterProfileModel(
        method="kmeans",
        k=int(len(unique_labels)),
        sizes=sizes,
        top_diff_features=top_diff_features,
        feature_importance=feature_importance,
        medoids=medoids,
        per_feature_stats=per_feature_stats,
        by_time=by_time,
    )


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
    *,
    cluster_profile: Optional[ClusterProfileModel],
    cluster_labels: Optional[np.ndarray],
    change_point_reports: Sequence[ChangePointReportModel],
    imputation_flags: Optional[dict[str, float]] = None,
) -> tuple[list[SuspicionScore], list[SuspicionItemModel]]:
    """Blend signals into rankings and structured suspicion items."""
    
    if imputation_flags is None:
        imputation_flags = {}

    weights = {
        "pca_loading": 0.35,
        "changepoint": 0.25,
        "cluster": 0.2,
        "residual": 0.1,
        "dispersion": 0.1,
    }

    change_summary = defaultdict(list)
    for report in change_point_reports:
        change_summary[report.column].append(report)

    residual_summary: dict[str, dict[str, Any]] = defaultdict(lambda: {"max_bucket": 0.0, "bucket_name": None})
    for insight in residuals:
        if not insight.buckets:
            continue
        top_bucket = max(insight.buckets, key=lambda bucket: bucket.average_residual)
        for column, value in top_bucket.column_residuals.items():
            meta = residual_summary[column]
            if value > meta["max_bucket"]:
                meta["max_bucket"] = float(value)
                meta["bucket_name"] = top_bucket.label

    cluster_lookup = {}
    if cluster_profile:
        for feature_entry in cluster_profile.top_diff_features:
            cluster_lookup[feature_entry["feature"]] = feature_entry

    vectors: dict[str, SignalVector] = {}
    for column in numeric_data.columns:
        series = numeric_data[column]
        vector = SignalVector(target=column)
        vector.raw_signals["pca_loading"] = float(pca_strength.get(column, 0.0))

        # Change-point signal
        reports = change_summary.get(column, [])
        if reports:
            total_changes = sum(report.n for report in reports)
            vector.raw_signals["changepoint"] = float(total_changes)
            timestamps = [ctx.timestamp for report in reports for ctx in report.context if ctx.timestamp]
            vector.metadata["changepoint"] = {
                "count": total_changes,
                "timestamps": timestamps[:5],
            }

        # Cluster signal
        if cluster_lookup.get(column):
            feature_entry = cluster_lookup[column]
            vector.raw_signals["cluster"] = float(feature_entry.get("eta_squared", 0.0))
            vector.metadata["cluster"] = {
                "eta_squared": float(feature_entry.get("eta_squared", 0.0)),
                "p_value": float(feature_entry.get("p", 1.0)),
            }

        # Residual signal
        residual_meta = residual_summary.get(column)
        if residual_meta["max_bucket"] > 0:
            vector.raw_signals["residual"] = float(residual_meta["max_bucket"])
            vector.metadata["residual"] = {
                "max_bucket": residual_meta["max_bucket"],
                "bucket_name": residual_meta["bucket_name"],
            }

        # Dispersion (MAD over sigma)
        mad = float(np.median(np.abs(series - np.median(series))))
        std = float(series.std(ddof=0)) + 1e-6
        dispersion = mad / std if std > 0 else 0.0
        vector.raw_signals["dispersion"] = dispersion
        vector.metadata["dispersion"] = {"mad_over_sigma": dispersion}

        # Additional change point metadata when none exist
        if "changepoint" not in vector.metadata and reports:
            vector.metadata["changepoint"] = {"count": len(reports)}

        vectors[column] = vector

    all_signals = {target: vec.raw_signals for target, vec in vectors.items()}
    for vector in vectors.values():
        vector.normalize(all_signals)
        vector.compute_weighted_score(weights)

    suspicion_scores: list[SuspicionScore] = []
    suspicion_items: list[SuspicionItemModel] = []

    for column, vector in vectors.items():
        bullets = vector.build_bullets()
        contrib_active = {k: v for k, v in vector.normalized_signals.items() if v > 0}
        total_active = sum(contrib_active.values()) or 1.0
        contrib = {k: v / total_active for k, v in contrib_active.items()}
        
        # Build quality flags for this column
        flags: list[str] = []
        if column in imputation_flags and imputation_flags[column] > config.high_missing_threshold:
            flags.append("high_missing")
        if vector.raw_signals.get("dispersion", 0.0) > 0.8:
            flags.append("high_dispersion")
        
        suspicion_scores.append(
            SuspicionScore(
                target=column,
                target_type="variable",
                score=vector.weighted_score,
                drivers=tuple(b.detail for b in bullets) or ("no signal",),
            )
        )
        try:
            suspicion_items.append(
                SuspicionItemModel(
                    target=column,
                    score=round(vector.weighted_score, 4),
                    contrib=contrib or {"pca_loading": 0.0},
                    top_signals=bullets,
                    links={
                        key: value
                        for key, value in {
                            "pca_component": vector.metadata.get("pca_loading", {}).get("component"),
                            "changepoint_tab": column if vector.raw_signals.get("changepoint") else None,
                            "cluster_profile": column if vector.raw_signals.get("cluster") else None,
                        }.items()
                        if value is not None
                    },
                    flags=flags,
                    raw_stats={k: v for k, v in vector.metadata.items()},
                )
            )
        except ValueError as exc:
            logging.warning("Suspicion item validation failed for %s: %s", column, exc)

    suspicion_scores.sort(key=_suspicion_score_key, reverse=True)
    suspicion_items.sort(key=lambda item: item.score, reverse=True)

    suspicion_scores = suspicion_scores[: config.suspicion_top_k]
    suspicion_items = suspicion_items[: config.suspicion_top_k]

    if config.datetime_column:
        time_scores = _score_time_windows(frame, change_points, config)
        suspicion_scores.extend(time_scores)

    return suspicion_scores, suspicion_items


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


def _format_signal_detail(kind: str, value: float, metadata: dict[str, Any]) -> str:
    if kind == "pca_loading":
        component = metadata.get("component", "PC1")
        loading = metadata.get("loading", value)
        return f"{component} loading {loading:.3f}"
    if kind == "changepoint":
        count = metadata.get("count", 0)
        timestamps = metadata.get("timestamps", [])
        ts_fragment = f" ({', '.join(timestamps[:3])})" if timestamps else ""
        plural = "s" if count != 1 else ""
        return f"{count} change point{plural}{ts_fragment}"
    if kind == "cluster":
        eta_sq = metadata.get("eta_squared", 0.0)
        p_value = metadata.get("p_value", 1.0)
        return f"Cluster separation η²={eta_sq:.2f} (p={p_value:.2e})"
    if kind == "residual":
        max_bucket = metadata.get("max_bucket", 0.0)
        bucket_name = metadata.get("bucket_name")
        suffix = f" in {bucket_name}" if bucket_name else ""
        return f"Residual spike {max_bucket:.2f}{suffix}"
    if kind == "dispersion":
        return f"High dispersion (MAD/σ={metadata.get('mad_over_sigma', value):.2f})"
    return f"{kind}: {value:.2f}"


def _build_signal_link(kind: str, target: str, metadata: dict[str, Any]) -> Optional[dict[str, Any]]:
    if kind == "pca_loading":
        component = metadata.get("component")
        if component:
            return {"tab": "pca", "component": component}
    if kind == "changepoint":
        return {"tab": "changepoints", "column": target}
    if kind == "cluster":
        return {"tab": "clusters", "feature": target}
    if kind == "residual":
        return {"tab": "residuals", "target": target}
    return None


def _build_change_point_report(
    *,
    frame: pd.DataFrame,
    series: pd.Series,
    column: str,
    method: str,
    locations: Sequence[int],
    config: AutoTriageConfig,
    cluster_labels: Optional[np.ndarray],
    cluster_profile: Optional[ClusterProfileModel],
) -> ChangePointReportModel:
    """Construct a structured change-point report."""

    total_len = len(series)
    boundaries = [0, *locations, total_len]
    segments: list[SegmentSummary] = []
    flags: set[str] = set()

    for start, end in zip(boundaries[:-1], boundaries[1:]):
        # The segment includes rows [start, end), translate to inclusive indices for reporting
        segment_slice = series.iloc[start:end]
        if segment_slice.empty:
            continue
        end_inclusive = end - 1
        summary = SegmentSummary(
            start=int(start),
            end=int(max(end_inclusive, start)),
            mean=float(segment_slice.mean()),
            std=float(segment_slice.std(ddof=0)),
            n=int(len(segment_slice)),
            pct=round(len(segment_slice) / max(total_len, 1), 4),
        )
        if summary.n < config.min_segment_size:
            flags.add("insufficient_data")
        segments.append(summary)

    if len(locations) > 0 and len(locations) > max(1, total_len // max(config.min_segment_size, 1)):
        flags.add("over_segmented")

    strengths: list[float] = []
    contexts: list[ChangePointContext] = []
    dt_series = None
    if config.datetime_column and config.datetime_column in frame.columns:
        dt_series = frame.loc[series.index, config.datetime_column]
        dt_series = pd.to_datetime(dt_series, errors="coerce")

    batch_series = None
    if config.batch_column and config.batch_column in frame.columns:
        batch_series = frame.loc[series.index, config.batch_column]

    for idx, location in enumerate(locations):
        prev_boundary = boundaries[idx]
        next_boundary = boundaries[idx + 1]
        before = series.iloc[prev_boundary:location]
        after = series.iloc[location:next_boundary]
        if len(before) > 0 and len(after) > 0:
            strengths.append(float(abs(before.mean() - after.mean())))
        else:
            strengths.append(0.0)

        timestamp = None
        if dt_series is not None and 0 <= location < len(dt_series):
            ts_value = dt_series.iloc[location]
            if not pd.isna(ts_value):
                timestamp = pd.Timestamp(ts_value).isoformat()

        cluster_shift = None
        if cluster_labels is not None and len(cluster_labels) == total_len:
            before_labels = cluster_labels[prev_boundary:location]
            after_labels = cluster_labels[location:next_boundary]
            if before_labels.size > 0 and after_labels.size > 0:
                before_mode = int(np.bincount(before_labels).argmax())
                after_mode = int(np.bincount(after_labels).argmax())
                if before_mode != after_mode:
                    cluster_shift = {"before": before_mode, "after": after_mode}

        batch_info = None
        if batch_series is not None and 0 <= location < len(batch_series):
            batch_value = batch_series.iloc[location]
            if not pd.isna(batch_value):
                batch_info = str(batch_value)

        contexts.append(
            ChangePointContext(
                index=int(location),
                timestamp=timestamp,
                cluster_shift=cluster_shift,
                batch_info=batch_info,
            )
        )

    return ChangePointReportModel(
        column=column,
        method=method,
        n=len(locations),
        indices=list(locations),
        segments=segments,
        strength=strengths,
        context=contexts,
        flags=sorted(flags),
    )


__all__ = [
    "AutoTriageConfig",
    "AutoTriageResult",
    "ChangePointInsight",
    "ClusterInsight",
    "SignalVector",
    "compute_cluster_profile",
    "PCAComponentInsight",
    "QualityFlag",
    "ResidualBucket",
    "ResidualForensicsInsight",
    "SuspicionScore",
    "run_auto_triage",
]

