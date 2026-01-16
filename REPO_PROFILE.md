# REPO_PROFILE.md

## What is this repo?
- **Name:** RelatAI
- **One-liner:** Self-service analytics platform for rapid statistical triage during quality events and CAPA investigations.
- **What "done" looks like:** 
  - Users can upload datasets and run Correlation, Multivariate, or Auto-Triage analyses.
  - Results display with confidence flags, AI summaries, and ranked insights.
  - Full audit trail of preprocessing actions for traceability.
  - Export capabilities for downstream analysis (JMP, Python).
  - Streamlit prototype functional; React/Dash production frontend pending.

## Specifications (The "North Star")
- **User Requirements:** See `docs/URS.md` (v2.1)
- **Technical Specification:** See `docs/TS.md` (v2.1)
- **Trace Matrix:** See `docs/TRACE-MATRIX.md`

## Domain Vocabulary
- **Correlation Mode:** Pairwise correlation analysis across numeric, categorical, and mixed variable types.
- **Multivariate Mode:** Regression, ANOVA, partial correlations, PLS with configurable interaction depth and anchor columns.
- **Auto-Triage Mode:** Unsupervised scan combining PCA loadings, change-point detection, clustering, and residual forensics for anomaly triage.
- **Suspicion Ranking:** Ranked list of variables/time windows most associated with anomalies.
- **Confidence Flags:** Quality indicators (low n, collinearity, high missingness) attached to findings.
- **Audit Trail:** Logged preprocessing actions (dropped columns, imputations, scaling) with timestamps and dataset hash.
- **Configuration Templates:** Saved column selections, filters, anchors, and parameters for repeatable workflows.
- **Anchor Columns:** Variables always included in multivariate analysis plans.
- **Change-Point Detection:** CUSUM/PELT algorithms identifying shifts in time-indexed variables.
- **Residual Forensics:** Bucketing residuals by instrument, lot, operator, analyte, or time to identify systematic bias.

## Tech Stack
- **Languages:** Python 3.11
- **Backend:** FastAPI, Pydantic v2, uvicorn
- **Frontend:** Streamlit (prototype), React/Dash (planned production)
- **Core Libraries:** pandas, numpy, scipy, scikit-learn, statsmodels, pingouin (partial), joblib, dask
- **Visualization:** plotly, seaborn, networkx
- **Testing:** pytest, pytest-cov
- **Linting/Formatting:** ruff, black, mypy (strict)
- **Containers:** Docker, docker-compose

## How to Run / Test
- **Install:** `make install` (runtime deps) or `pip install -r backend/requirements.txt`
- **Install Dev:** `make install-dev` or `pip install -r backend/requirements-dev.txt`
- **Run Backend:** `make run-backend` or `uvicorn relat_ai.api.main:app --reload`
- **Run Frontend:** `streamlit run frontend/streamlit_app/app.py`
- **Test:** `make test` or `pytest backend/relat_ai/tests`
- **Lint:** `make lint` or `ruff check backend/relat_ai`
- **Type Check:** `make type-check` or `mypy backend/relat_ai`
- **Format:** `make format` or `black backend/relat_ai`

## Repo Layout
- `backend/relat_ai/api/`: FastAPI routes (datasets, configuration, analysis, audit, health).
- `backend/relat_ai/core/`: Domain models, config, exceptions, result schemas.
- `backend/relat_ai/services/`: Business logic (ingestion, preprocessing, analysis, visualization, summarization).
- `backend/relat_ai/services/analysis/`: Statistical pipelines (pairwise, multivariate, auto_triage, change_detection).
- `backend/relat_ai/tests/`: Unit and integration test suites.
- `frontend/streamlit_app/`: Streamlit prototype with pages, components, utils, assets.
- `frontend/webapp/`: Placeholder for React/Dash production frontend.
- `docs/`: URS, TS, implementation plans, milestone reviews, developer guides.
- `infrastructure/`: Dockerfiles, docker-compose, CI workflows.
- `datasets/`: Sample datasets and upload storage.

## Boundaries & Constraints
- **Generated:** `__pycache__/`, `*.pyc`, `.pytest_cache/`, coverage reports.
- **Infra:** Docker configs in `infrastructure/`; do not modify CI workflows without review.
- **High-Stakes Logic:** 
  - `services/analysis/auto_triage.py` — anomaly detection and suspicion ranking.
  - `services/analysis/multivariate.py` — regression coefficients and p-values for decision-making.
  - `services/preprocessing.py` — data transformations affecting all downstream analyses.
  - `services/audit_trail.py` — traceability for regulatory/quality investigations.
- **Security:** Processing is local by default; no external data transmission unless explicitly enabled for AI summarization.
- **Performance Targets:** Correlation < 5s, Multivariate < 60s, Auto-Triage < 90s for 50k × 50 datasets.

## Decision Log
Capture architectural or stability decisions to prevent "reasoning drift."
- **Full History:** See `docs/DECISION-LOG.md`

## Known Hazards
List recurring bugs, edge cases, or Known Hazards encountered in this repo.
- **Index alignment in Auto-Triage:** PCA loadings must align with filtered column indices; mismatch can produce incorrect suspicion rankings.
- **Configuration anchor validation:** Anchor columns must be subset of selected_columns; validation enforced in `DatasetConfiguration` model.
- **LLM Summarization is placeholder:** `services/summarization.py` returns stub content; rule-based fallback in frontend.
- **In-memory stores:** Dataset registry, configuration store, template store, and audit trail are in-memory; no persistence across restarts yet.
- **Frontend API client timeout:** Analysis endpoints may timeout on large datasets; extended timeout configured in `api_client.py`.
