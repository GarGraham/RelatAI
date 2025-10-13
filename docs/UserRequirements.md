📄 User Requirements Document (URD v2.1)
1. Purpose

Provide a self-service triage platform to rapidly surface statistical drivers during quality events and CAPA investigations.
The system accelerates root-cause analysis by automating correlation discovery, multivariate modeling, and anomaly triage, allowing engineers to isolate probable causes and prioritize deeper statistical work.

2. Users

Quality / Process Engineers – need rapid triage during investigations.

Data Analysts – want systematic, reproducible exploratory data analysis (EDA).

Domain Experts / Managers – want AI-summarized insights, not raw statistics.

3. Functional Requirements
3.1 Data Input

Upload CSV / Excel / Parquet datasets.

Auto-detect column types (numeric, categorical, datetime, text).

Handle missing values and outliers gracefully.

Audit Trail: log all preprocessing actions (dropped columns, imputations, scaling methods, filters) with timestamps and dataset hash for traceability.

3.2 UI Controls

All columns included by default; user may deselect.

Filtering panel to subset by column values (e.g., Region = Europe).

Mode toggle: Correlation | Multivariate | Auto-Triage.

Option to save/load analysis templates (column selections, filters, anchors, parameters) for repeatable workflows.

3.3 Analysis Modes
A. Correlation Mode

Pairwise correlations across all selected columns.

No column limit.

Supports numeric↔numeric, categorical↔categorical, and mixed variable types.

B. Multivariate Mode

User sets max number of variables (e.g., 3–5).

User sets max interaction depth (default = 2).

Option to anchor variables (always included).

Linear / logistic regression, ANOVA, partial correlations, and PLS (Partial Least Squares) for collinear predictors.

C. Auto-Triage Mode

Unsupervised scan combining correlations, PCA loadings, clustering, and change-point detection.

Ranks variables and time windows most associated with anomalies.

Residual Forensics: buckets residuals by instrument, lot, operator, analyte, or time to identify systematic bias.

Produces a Suspicion Ranking (top contributors and anomaly segments).

Optional future extensions: t-SNE / UMAP dimensionality reduction and anomaly detection via Isolation Forest or One-Class SVM.

3.4 Outputs

Ranked Correlation Tables (r, p-value, n).

Multivariate Model Summaries (coefficients, effect sizes, interactions).

Ranked Insights

Top contributing variables by variance explained.

Change-point detections (if time field exists).

Optional reduced dataset export (top-N variables).

Visualizations: heatmaps, network graphs, faceted plots, PCA biplots, change-point charts.

Insights Layer: AI-generated summaries with confidence references (e.g., “Based on 8 k samples, R² = 0.82”) and links back to plots/tables.

Confidence Flags: each finding labeled with quality indicators (low n, collinearity, high missingness).

4. Non-Functional Requirements

Interpretability: each relationship includes strength (r or β), significance (p-value / CI), and sample size (n).

Usability: sensible defaults that “just work.”

Extensibility: modular backend for additional statistical tests or models.

Scalability: handle ≈ 50 k rows × dozens of columns; degrade gracefully via sampling/pruning.

Security / Compliance: processing is local or on-prem by default; no external data transmission unless explicitly enabled for AI summarization.