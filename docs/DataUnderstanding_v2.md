# Implementation Plan: "Make It Understandable" (v2.0)

**Document Version**: 2.0  
**Last Updated**: 2025-10-14  
**Status**: Planning (Pre-Implementation)

---

## Executive Summary

**Purpose**: Transform auto-triage outputs from raw statistical scores into actionable, 
interpretable insights with clear narratives, contribution breakdowns, and navigable 
context. This addresses UserRequirements.md section 3.4 (Insights Layer) and enables 
non-statisticians to understand "why" findings matter.

**Risk Assessment**: Medium-High
- Statistical correctness must be validated against reference implementations
- Performance impact on 50k × 50 datasets needs benchmarking before implementation
- Integration with existing QualityFlag and caching systems requires careful coordination
- Serialization layer expansion affects API contracts and frontend consumers

**Success Metrics**:
- Users can answer "Why is X suspicious?" in one sentence from the UI
- Suspicion scores have <5% variance across identical inputs (deterministic)
- Cluster profiling completes within 90-second budget (TechnicalSpecification.md Appendix A)
- All p-values and effect sizes match reference implementations (scipy, statsmodels)
- Zero NaN/Inf values in output JSON
- Navigation links successfully jump between tabs with correct context

**Estimated Effort**: 3-4 weeks
- Week 1: Data contracts, backend scaffolding, statistical validation tests
- Week 2: Core interpretation functions (cluster profiling, PCA narratives, suspicion scoring)
- Week 3: Frontend integration, state management, visualization components
- Week 4: Performance optimization, integration testing, documentation

---

## Table of Contents

0. Data Contracts & Type Safety
1. Backend Implementation
   - 1.0 Suspicion Scoring & Explanation Wiring
   - 1.1 Cluster Profiling
   - 1.2 PCA Narratives
   - 1.3 Change-Point Context & Segmentation
   - 1.4 Evidence Builder
2. Frontend Implementation
   - 2.0 State Management Architecture
   - 2.1 Suspicion Rankings Tab
   - 2.2 PCA Tab Enhancements
   - 2.3 Change-Points Tab Redesign
   - 2.4 Clusters Tab Deep Dive
   - 2.5 Navigation & Deep Linking
   - 2.6 Responsive Design
3. Quality & Guardrails
4. Configuration Management
5. Testing Strategy
6. Performance Profiling
7. Migration & Backward Compatibility
8. Acceptance Tests

---

## 0. Data Contracts & Type Safety

### 0.1 Pydantic Models for Validation

All new data structures use Pydantic BaseModel for JSON schema validation, 
automatic serialization, and OpenAPI documentation generation.

```python
# backend/relat_ai/core/autotriage_models.py (NEW FILE)
from pydantic import BaseModel, Field, validator, root_validator
from typing import Literal, Optional, Any
from datetime import datetime

class SignalDetail(BaseModel):
    """Individual signal contributing to suspicion score."""
    kind: Literal["pca_loading", "changepoint", "cluster", "residual", "dispersion"]
    weight: float = Field(ge=0.0, le=1.0, description="Normalized contribution (0-1)")
    detail: str = Field(min_length=1, description="Human-readable explanation")
    link: Optional[dict[str, Any]] = Field(default=None, description="UI navigation hints")
    
    class Config:
        frozen = True  # Immutable after creation

class SuspicionItemModel(BaseModel):
    """Enhanced suspicion ranking with contribution breakdown and evidence."""
    target: str = Field(min_length=1, description="Variable or feature name")
    score: float = Field(ge=0.0, le=1.0, description="Normalized suspicion score")
    contrib: dict[str, float] = Field(description="Contribution by signal type")
    top_signals: list[SignalDetail] = Field(
        max_items=4, 
        description="Top 4 evidence bullets, sorted by weight descending"
    )
    links: dict[str, str] = Field(
        default_factory=dict, 
        description="Navigation targets: {pca_component: 'PC1', ...}"
    )
    flags: list[str] = Field(
        default_factory=list, 
        description="Quality codes: ['collinearity', 'low_n', ...]"
    )
    raw_stats: Optional[dict[str, dict]] = Field(
        default=None, 
        description="Underlying statistics for tooltips/drill-downs"
    )
    
    @validator('contrib')
    def contributions_sum_to_one(cls, v):
        """Ensure contribution weights are normalized."""
        total = sum(v.values())
        if not (0.95 <= total <= 1.05):
            raise ValueError(f"Contributions must sum to ~1.0, got {total:.3f}")
        # Normalize to exactly 1.0
        normalizer = 1.0 / total
        return {k: round(val * normalizer, 4) for k, val in v.items()}
    
    @validator('top_signals')
    def signals_sorted_by_weight(cls, v):
        """Ensure signals are sorted descending by weight."""
        weights = [s.weight for s in v]
        if weights != sorted(weights, reverse=True):
            raise ValueError("Signals must be sorted by weight descending")
        return v
    
    @root_validator
    def validate_consistency(cls, values):
        """Ensure contrib keys match signal kinds."""
        contrib_keys = set(values.get('contrib', {}).keys())
        signal_kinds = {s.kind for s in values.get('top_signals', [])}
        # Signal kinds should be subset of contrib keys
        if not signal_kinds.issubset(contrib_keys):
            missing = signal_kinds - contrib_keys
            raise ValueError(f"Signals reference missing contrib keys: {missing}")
        return values


class ClusterFeatureStats(BaseModel):
    """Per-feature statistics for a single cluster."""
    mean: float
    median: float
    std: float
    iqr: float  # Interquartile range (Q3 - Q1)
    n: int = Field(gt=0, description="Non-NaN sample count")


class ClusterProfileModel(BaseModel):
    """Enhanced cluster information with profiling statistics."""
    method: Literal["kmeans", "hierarchical"]
    k: int = Field(gt=0, description="Number of clusters")
    sizes: list[dict[str, Any]] = Field(
        description="[{id:0, n:850, pct:0.471}, ...]"
    )
    top_diff_features: list[dict[str, Any]] = Field(
        max_items=15,
        description="Features with strongest between-cluster differences (ANOVA/Kruskal)"
    )
    feature_importance: list[dict[str, float]] = Field(
        max_items=15,
        description="Tree-based importance scores for cluster prediction"
    )
    medoids: dict[str, list[int]] = Field(
        description="Representative sample indices per cluster: {'0': [12, 89, ...], ...}"
    )
    per_feature_stats: dict[str, dict[str, ClusterFeatureStats]] = Field(
        description="Statistics by cluster: {cluster_id: {feature: stats, ...}, ...}"
    )
    by_time: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Temporal distribution if datetime column present"
    )


class PCAExplainModel(BaseModel):
    """PCA results with narrative explanations and sorted loadings."""
    variance: list[dict[str, float]] = Field(
        description="[{pc:'PC1', ratio:0.3454}, ...]"
    )
    loadings: dict[str, list[tuple[str, float]]] = Field(
        description="Top contributors per PC: {'PC1': [('feat', 0.34), ...], ...}"
    )
    narrative: list[str] = Field(
        description="Plain-English interpretations per PC"
    )
    cumulative_variance: float = Field(
        ge=0.0, le=1.0, 
        description="Cumulative variance explained by all components"
    )


class SegmentSummary(BaseModel):
    """Statistical summary for a time series segment between change points."""
    start: int = Field(ge=0, description="Start index (inclusive)")
    end: int = Field(ge=0, description="End index (inclusive)")
    mean: float
    std: float
    n: int = Field(gt=0)
    
    @validator('end')
    def end_after_start(cls, v, values):
        if 'start' in values and v < values['start']:
            raise ValueError("end must be >= start")
        return v


class ChangePointContext(BaseModel):
    """Contextual information around a change point."""
    index: int = Field(ge=0)
    timestamp: Optional[str] = None
    cluster_shift: Optional[dict[str, int]] = Field(
        default=None,
        description="Cluster composition before/after: {before: 1, after: 2}"
    )
    batch_info: Optional[str] = None
    

class ChangePointReportModel(BaseModel):
    """Enhanced change-point detection with segment summaries and context."""
    column: str
    method: Literal["pelt", "cusum"]
    n: int = Field(ge=0, description="Number of change points detected")
    indices: list[int] = Field(description="Change point locations (sorted)")
    segments: list[SegmentSummary] = Field(
        description="Statistical summaries for each segment"
    )
    strength: list[float] = Field(
        description="Test statistics indicating change magnitude"
    )
    context: list[ChangePointContext] = Field(
        default_factory=list,
        description="Contextual metadata (time, cluster, batch) per change point"
    )
    flags: list[str] = Field(
        default_factory=list,
        description="Quality flags: ['over_segmented', 'low_strength', ...]"
    )
```

### 0.2 Integration with Existing Systems

**QualityFlag Integration**:
- Existing `backend/relat_ai/services/analysis/confidence_flags.py` remains authoritative source
- New `SuspicionItemModel.flags` and `ChangePointReportModel.flags` contain string codes
- Codes map 1:1 to existing `QualityFlag.code` values:
  - `"collinearity"` → Pearson |r| > 0.95
  - `"low_n"` → Sample size < 300
  - `"high_missing"` → >20% missing values
  - `"constant_series"` → std < 1e-9
  - `"insufficient_data"` → n < 2 * min_segment_size
  - `"over_segmented"` → change points > max_breaks
  - `"fallback_used"` → ruptures failed, legacy method used
- Backend serializer converts `QualityFlag` objects to codes via `QualityFlagConverter`
- Frontend receives codes and renders using existing `render_flags_inline()` component

**Caching Integration**:
- Result signatures (from `backend/relat_ai/services/results.py`) incorporate new metadata
- `SignatureBuilder.for_configuration()` unchanged (metadata is payload, not config)
- Cache keys remain stable; expanded payloads stored as-is
- Partial recomputation strategy (future): Use `@lru_cache` for expensive profiling functions

**Audit Trail Integration**:
- New profiling actions logged via existing `audit_trail.py` infrastructure
- Log entries: `"cluster_profiling_computed"`, `"pca_narrative_generated"`, `"suspicion_scores_ranked"`
- Metadata includes: timestamp, dataset_id, n_clusters, n_components, computation_time_ms

---

## 1. Backend Implementation

### 1.0 Suspicion Scoring & Explanation Wiring

#### 1.0.1 Normalizing Component Signals

Current `_score_suspicion()` in `auto_triage.py` sums raw contributions (PCA variance, 
change-point counts, residual magnitudes) making rankings opaque. New implementation:

```python
# backend/relat_ai/services/analysis/auto_triage.py

from dataclasses import dataclass, field

@dataclass
class SignalVector:
    """Normalized signal contributions for a single target (column/feature)."""
    target: str
    raw_signals: dict[str, float] = field(default_factory=dict)
    normalized_signals: dict[str, float] = field(default_factory=dict)
    weighted_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def normalize(self, all_targets_signals: dict[str, dict[str, float]]) -> None:
        """
        Normalize raw signals to [0, 1] via percentile ranking within batch.
        
        For each signal type, compute percentile rank across all targets,
        then store as normalized_signals. Handles zeros gracefully.
        """
        import numpy as np
        
        for signal_kind in self.raw_signals.keys():
            values = [
                all_targets_signals[t].get(signal_kind, 0.0) 
                for t in all_targets_signals.keys()
            ]
            values_array = np.array(values)
            
            if values_array.max() == 0:
                self.normalized_signals[signal_kind] = 0.0
            else:
                # Percentile rank: 0 (lowest) to 1 (highest)
                percentile = np.searchsorted(
                    np.sort(values_array), 
                    self.raw_signals[signal_kind]
                ) / len(values_array)
                self.normalized_signals[signal_kind] = float(percentile)
    
    def compute_weighted_score(self, weights: dict[str, float]) -> float:
        """
        Compute final score as weighted average of non-zero signals.
        
        Args:
            weights: Signal weights (must sum to 1.0)
        
        Returns:
            Weighted score in [0, 1]
        """
        active_signals = {
            k: v for k, v in self.normalized_signals.items() if v > 0
        }
        if not active_signals:
            self.weighted_score = 0.0
            return 0.0
        
        # Renormalize weights for active signals only
        active_weights = {k: weights.get(k, 0.0) for k in active_signals.keys()}
        weight_sum = sum(active_weights.values())
        
        if weight_sum == 0:
            self.weighted_score = 0.0
            return 0.0
        
        score = sum(
            active_signals[k] * (active_weights[k] / weight_sum)
            for k in active_signals.keys()
        )
        self.weighted_score = score
        return score
    
    def build_bullets(self, top_n: int = 4) -> list[SignalDetail]:
        """
        Create narrative bullets sorted by signal strength.
        
        Returns:
            List of SignalDetail objects for UI display
        """
        bullets = []
        
        # Sort signals by normalized value descending
        sorted_signals = sorted(
            self.normalized_signals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        for signal_kind, norm_value in sorted_signals:
            if norm_value < 0.01:  # Skip negligible signals
                continue
            
            detail_text = self._format_signal_detail(signal_kind)
            link_data = self._build_signal_link(signal_kind)
            
            bullets.append(SignalDetail(
                kind=signal_kind,
                weight=round(norm_value, 3),
                detail=detail_text,
                link=link_data
            ))
        
        return bullets
    
    def _format_signal_detail(self, signal_kind: str) -> str:
        """Generate human-readable detail string for a signal."""
        raw_value = self.raw_signals.get(signal_kind, 0.0)
        meta = self.metadata.get(signal_kind, {})
        
        if signal_kind == "pca_loading":
            pc = meta.get("component", "PC?")
            loading = meta.get("loading", 0.0)
            percentile = self.normalized_signals[signal_kind] * 100
            return f"{pc} loading {loading:.3f} ({percentile:.0f}th percentile)"
        
        elif signal_kind == "changepoint":
            count = meta.get("count", 0)
            dates = meta.get("dates", [])
            date_str = ", ".join(dates[:3]) if dates else ""
            return f"{count} change point{'s' if count != 1 else ''}" + (
                f" ({date_str})" if date_str else ""
            )
        
        elif signal_kind == "cluster":
            effect_size = meta.get("eta_squared", 0.0)
            p_value = meta.get("p_value", 1.0)
            return f"Cluster means differ (η²={effect_size:.2f}, p={p_value:.2e})"
        
        elif signal_kind == "residual":
            max_residual = meta.get("max_bucket", 0.0)
            bucket_name = meta.get("bucket_name", "")
            return f"Residual spike: {max_residual:.2f}σ" + (
                f" in {bucket_name}" if bucket_name else ""
            )
        
        elif signal_kind == "dispersion":
            mad_ratio = meta.get("mad_over_sigma", 0.0)
            return f"High dispersion (MAD/σ = {mad_ratio:.2f})"
        
        return f"{signal_kind}: {raw_value:.2f}"
    
    def _build_signal_link(self, signal_kind: str) -> dict[str, str] | None:
        """Build navigation link for UI deep-linking."""
        meta = self.metadata.get(signal_kind, {})
        
        if signal_kind == "pca_loading":
            return {"tab": "pca", "component": meta.get("component", "PC1")}
        elif signal_kind == "changepoint":
            return {"tab": "changepoints", "column": self.target}
        elif signal_kind == "cluster":
            return {"tab": "clusters", "feature": self.target}
        elif signal_kind == "residual":
            return {"tab": "residuals", "target": self.target}
        
        return None


def _compute_component_signals(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    pca_component_strength: dict[str, float],
    change_points: Sequence[ChangePointInsight],
    residual_insights: Sequence[ResidualForensicsInsight],
    cluster_labels: np.ndarray,
    config: AutoTriageConfig
) -> dict[str, SignalVector]:
    """
    Collect and normalize all signal types per column.
    
    Returns:
        Dictionary mapping column name to SignalVector
    """
    vectors = {}
    
    for column in numeric_data.columns:
        vector = SignalVector(target=column)
        
        # PCA loading (from existing pca_component_strength)
        pca_strength = pca_component_strength.get(column, 0.0)
        vector.raw_signals["pca_loading"] = pca_strength
        vector.metadata["pca_loading"] = {
            "component": _find_top_pca_component(column, pca_component_strength),
            "loading": pca_strength
        }
        
        # Change points
        col_changes = [cp for cp in change_points if cp.column == column]
        change_count = sum(len(cp.locations) for cp in col_changes)
        vector.raw_signals["changepoint"] = float(change_count)
        vector.metadata["changepoint"] = {
            "count": change_count,
            "dates": _extract_change_dates(col_changes, frame, config.datetime_column)
        }
        
        # Cluster separation (ANOVA F-statistic or effect size)
        cluster_stat = _compute_cluster_separation(
            frame[column], cluster_labels
        )
        vector.raw_signals["cluster"] = cluster_stat["f_stat"]
        vector.metadata["cluster"] = {
            "eta_squared": cluster_stat["eta_squared"],
            "p_value": cluster_stat["p_value"]
        }
        
        # Residual magnitude
        residual_mag = _extract_residual_magnitude(column, residual_insights)
        vector.raw_signals["residual"] = residual_mag["value"]
        vector.metadata["residual"] = {
            "max_bucket": residual_mag["value"],
            "bucket_name": residual_mag["bucket"]
        }
        
        # Dispersion anomaly (MAD/σ ratio)
        dispersion = _compute_dispersion_anomaly(frame[column])
        vector.raw_signals["dispersion"] = dispersion
        vector.metadata["dispersion"] = {
            "mad_over_sigma": dispersion
        }
        
        vectors[column] = vector
    
    # Normalize all signals via percentile ranking
    all_raw_signals = {
        col: vec.raw_signals for col, vec in vectors.items()
    }
    for vector in vectors.values():
        vector.normalize(all_raw_signals)
    
    return vectors


def _score_suspicion(
    frame: pd.DataFrame,
    numeric_data: pd.DataFrame,
    pca_component_strength: dict[str, float],
    change_points: Sequence[ChangePointInsight],
    residual_insights: Sequence[ResidualForensicsInsight],
    cluster_labels: np.ndarray,
    config: AutoTriageConfig,
    weights: Optional[dict[str, float]] = None
) -> list[SuspicionScore]:
    """
    Build suspicion rankings with contribution vectors and evidence bullets.
    
    Args:
        weights: Signal weights (default: pca=0.35, changepoint=0.25, cluster=0.25, residual=0.10, dispersion=0.05)
    
    Returns:
        List of SuspicionScore objects with metadata for serialization
    """
    if weights is None:
        weights = {
            "pca_loading": 0.35,
            "changepoint": 0.25,
            "cluster": 0.25,
            "residual": 0.10,
            "dispersion": 0.05
        }
    
    # Validate weights sum to 1.0
    assert abs(sum(weights.values()) - 1.0) < 0.01, "Weights must sum to 1.0"
    
    # Compute signal vectors
    vectors = _compute_component_signals(
        frame, numeric_data, pca_component_strength,
        change_points, residual_insights, cluster_labels, config
    )
    
    # Build SuspicionScore objects
    scores = []
    for column, vector in vectors.items():
        score_value = vector.compute_weighted_score(weights)
        bullets = vector.build_bullets(top_n=4)
        
        # Build flags (integrate with confidence_flags.py)
        flags = _build_quality_flags_for_column(
            frame[column], numeric_data[column], vector
        )
        
        # Build navigation links
        links = {
            "pca_component": vector.metadata.get("pca_loading", {}).get("component"),
            "changepoints_for": column if vector.raw_signals.get("changepoint", 0) > 0 else None,
            "cluster_profile": True if vector.raw_signals.get("cluster", 0) > 0 else False
        }
        links = {k: v for k, v in links.items() if v is not None}
        
        # Build contribution vector (normalized weights)
        active_signals = {k: v for k, v in vector.normalized_signals.items() if v > 0}
        contrib_sum = sum(active_signals.values())
        contrib = {
            k: v / contrib_sum if contrib_sum > 0 else 0.0
            for k, v in active_signals.items()
        }
        
        scores.append(SuspicionScore(
            target=column,
            target_type="variable",
            score=score_value,
            drivers=[bullet.detail for bullet in bullets],
            metadata={
                "contributions": contrib,
                "top_signals": [bullet.dict() for bullet in bullets],
                "links": links,
                "flags": flags,
                "raw_stats": vector.metadata
            }
        ))
    
    # Sort by score descending
    scores.sort(key=lambda s: s.score, reverse=True)
    return scores


def _build_quality_flags_for_column(
    raw_series: pd.Series,
    numeric_series: pd.Series,
    vector: SignalVector
) -> list[str]:
    """Generate quality flag codes for a column."""
    flags = []
    
    # Sample size
    n_valid = numeric_series.notna().sum()
    if n_valid < 300:
        flags.append("low_n")
    
    # Missing data
    missing_pct = raw_series.isna().mean()
    if missing_pct > 0.2:
        flags.append("high_missing")
    
    # Constant series
    if numeric_series.std() < 1e-9:
        flags.append("constant_series")
    
    # Collinearity (check correlation with other high-scoring variables)
    # TODO: Requires correlation matrix; defer to build_quality_flags()
    
    return flags
```

#### 1.0.2 Tests for Suspicion Scoring

```python
# backend/relat_ai/tests/unit/test_auto_triage_suspicion.py (NEW FILE)

import pytest
import numpy as np
import pandas as pd
from relat_ai.services.analysis.auto_triage import (
    _compute_component_signals,
    _score_suspicion,
    SignalVector
)

def test_signal_vector_normalization():
    """Signals should normalize to percentile ranks."""
    all_signals = {
        "A": {"pca_loading": 0.8, "changepoint": 3},
        "B": {"pca_loading": 0.5, "changepoint": 1},
        "C": {"pca_loading": 0.2, "changepoint": 0}
    }
    
    vector = SignalVector(target="A", raw_signals=all_signals["A"])
    vector.normalize(all_signals)
    
    # A has highest PCA loading → should be 1.0
    assert vector.normalized_signals["pca_loading"] == 1.0
    # A has highest changepoint count → should be 1.0
    assert vector.normalized_signals["changepoint"] == 1.0


def test_contributions_sum_to_one():
    """Active signal contributions should sum to ~1.0."""
    vector = SignalVector(target="X")
    vector.normalized_signals = {
        "pca_loading": 0.7,
        "changepoint": 0.3,
        "cluster": 0.0  # Inactive
    }
    
    weights = {"pca_loading": 0.5, "changepoint": 0.5, "cluster": 0.0}
    vector.compute_weighted_score(weights)
    
    # Only pca and changepoint are active
    contrib = {
        k: v for k, v in vector.normalized_signals.items() if v > 0
    }
    contrib_sum = sum(contrib.values())
    # Normalized should equal weighted score calculation
    assert abs(vector.weighted_score - 0.5 * (0.7 + 0.3) / 2) < 0.01


def test_suspicion_score_deterministic():
    """Same data should produce same rankings."""
    # Generate deterministic data
    np.random.seed(42)
    df = pd.DataFrame({
        "A": np.random.randn(100),
        "B": np.random.randn(100) + 5,
        "C": np.ones(100)  # Constant
    })
    
    # Mock config and inputs
    # ... (create minimal test fixtures)
    
    # Run twice
    scores1 = _score_suspicion(...)
    scores2 = _score_suspicion(...)
    
    # Rankings should match
    ranks1 = [s.target for s in scores1]
    ranks2 = [s.target for s in scores2]
    assert ranks1 == ranks2


def test_zero_signal_handling():
    """Columns with no signals should get score=0.0."""
    vector = SignalVector(target="Constant")
    vector.normalized_signals = {
        "pca_loading": 0.0,
        "changepoint": 0.0,
        "cluster": 0.0
    }
    
    weights = {"pca_loading": 0.5, "changepoint": 0.5, "cluster": 0.0}
    score = vector.compute_weighted_score(weights)
    
    assert score == 0.0
    assert len(vector.build_bullets()) == 0


def test_bullet_formatting():
    """Bullets should include context from metadata."""
    vector = SignalVector(target="X")
    vector.normalized_signals = {"pca_loading": 0.92}
    vector.metadata = {
        "pca_loading": {"component": "PC1", "loading": 0.34}
    }
    
    bullets = vector.build_bullets()
    assert len(bullets) == 1
    assert "PC1" in bullets[0].detail
    assert "0.34" in bullets[0].detail
    assert bullets[0].kind == "pca_loading"
    assert 0.9 <= bullets[0].weight <= 1.0
```

---

### 1.1 Cluster Profiling

#### 1.1.1 Implementation with Performance Safeguards

```python
# backend/relat_ai/services/analysis/auto_triage.py

def compute_cluster_profile(
    df: pd.DataFrame,
    features: list[str],
    cluster_labels: np.ndarray,
    cat_cols: list[str] = None,
    time_col: str = None,
    n_medoids: int = 5,
    max_samples_for_distance: int = 5000
) -> ClusterProfileModel:
    """
    Compute comprehensive cluster profiling with ANOVA, feature importance, and medoids.
    
    Performance safeguards:
    - Sample to max_samples_for_distance for pairwise distance computation
    - Limit tree depth to prevent overfitting
    - Short-circuit if features > 30 (skip tree-based importance)
    
    Args:
        df: Full dataframe with features and labels
        features: Numeric feature column names
        cluster_labels: Cluster assignments (0-indexed)
        cat_cols: Categorical columns for residual bucketing (not yet used)
        time_col: Optional datetime column for temporal analysis
        n_medoids: Number of representative samples per cluster
        max_samples_for_distance: Sample limit for distance matrix (prevents OOM)
    
    Returns:
        ClusterProfileModel with statistics, importance, medoids, and temporal data
        
    Raises:
        ValueError: If cluster_labels length doesn't match df
    """
    import numpy as np
    import pandas as pd
    from scipy.stats import f_oneway
    from sklearn.metrics import pairwise_distances
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.preprocessing import StandardScaler
    
    if len(cluster_labels) != len(df):
        raise ValueError(f"cluster_labels length {len(cluster_labels)} != df length {len(df)}")
    
    unique_labels = np.unique(cluster_labels)
    k = len(unique_labels)
    
    # Cluster sizes
    sizes = []
    total_n = len(df)
    for label in unique_labels:
        n = (cluster_labels == label).sum()
        sizes.append({
            "id": int(label),
            "n": int(n),
            "pct": float(n / total_n)
        })
    
    # Per-feature ANOVA
    top_diff_features = []
    for col in features:
        values_by_cluster = [
            df.loc[cluster_labels == c, col].dropna().values
            for c in unique_labels
        ]
        
        # Require at least 3 samples per cluster
        if all(len(v) >= 3 for v in values_by_cluster):
            try:
                f_stat, p_value = f_oneway(*values_by_cluster)
                
                # Compute eta-squared (effect size)
                ss_between = sum(
                    len(v) * (np.mean(v) - df[col].mean()) ** 2
                    for v in values_by_cluster
                )
                ss_total = ((df[col] - df[col].mean()) ** 2).sum()
                eta_squared = ss_between / ss_total if ss_total > 0 else 0.0
                
                means = {
                    str(int(c)): float(np.nanmean(df.loc[cluster_labels == c, col]))
                    for c in unique_labels
                }
                
                top_diff_features.append({
                    "feature": col,
                    "p": float(p_value),
                    "f_stat": float(f_stat),
                    "eta_squared": float(eta_squared),
                    "means": means
                })
            except Exception as e:
                # Handle constant columns, etc.
                continue
    
    # Sort by p-value, then effect size
    top_diff_features.sort(key=lambda r: (r["p"], -r["eta_squared"]))
    top_diff_features = top_diff_features[:15]
    
    # Tree-based feature importance (skip if too many features)
    feature_importance = []
    if len(features) <= 30:
        try:
            X = df[features].select_dtypes(include="number").fillna(df[features].mean())
            if X.shape[1] >= 1:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                clf = DecisionTreeClassifier(
                    max_depth=4,
                    min_samples_leaf=max(50, len(df) // 100),
                    random_state=42
                )
                clf.fit(X_scaled, cluster_labels)
                
                importances = clf.feature_importances_
                feature_importance = [
                    {"feature": feat, "importance": float(imp)}
                    for feat, imp in zip(X.columns, importances)
                    if imp > 0
                ]
                feature_importance.sort(key=lambda x: x["importance"], reverse=True)
                feature_importance = feature_importance[:15]
        except Exception as e:
            # Log but don't fail
            import logging
            logging.warning(f"Tree-based importance failed: {e}")
    
    # Medoids (sample if too many points)
    medoids = {}
    try:
        X_numeric = df[features].select_dtypes(include="number").fillna(df[features].mean())
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_numeric)
        
        for c in unique_labels:
            idx = np.where(cluster_labels == c)[0]
            
            # Sample if cluster too large
            if len(idx) > max_samples_for_distance:
                sampled_idx = np.random.choice(
                    idx, 
                    size=max_samples_for_distance, 
                    replace=False
                )
            else:
                sampled_idx = idx
            
            # Compute distances within sampled cluster
            X_cluster = X_scaled[sampled_idx]
            D = pairwise_distances(X_cluster, metric="euclidean")
            
            # Find medoid (point with min total distance)
            medoid_local_idx = np.argmin(D.sum(axis=1))
            medoid_global_idx = sampled_idx[medoid_local_idx]
            
            # Get n_medoids closest points to medoid
            distances_to_medoid = D[medoid_local_idx]
            closest_local = np.argsort(distances_to_medoid)[:n_medoids]
            closest_global = sampled_idx[closest_local]
            
            medoids[str(int(c))] = [int(i) for i in closest_global.tolist()]
    except Exception as e:
        import logging
        logging.warning(f"Medoid computation failed: {e}")
    
    # Per-feature statistics per cluster
    per_feature_stats = {}
    for c in unique_labels:
        cluster_mask = cluster_labels == c
        cluster_stats = {}
        
        for feat in features:
            values = df.loc[cluster_mask, feat].dropna()
            if len(values) > 0:
                q1, q3 = np.percentile(values, [25, 75])
                cluster_stats[feat] = ClusterFeatureStats(
                    mean=float(values.mean()),
                    median=float(values.median()),
                    std=float(values.std()),
                    iqr=float(q3 - q1),
                    n=int(len(values))
                )
        
        per_feature_stats[str(int(c))] = cluster_stats
    
    # Temporal analysis (if datetime column present)
    by_time = None
    if time_col is not None and time_col in df.columns:
        try:
            df_with_cluster = df.assign(cluster=cluster_labels)
            df_with_cluster['time_period'] = pd.to_datetime(
                df_with_cluster[time_col]
            ).dt.to_period("W")
            
            # Count by (period, cluster)
            counts = df_with_cluster.groupby(['time_period', 'cluster']).size()
            
            # Normalize within each period
            proportions = counts.groupby(level=0).apply(
                lambda s: s / s.sum()
            ).round(3)
            
            by_time = [
                {
                    "cluster": int(k[1]),
                    "window": str(k[0]),
                    "pct": float(v),
                    "n": int(counts.loc[k])
                }
                for k, v in proportions.items()
            ]
        except Exception as e:
            import logging
            logging.warning(f"Temporal analysis failed: {e}")
    
    return ClusterProfileModel(
        method="kmeans",  # TODO: Pass as parameter
        k=k,
        sizes=sizes,
        top_diff_features=top_diff_features,
        feature_importance=feature_importance,
        medoids=medoids,
        per_feature_stats=per_feature_stats,
        by_time=by_time
    )
```

#### 1.1.2 Integration into AutoTriageResult

```python
# Modify _perform_clustering() in auto_triage.py

def _perform_clustering(
    numeric_data: pd.DataFrame, 
    config: AutoTriageConfig,
    full_frame: pd.DataFrame  # NEW: Pass full frame for profiling
) -> tuple[Sequence[ClusterInsight], ClusterProfileModel]:
    """
    Run clustering and compute profile.
    
    Returns:
        Tuple of (basic insights, detailed profile)
    """
    # Existing clustering logic...
    kmeans = KMeans(n_clusters=3, random_state=config.random_state)
    labels = kmeans.fit_predict(numeric_data)
    
    cluster_sizes = {int(i): int((labels == i).sum()) for i in np.unique(labels)}
    
    insight = ClusterInsight(
        method="kmeans",
        cluster_sizes=cluster_sizes
    )
    
    # NEW: Compute profile
    profile = compute_cluster_profile(
        df=full_frame,
        features=list(numeric_data.columns),
        cluster_labels=labels,
        time_col=config.datetime_column,
        n_medoids=5,
        max_samples_for_distance=5000
    )
    
    return [insight], profile


# Update AutoTriageResult dataclass
@dataclass(slots=True)
class AutoTriageResult:
    """Aggregate payload returned by :func:`run_auto_triage`."""
    pca_components: Sequence[PCAComponentInsight]
    change_points: Sequence[ChangePointInsight]
    clusters: Sequence[ClusterInsight]
    cluster_profile: ClusterProfileModel  # NEW
    residual_forensics: Sequence[ResidualForensicsInsight]
    suspicion_rankings: Sequence[SuspicionScore]
    quality_flags: Sequence[QualityFlag]
```

#### 1.1.3 Tests for Cluster Profiling

```python
# backend/relat_ai/tests/unit/test_cluster_profiling.py (NEW FILE)

import pytest
import numpy as np
import pandas as pd
from relat_ai.services.analysis.auto_triage import compute_cluster_profile
from scipy.stats import f_oneway

def test_cluster_profile_anova_matches_scipy():
    """ANOVA p-values should match scipy.stats.f_oneway."""
    # Create data with known clusters
    np.random.seed(42)
    df = pd.DataFrame({
        "A": np.concatenate([
            np.random.randn(100) + 0,
            np.random.randn(100) + 5,
            np.random.randn(100) + 10
        ]),
        "B": np.random.randn(300)  # No cluster effect
    })
    labels = np.array([0]*100 + [1]*100 + [2]*100)
    
    profile = compute_cluster_profile(df, ["A", "B"], labels)
    
    # Extract our p-value for feature A
    our_pvalue_A = next(
        f["p"] for f in profile.top_diff_features if f["feature"] == "A"
    )
    
    # Compute reference p-value
    values_A = [df.loc[labels==c, "A"].values for c in [0, 1, 2]]
    _, ref_pvalue_A = f_oneway(*values_A)
    
    # Should match within floating-point tolerance
    assert abs(our_pvalue_A - ref_pvalue_A) < 1e-6


def test_cluster_profile_handles_constant_features():
    """Constant features should not crash profiling."""
    df = pd.DataFrame({
        "A": np.ones(100),  # Constant
        "B": np.random.randn(100)
    })
    labels = np.array([0]*50 + [1]*50)
    
    # Should complete without error
    profile = compute_cluster_profile(df, ["A", "B"], labels)
    
    # Constant feature should not appear in top_diff (or have p=1.0)
    feature_names = [f["feature"] for f in profile.top_diff_features]
    if "A" in feature_names:
        pvalue_A = next(f["p"] for f in profile.top_diff_features if f["feature"] == "A")
        assert pvalue_A > 0.9  # Should be non-significant


def test_medoids_are_valid_indices():
    """Medoid indices should be valid row numbers."""
    df = pd.DataFrame(np.random.randn(200, 5), columns=list("ABCDE"))
    labels = np.array([0]*100 + [1]*100)
    
    profile = compute_cluster_profile(df, list("ABCDE"), labels, n_medoids=3)
    
    for cluster_id, indices in profile.medoids.items():
        assert len(indices) == 3
        for idx in indices:
            assert 0 <= idx < len(df)
            # Check that medoid is in correct cluster
            assert labels[idx] == int(cluster_id)


def test_feature_importance_sums_to_one():
    """Tree-based importances should sum to ~1.0."""
    df = pd.DataFrame(np.random.randn(500, 10), columns=[f"F{i}" for i in range(10)])
    labels = np.array([0]*250 + [1]*250)
    
    profile = compute_cluster_profile(df, df.columns.tolist(), labels)
    
    if profile.feature_importance:  # May be empty if skipped
        total_importance = sum(f["importance"] for f in profile.feature_importance)
        assert 0.95 <= total_importance <= 1.05


def test_temporal_analysis_produces_valid_proportions():
    """Time-slice proportions should sum to ~1.0 within each window."""
    dates = pd.date_range("2025-01-01", periods=300, freq="D")
    df = pd.DataFrame({
        "time": dates,
        "A": np.random.randn(300)
    })
    labels = np.array([0]*150 + [1]*150)
    
    profile = compute_cluster_profile(df, ["A"], labels, time_col="time")
    
    if profile.by_time:
        # Group by window
        from collections import defaultdict
        window_sums = defaultdict(float)
        for entry in profile.by_time:
            window_sums[entry["window"]] += entry["pct"]
        
        # Each window should sum to ~1.0
        for window, total in window_sums.items():
            assert 0.95 <= total <= 1.05, f"Window {window} sum = {total}"
```

---

### 1.2 PCA Narratives & Drill-Downs

```python
# backend/relat_ai/services/analysis/auto_triage.py

def interpret_pca(
    pca: PCA,
    feature_names: list[str],
    top_n: int = 5,
    narrative_pcs: int = 3
) -> PCAExplainModel:
    """
    Generate human-readable PCA interpretations with signed loadings.
    
    Args:
        pca: Fitted sklearn PCA object
        feature_names: Original feature names
        top_n: Number of top contributors to show per PC
        narrative_pcs: Number of PCs to generate narratives for
    
    Returns:
        PCAExplainModel with variance, loadings, and plain-English narratives
    """
    import numpy as np
    
    # Variance explained
    variance_ratios = pca.explained_variance_ratio_.tolist()
    variance = [
        {"pc": f"PC{i+1}", "ratio": float(ratio)}
        for i, ratio in enumerate(variance_ratios)
    ]
    cumulative_variance = float(np.sum(variance_ratios))
    
    # Loadings table (signed)
    loadings_matrix = pca.components_.T  # shape: [n_features, n_components]
    loadings = {}
    
    for j in range(min(10, loadings_matrix.shape[1])):  # First 10 PCs
        pc_loadings = loadings_matrix[:, j]
        
        # Sort by absolute value, keep sign
        indexed_loadings = [
            (feature_names[i], float(abs(pc_loadings[i])), float(pc_loadings[i]))
            for i in range(len(feature_names))
        ]
        indexed_loadings.sort(key=lambda x: x[1], reverse=True)
        
        # Take top_n
        top_features = indexed_loadings[:top_n]
        loadings[f"PC{j+1}"] = [
            (name, signed_loading)
            for name, _, signed_loading in top_features
        ]
    
    # Generate narratives for first N PCs
    narratives = []
    for k in range(min(narrative_pcs, len(variance))):
        pc_name = f"PC{k+1}"
        variance_pct = variance_ratios[k] * 100
        top_contribs = loadings[pc_name]
        
        # Build descriptive text
        contrib_str = ", ".join([
            f"{name} ({loading:+.2f})"
            for name, loading in top_contribs[:3]
        ])
        
        # Attempt semantic interpretation
        positive_features = [name for name, load in top_contribs if load > 0]
        negative_features = [name for name, load in top_contribs if load < 0]
        
        if len(positive_features) > 0 and len(negative_features) > 0:
            narrative = (
                f"{pc_name} ({variance_pct:.1f}%) contrasts "
                f"{_feature_theme(positive_features)} vs {_feature_theme(negative_features)}."
            )
        else:
            dominant_theme = _feature_theme(positive_features + negative_features)
            narrative = (
                f"{pc_name} ({variance_pct:.1f}%) captures '{dominant_theme}' variation "
                f"driven by {contrib_str}."
            )
        
        narratives.append(narrative)
    
    return PCAExplainModel(
        variance=variance,
        loadings=loadings,
        narrative=narratives,
        cumulative_variance=cumulative_variance
    )


def _feature_theme(feature_names: list[str]) -> str:
    """
    Attempt to infer semantic theme from feature names.
    
    Simple heuristic: check for common keywords.
    """
    names_lower = " ".join(feature_names).lower()
    
    if "time" in names_lower or "duration" in names_lower:
        return "timing"
    elif "mean" in names_lower or "avg" in names_lower:
        return "magnitude/level"
    elif "std" in names_lower or "variance" in names_lower:
        return "variability"
    elif "max" in names_lower or "min" in names_lower:
        return "extremes"
    elif "response" in names_lower or "output" in names_lower:
        return "response"
    elif "injection" in names_lower or "input" in names_lower:
        return "input conditions"
    elif "calibration" in names_lower or "drift" in names_lower:
        return "calibration/drift"
    else:
        return "composite"
```

---

### 1.3 Change-Point Context & Segmentation

#### 1.3.1 Context-Enriched Detectors

- Extend `ChangePointReportModel` population within
  `backend/relat_ai/services/analysis/auto_triage.py` to attach contextual
  metadata for every detected breakpoint.
- Reuse the existing ruptures-based pipeline (PELT + windowed CUSUM) while
  introducing a **context assembler** that consumes:
  - Cluster membership deltas (requires calling `compute_cluster_profile`
    when `config.enable_cluster_context` is true).
  - Batch/production run identifiers from `frame[config.batch_column]` when
    available.
  - Temporal anchors derived from `config.datetime_column` (fall back to row
    index when absent).
- Enforce deterministic ordering by sorting change points by index prior to
  context enrichment to keep UI references stable.

#### 1.3.2 Segment Summaries & Guardrails

- Generate `SegmentSummary` entries for **every interval** between change
  points, including the leading and trailing tails. For each summary capture:
  mean, standard deviation, count, and percentage of total rows.
- Validate segment sizes against `config.min_segment_size`; emit the
  `"insufficient_data"` flag whenever a segment violates the threshold.
- Add benchmarking hooks (`time.perf_counter`) to measure detector latency on
  5k, 10k, and 50k row samples; log to audit trail for regression tracking.
- Unit tests:
  - Deterministic segmentation on synthetic sinusoid with injected shifts.
  - Correct propagation of batch metadata when batches straddle change points.
  - Coverage for absence of optional context columns (ensure graceful None).

#### 1.3.3 API & Serialization Updates

- Extend the auto-triage response DTO (`AutoTriageResult`) to surface a
  `change_point_reports: list[ChangePointReportModel]` field with stable
  ordering.
- Update serialization adapters to map existing ORM entities to the expanded
  Pydantic models, ensuring backwards compatibility by supplying defaults for
  new keys.
- Add snapshot fixtures in `tests/backend/fixtures/change_point_reports.json`
  for regression testing.

### 1.4 Evidence Builder

#### 1.4.1 Narrative Composition Service

- Introduce `backend/relat_ai/services/analysis/evidence_builder.py` that
  consumes `SuspicionItemModel`, `PCAExplainModel`, and
  `ChangePointReportModel` instances.
- Responsibilities:
  - Merge top signals into a ranked markdown bullet list using reusable
    templates (`f-string` fragments stored in `/templates/analysis/`).
  - Provide CTA metadata for frontend cards (e.g., "View PCA Component" with
    tab routing payload).
  - Surface uncertainty qualifiers when quality flags contain risk codes.
- Service exposes a `build_evidence_bundle(dataset_id: str) -> EvidenceBundle`
  method returning structured content for all tabs.

#### 1.4.2 Cross-Artifact Linking

- Maintain `link_registry` dict that maps entity IDs (target column, cluster
  id, PCA component) to canonical deep-link payloads. Evidence Builder queries
  this registry to avoid hard-coded routing strings.
- Synchronize registry keys with frontend enums (see Section 2.5) by sharing a
  generated `navigation_contract.json` artifact checked into `docs/contracts/`.

#### 1.4.3 Validation & Telemetry

- Add unit tests to verify evidence bundles contain required keys, respect top
  N limits, and omit empty narratives.
- Emit telemetry via `audit_trail.log_event("evidence_bundle_built", …)`
  capturing dataset size, build duration, and number of insights surfaced.

---

## 2. Frontend Implementation

### 2.0 State Management Architecture

```python
# frontend/streamlit_app/utils/session_state.py

from typing import Optional, Literal
from dataclasses import dataclass, field

TabName = Literal["suspicion", "pca", "changepoints", "clusters"]

@dataclass
class AutoTriageState:
    """Centralized state for auto-triage tab navigation and drill-downs."""
    active_tab: TabName = "suspicion"
    selected_suspicion_target: Optional[str] = None
    selected_pca_component: Optional[int] = None
    selected_changepoint_column: Optional[str] = None
    selected_cluster_id: Optional[int] = None
    drill_down_context: dict = field(default_factory=dict)
    
    def navigate_to(
        self,
        tab: TabName,
        context: Optional[dict] = None
    ) -> None:
        """Navigate to a tab with optional context."""
        self.active_tab = tab
        if context:
            self.drill_down_context.update(context)


def get_autotriage_state() -> AutoTriageState:
    """Get or initialize auto-triage state."""
    if "autotriage_state" not in st.session_state:
        st.session_state["autotriage_state"] = AutoTriageState()
    return st.session_state["autotriage_state"]


def set_active_autotriage_tab(tab: TabName, context: Optional[dict] = None) -> None:
    """Set active tab and optional drill-down context."""
    state = get_autotriage_state()
    state.navigate_to(tab, context)
```

---

### 2.1 Suspicion Rankings Tab

- Replace the existing simple table with a **ranked card layout** highlighting
  score, narrative bullets, and quality flags.
- Display contribution breakdown using a horizontal stacked bar (Plotly) whose
  colors map to signal kinds; implement tooltip tool to show precise values.
- Integrate quick filters (chips) for `cluster`, `changepoint`, and
  `pca_loading` dominance; filters update state via `set_active_autotriage_tab`
  context.
- Accessibility: Ensure cards are keyboard navigable with ARIA labels for
  score, description, and CTA buttons.

### 2.2 PCA Tab Enhancements

- Introduce two-panel layout:
  1. Variance overview (bar chart + cumulative line) using data from
     `PCAExplainModel.variance`.
  2. Narrative feed showing top PCs with plain-English summaries and top
     contributors.
- Add "Compare Components" toggle that renders a radar chart comparing selected
  PCs; fallback to text list when only one PC selected.
- Provide download button for loadings as CSV via Streamlit's `download_button`.

### 2.3 Change-Points Tab Redesign

- Visualization stack:
  - Primary chart: Time-series (Altair) with vertical markers for each change
    point colored by strength bucket.
  - Secondary panel: Segment summary table displaying stats and quality flags.
- Enable drill-down navigation by clicking markers → triggers state update to
  highlight corresponding segment details and open Evidence Builder entries.
- Handle non-temporal datasets by switching to index-based x-axis and surfacing
  helper text describing limitation.

### 2.4 Clusters Tab Deep Dive

- Render cluster size distribution (stacked bar) and medoid sample table with
  pagination.
- Provide "Feature Differences" accordion that shows ANOVA results, effect
  sizes, and tree-based importance in descending order.
- Integrate cluster timeline view when `by_time` present; reuse color palette
  from suspicion tab for consistency.
- Add "Export cluster assignments" button leveraging backend CSV endpoint.

### 2.5 Navigation & Deep Linking

- Centralize tab routing in `frontend/streamlit_app/navigation.py` exposing
  `navigate(payload: dict)` that interprets `link_registry` entries.
- Support URL query parameters (`?tab=clusters&target=Voltage_A`) using
  Streamlit's experimental `st.experimental_get_query_params` API; ensure state
  sync occurs on initial page load.
- Persist last visited tab in browser local storage via
  `components.v1.html("window.localStorage…")` fallback when cookies disabled.

### 2.6 Responsive Design

- Adopt CSS grid layout with breakpoints at 768px and 1200px using Streamlit's
  theming hooks and custom components.
- Collapse side-by-side panels into stacked layout on small screens; ensure
  charts re-render with simplified legends to avoid overflow.
- Run manual QA on Safari, Chrome, and Edge latest to verify scroll/touch
  interactions (document results in QA log).

---

## 3. Quality & Guardrails

- Implement `pydantic` validation on all incoming configuration payloads before
  triggering analysis jobs; reject invalid inputs with actionable error
  messages.
- Extend existing anomaly detection guardrails to include
  `max_clusters=12` and `max_components=8`; log overrides via audit trail.
- Add feature flag `AUTO_TRIAGE_EXPLAINABILITY` (configurable via environment)
  gating release to internal users first.
- Security review: ensure serialized evidence bundles exclude raw PII columns;
  add allowlist to backend serializer.

## 4. Configuration Management

- Document new config keys in `docs/Reference-Guide.md` and propagate defaults
  through `backend/relat_ai/config/settings.py`.
- Provide migration script that adds toggles to existing `.env` files with
  default "off" values.
- Introduce YAML-driven visualization presets (stored in
  `infrastructure/config/visualization.yml`) enabling data science team to
  adjust chart thresholds without redeploying.

## 5. Testing Strategy

- **Backend**: pytest suites covering Pydantic models, signal normalization,
  evidence builder logic, and change-point segmentation. Include property tests
  using Hypothesis for percentile ranking edge cases.
- **Frontend**: Cypress regression pack for tab navigation, filter behavior, and
  responsive breakpoints; integrate Percy for visual diffs of key charts.
- **Integration**: End-to-end smoke test orchestrated via `make autotriage-e2e`
  that loads fixture dataset, runs auto-triage pipeline, and asserts rendered
  UI JSON contract using Playwright.
- **Data Validation**: Leverage Great Expectations checkpoints to guarantee no
  NaNs/Inf propagate to serialized outputs.

## 6. Performance Profiling

- Backend micro-benchmarks executed via `pytest --benchmark-only` for
  normalization, clustering, and change-point routines; store baseline metrics
  in `docs/performance/auto_triage_benchmarks.md`.
- Frontend perceived performance tracked using Web Vitals instrumentation (CLS,
  LCP) captured through Streamlit's `st.experimental_user_info` hook and logged
  to analytics warehouse.
- Implement async job batching for heavy computations by queuing tasks through
  existing Celery infrastructure (max concurrency 4) and streaming progress to
  UI using WebSocket channel.

## 7. Migration & Backward Compatibility

- Maintain legacy response structure behind `?v=1` query flag for two release
  cycles; new clients default to explainability-enhanced schema.
- Supply transformation utilities to convert legacy cached payloads into new
  models, ensuring old cache entries remain consumable during rollout.
- Update user documentation (`AuditTrail_UserGuide.md`, `ImplementationPlan.md`)
  with callouts explaining new navigation patterns and data contracts.

## 8. Acceptance Tests

- Define UAT checklist covering:
  1. Suspicion explanation readability scoring (stakeholder review).
  2. Ability to trace evidence from suspicion card → PCA → change-point views
     without losing context.
  3. Confirmation that cluster profiling exports load in downstream reporting
     notebooks.
  4. Validation that feature flags disable the experience cleanly.
- Capture sign-off in Confluence with screenshots + dataset IDs.

---

## Summary of Key Additions

This updated plan adds:

1. **Type Safety & Data Contracts**: Expanded Pydantic models with guardrails.
2. **Backend Integration & Evidence**: QualityFlag alignment plus narrative builder.
3. **Frontend Experience Redesign**: Suspicion, PCA, change-point, and cluster tabs with deep linking.
4. **Quality Guardrails**: Feature flags, security reviews, and validation layers.
5. **Configuration Management**: Documented toggles and visualization presets.
6. **Testing Coverage**: Backend, frontend, integration, and data validation strategies.
7. **Performance Monitoring**: Benchmark suites and Web Vitals instrumentation.
8. **Migration & Acceptance**: Rollout plan with UAT checklist and documentation updates.

**Next Steps**:
1. Review and approve this expanded plan
2. Create spike/prototype for cluster profiling performance
3. Implement statistical validation tests (TDD approach)
4. Begin phased backend implementation
5. Update Reference-Guide.md with new modules

