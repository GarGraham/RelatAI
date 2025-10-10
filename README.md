# RelatAI

RelatAI is a self-service analytics platform that highlights correlations and multivariate
relationships in tabular datasets. This repository contains the backend services, frontend
prototypes, infrastructure assets, and documentation required to deliver the experience.

## Getting Started

1. Create a Python 3.11 virtual environment.
2. Install backend dependencies:
   ```bash
   make install
   ```
3. Install development tooling (linters, formatters, tests):
   ```bash
   make install-dev
   ```
4. Launch the backend API:
   ```bash
   make run-backend
   ```
5. Open the Streamlit prototype:
   ```bash
   streamlit run frontend/streamlit_app/app.py
   ```

## Tooling

- **Formatting**: Black (configured via `pyproject.toml`).
- **Linting**: Ruff for Python code quality checks.
- **Type Checking**: Mypy running in strict mode.
- **Testing**: Pytest with sample health endpoint coverage.
- **Containers**: Dockerfiles for backend and frontend with a docker-compose definition under `infrastructure/`.

## Repository Layout

See `docs/Reference-Guide.md` for file-by-file documentation and ownership details.
