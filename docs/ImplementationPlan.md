# Implementation Plan for RelatAI

## 1. Objectives Alignment
- **Goal**: Deliver a self-service platform that ingests tabular datasets and quickly surfaces correlations and multivariate relationships for non-specialists and analysts.
- **Key Outcomes**: Fast exploratory analysis, AI-generated insights, scalable performance for ~50k rows datasets, modular architecture for future statistical methods.

## 2. Milestone Roadmap
1. **Project Setup**
   - Scaffold repository structure and development tooling (linting, formatting, testing).
   - Implement configuration management and environment setup (Docker/dev containers optional).
2. **Data Ingestion & Schema Detection**
   - Build file upload handlers supporting CSV, Parquet, Excel.
   - Implement data profiling to detect column types (numeric, categorical, datetime, text) and basic statistics.
3. **Backend Analysis Engine**
   - Develop correlation engine covering pairwise methods (Pearson, Spearman, Kendall, Chi-square, Cramér's V, ANOVA, point-biserial).
   - Implement multivariate module with configurable max variables, anchor handling, and interaction depth (regression, ANOVA, partial correlations).
   - Add performance optimizations (feature pre-filtering, parallel execution, sampling safeguards).
4. **Configuration & Filtering Layer**
   - Build API endpoints to manage column selection, filtering, and analysis mode toggling.
   - Ensure validation of user inputs and dataset constraints.
5. **Result Serialization & Storage**
   - Define JSON schemas for tables, plots metadata, and AI summaries.
   - Implement caching strategy for reusing computation results when configurations repeat.
6. **Frontend Experience**
   - Prototype UI in Streamlit covering dataset upload, column/filter controls, mode selection, and results visualization (tables, heatmaps, network graphs, faceted plots).
   - Plan migration path to React/Dash for production (component mapping, shared API contract).
7. **AI Summarization Module**
   - Integrate LLM pipeline that consumes structured results and outputs narrative insights.
   - Design prompt templates emphasizing interpretability and highlighting surprising relationships.
   - Implement safeguards for summarization latency (async processing, caching).
8. **Testing & Quality Assurance**
   - Unit tests for schema detection, statistical computations, and API endpoints.
   - Integration tests covering end-to-end workflow with sample datasets.
   - Performance tests to validate throughput on 50k-row datasets and stress regression module.
9. **Documentation & Deployment Prep**
   - User-facing documentation for workflow explanation and interpretation guidance.
   - Developer documentation for extending statistical methods and visualizations.
   - Deployment scripts (CI/CD pipelines, containerization) and monitoring hooks.

## 3. Detailed Workstreams

### 3.1 Backend Services (FastAPI/Flask)
- **Modules**: `api`, `services/analysis`, `services/preprocessing`, `services/summarization`, `core/models`.
- **Responsibilities**:
  - Handle file uploads and persist temporary datasets securely.
  - Run schema detection and maintain metadata catalogue.
  - Dispatch statistical computations, leveraging joblib/Dask for parallelism.
  - Manage user session state (selected columns, filters, anchors).
  - Expose REST endpoints returning JSON payloads consumed by frontend.
- **Key Considerations**:
  - Input validation and error messaging for unsupported file formats or excessive dataset sizes.
  - Graceful degradation through sampling when performance thresholds are exceeded.

### 3.2 Analysis Engine
- **Pairwise Analysis Pipeline**:
  - Iterate over selected column pairs using type-driven method selection.
  - Compute effect sizes, p-values, and confidence intervals where applicable.
  - Rank results and flag notable relationships based on strength/novelty heuristics.
- **Multivariate Analysis Pipeline**:
  - Construct model matrices honoring max variable count, anchors, and interaction depth.
  - Support regression (continuous outcome), ANOVA (categorical outcome), and partial correlations.
  - Implement model evaluation metrics (R², adjusted R², F-statistics, significance levels).
- **Performance**:
  - Pre-filter candidate variables via mutual information / variance thresholds.
  - Introduce caching of intermediate computations.
  - Utilize parallel workers for independent model fits.

### 3.3 Frontend (Streamlit Prototype → React/Dash)
- **Streamlit Prototype Tasks**:
  - Build upload widget, column selector with default all-selected state, and filter UI.
  - Render correlation tables with sorting, heatmaps via seaborn/plotly, and network graphs using networkx/plotly.
  - Display AI summaries alongside visualizations, emphasizing interpretability.
- **Production-ready UI Planning**:
  - Define API contracts for React/Dash components to mirror Streamlit behaviors.
  - Establish state management strategy (e.g., Redux or Zustand) for user configurations.
  - Ensure responsive design for analyst dashboards.

### 3.4 AI Summarization Workflow
- **Inputs**: Ranked statistical results, metadata about variable types, dataset context.
- **Processing**:
  - Template-driven prompts with guardrails to explain statistical significance and caveats.
  - Option for multiple summaries (executive overview vs. analyst deep dive).
- **Outputs**: JSON containing textual insights and structured tags (e.g., “strong positive correlation”, “notable interaction”).
- **Risks**: Latency and hallucination; mitigate via deterministic prompt structures, verifying claims against computed stats.

### 3.5 Infrastructure & DevOps
- **Environment Management**: `pyproject.toml`/`requirements.txt`, optional `environment.yml` for conda.
- **CI/CD**: Automated tests, linting (ruff/flake8), type checking (mypy), build checks for frontend.
- **Deployment**: Containerization with Docker, orchestrated via Docker Compose or similar.
- **Monitoring**: Application logs, performance metrics for long-running analyses.

## 4. Risk Assessment & Mitigations
- **Performance Bottlenecks**: Employ sampling, parallelism, and pre-filtering to keep runtimes manageable.
- **Statistical Validity**: Validate methods with known datasets, surface method descriptions in UI for transparency.
- **LLM Reliability**: Implement review mode to compare AI summaries against raw metrics; include disclaimers.
- **Scalability of Architecture**: Modularize statistical functions and visualization components for future extension.

## 5. Deliverables Checklist
- Repository scaffold with automated tooling.
- Backend API implementing ingestion, analysis, summarization endpoints.
- Streamlit prototype UI with visualizations and summary display.
- Testing suite and performance benchmarks.
- Documentation covering usage, architecture, and extension guidance.

# Proposed Repository Structure
```
RelatAI/
├── README.md
├── Reference-Guide.md
├── docs/
│   ├── ImplementationPlan.md  (this document)
│   ├── architecture.md        (high-level system diagrams)
│   ├── api/                   (OpenAPI specs, endpoint docs)
│   └── user-guide.md          (end-user instructions)
├── backend/
│   ├── pyproject.toml / requirements.txt
│   ├── relat_ai/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── ingestion.py
│   │   │   ├── schema_detection.py
│   │   │   ├── analysis/
│   │   │   │   ├── pairwise.py
│   │   │   │   ├── multivariate.py
│   │   │   │   └── utils.py
│   │   │   ├── summarization.py
│   │   │   └── visualization.py
│   │   ├── utils/
│   │   │   ├── caching.py
│   │   │   └── parallel.py
│   │   └── tests/
│   │       ├── unit/
│   │       └── integration/
│   └── scripts/
│       └── benchmark.py
├── frontend/
│   ├── streamlit_app/
│   │   ├── app.py
│   │   └── components/
│   └── webapp/                (future React/Dash implementation)
│       ├── package.json
│       └── src/
├── datasets/
│   ├── samples/
│   └── README.md
├── infrastructure/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   └── frontend.Dockerfile
│   ├── docker-compose.yml
│   └── ci/
│       └── workflows/
└── tests/
    ├── performance/
    └── end_to_end/
```
