# Reference Guide

## Root
- `README.md`: Onboarding overview, setup instructions, and tooling summary for the RelatAI repository.
- `pyproject.toml`: Centralized configuration for Black, Ruff, Pytest, Coverage, and Mypy tooling.
- `Makefile`: Convenience commands for installing dependencies, running formatters, linters, tests, and starting the backend.
- `.gitignore`: Excludes Python caches, virtual environments, node modules, dataset artifacts, and build outputs from version control.

## Documentation (`docs/`)
- `docs/agents.md`: Contribution guidelines covering reviews, planning expectations, and commit conventions.
- `docs/BUG_FIX_ASSESSMENT.md`: Assessment of bug fixes and refactoring completion from initial repository review.
- `docs/ImplementationPlan.md`: Detailed implementation roadmap (v2.1), milestone descriptions, repository structure blueprint. Updated to align with UserRequirements v2.1 and TechnicalSpecification v2.1, includes Auto-Triage mode, audit trail system, confidence flags, template management, and performance targets.
- `docs/MILESTONE3_REVIEW.md`: Comprehensive review of Milestone 3 (Backend Analysis Engine) identifying bugs, refactoring opportunities, and progress assessment.
- `docs/MILESTONE4_REVIEW.md`: Comprehensive review of Milestone 4 (Audit Trail & Preprocessing Transparency) identifying bugs, refactoring opportunities, documentation gaps, and completion assessment.
- `docs/MILESTONE4_SUMMARY.md`: Quick reference summary for Milestone 4 completion with actionable immediate, short-term, and future items.
- `docs/MILESTONE4_COMPLETION_REPORT.md`: Final completion report documenting all deliverables, testing, documentation, bug fixes, and success criteria met for Milestone 4.
- `docs/MILESTONE5_REVIEW.md`: Comprehensive review of Milestone 5 (Auto-Triage Mode) identifying 3 bugs (1 critical index alignment issue), refactoring opportunities, missing components (API routes, integration tests), and holistic repository status assessment.
- `docs/MILESTONE5_SUMMARY.md`: Executive summary for Milestone 5 review with quick status, critical findings, immediate action items, and strategic recommendations.
- `docs/MILESTONE8_REVIEW.md`: Comprehensive review of Milestone 8 (Result Serialization & Storage) identifying 4 bugs (1 high-priority signature mismatch, missing validation), 4 refactoring opportunities, test coverage gaps, and repository completion assessment at 65%.
- `docs/MILESTONE9_DETAILED.md`: Detailed 10-day implementation plan for Milestone 9 (Frontend Experience - Streamlit Prototype) organized into 5 phases covering foundation and upload (Phase 1), configuration interface (Phase 2), analysis execution and results (Phase 3), templates and export (Phase 4), polish and documentation (Phase 5), with component specifications, visual mockups, API integration strategy, risk assessment, and success criteria.
- `docs/MILESTONE9_PHASE2_COMPLETION.md`: Completion report for Phase 2 (Configuration Interface) documenting all deliverables (column selector, filter panel, mode selector, preview table, configuration page, template management), success metrics achieved, technical implementation details, code quality assessment, testing performed, and next steps for Phase 3.
- `docs/PHASE3_BACKEND_REVIEW.md`: Comprehensive review of backend analysis endpoint implementation verifying readiness for Phase 3 (Analysis Execution & Results Display), including verification of API routes, analysis runner service, result models (correlation, multivariate, auto-triage), integration tests, caching strategy, and frontend data requirements analysis with approval to proceed and minor issue identified (missing frontend API client method).
- `docs/AuditTrail_UserGuide.md`: User-facing documentation for audit trail interpretation, API usage, action types reference, use cases, and troubleshooting.
- `docs/Preprocessing_DeveloperGuide.md`: Developer guide for extending preprocessing system, architecture overview, adding new strategies/transformations, testing patterns, and best practices.
- `docs/FutureEnhancements.md`: Backlog of stretch goals and nice-to-have features including advanced imputation, audit persistence, user tracking, feature engineering, and ML integrations.
- `docs/Reference-Guide.md`: This reference document mapping repository files to their purpose.
- `docs/REPO_REVIEW.md`: Comprehensive repository review identifying bugs, refactoring opportunities, and capability assessment against intended use-case.
- `docs/TechnicalSpecification.md`: Architectural design (v2.1), statistical methods (including PLS, change-point detection, residual forensics), and performance constraints with explicit runtime targets.
- `docs/UserRequirements.md`: Personas, functional requirements (v2.1), and experience goals for the analytics platform. Includes three analysis modes (Correlation, Multivariate, Auto-Triage), audit trail, confidence flags, and template management.

## Backend (`backend/`)
- `backend/README.md`: Backend-specific setup steps, layout explanation, and run commands.
- `backend/.env.example`: Sample environment variable definitions for local development.
- `backend/requirements.txt`: Runtime Python dependencies for the FastAPI service and analysis stack.
- `backend/requirements-dev.txt`: Developer tooling dependencies (formatting, linting, testing, typing).
- `backend/relat_ai/__init__.py`: Declares the backend Python package namespaces.
- `backend/relat_ai/api/__init__.py`: Exposes the FastAPI application factory.
- `backend/relat_ai/api/main.py`: Creates the FastAPI app, registers routes, and exposes configuration metadata endpoint.
- `backend/relat_ai/api/routes/__init__.py`: Registers public API route modules.
- `backend/relat_ai/api/routes/datasets.py`: Dataset upload and retrieval endpoints returning profiling metadata.
- `backend/relat_ai/api/routes/configuration.py`: Configuration management endpoints for column selection, filtering, previews, and template operations.
- `backend/relat_ai/api/routes/analysis.py`: Analysis execution endpoint allowing clients to trigger correlation, multivariate, and auto-triage runs.
- `backend/relat_ai/api/routes/health.py`: Health check endpoint used for uptime monitoring.
- `backend/relat_ai/api/routes/audit.py`: REST endpoints exposing preprocessing audit logs for datasets.
- `backend/relat_ai/core/__init__.py`: Re-exports configuration primitives.
- `backend/relat_ai/core/config.py`: Pydantic settings model sourcing environment configuration (upload size, profiling sample size, storage paths) with ContextVar-based dependency injection support.
- `backend/relat_ai/core/exceptions.py`: Custom exception hierarchy for domain-specific errors including persistence failures and registry errors.
- `backend/relat_ai/core/models.py`: Shared domain models for dataset metadata, profiling payloads, and analysis requests.
- `backend/relat_ai/core/results.py`: Pydantic schemas describing serialized analysis results, quality flags, ranked insights, and AI summaries.
- `backend/relat_ai/services/__init__.py`: Aggregates service layer modules.
- `backend/relat_ai/services/ingestion.py`: Streaming upload persistence, dataset registry management with retry logic, and dataframe loaders supporting CSV, Parquet, and Excel formats.
- `backend/relat_ai/services/registry_state.py`: Persistence and restoration helpers for dataset registry state with defensive error handling and validation.
- `backend/relat_ai/services/schema_detection.py`: Dataset and column profiling utilities with logical type inference, statistics extraction, and consolidated computation helpers.
- `backend/relat_ai/services/analysis/__init__.py`: Public interface for statistical pipelines.
- `backend/relat_ai/services/analysis/pairwise.py`: Configurable pairwise analysis engine supporting numeric (Pearson, Spearman, Kendall), mixed (ANOVA, point-biserial), and categorical (Chi-square, Cramér's V) statistics with caching and sampling controls.
- `backend/relat_ai/services/analysis/multivariate.py`: Multivariate analysis pipeline providing regression plan expansion, ANOVA fitting with effect sizes, Partial Least Squares (PLS) support, interaction depth controls, variance inflation factor (VIF) diagnostics, and partial correlation computation.
- `backend/relat_ai/services/analysis_runner.py`: Service orchestrating dataset retrieval, configuration overrides, pipeline execution, serialization, and caching for the analysis API.
- `backend/relat_ai/services/analysis/auto_triage.py`: Auto-triage analysis pipeline combining PCA loadings, change-point detection (CUSUM, PELT algorithms), clustering (K-Means, Hierarchical), residual forensics, and suspicion ranking for unsupervised anomaly triage during quality events.
- `backend/relat_ai/services/analysis/change_detection.py`: Shared change-point detection algorithms (CUSUM and PELT) exposed for reuse across analysis pipelines with configurable thresholds.
- `backend/relat_ai/services/analysis/confidence_flags.py`: Centralised quality flag dataclass and builder utilities producing consistent dataset warnings across analysis modes.
- `backend/relat_ai/services/configuration.py`: In-memory configuration store with validation, filter application helpers, and defaults derived from dataset profiles.
- `backend/relat_ai/services/templates.py`: Thread-safe storage for reusable configuration templates referencing dataset configurations.
- `backend/relat_ai/services/analysis/utils.py`: Shared enums and data structures for correlation/model summaries consumed by visualization and summarization layers.
- `backend/relat_ai/services/results.py`: SignatureBuilder for deterministic cache keys, converter utilities for analysis payloads, ResultStorage with TTL/LRU eviction, and reduced dataset export helpers.
- `backend/relat_ai/services/summarization.py`: Placeholder LLM summarization service for analysis results.
- `backend/relat_ai/services/visualization.py`: Heatmap metadata factory for frontend visualizations.
- `backend/relat_ai/services/audit_trail.py`: In-memory audit store capturing preprocessing actions with dataset hashes and timestamps.
- `backend/relat_ai/services/preprocessing.py`: DataFrame preprocessing strategies (imputation, outlier clipping, robust scaling) with audit trail integration.
- `backend/relat_ai/utils/__init__.py`: Utility package exports for caching helpers.
- `backend/relat_ai/utils/caching.py`: Cache interface, in-memory LRU implementation, and decorator utility for memoization.
- `backend/relat_ai/tests/__init__.py`: Test suite package initialization.
- `backend/relat_ai/tests/conftest.py`: Shared pytest fixtures including FastAPI test client setup.
- `backend/relat_ai/tests/unit/__init__.py`: Unit test namespace marker.
- `backend/relat_ai/tests/unit/test_health.py`: Validates health and configuration endpoints of the API.
- `backend/relat_ai/tests/unit/test_ingestion.py`: Verifies upload persistence behaviors, size enforcement, and loader support for multiple formats.
- `backend/relat_ai/tests/unit/test_schema_detection.py`: Exercises profiling heuristics and serialization to API models.
- `backend/relat_ai/tests/unit/test_preprocessing.py`: Validates preprocessing strategies and audit logging integration.
- `backend/relat_ai/tests/unit/test_analysis_pairwise.py`: Validates pairwise analysis planning across numeric, categorical, and mixed methods.
- `backend/relat_ai/tests/unit/test_analysis_multivariate.py`: Verifies regression plan expansion, interaction controls, regression/ANOVA/PLS outputs, effect sizes, and diagnostic calculations.
- `backend/relat_ai/tests/unit/test_analysis_auto_triage.py`: Unit tests for auto-triage pipeline validating PCA components, change-point detection (CUSUM, PELT), clustering, residual forensics, and suspicion rankings.
- `backend/relat_ai/tests/unit/test_configuration.py`: Unit tests for configuration and template services covering defaults, validation, and filter application.
- `backend/relat_ai/tests/unit/test_analysis_change_detection.py`: Unit tests verifying the extracted CUSUM and PELT change-point detection helpers handle shifts and edge cases.
- `backend/relat_ai/tests/integration/test_datasets_api.py`: Integration coverage for dataset upload and retrieval endpoints.
- `backend/relat_ai/tests/integration/test_audit_api.py`: Validates audit trail API responses after dataset ingestion.
- `backend/relat_ai/tests/integration/test_configuration_api.py`: Integration tests verifying configuration endpoints, previews, template persistence, and validation errors.
- `backend/relat_ai/tests/integration/__init__.py`: Integration test namespace marker.
- `backend/scripts/benchmark.py`: CLI utility to benchmark correlation throughput on datasets.

## Frontend (`frontend/`)
- `frontend/streamlit_app/README.md`: Frontend-specific setup steps, configuration guide, usage instructions, and troubleshooting for the Streamlit application.
- `frontend/streamlit_app/app.py`: Main Streamlit application entry point providing dashboard with backend status monitoring, dataset navigation, quick actions, and help resources.
- `frontend/streamlit_app/config.py`: Centralized configuration management with AppConfig dataclass supporting environment variables for backend URL, upload limits, UI preferences, and feature flags.
- `frontend/streamlit_app/requirements.txt`: Production dependencies for Streamlit application including web framework, data processing, API communication, visualization, and configuration management libraries.
- `frontend/streamlit_app/requirements-dev.txt`: Development dependencies for testing, formatting, linting, and type checking.
- `frontend/streamlit_app/pages/1_📊_Dataset_Upload.py`: Dataset upload page with file validation, backend upload integration, profile display with column statistics, quality warnings, and navigation to configuration workflow.
- `frontend/streamlit_app/pages/2_⚙️_Configuration.py`: Configuration page providing column selection with search/filtering, dynamic filter builder with type-aware inputs, analysis mode selector with mode-specific parameters, live configuration preview, and template management (save/load/delete functionality).
- `frontend/streamlit_app/pages/3_🔬_Analysis.py`: Analysis execution and results display page with run controls, progress tracking, mode-specific result tabs (correlation/multivariate/auto-triage), confidence flag displays, AI-generated summaries, and export options for JSON results.
- `frontend/streamlit_app/components/__init__.py`: Reusable Streamlit component exports including configuration components (column selector, filter panel, mode selector, preview table), confidence flag components (badge rendering, flag filtering, severity categorization), and visualization components (correlation results, multivariate results, auto-triage results, AI summary).
- `frontend/streamlit_app/components/column_selector.py`: Interactive column selection component with search functionality, data type filtering, grouped display by type, column statistics tooltips, and anchor column designation for multivariate analysis.
- `frontend/streamlit_app/components/filter_panel.py`: Dynamic filter builder component with type-aware inputs supporting numeric range sliders, categorical multi-select, datetime ranges, and text keyword filtering with add/remove filter controls.
- `frontend/streamlit_app/components/mode_selector.py`: Analysis mode selector component with tabbed interface for Correlation, Multivariate, and Auto-Triage modes, displaying mode descriptions and rendering mode-specific parameter controls (thresholds, max variables, interaction depth, clustering params, change-point sensitivity).
- `frontend/streamlit_app/components/preview_table.py`: Configuration preview component displaying filtered dataset samples with row/column metrics, quick statistics for numeric columns, column information table, and refresh controls.
- `frontend/streamlit_app/components/confidence_flags.py`: Confidence flag display components with severity-based badges (error/warning/info), aggregate flag summaries with counts, severity filtering, inline flag display with limits, tooltip support, and flag extraction utilities for nested result structures across all analysis modes.
- `frontend/streamlit_app/components/correlation_view.py`: Correlation analysis visualization component with ranked sortable table displaying variable pairs and coefficients, interactive Plotly heatmap with customizable color scales, force-directed network graph with threshold filtering showing positive/negative correlation edges, and summary statistics expandable panel.
- `frontend/streamlit_app/components/multivariate_view.py`: Multivariate analysis visualization component with model summary displaying R², adjusted R², coefficients table with significance indicators, horizontal coefficient plot with 95% confidence intervals, and four diagnostic plots (residuals vs fitted, Q-Q plot, scale-location, residuals histogram) with interpretation guides.
- `frontend/streamlit_app/components/autotriage_view.py`: Auto-triage visualization component with suspicion rankings table showing severity categories (high/medium/low), detailed scoring breakdown by component (missing data, outliers, distribution, correlation, pattern), PCA biplot with loadings vectors, change-point detection charts with severity indicators, and cluster visualization with centroid markers and size distribution pie chart.
- `frontend/streamlit_app/components/ai_summary.py`: AI-generated summary component providing collapsible narrative insights with mode-specific rule-based summaries, key findings highlighting strongest correlations/significant predictors/high-suspicion columns, interpretation guidance, and recommendations (placeholder for future LLM integration).
- `frontend/streamlit_app/utils/__init__.py`: Utility package exports for API client, session state management with configuration helpers, and error handling functions.
- `frontend/streamlit_app/utils/api_client.py`: Backend API communication layer with APIClient class supporting dataset operations (upload, list, get), configuration management (get, update, preview), template persistence (list, apply, save, delete), audit log retrieval, analysis execution with extended timeouts, and comprehensive error handling with user-friendly messages.
- `frontend/streamlit_app/utils/session_state.py`: Session state management utilities providing initialization helpers including analysis_running and analysis_results state, safe state access (get_state, set_state), context loading (get_selected_dataset, get_analysis_mode, get_current_config), dataset status checks, configuration management helpers (has_configuration, get_configuration, update_configuration, reset_configuration), analysis state management (set_analysis_running, get_analysis_results, set_analysis_results), and debug display for development.
- `frontend/streamlit_app/assets/styles.css`: Custom CSS styling with Professional Blue color scheme defining typography, button styles, metrics display, alert cards, sidebar aesthetics, table enhancements, badge classes for confidence flags, and responsive design breakpoints.
- `frontend/webapp/README.md`: Placeholder documentation for the future React/Dash implementation.

## Data Assets (`datasets/`)
- `datasets/README.md`: Guidance for sample datasets, uploads, and storage conventions.
- `datasets/samples/.gitkeep`: Keeps the samples directory tracked for curated datasets.

## Infrastructure (`infrastructure/`)
- `infrastructure/docker/backend.Dockerfile`: Container image definition for the FastAPI backend service.
- `infrastructure/docker/frontend.Dockerfile`: Container image definition for the Streamlit prototype frontend.
- `infrastructure/docker-compose.yml`: Compose file orchestrating backend and frontend containers with shared volumes.
- `infrastructure/ci/workflows/ci.yml`: GitHub Actions workflow running lint, format check, type check, and tests on pushes and PRs.

## Testing Harnesses (`tests/`)
- `tests/performance/README.md`: Placeholder for benchmarking scenarios measuring performance characteristics.
- `tests/end_to_end/README.md`: Placeholder for end-to-end workflow tests spanning ingestion through summarization.
