Technical Specification
1. Architecture
Frontend:

Streamlit (prototype) → React/Dash (production).

Column selector, filter panel, mode toggle.

Backend:

Python (FastAPI/Flask).

Core libraries: pandas, numpy, scipy, scikit-learn, pingouin.

Optional: statsmodels for regression/ANOVA.

Visualization:

seaborn, plotly, networkx.

AI Summarization:

LLM pass over results table to generate human‑readable insights.

2. Data Flow
User uploads dataset → schema detection.

User configures analysis (mode, filters, anchors).

Backend runs correlation/multivariate engine.

Results stored in structured JSON.

Frontend renders tables/plots.

AI summarizer generates narrative insights.

3. Correlation Engine
Pairwise:

Numeric↔Numeric: Pearson, Spearman, Kendall.

Categorical↔Categorical: Chi‑square, Cramér’s V.

Mixed: ANOVA, point‑biserial.

Multivariate:

Regression with interaction terms.

ANOVA for categorical predictors.

Partial correlations.

Configurable max interaction depth.

4. Performance Optimizations
Pre‑filter features using mutual information.

Parallelize computations (joblib, Dask).

Cap subset size in multivariate mode.
