# RelatAI Backend

This package hosts the FastAPI backend for the RelatAI platform. It provides data ingestion,
schema detection, statistical analysis, visualization metadata generation, and AI summarization
services that power the analyst experience.

## Getting Started

1. Create and activate a Python 3.11 virtual environment.
2. Install runtime dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. For development tooling (formatters, linters, tests), install:
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Launch the development server:
   ```bash
   uvicorn relat_ai.api.main:app --reload
   ```

## Project Layout

- `relat_ai/api`: FastAPI application entrypoint and routing modules.
- `relat_ai/core`: Core configuration management and domain models.
- `relat_ai/services`: Ingestion, schema detection, statistical analysis, summarization, and visualization logic.
- `relat_ai/utils`: Shared utilities such as caching and parallel execution helpers.
- `relat_ai/tests`: Pytest-based test suites for unit and integration coverage.
- `scripts/`: Operational scripts such as performance benchmarking harnesses.
