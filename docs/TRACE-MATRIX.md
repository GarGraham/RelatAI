# Requirements Traceability Matrix

This matrix links **requirements → implementation → verification → evidence**.

It exists to prevent:
- Undocumented assumptions
- Orphaned features
- "Done" without proof
- Silent regressions

---

## Legend

**Verification Type**
- Unit = isolated logic
- Integration = system boundaries
- E2E = full workflow
- Manual = human verification
- Static = linting, type checks, analysis

---

## Trace Matrix

### 3.1 Data Input Requirements

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-3.1.1 | Upload CSV / Excel / Parquet datasets | URS §3.1 | TS §5.2 | `services/ingestion.py` | Integration | `tests/integration/test_datasets_api.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.1.2 | Auto-detect column types (numeric, categorical, datetime, text) | URS §3.1 | TS §5.3 | `services/schema_detection.py` | Unit | `tests/unit/test_schema_detection.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.1.3 | Handle missing values gracefully | URS §3.1 | TS §5.3 | `services/preprocessing.py` | Unit | `tests/unit/test_preprocessing.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.1.4 | Handle outliers gracefully | URS §3.1 | TS §5.3 | `services/preprocessing.py` | Unit | `tests/unit/test_preprocessing.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.1.5 | Audit Trail: log all preprocessing actions with timestamps and dataset hash | URS §3.1 | TS §5.3 | `services/audit_trail.py`, `api/routes/audit.py` | Integration | `tests/integration/test_audit_api.py` | ✅ | Gareth | 2026-01-15 |

### 3.2 UI Controls Requirements

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-3.2.1 | All columns included by default; user may deselect | URS §3.2 | TS §5.1 | `services/configuration.py`, `components/column_selector.py` | Unit | `tests/unit/test_configuration.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.2.2 | Filtering panel to subset by column values | URS §3.2 | TS §5.1 | `services/configuration.py`, `components/filter_panel.py` | Integration | `tests/integration/test_configuration_api.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.2.3 | Mode toggle: Correlation, Multivariate, Auto-Triage | URS §3.2 | TS §5.1 | `core/models.py::AnalysisMode`, `components/mode_selector.py` | Unit | `tests/unit/test_configuration.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.2.4 | Save/load analysis templates | URS §3.2 | TS §5.1 | `services/templates.py`, `api/routes/configuration.py` | Integration | `tests/integration/test_configuration_api.py` | ✅ | Gareth | 2026-01-15 |

### 3.3 Analysis Mode Requirements

#### 3.3.A Correlation Mode

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-3.3.A.1 | Pairwise correlations across all selected columns | URS §3.3.A | TS §5.4 | `services/analysis/pairwise.py` | Unit | `tests/unit/test_analysis_pairwise.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.A.2 | No column limit | URS §3.3.A | TS §5.4 | `services/analysis/pairwise.py` | Unit | `tests/unit/test_analysis_pairwise.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.A.3 | Supports numeric↔numeric (Pearson, Spearman, Kendall) | URS §3.3.A | TS §5.4 | `services/analysis/pairwise.py` | Unit | `tests/unit/test_analysis_pairwise.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.A.4 | Supports categorical↔categorical (Chi-square, Cramér's V) | URS §3.3.A | TS §5.4 | `services/analysis/pairwise.py` | Unit | `tests/unit/test_analysis_pairwise.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.A.5 | Supports mixed variable types (ANOVA, Point-Biserial) | URS §3.3.A | TS §5.4 | `services/analysis/pairwise.py` | Unit | `tests/unit/test_analysis_pairwise.py` | ✅ | Gareth | 2026-01-15 |

#### 3.3.B Multivariate Mode

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-3.3.B.1 | User sets max number of variables (3–5) | URS §3.3.B | TS §5.4 | `core/models.py::DatasetConfiguration.max_variables` | Unit | `tests/unit/test_configuration.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.B.2 | User sets max interaction depth (default = 2) | URS §3.3.B | TS §5.4 | `core/models.py::DatasetConfiguration.interaction_depth` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.B.3 | Option to anchor variables (always included) | URS §3.3.B | TS §5.4 | `core/models.py::DatasetConfiguration.anchor_columns` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.B.4 | Linear / logistic regression | URS §3.3.B | TS §5.4 | `services/analysis/multivariate.py` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.B.5 | ANOVA for categorical predictors | URS §3.3.B | TS §5.4 | `services/analysis/multivariate.py` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.B.6 | Partial correlations | URS §3.3.B | TS §5.4 | `services/analysis/multivariate.py` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.B.7 | PLS for collinear predictors | URS §3.3.B | TS §5.4 | `services/analysis/multivariate.py` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |

#### 3.3.C Auto-Triage Mode

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-3.3.C.1 | Unsupervised scan combining correlations, PCA loadings, clustering, change-point detection | URS §3.3.C | TS §5.4 | `services/analysis/auto_triage.py` | Unit | `tests/unit/test_analysis_auto_triage.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.C.2 | Ranks variables and time windows most associated with anomalies | URS §3.3.C | TS §5.4 | `services/analysis/auto_triage.py` | Unit | `tests/unit/test_analysis_auto_triage.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.C.3 | Residual Forensics: buckets residuals by instrument, lot, operator, analyte, or time | URS §3.3.C | TS §5.4 | `services/analysis/auto_triage.py` | Unit | `tests/unit/test_analysis_auto_triage.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.C.4 | Produces Suspicion Ranking (top contributors and anomaly segments) | URS §3.3.C | TS §5.4 | `services/analysis/auto_triage.py` | Unit | `tests/unit/test_autotriage_explainability.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.3.C.5 | Optional: t-SNE / UMAP dimensionality reduction | URS §3.3.C | TS §5.4 | — | — | — | ⏳ | Gareth | — |
| REQ-3.3.C.6 | Optional: Anomaly detection via Isolation Forest or One-Class SVM | URS §3.3.C | TS §5.4 | — | — | — | ⏳ | Gareth | — |

### 3.4 Output Requirements

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-3.4.1 | Ranked Correlation Tables (r, p-value, n) | URS §3.4 | TS §5.5 | `core/results.py`, `components/correlation_view.py` | Integration | `tests/integration/test_analysis_api.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.4.2 | Multivariate Model Summaries (coefficients, effect sizes, interactions) | URS §3.4 | TS §5.5 | `core/results.py`, `components/multivariate_view.py` | Unit | `tests/unit/test_analysis_multivariate.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.4.3 | Ranked Insights: Top contributing variables by variance explained | URS §3.4 | TS §5.5 | `services/analysis/auto_triage.py`, `components/autotriage_view.py` | Unit | `tests/unit/test_analysis_auto_triage.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.4.4 | Change-point detections (if time field exists) | URS §3.4 | TS §5.4 | `services/analysis/change_detection.py` | Unit | `tests/unit/test_analysis_change_detection.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.4.5 | Optional reduced dataset export (top-N variables) | URS §3.4 | TS §5.5 | `services/results.py`, `utils/export_utils.py` | Unit | `tests/unit/test_results.py` | ✅ | Gareth | 2026-01-15 |
| REQ-3.4.6 | Visualizations: heatmaps, network graphs, faceted plots, PCA biplots, change-point charts | URS §3.4 | TS §5.5 | `services/visualization.py`, `components/*.py` | Manual | Streamlit UI inspection | ✅ | Gareth | 2026-01-15 |
| REQ-3.4.7 | AI-generated summaries with confidence references | URS §3.4 | TS §5.5 | `services/summarization.py`, `components/ai_summary.py` | Manual | Streamlit UI inspection | ⚠️ | Gareth | 2026-01-15 |
| REQ-3.4.8 | Confidence Flags: each finding labeled with quality indicators | URS §3.4 | TS §5.5 | `services/analysis/confidence_flags.py`, `components/confidence_flags.py` | Unit | `tests/unit/test_analysis.py` | ✅ | Gareth | 2026-01-15 |

### 4. Non-Functional Requirements

| Req ID | Requirement | Source | Design Reference | Implementation | Verification Type | Evidence | Status | Owner | Last Verified |
|--------|-------------|--------|------------------|----------------|-------------------|----------|--------|--------|----------------|
| REQ-4.1 | Interpretability: each relationship includes strength, significance, and sample size | URS §4 | TS §5.5 | `core/results.py` | Unit | `tests/unit/test_results.py` | ✅ | Gareth | 2026-01-15 |
| REQ-4.2 | Usability: sensible defaults that "just work" | URS §4 | TS §5.1 | `services/configuration.py` | Unit | `tests/unit/test_configuration.py` | ✅ | Gareth | 2026-01-15 |
| REQ-4.3 | Extensibility: modular backend for additional tests/models | URS §4 | TS §5.1 | `services/analysis/` package structure | Static | Code review | ✅ | Gareth | 2026-01-15 |
| REQ-4.4 | Scalability: handle ≈ 50k rows × dozens of columns; degrade gracefully | URS §4 | TS §5.6 | `services/analysis/*.py` (sampling, caching) | Manual | `scripts/benchmark.py` | ⚠️ | Gareth | — |
| REQ-4.5 | Security: processing is local by default; no external data transmission | URS §4 | TS §5.1 | Architecture design | Static | Code review | ✅ | Gareth | 2026-01-15 |

---

## Status Codes

- ⏳ Planned
- 🛠 In Progress
- ✅ Verified
- ❌ Broken
- ⚠️ Needs Review (partial implementation or placeholder)

---

## Rules

- Every requirement must have:
  - A design reference
  - An implementation reference
  - A verification type
  - Evidence
- "Done" without evidence is not done.
- If a requirement changes, update this table.
- If verification fails, downgrade the status immediately.

---

## Notes

Use links wherever possible:
- Code paths
- Test files
- Screenshots
- Logs
- CI runs
- Commits

## Summary

| Category | Total | ✅ Verified | ⚠️ Needs Review | ⏳ Planned | ❌ Broken |
|----------|-------|-------------|-----------------|-----------|----------|
| Data Input (§3.1) | 5 | 5 | 0 | 0 | 0 |
| UI Controls (§3.2) | 4 | 4 | 0 | 0 | 0 |
| Correlation Mode (§3.3.A) | 5 | 5 | 0 | 0 | 0 |
| Multivariate Mode (§3.3.B) | 7 | 7 | 0 | 0 | 0 |
| Auto-Triage Mode (§3.3.C) | 6 | 4 | 0 | 2 | 0 |
| Outputs (§3.4) | 8 | 7 | 1 | 0 | 0 |
| Non-Functional (§4) | 5 | 4 | 1 | 0 | 0 |
| **Total** | **40** | **36** | **2** | **2** | **0** |

**Overall Completion: 90%** (36/40 requirements verified)
