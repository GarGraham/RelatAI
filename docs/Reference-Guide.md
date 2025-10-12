# Reference Guide

## Root
- `README.md`: Onboarding overview, setup instructions, and tooling summary for the RelatAI repository.
- `pyproject.toml`: Centralized configuration for Black, Ruff, Pytest, Coverage, and Mypy tooling.
- `Makefile`: Convenience commands for installing dependencies, running formatters, linters, tests, and starting the backend.
- `.gitignore`: Excludes Python caches, virtual environments, node modules, dataset artifacts, and build outputs from version control.

## Documentation (`docs/`)
- `docs/agents.md`: Contribution guidelines covering reviews, planning expectations, and commit conventions.
- `docs/ImplementationPlan.md`: Detailed implementation roadmap, milestone descriptions, and repository structure blueprint.
- `docs/Reference-Guide.md`: This reference document mapping repository files to their purpose.
- `docs/REPO_REVIEW.md`: Comprehensive repository review identifying bugs, refactoring opportunities, and capability assessment against intended use-case.
- `docs/TechnicalSpecification.md`: Architectural design, statistical methods, and performance constraints.
- `docs/UserRequirements.md`: Personas, functional requirements, and experience goals for the analytics platform.

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
- `backend/relat_ai/api/routes/health.py`: Health check endpoint used for uptime monitoring.
- `backend/relat_ai/core/__init__.py`: Re-exports configuration primitives.
- `backend/relat_ai/core/config.py`: Pydantic settings model sourcing environment configuration (upload size, profiling sample size, storage paths).
- `backend/relat_ai/core/models.py`: Shared domain models for dataset metadata, profiling payloads, and analysis requests.
- `backend/relat_ai/services/__init__.py`: Aggregates service layer modules.
- `backend/relat_ai/services/ingestion.py`: Streaming upload persistence, dataset registry management, and dataframe loaders.
- `backend/relat_ai/services/schema_detection.py`: Dataset and column profiling utilities with logical type inference and statistics extraction.
- `backend/relat_ai/services/analysis/__init__.py`: Public interface for statistical pipelines.
- `backend/relat_ai/services/analysis/pairwise.py`: Pairwise correlation computations (Pearson, Spearman, Kendall).
- `backend/relat_ai/services/analysis/multivariate.py`: Regression-based multivariate modeling helpers.
- `backend/relat_ai/services/analysis/utils.py`: Data structures for correlation and model outputs.
- `backend/relat_ai/services/summarization.py`: Placeholder LLM summarization service for analysis results.
- `backend/relat_ai/services/visualization.py`: Heatmap metadata factory for frontend visualizations.
- `backend/relat_ai/utils/__init__.py`: Utility package exports for caching and parallelism helpers.
- `backend/relat_ai/utils/caching.py`: Cache interface, in-memory implementation, and decorator utility.
- `backend/relat_ai/utils/parallel.py`: Chunking and thread pool execution helpers for workload parallelism.
- `backend/relat_ai/tests/__init__.py`: Test suite package initialization.
- `backend/relat_ai/tests/conftest.py`: Shared pytest fixtures including FastAPI test client setup.
- `backend/relat_ai/tests/unit/__init__.py`: Unit test namespace marker.
- `backend/relat_ai/tests/unit/test_health.py`: Validates health and configuration endpoints of the API.
- `backend/relat_ai/tests/unit/test_ingestion.py`: Verifies upload persistence behaviors, size enforcement, and loader support for multiple formats.
- `backend/relat_ai/tests/unit/test_schema_detection.py`: Exercises profiling heuristics and serialization to API models.
- `backend/relat_ai/tests/integration/test_datasets_api.py`: Integration coverage for dataset upload and retrieval endpoints.
- `backend/relat_ai/tests/integration/__init__.py`: Integration test namespace marker.
- `backend/scripts/benchmark.py`: CLI utility to benchmark correlation throughput on datasets.

## Frontend (`frontend/`)
- `frontend/streamlit_app/app.py`: Streamlit prototype entrypoint accepting uploads and previewing workflow messaging.
- `frontend/streamlit_app/components/__init__.py`: Placeholder package for reusable Streamlit components.
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
