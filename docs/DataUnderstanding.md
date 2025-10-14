Implementation Plan: “Make It Understandable”
0) Data Contracts (add to your results JSON)

Store evidence and narrative alongside the numbers so the UI can explain why.

# types.py (TypedDict or pydantic models)
SuspicionItem = {
  "target": str,
  "score": float,                 # 0..1
  "contrib": {                    # score breakdown
    "pca_loading": float,         # 0..1
    "changepoint_strength": float,
    "cluster_separation": float,
    "model_importance": float
  },
  "top_signals": [                # short bullets for UI
    {"kind":"pca_loading","detail":"High loading on PC1 (0.34)"},
    {"kind":"changepoint","detail":"3 strong shifts (Mar 5, Mar 18, Apr 02)"},
    {"kind":"cluster","detail":"Means differ 22% between C0 and C2 (p<0.001)"}
  ],
  "links": {                      # jump targets in UI
    "pca_component": "PC1",
    "changepoints_for": "Cdrift Min",
    "cluster_profile": True
  },
  "flags": ["collinearity","low_n"] # quality/confidence flags
}

### How these map to existing response models

`SuspicionItem` is intended to replace the thinner `RankedInsightModel` that is
currently emitted from `backend/relat_ai/core/results.py`.  The existing model
has a `label`, `score`, and loose `metadata` bag; the richer structure above
would move the `label` → `target`, keep `score` as-is, move `drivers` into
`top_signals`, and break the old `metadata` field into first-class `contrib`,
`links`, and `flags`.  Downstream code should treat the new object as a superset
of the existing insight with backwards compatibility provided by folding the
old `metadata` keys into the new nested dictionaries when needed.  The
`RankedInsightModel` class remains as the compatibility shim until all clients
understand the expanded structure.

`ClusterProfile`, `PCAExplain`, and `ChangePointReport` correspond to the
cluster, PCA, and change-point sections on `AutoTriageResultModel`.  Today those
fields are thin (`ClusterModel`, `PCAComponentModel`, `ChangePointModel`).  The
plan is to evolve `AutoTriageResultModel` so that:

* `clusters: list[ClusterModel]` becomes a single `ClusterProfile` (with the
  existing size counts exposed as `sizes` and new `top_diff_features`,
  `feature_importance`, `medoids`, and `by_time` sections replacing the opaque
  `metadata`).
* `pca_components: list[PCAComponentModel]` is replaced by a `PCAExplain`
  payload, keeping component-level variance ratios while surfacing the new
  narrative strings and sorted loading table.
* `change_points: list[ChangePointModel]` is upgraded so each entry is a
  `ChangePointReport` that captures segment summaries, test strength, and UI
  context hooks.

`ResidualForensicsModel` within `AutoTriageResultModel` does not yet have an
explicit replacement, but the intention is to align it with the `links` and
`flags` structure from `SuspicionItem` to maintain consistent UX affordances.

ClusterProfile = {
  "method": "kmeans" | "hierarchical",
  "k": int,
  "sizes": [{"id":0,"n":850,"pct":0.471}, ...],
  "top_diff_features": [  # ANOVA/Kruskal results
    {"feature":"Injection Time","effect":"η²=0.21","p":1.2e-6,
     "means":{"0":3.2,"1":5.9,"2":8.1}}
  ],
  "feature_importance": [  # tree-based importance to explain splits
    {"feature":"Calibration Mean","importance":0.27}, ...
  ],
  "medoids": { "0": [row_idx,...], "1": [...], "2":[...] },  # representative samples
  "per_feature_stats": {
    "0": {"Injection Time": {"mean": 3.2, "median": 3.1, "iqr": 0.8}, ...},
    "1": {...},
    "2": {...}
  },
  "time_slices": {
    "window_unit": "week",
    "summaries": [
      {"window":"2025-W10..W12","cluster":2,"pct":0.73,
       "n": 95, "trend":"increasing"}
    ]
  }
}

PCAExplain = {
  "variance": [{"pc":"PC1","ratio":0.3454}, ...],
  "loadings": { "PC1":[["Cmean Max",0.3426],["Cmean Mean",0.3410], ...], ... },
  "narrative": [
    "PC1 (34.5%) is a 'concentration level' axis driven by Cmean Max/Mean and Cdrift Max.",
    "PC2 (16.8%) contrasts timing vs response (Injection Time vs Raw Response)."
  ]
}

ChangePointReport = {
  "column":"Card Age Min",
  "method":"pelt", "n":7,
  "indices":[4, 231, 498, ...],
  "segments":[
    {"start":0,"end":230,"mean":2.1,"std":0.3,"n":231},
    {"start":231,"end":497,"mean":3.9,"std":0.4,"n":267}
  ],
  "strength":[2.3, 4.8, 3.1],      # test statistics
  "context": [ {"index":231,"time":"2025-03-18","cluster_shift_to":2,"batch":"B-104"} ]
}

## Change-point detection implementation decision

- **Adopt `ruptures` for the production implementation.** The current
  `backend/relat_ai/services/analysis/change_detection.py` shim will be replaced
  with a thin wrapper around `ruptures.detection.Pelt` so we can rely on the
  battle-tested penalty + minimum-segment logic already provided by the
  library, instead of continually patching our simplified PELT translation.
- **Dependency + configuration updates.** Add `ruptures>=1.1.9` to
  `backend/requirements.txt`. Default configuration inside the wrapper should
  expose the same call signature (series in, indices out) while pinning
  `model="rbf"`, `min_size=5`, and a default penalty equal to
  `penalty_multiplier * np.log(len(series))` (retaining today’s multiplier
  semantics).
- **Unit-test updates.** Extend
  `backend/relat_ai/tests/unit/test_analysis_change_detection.py` to (a)
  validate that we pass the penalty/min-size defaults through to the
  `ruptures.detection.Pelt` instance, (b) continue exercising the CUSUM helper
  for backwards compatibility, and (c) assert that a synthetic step series
  returns monotonically increasing change indices when `ruptures` is wired up.
- **Fallback + compatibility expectations.** Keep the existing numpy-only
  routines available behind the same module-level symbols until downstream
  consumers migrate. Auto-triage scoring and the frontend change-point tab
  expect the `ChangePointReport` schema above and a synchronous API; maintain
  those interfaces by (1) guarding the `ruptures` import so notebooks/tests can
  fall back to the legacy implementation if the dependency is unavailable, and
  (2) mirroring the legacy output format (list of indices + `method="pelt"`).
  During the rollout the UI should continue to receive identical payloads, with
  only the internal scoring heuristics benefiting from the more stable
  segmentation.

1) Backend: add interpretation functions
1.1 Cluster profiling (the missing piece)
def compute_cluster_profile(
    df, features, cluster_labels, cat_cols=(), time_col=None, n_medoids=5
) -> dict:
    import numpy as np, pandas as pd
    from scipy.stats import f_oneway, kruskal
    from sklearn.metrics import pairwise_distances
    from sklearn.tree import DecisionTreeClassifier

    out = {"method":"kmeans","k":int(len(np.unique(cluster_labels)))}
    out["sizes"] = (
        pd.Series(cluster_labels).value_counts().sort_index()
        .pipe(lambda s: [{"id":int(i),"n":int(n),"pct":float(n/len(df))} for i,n in s.items()])
    )

    # Per-feature differences across clusters
    rows = []
    for col in features:
        x = [df.loc[cluster_labels==c, col].dropna().values for c in np.unique(cluster_labels)]
        if df[col].dtype.kind in "iufc":  # numeric
            try:
                stat, p = f_oneway(*x) if all(len(v)>2 for v in x) else (np.nan, 1.0)
            except Exception:
                stat, p = (np.nan, 1.0)
            means = {str(int(c)): float(np.nanmean(df.loc[cluster_labels==c, col])) for c in np.unique(cluster_labels)}
            rows.append({"feature":col, "p":float(p), "stat":float(stat), "means":means})
    top = sorted(rows, key=lambda r: (r["p"], -np.nan_to_num(r["stat"])))[:15]
    out["top_diff_features"] = [
        {"feature":r["feature"],
         "effect": f"F={r['stat']:.2f}",
         "p": r["p"],
         "means": r["means"]}
        for r in top
    ]

    # Tree-based importance (predict cluster id)
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    X = df[features].select_dtypes(include="number").fillna(df[features].mean()).values
    y = cluster_labels
    if X.shape[1] >= 1:
        Xs = StandardScaler().fit_transform(X)
        clf = DecisionTreeClassifier(max_depth=4, min_samples_leaf=50, random_state=42)
        clf.fit(Xs, y)
        out["feature_importance"] = [
            {"feature":f, "importance":float(i)}
            for f,i in sorted(zip(df[features].columns, clf.feature_importances_),
                              key=lambda t: t[1], reverse=True) if i>0
        ][:15]

    # Representative samples (medoids)
    try:
        D = pairwise_distances(Xs, metric="euclidean")
        medoids = {}
        for c in np.unique(y):
            idx = np.where(y==c)[0]
            sub = D[np.ix_(idx, idx)]
            medoid_local = idx[np.argmin(sub.sum(axis=1))]
            # top n closest to medoid
            order = idx[np.argsort(D[medoid_local, idx])[:n_medoids]]
            medoids[str(int(c))] = [int(i) for i in order.tolist()]
        out["medoids"] = medoids
    except Exception:
        out["medoids"] = {}

    # Cluster distribution over time (optional)
    if time_col is not None and time_col in df.columns:
        tmp = df.assign(cluster=y).groupby([pd.to_datetime(df[time_col]).dt.to_period("W"),"cluster"]).size()
        tmp = tmp.groupby(level=0).apply(lambda s: (s/s.sum()).round(2))
        out["by_time"] = [
            {"cluster":int(k[1]), "window":str(k[0]), "pct":float(v)}
            for k,v in tmp.items()
        ]
    return out


UI result: under the pie charts, render:

“Top Features Differing by Cluster” table (means + p-value)

“What defines each cluster?” chips using the largest mean deltas

“Representative rows” link (medoids) plus profiling table (per_feature_stats)

Temporal chips sourced from time_slices summaries (“Appears mostly during…”)


Implementation checklist (cluster profiling payload):

1. Persist cluster membership in auto-triage
   * Extend `ClusterInsight` (in `backend/relat_ai/services/analysis/auto_triage.py`) so it carries:
     - `member_indices: list[int]` (row ids relative to the profiled frame) per cluster id
     - `member_ids: list[str]` or similar if the ingestion pipeline exposes stable primary keys
     - a `label_column`/`cluster_labels` vector to keep alignment with the dataframe for downstream routines.
   * When `auto_triage.clusterize()` runs, stash the raw `labels_` from the clustering estimator on the insight object before any dataframe slicing/shuffling. Do **not** rely on recomputing labels.
   * Update `compute_cluster_profile` to accept the persisted labels instead of deriving them from re-running the model. Use the stored `member_indices` to fetch rows for medoid reconstruction and profiling routines.

2. Serialize richer structures in results
   * In `backend/relat_ai/services/results.py`, augment `ClusterModel` (or introduce a sibling `ClusterProfileModel`) with fields for:
     - `medoids: dict[str, list[int]]`
     - `per_feature_stats: dict[str, dict[str, ClusterFeatureStats]]` where `ClusterFeatureStats` captures mean/median/std/iqr/count.
     - `time_slices: TimeSliceSummary` encapsulating aggregation windows, cluster proportions, counts, and optional trend labels.
     - `member_indices` / `member_ids` to allow front-end drill-downs.
   * Ensure `to_dict()`/`model_dump()` serializes nested dataclasses/TypedDicts cleanly (use `jsonable_encoder` or pydantic models as needed).
   * Document how medoids are computed (distance to centroid or stored representative indices) and confirm we rehydrate original rows when building response payloads.
   * Capture per-feature stats by applying `df.loc[cluster_indices, feature].agg(["mean","median","std",q1,q3])` and store `iqr=q3-q1`. Persist each cluster’s stats under the cluster id key.
   * Time-slice summaries: bucket by iso week (default) or configured granularity, compute `n` per cluster per bucket, and derive `pct = n / window_total`. Add `trend` via rolling comparison (e.g., direction of `pct` change over last 3 buckets).
   * Provide helper functions in `results.py` to convert numpy types to native Python before serialization to avoid JSON issues.

3. Streamlit auto-triage surface
   * Update `frontend/streamlit_app/components/autotriage_view.py` to read the new payload keys and render:
     - “Representative Samples” table showing medoid rows (include key features, timestamp, and label).
     - “Cluster Profiling” expandable section with per-feature stats (mean/median/std/iqr deltas).
     - Temporal chips: e.g., `st.status`/`st.metric` style badges summarizing `time_slices.summaries` and highlighting dominant windows.
     - Inline tooltips describing how medoids were selected and how statistics are computed.

4. Test coverage
   * Backend: extend `tests/backend/services/analysis/test_auto_triage.py` (or create new coverage) to assert `ClusterInsight` retains labels, medoids, per-feature stats, and time-slice structures. Mock dataframe to verify serialization via `results.ClusterModel`.
   * Frontend: add a smoke test (e.g., `tests/frontend/test_autotriage_view.py`) wiring a sample payload through Streamlit component to ensure new tables render without exceptions (use `streamlit.testing.v1.AppTest` helper).
   * Update any snapshot fixtures to include the additional keys, and add regression cases for missing optional fields (`time_slices` absent, medoids empty).

1.2 PCA narrative + drill-downs
def interpret_pca(pca, feature_names, top=5) -> dict:
    import numpy as np
    loadings = pca.components_.T  # shape: [features, pcs]
    var = pca.explained_variance_ratio_.tolist()
    load_tbl = {}
    for j in range(min(10, loadings.shape[1])):  # first 10 PCs
        pairs = sorted(
            [(feature_names[i], float(abs(loadings[i, j])), float(loadings[i, j]))
             for i in range(loadings.shape[0])],
            key=lambda t: t[1], reverse=True
        )[:top]
        load_tbl[f"PC{j+1}"] = [(n, sgn) for (n, _abs, sgn) in pairs]
    narrative = []
    for k,(pc, feats) in enumerate(load_tbl.items(), start=1):
        sides = [f"{name} ({val:+.2f})" for (name,val) in feats]
        narrative.append(f"PC{k} ({var[k-1]*100:.1f}%) is driven by: " + ", ".join(sides))
    return {"variance":[{"pc":f"PC{i+1}","ratio":v} for i,v in enumerate(var)],
            "loadings":load_tbl, "narrative":narrative}


UI result:

Keep your “Top Contributing Features” but add signs and a plain-English line per PC.

Clicking a feature opens its distribution by cluster + time trend → connects PCA to real-world signals.

1.3 Change-point sanity + context

Your screenshot shows “151 changepoints” → classic over-segmentation. Add auto-penalty, min segment length, and a before/after summary for each break.

def detect_change_points(series, timestamps=None, min_size=100, max_breaks=10):
    import numpy as np, ruptures as rpt
    x = np.asarray(series, dtype=float)
    model = "rbf"  # or "l2"
    algo = rpt.Pelt(model=model).fit(x)
    # penalty via BIC-ish heuristic
    import math
    pen = 2.0 * np.std(x) * math.log(len(x))
    idxs = algo.predict(pen=pen)
    idxs = sorted(set([i for i in idxs if i>=min_size and i<=len(x)-min_size]))[:max_breaks]
    segs, strengths = [], []
    start = 0
    for cp in idxs:
        seg = x[start:cp]; nxt = x[cp: min(cp+min_size, len(x))]
        segs.append({"start":start,"end":cp-1,"mean":float(np.nanmean(seg)),
                     "std":float(np.nanstd(seg)),"n":int(len(seg))})
        # simple strength: mean shift / pooled std
        import numpy as np
        if len(nxt)>=10 and len(seg)>=10:
            num = abs(np.nanmean(nxt)-np.nanmean(seg))
            den = np.sqrt(np.nanvar(seg)+np.nanvar(nxt)+1e-9)
            strengths.append(float(num/(den+1e-9)))
        start = cp
    return {"indices":idxs, "segments":segs, "strength":strengths}


UI result:

Replace the long list with Top 10 strongest breaks and a chart that shades before vs after means.

Add a context join: show cluster mix, instrument, batch around each break (±N samples).

1.4 Build “Why is this suspicious?” evidence

Create a scorer that normalizes each signal 0..1 and stores contrib weights for transparency.

DEFAULT_WEIGHTS = {
  "pca_loading": 0.35,
  "changepoint_strength": 0.25,
  "cluster_separation": 0.25,
  "model_importance": 0.15
}

def build_suspicion_item(var, signals, weights=DEFAULT_WEIGHTS):
    # signals = {"pca_loading":0.92, "changepoint_strength":0.77, ...}
    import numpy as np
    score = float(sum(weights[k]*signals.get(k,0.0) for k in weights))
    bullets = []
    if "pca_loading" in signals: bullets.append({"kind":"pca_loading",
      "detail": f"High loading on PC1 ({signals['pca_loading']:.2f})"})
    if "changepoint_strength" in signals and signals["changepoint_strength"]>0:
      bullets.append({"kind":"changepoint","detail":"Significant regime shifts"})
    if "cluster_separation" in signals and signals["cluster_separation"]>0:
      bullets.append({"kind":"cluster","detail":"Large between-cluster mean difference"})
    return {
      "target": var,
      "score": score,
      "contrib": {k: float(signals.get(k,0.0)) for k in weights},
      "top_signals": bullets,
      "links": {},
      "flags": []
    }


UI result: in your “Detailed Breakdown”, show a stacked bar breaking the 100% into PCA / CP / Cluster / Model pieces + the bullets. That replaces the current “100% High” ambiguity.

2) Frontend: add the storytelling layer
2.1 Suspicion Rankings tab

New column: “Why (top signal)” → first bullet from top_signals.

Drill-down panel:

Contribution bar (PCA/CP/Cluster/Model)

Links to: “View on PCA”, “Open Change-Points”, “View Cluster Profile”, “Show top interactions”

Tiny playbook text: “Next: check time window around Mar 18; compare Cluster 2 mean vs spec.”

Acceptance: Clicking any row reveals contribution bar + at least two deep links that navigate to the exact component tab pre-filtered.

2.2 PCA tab

Under “Top Contributing Features”, add a sentence from PCAExplain.narrative[k].

On bar-click of a feature → right-side drawer with:

Distribution by cluster (violin/boxplot)

Time series with change-points overlaid (if time)

Scatter vs an anchor variable (if any)

Acceptance: For a chosen PC, users can name the axis in plain English from the narrative; clicking a feature opens the drawer with the three plots.

2.3 Change-Points tab

Replace the long list with a ranked “Top Breaks” table:

Rank	Index	Time	ΔMean	Strength	Cluster mix change

Chart: show the series with mean bands before/after each listed break (hover to highlight).

Add min segment length & “Max breaks” sliders at top.

Acceptance: Reducing “Max breaks” reduces the list; each row highlights the correct region in the plot and shows before/after means.

2.4 Clusters tab

Keep the pies, then add two panels:

(a) What distinguishes clusters?
Table from top_diff_features with means/p and quick chips:

Cluster 2: ↑ Injection Time, ↓ Calibration Mean (p<0.001)

(b) Representative samples
Show 3 rows per cluster (medoids), link “Open in data table”.

If by_time exists, add a stacked area over time (“cluster prevalence”).

Acceptance: A non-statistician can read 2–3 chips and describe Cluster 2 in one sentence; representative rows open correctly.

3) Quality & guardrails

Flags: show yellow/red badges when: n<300, collinearity (|r|>0.95 group), >20% missingness.

Tooltips: short defs for “loading”, “change-point”, “residual”, “η²”, etc.

Defaults: CP min_size = 100, max_breaks = 10; clusters projected into PC space (first 10 PCs) for stability.

4) Wiring it in (endpoint sketch)
# POST /analyze returns all pieces
{
  "suspicion": [SuspicionItem, ...],
  "pca": PCAExplain,
  "clusters": {"kmeans": ClusterProfile, "hierarchical": ClusterProfile},
  "changepoints": { "Card Age Min": ChangePointReport, ... },
  "audit": {...}
}


Frontend loads once and routes each tab to its slice of JSON. Deep-linking is just storing the selected ids in query params (?tab=clusters&method=kmeans&cluster=2).

5) Acceptance tests (copy into your PR)

AT-1: Suspicion row shows a contribution bar that sums to 100% and at least 2 links that navigate to PCA/CP/Clusters with the relevant item preselected.

AT-2: Clusters tab renders a “Top Differences” table with p-values and per-cluster means; selecting a feature highlights its distribution by cluster.

AT-3: PCA tab shows narratives including signed loadings; clicking a feature opens a drawer with (a) by-cluster distribution, (b) time trend with CP overlays, (c) scatter vs anchor.

AT-4: Change-Points tab lists ≤ MaxBreaks strongest breaks with ΔMean and Strength; selecting one shades the correct region in the chart and shows before/after stats.

AT-5: Any item flagged low_n or collinearity displays a visible badge and a tooltip explaining the limitation.

6) Config (one JSON your app reads)
{
  "weights": { "pca_loading":0.35, "changepoint_strength":0.25, "cluster_separation":0.25, "model_importance":0.15 },
  "changepoints": { "method":"pelt", "min_size":100, "max_breaks":10, "model":"rbf" },
  "clustering": { "k_list":[2,3,4,5,6], "space":"pc", "n_pcs":10 },
  "profiling": { "top_features":15, "medoids":5 },
  "flags": { "min_n":300, "max_missing_pct":0.2, "high_collinearity_r":0.95 }
}

TL;DR

Keep the math; add profiling, narratives, contribution bars, and deep links.

Your users should be able to answer, in one glance:
“What is Cluster 2?”, “Why is Cdrift Min suspicious?”, “When did it change?”, “What should I look at next?”