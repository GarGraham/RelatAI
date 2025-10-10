1. Purpose
Provide a self‑service platform for automated correlation and multivariate analysis of tabular datasets. The tool should allow non‑specialists and analysts alike to quickly surface relationships between variables without manually coding statistical tests.

2. Users
Data analysts: want fast exploratory insights.

Domain experts: want to test hypotheses without deep statistical coding.

Executives/researchers: want AI‑summarized insights, not raw stats.

3. Functional Requirements
Data Input

Upload CSV/Parquet/Excel.

Auto‑detect column types (numeric, categorical, datetime, text).

UI Controls

All columns included by default.

User can deselect columns.

Option to filter dataset by column values (e.g., only rows where Region = Europe).

Analysis Modes

Correlational mode:

No column limit.

Pairwise correlations across all selected columns.

Multivariate mode:

User sets max number of variables (e.g., 3–5).

User sets max interaction depth (default = 2).

Option to anchor variables (always included).

Outputs

Ranked correlation tables.

Heatmaps, network graphs, faceted plots.

AI‑generated summaries of strongest/most surprising relationships.

Performance

Handle datasets up to ~50k rows, dozens of columns.

Run within seconds to minutes depending on complexity.

4. Non‑Functional Requirements
Usability: Simple UI with defaults that “just work.”

Extensibility: Modular backend for plugging in new statistical tests.

Interpretability: Clear explanations of what each test means.

Scalability: Should degrade gracefully with larger datasets (sampling, pruning).
