# Implementation Plan for RelatAI

**Version**: 2.1  
**Last Updated**: 2025-10-13  
**Status**: Updated to align with UserRequirements v2.1 and TechnicalSpecification v2.1

---

## Document Change Summary (v2.1)

This update synchronizes the Implementation Plan with significant enhancements to UserRequirements.md and TechnicalSpecification.md:

### Major Additions
1. **Auto-Triage Mode** - New analysis mode featuring:
   - PCA loadings for variance drivers
   - Change-point detection (CUSUM, PELT)
   - Clustering (K-Means, Hierarchical)
   - Residual forensics and suspicion ranking
   - Optional t-SNE/UMAP and anomaly detection

2. **Audit Trail System** - Comprehensive preprocessing action logging for compliance:
   - Timestamps and dataset hash tracking
   - Dropped columns, imputations, scaling methods
   - Filter operations and transformations

3. **Confidence Flag Framework** - Quality indicators for all findings:
   - Low sample size warnings
   - Collinearity detection
   - High missingness flags
   - Clustering stability indicators

4. **Template Management** - Save/load analysis configurations:
   - Column selections
   - Filter criteria
   - Anchor variables
   - Analysis parameters

5. **Enhanced AI Summarization** - Improved interpretability:
   - Confidence references with sample sizes and effect sizes
   - Links to specific plots and tables
   - Local/on-prem processing options

6. **Performance Targets** - Explicit runtime expectations:
   - Correlation: < 5s
   - Multivariate: < 60s (≤ 5 vars)
   - Auto-Triage: < 90s (50k × 50)
   - Visualization: < 10s
   - AI Summary: < 5s

7. **Additional Statistical Methods**:
   - Partial Least Squares (PLS) regression
   - Change-point detection algorithms
   - Residual forensics capabilities

### Updated Milestones
- Milestone 3 marked as completed (Correlation & Multivariate engines)
- New Milestone 4: Audit Trail & Preprocessing Transparency
- New Milestone 5: Auto-Triage Mode implementation
- New Milestone 6: Multivariate Enhancements (PLS)
- Expanded risk assessment with mitigation strategies
- Comprehensive deliverables checklist with completion tracking

### Repository Structure Changes
- New modules: `preprocessing.py`, `auto_triage.py`, `change_detection.py`, `confidence_flags.py`, `templates.py`
- New API routes: `analysis.py`, `templates.py`, `audit.py`
- Technology stack updates with new dependencies (ruptures, optional umap-learn)

---

## 1. Objectives Alignment
- **Goal**: Deliver a self-service triage platform to rapidly surface statistical drivers during quality events and CAPA investigations, accelerating root-cause analysis through automated correlation discovery, multivariate modeling, and anomaly triage.
- **Key Outcomes**: 
  - Fast exploratory analysis with three distinct modes (Correlation, Multivariate, Auto-Triage)
  - AI-generated insights with confidence references and quality flags
  - Scalable performance for ~50k rows × dozens of columns datasets
  - Modular architecture for future statistical methods
  - Audit trail for compliance and reproducibility
  - Local/on-prem processing with optional AI summarization

## 2. Milestone Roadmap
1. **Project Setup** *(Completed)*
   - Scaffolded repository structure spanning backend, frontend, infrastructure, datasets, and testing harnesses.
   - Established Python tooling (Makefile, pyproject configuration, Black, Ruff, Pytest, Mypy) and dependency manifests.
   - Added containerization assets and CI workflow to standardize environments and automation.

2. **Data Ingestion & Schema Detection** *(Completed)*
   - Delivered FastAPI dataset upload and retrieval endpoints backed by a thread-safe in-memory registry.
   - Persist uploads with streaming writes, size enforcement, and support for CSV, Parquet, and Excel sources.
   - Implemented profiling heuristics covering logical type inference, per-column statistics, and dataset-level summaries.

3. **Backend Analysis Engine - Correlation & Multivariate** *(Completed)*
   - Developed correlation engine covering pairwise methods (Pearson, Spearman, Kendall, Chi-square, Cramér's V, ANOVA, point-biserial).
   - Implemented multivariate module with configurable max variables, anchor handling, and interaction depth (regression, ANOVA, partial correlations).
   - Added performance optimizations (feature pre-filtering via mutual information, parallel execution, sampling safeguards, caching).

4. **Audit Trail & Preprocessing Transparency** *(Completed)*
   - Implemented comprehensive logging of all preprocessing actions (dropped columns, imputations, scaling methods, filters).
   - Included timestamps and dataset hash for traceability and compliance.
   - Exposed audit log via REST API for review and export.
   - Added missing value and outlier handling with configurable strategies (imputation, IQR trimming, robust scaling).
   - Created thread-safe in-memory audit store with action recording.
   - Integrated preprocessing pipeline with dataset ingestion workflow.

5. **Backend Analysis Engine - Auto-Triage Mode** *(Completed)*
   - Implement unsupervised analysis pipeline combining:
     - PCA loadings for variance drivers
     - Change-point detection (CUSUM, PELT algorithms) for time-indexed variables
     - K-Means and Hierarchical clustering for structure discovery
   - Develop residual forensics module to bucket residuals by instrument, lot, operator, analyte, or time
   - Create suspicion ranking algorithm for variables and time windows
   - Add confidence and quality flag assignment (low n, collinearity, high missingness warnings)
   - Optional extensions: t-SNE/UMAP dimensionality reduction, Isolation Forest, One-Class SVM anomaly detection

6. **Multivariate Enhancements**
   - Add Partial Least Squares (PLS) regression for collinear predictor sets
   - Enhance interaction term generation with configurable depth control
   - Implement effect size computations and multi-collinearity diagnostics (VIF)

7. **Configuration & Filtering Layer**
   - Build API endpoints to manage column selection (default all-selected), filtering, and analysis mode toggling (Correlation | Multivariate | Auto-Triage)
   - Implement template save/load functionality for repeatable workflows (column selections, filters, anchors, parameters)
   - Ensure validation of user inputs and dataset constraints
   - Add data subsetting by column values (e.g., Region = Europe)

8. **Result Serialization & Storage**
   - Define JSON schemas for correlation tables, multivariate model summaries, ranked insights, and AI summaries
   - Include confidence flags and quality indicators in all result structures
   - Implement caching strategy keyed by (dataset hash + filter signature + configuration)
   - Add reduced dataset export functionality (top-N variables for downstream analysis)

9. **Frontend Experience - Streamlit Prototype**
   - Dataset upload widget with format support (CSV, Excel, Parquet)
   - Column selector with default all-selected state and deselection capability
   - Filtering panel for subsetting by column values
   - Mode toggle (Correlation | Multivariate | Auto-Triage)
   - Template save/load interface
   - Results visualization:
     - Ranked correlation tables with sorting
     - Heatmaps (seaborn/plotly)
     - Network graphs (networkx/plotly)
     - PCA biplots
     - Change-point charts
     - Faceted plots
   - AI summary display with confidence references and links to plots/tables
   - Confidence flag indicators on all findings

10. **AI Summarization Module**
    - Integrate LLM pipeline that consumes structured results and outputs narrative insights
    - Design prompt templates emphasizing interpretability, sample sizes (n), effect sizes, and confidence intervals
    - Include confidence references (e.g., "Based on 8k samples, R² = 0.82")
    - Link summaries back to specific plots and tables
    - Implement async processing and caching for latency management
    - Add local/on-prem toggle with optional external API integration
    - Build safeguards against hallucination via deterministic prompt structures

11. **Testing & Quality Assurance**
    - Unit tests for schema detection, all statistical methods, API endpoints, audit trail, confidence flags
    - Integration tests covering end-to-end workflows with sample datasets across all three analysis modes
    - Performance tests validating:
      - Correlation mode: < 5 seconds
      - Multivariate mode: < 60 seconds (≤ 5 variables)
      - Auto-Triage mode: < 90 seconds (capped @ 50k × 50 columns)
      - Visualization: < 10 seconds
      - AI Summary: < 5 seconds
    - Stress tests for 50k-row datasets with dozens of columns

12. **Security, Compliance & Documentation**
    - Ensure local/on-prem data processing by default (no external transmission)
    - Implement audit trail export for regulatory compliance
    - User-facing documentation:
      - Workflow explanation for each analysis mode
      - Statistical interpretation guidance
      - Confidence flag meanings
      - Template usage examples
    - Developer documentation:
      - Extending statistical methods
      - Adding visualizations
      - Custom preprocessing strategies
    - Deployment scripts (CI/CD pipelines, containerization) and monitoring hooks

13. **Production Frontend Migration** *(Future)*
    - Plan migration path from Streamlit to React/Dash
    - Define API contracts and component mappings
    - Establish state management strategy (Redux/Zustand)
    - Implement responsive design for analyst dashboards

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
- **Pairwise Analysis Pipeline (Correlation Mode)**:
  - Iterate over selected column pairs using type-driven method selection.
  - Compute effect sizes, p-values, confidence intervals, and sample sizes where applicable.
  - Rank results and flag notable relationships based on strength/novelty heuristics.
  - Assign confidence flags (low n, high missingness) to each correlation.
  - Target runtime: < 5 seconds for typical datasets.
  
- **Multivariate Analysis Pipeline (Multivariate Mode)**:
  - Construct model matrices honoring max variable count, anchors, and interaction depth.
  - Support:
    - Linear/Logistic Regression (continuous/binary outcomes)
    - ANOVA (categorical predictors)
    - Partial Correlations
    - Partial Least Squares (PLS) for collinear predictor sets
  - Implement model evaluation metrics (R², adjusted R², F-statistics, VIF for collinearity, significance levels).
  - Assign confidence flags (collinearity warnings, low sample size).
  - Target runtime: < 60 seconds (≤ 5 variables).
  
- **Auto-Triage Pipeline (Auto-Triage Mode)**:
  - Unsupervised scan combining:
    - PCA loadings to identify variance drivers
    - Change-point detection (CUSUM, PELT) for time-indexed anomalies
    - Clustering (K-Means, Hierarchical) for structure discovery
  - Residual forensics: bucket residuals by grouping variables (instrument, lot, operator, analyte, time) to identify systematic bias
  - Generate suspicion ranking of top contributing variables and anomaly segments
  - Assign confidence flags (sample size, clustering stability, detection sensitivity)
  - Optional extensions: t-SNE/UMAP, Isolation Forest, One-Class SVM
  - Target runtime: < 90 seconds (capped @ 50k rows × 50 columns).
  
- **Performance Optimizations**:
  - Pre-filter candidate variables via mutual information / variance thresholds.
  - Cache computations keyed by (dataset hash + filter signature + configuration).
  - Utilize parallel workers (joblib, Dask) for independent model fits.
  - Implement sampling for very large datasets with configurable thresholds.
  - Use multi-threaded BLAS (MKL / OpenBLAS) for matrix operations.

### 3.3 Frontend (Streamlit Prototype → React/Dash)
- **Streamlit Prototype Tasks**:
  - Build upload widget supporting CSV, Excel, and Parquet formats.
  - Column selector with default all-selected state and multi-select deselection capability.
  - Filtering panel for subsetting data by column values (e.g., Region = Europe).
  - Mode toggle UI: Correlation | Multivariate | Auto-Triage.
  - Template save/load interface for repeatable analysis workflows (persist column selections, filters, anchors, parameters).
  - Visualization rendering:
    - Ranked correlation tables with sorting and confidence flags
    - Heatmaps (seaborn/plotly)
    - Network graphs (networkx/plotly)
    - PCA biplots
    - Change-point detection charts
    - Faceted plots
  - Display AI summaries alongside visualizations with:
    - Confidence references (sample sizes, R², p-values)
    - Links back to specific plots and tables
    - Quality indicators (low n, collinearity, high missingness)
  - Export controls for reduced datasets (top-N variables) and audit logs.
  - Target render time: < 10 seconds for visualization.
  
- **Production-ready UI Planning**:
  - Define API contracts for React/Dash components to mirror Streamlit behaviors.
  - Establish state management strategy (Redux or Zustand) for user configurations and templates.
  - Ensure responsive design for analyst dashboards.
  - Plan component architecture for three analysis modes with shared data flow.

### 3.4 AI Summarization Workflow
- **Inputs**: 
  - Ranked statistical results with confidence flags and quality indicators
  - Metadata about variable types, sample sizes, missing data percentages
  - Dataset context (source, filters applied, preprocessing actions)
  
- **Processing**:
  - Template-driven prompts with guardrails to explain statistical significance, effect sizes, and caveats.
  - Include explicit confidence references (e.g., "Based on 8k samples, R² = 0.82, p < 0.001").
  - Reference specific plots and tables in narrative.
  - Option for multiple summary levels (executive overview vs. analyst deep dive).
  - Local/on-prem processing by default; optional external LLM API integration.
  
- **Outputs**: 
  - JSON containing textual insights with structured metadata
  - Tags (e.g., "strong positive correlation", "notable interaction", "collinearity warning")
  - Links to corresponding visualizations
  - Confidence level indicators
  
- **Performance & Safety**:
  - Target runtime: < 5 seconds
  - Async processing with caching for repeated configurations
  - Deterministic prompt structures to minimize hallucination risk
  - Verify all numerical claims against computed statistics
  - Include disclaimers about AI-generated content

### 3.5 Infrastructure & DevOps
- **Environment Management**: 
  - `pyproject.toml`/`requirements.txt` for Python dependencies
  - Optional `environment.yml` for conda environments
  - Pin critical dependencies (numpy, scipy, scikit-learn, statsmodels, pingouin, ruptures) for reproducibility
  
- **CI/CD**: 
  - Automated tests (unit, integration, performance benchmarks)
  - Linting (ruff/flake8) and formatting (Black)
  - Type checking (mypy)
  - Build checks for frontend
  - Performance regression tests against runtime targets
  
- **Deployment**: 
  - Containerization with Docker (backend and frontend images)
  - Orchestration via Docker Compose
  - Local/on-prem deployment by default for data security
  - Optional cloud deployment configurations
  
- **Monitoring & Compliance**:
  - Application logs with structured output
  - Performance metrics for analysis runtimes
  - Audit trail persistence and export capabilities
  - Data retention policies for uploaded datasets
  - Privacy controls (no external data transmission unless explicitly enabled)

## 4. Performance Targets & Runtime Expectations

The following runtime targets are established to ensure the platform remains responsive for interactive analysis:

| Module | Target Runtime | Dataset Size | Notes |
|--------|---------------|--------------|-------|
| **Correlation Mode** | < 5 seconds | ~50k rows × dozens of columns | Pairwise computations only; parallelized |
| **Multivariate Mode** | < 60 seconds | ≤ 5 variables | Includes regression, ANOVA, partial correlations, PLS |
| **Auto-Triage Mode** | < 90 seconds | Capped @ 50k rows × 50 columns | PCA, change-point, clustering, residual forensics |
| **Visualization** | < 10 seconds | All result types | Cached outputs; lazy rendering for complex plots |
| **AI Summarization** | < 5 seconds | Per analysis run | Async processing; cached by configuration |

### Performance Optimization Strategies
- **Pre-filtering**: Mutual information and variance thresholds remove low-signal variables before expensive computations
- **Sampling**: Configurable thresholds automatically subsample very large datasets while maintaining statistical validity
- **Caching**: Results keyed by (dataset hash + filter signature + configuration) avoid redundant computation
- **Parallelization**: Independent model fits and correlations distributed across CPU cores (joblib/Dask)
- **BLAS Acceleration**: Multi-threaded matrix operations via MKL or OpenBLAS
- **Incremental Rendering**: Visualizations render progressively for large result sets

### Graceful Degradation
When performance targets cannot be met:
- Surface progress indicators to users
- Implement sampling with clear communication about trade-offs
- Offer option to abort long-running operations
- Log performance metrics for optimization opportunities

## 5. Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| **Performance Bottlenecks** | High - Analysis timeouts frustrate users | Medium | • Employ sampling with configurable thresholds<br>• Parallelize independent computations (joblib/Dask)<br>• Pre-filter via mutual information/variance<br>• Cache results keyed by dataset + config<br>• Target runtimes: 5s/60s/90s for modes |
| **Statistical Validity** | High - Incorrect results undermine trust | Low | • Validate methods against known datasets<br>• Include confidence flags (low n, collinearity)<br>• Surface method descriptions in UI<br>• Comprehensive unit tests for all statistical methods<br>• Peer review of implementations |
| **LLM Hallucination** | Medium - Misleading summaries cause confusion | Medium | • Deterministic prompt structures<br>• Verify all numerical claims against computed stats<br>• Include confidence references with sample sizes<br>• Local/on-prem LLM option<br>• Review mode to compare summaries vs. raw data<br>• Explicit AI disclaimers |
| **Data Privacy & Compliance** | High - Breach damages reputation and regulatory standing | Low | • Local/on-prem processing by default<br>• No external transmission unless explicitly enabled<br>• Audit trail with timestamps and dataset hash<br>• Data retention policies<br>• Encryption at rest for sensitive uploads |
| **Scalability of Architecture** | Medium - Difficult to extend with new methods | Low | • Modular statistical function design<br>• Plugin architecture for new analyses<br>• Clear separation of concerns (ingestion/analysis/viz/summary)<br>• Comprehensive developer documentation |
| **Missing Data Handling** | Medium - Poor handling leads to biased results | Medium | • Configurable imputation strategies<br>• Flag high-missingness in confidence indicators<br>• Pairwise deletion where appropriate<br>• Surface missing data percentages in results |
| **User Adoption** | Medium - Complex UI deters non-technical users | Medium | • Sensible defaults that "just work"<br>• Progressive disclosure (simple → advanced)<br>• Template save/load for workflow repeatability<br>• Clear interpretation guidance in summaries<br>• User testing with target personas |
| **Change-Point False Positives** | Medium - Spurious alerts waste investigation time | Medium | • Multiple detection algorithms (CUSUM, PELT)<br>• Configurable sensitivity thresholds<br>• Confidence scoring for detected changes<br>• Visual inspection tools for validation |

## 6. Deliverables Checklist

### Core Platform
- [x] Repository scaffold with automated tooling (Makefile, pyproject.toml, CI/CD)
- [x] Data ingestion API with CSV/Parquet/Excel support
- [x] Schema detection and profiling service
- [x] Correlation mode analysis engine (Pearson, Spearman, Kendall, Chi-square, Cramér's V, ANOVA, point-biserial)
- [x] Multivariate mode analysis engine (regression, ANOVA, partial correlations)
- [x] Audit trail system with preprocessing action logging
- [x] Preprocessing pipeline (imputation, outlier clipping, robust scaling)
- [x] Audit trail REST API endpoints
- [x] Result caching with intelligent key generation
- [ ] Partial Least Squares (PLS) implementation
- [ ] Auto-Triage mode analysis engine (PCA, change-point detection, clustering, residual forensics)
- [ ] Confidence flag assignment across all analysis modes
- [ ] Template save/load functionality for repeatable workflows
- [ ] Reduced dataset export (top-N variables)

### Frontend
- [ ] Streamlit prototype with upload widget
- [ ] Column selector (default all-selected) and filtering panel
- [ ] Mode toggle (Correlation | Multivariate | Auto-Triage)
- [ ] Template management interface
- [ ] Visualization suite:
  - [ ] Ranked correlation tables with confidence flags
  - [ ] Heatmaps
  - [ ] Network graphs
  - [ ] PCA biplots
  - [ ] Change-point detection charts
  - [ ] Faceted plots
- [ ] AI summary display with confidence references and plot links
- [ ] Export controls for datasets and audit logs

### AI Summarization
- [ ] LLM integration with configurable backend (local/API)
- [ ] Prompt templates with confidence references
- [ ] Link generation to plots and tables
- [ ] Async processing with caching
- [ ] Hallucination safeguards and disclaimers

### Testing & Quality
- [x] Unit tests for ingestion and schema detection
- [x] Unit tests for correlation and multivariate analysis
- [x] Unit tests for preprocessing and audit trail
- [x] Integration tests for dataset API
- [x] Integration tests for audit trail API
- [ ] Unit tests for Auto-Triage mode
- [ ] Unit tests for confidence flags
- [ ] Integration tests for all analysis modes
- [ ] Performance benchmarks validating runtime targets:
  - [ ] Correlation: < 5s
  - [ ] Multivariate: < 60s (≤ 5 vars)
  - [ ] Auto-Triage: < 90s (50k × 50)
  - [ ] Visualization: < 10s
  - [ ] AI Summary: < 5s
- [ ] End-to-end workflow tests spanning upload → analysis → visualization → export

### Documentation & Compliance
- [x] User Requirements Document (v2.1)
- [x] Technical Specification (v2.1)
- [x] Implementation Plan (this document, updated)
- [x] Reference Guide (codebase map)
- [x] Milestone 3 Review (Backend Analysis Engine)
- [x] Milestone 4 Review (Audit Trail & Preprocessing)
- [x] .env.example with preprocessing configuration
- [ ] User-facing documentation:
  - [ ] Workflow guides for each analysis mode
  - [ ] Statistical interpretation guidance
  - [ ] Confidence flag explanations
  - [ ] Template usage examples
- [ ] Developer documentation:
  - [ ] Extending statistical methods
  - [ ] Adding visualizations
  - [ ] Custom preprocessing strategies
- [ ] Deployment guides (Docker, on-prem, cloud)
- [ ] Security and compliance documentation (audit trail, data retention, privacy controls)

## 7. Technology Stack Updates

### Core Dependencies
- **Statistical Computing**: scipy, numpy, scikit-learn, statsmodels, pingouin
- **Change-Point Detection**: ruptures (CUSUM, PELT algorithms)
- **Clustering & Dimensionality Reduction**: scikit-learn (K-Means, Hierarchical, PCA, optional t-SNE/UMAP)
- **Anomaly Detection (Optional)**: scikit-learn (Isolation Forest, One-Class SVM)
- **Partial Least Squares**: scikit-learn (PLSRegression)
- **Visualization**: seaborn, plotly, networkx, matplotlib
- **Data Manipulation**: pandas
- **Parallel Processing**: joblib, Dask
- **API Framework**: FastAPI
- **Frontend**: Streamlit (prototype), React/Dash (production roadmap)
- **AI Summarization**: OpenAI API / local LLM (llama.cpp, Ollama) with optional fallback

### New Library Additions Required
- `ruptures` - Change-point detection algorithms
- Consider: `umap-learn` - Optional dimensionality reduction (if implementing UMAP)
- Consider: Local LLM framework (e.g., `langchain`, `llama-cpp-python`) for on-prem AI summarization

# 8. Proposed Repository Structure
```
RelatAI/
├── README.md
├── Makefile
├── pyproject.toml
├── .gitignore
├── docs/
│   ├── agents.md
│   ├── ImplementationPlan.md  (this document)
│   ├── Reference-Guide.md
│   ├── TechnicalSpecification.md
│   └── UserRequirements.md
├── backend/
│   ├── README.md
│   ├── .env.example
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── relat_ai/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── datasets.py
│   │   │       ├── analysis.py           # NEW: correlation, multivariate, auto-triage endpoints
│   │   │       ├── templates.py          # NEW: save/load analysis configurations
│   │   │       ├── audit.py              # NEW: preprocessing audit trail endpoints
│   │   │       └── health.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── models.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── ingestion.py
│   │   │   ├── schema_detection.py
│   │   │   ├── preprocessing.py              # NEW: audit trail, missing value handling, outlier detection
│   │   │   ├── analysis/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pairwise.py
│   │   │   │   ├── multivariate.py
│   │   │   │   ├── auto_triage.py           # NEW: PCA, change-point, clustering, residual forensics
│   │   │   │   ├── change_detection.py       # NEW: CUSUM, PELT algorithms
│   │   │   │   ├── confidence_flags.py       # NEW: quality indicator assignment
│   │   │   │   └── utils.py
│   │   │   ├── templates.py                  # NEW: save/load analysis configurations
│   │   │   ├── summarization.py
│   │   │   └── visualization.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── caching.py
│   │   │   └── parallel.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── unit/
│   │       │   ├── __init__.py
│   │       │   ├── test_health.py
│   │       │   ├── test_ingestion.py
│   │       │   └── test_schema_detection.py
│   │       └── integration/
│   │           ├── __init__.py
│   │           └── test_datasets_api.py
│   └── scripts/
│       └── benchmark.py
├── frontend/
│   ├── streamlit_app/
│   │   ├── app.py
│   │   └── components/
│   │       └── __init__.py
│   └── webapp/
│       └── README.md
├── datasets/
│   ├── README.md
│   └── samples/
│       └── .gitkeep
├── infrastructure/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   └── frontend.Dockerfile
│   ├── docker-compose.yml
│   └── ci/
│       └── workflows/
│           └── ci.yml
└── tests/
    ├── performance/
    │   └── README.md
    └── end_to_end/
        └── README.md
```
