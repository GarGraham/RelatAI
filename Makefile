.PHONY: install install-dev format lint test type-check run-backend

PYTHON?=python3
PIP?=pip3
BACKEND_DIR=backend

install:
$(PIP) install -r $(BACKEND_DIR)/requirements.txt

install-dev:
$(PIP) install -r $(BACKEND_DIR)/requirements-dev.txt

format:
$(PYTHON) -m black $(BACKEND_DIR)/relat_ai

lint:
ruff check $(BACKEND_DIR)/relat_ai

lint-fix:
ruff check --fix $(BACKEND_DIR)/relat_ai
ruff format $(BACKEND_DIR)/relat_ai

test:
pytest $(BACKEND_DIR)/relat_ai/tests

type-check:
mypy $(BACKEND_DIR)/relat_ai

run-backend:
uvicorn relat_ai.api.main:app --reload
