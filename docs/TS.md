⚙️ Technical Specification
5.1 Architecture
Layer	Technology	Notes
Frontend	Streamlit (prototype) → React / Dash (production)	Column selector, filter panel, mode toggle
Backend	Python (FastAPI / Flask)	Modular analysis engine
Core Libraries	pandas, numpy, scipy, scikit-learn, pingouin, statsmodels	
Visualization	seaborn, plotly, networkx	Interactive + static outputs
AI Summarization	LLM pass over structured results	Uses contextual prompt templates
5.2 Data Flow
Upload → Preprocessing → Filter / Subset → Analysis Engine
       → Result JSON → Visualization Layer → AI Summary → Export

5.3 Preprocessing

Missing-value handling (imputation / drop).

Outlier handling (robust scaling, IQR trimming).

Encoding of categorical variables (one-hot / hash).

Normalization / standardization as needed.

Audit logging of all preprocessing actions.

5.4 Analysis Engine
Correlation

Numeric↔Numeric → Pearson, Spearman, Kendall.

Categorical↔Categorical → Chi-square, Cramér’s V.

Mixed → ANOVA, Point-Biserial.

Multivariate

Linear / Logistic Regression with interaction terms.

ANOVA for categorical predictors.

Partial Correlations.

Partial Least Squares (PLS) for collinear predictors.

Configurable max interaction depth.

Auto-Triage

PCA loadings for variance drivers.

Change-point detection (CUSUM, PELT) for time-indexed variables.

Clustering (K-Means / Hierarchical) for unsupervised structure discovery.

Residual forensics & suspicion ranking of variables / time windows.

Confidence and quality flag assignment.

5.5 Outputs

Structured JSON (results: coefficients, effect sizes, p-values, n, flags).

Ranked Insights List.

Visualizations (heatmaps, networks, PCA, change-point plots).

AI-generated narrative summary with confidence references.

Optional Reduced Dataset Export for downstream analysis (JMP, Python, etc.).

5.6 Performance Optimizations

Pre-filter features using mutual information and variance.

Parallelize independent computations (joblib, Dask).

Cap subset size in multivariate mode.

Sampling for very large datasets.

Utilize multi-threaded BLAS (MKL / OpenBLAS).

Cache standardized matrices and PCA transforms by (dataset hash + filter signature).

📊 Appendix A – Module Summary
Module	Inputs	Outputs	Libraries	Est. Runtime	Notes
Correlation	DataFrame	corr_table.json	scipy / pingouin	< 5 s	pairwise only
Multivariate	X, y	model.json	scikit-learn / statsmodels	< 60 s	≤ 5 vars
Auto-Triage	full DataFrame	ranked.json	scikit-learn / ruptures	< 90 s	capped @ 50 k × 50
Visualization	result JSON	plots / HTML report	plotly / seaborn	< 10 s	cached outputs
AI Summary	result JSON	markdown / text	LLM API	< 5 s	optional, local/offline toggle

Version: 2.1  Last Updated: 2025-10-13  Author: Gareth