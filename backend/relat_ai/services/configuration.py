"""Configuration management and filtering utilities for analysis workflows."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Iterable

import pandas as pd

from relat_ai.core.models import (
    ConfigurationUpdateRequest,
    DatasetConfiguration,
)
from relat_ai.services import schema_detection


def _normalise(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


@dataclass(slots=True)
class _ConfigurationStore:
    """Thread-safe storage for dataset configurations."""

    _items: dict[str, DatasetConfiguration]
    _lock: RLock

    def __init__(self) -> None:
        self._items = {}
        self._lock = RLock()

    def get(self, dataset_id: str) -> DatasetConfiguration | None:
        with self._lock:
            configuration = self._items.get(dataset_id)
            if configuration is None:
                return None
            return configuration.model_copy(deep=True)

    def set(self, configuration: DatasetConfiguration) -> DatasetConfiguration:
        with self._lock:
            self._items[configuration.dataset_id] = configuration.model_copy(deep=True)
            return configuration

    def ensure(self, configuration: DatasetConfiguration) -> DatasetConfiguration:
        with self._lock:
            existing = self._items.get(configuration.dataset_id)
            if existing is None:
                self._items[configuration.dataset_id] = configuration.model_copy(deep=True)
                return configuration
            return existing.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


_STORE = _ConfigurationStore()


def reset_store() -> None:
    """Reset the in-memory configuration store (primarily for tests)."""

    _STORE.clear()


def initialise_configuration(
    dataset_id: str, profile: schema_detection.DatasetProfile
) -> DatasetConfiguration:
    """Ensure a dataset has a default configuration seeded from its profile."""

    selected_columns = [column.name for column in profile.columns]
    configuration = DatasetConfiguration(dataset_id=dataset_id, selected_columns=selected_columns)
    return _STORE.ensure(configuration)


def get_configuration(dataset_id: str) -> DatasetConfiguration | None:
    """Return the stored configuration for ``dataset_id`` if available."""

    return _STORE.get(dataset_id)


def _available_columns(profile: schema_detection.DatasetProfile) -> set[str]:
    return {column.name for column in profile.columns}


def _validate_columns(values: Iterable[str], available: set[str], *, label: str) -> None:
    missing = set(values) - available
    if missing:
        raise ValueError(f"{label} reference unknown columns: {sorted(missing)!r}")


def _validate_filters(
    filters: dict[str, list[object]], available: set[str]
) -> dict[str, list[object]]:
    validated: dict[str, list[object]] = {}
    for column, values in filters.items():
        if column not in available:
            raise ValueError(f"Filter references unknown column: '{column}'")
        if not isinstance(values, list):
            raise TypeError("Filter values must be lists")
        if not values:
            continue
        seen: set[object] = set()
        deduped: list[object] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        validated[column] = deduped
    return validated


def _validate_numeric(value: int | None, *, field: str) -> int | None:
    if value is None:
        return None
    if value < 1:
        raise ValueError(f"{field} must be at least 1")
    return value


def update_configuration(
    dataset_id: str,
    update: ConfigurationUpdateRequest,
    profile: schema_detection.DatasetProfile,
) -> DatasetConfiguration:
    """Apply a partial update to the dataset configuration."""

    configuration = get_configuration(dataset_id)
    if configuration is None:
        configuration = initialise_configuration(dataset_id, profile)
    else:
        configuration = configuration.model_copy(deep=True)

    available = _available_columns(profile)

    if update.selected_columns is not None:
        if not update.selected_columns:
            raise ValueError("selected_columns must contain at least one column")
        _validate_columns(update.selected_columns, available, label="selected_columns")
        configuration.selected_columns = _normalise(update.selected_columns)
        configuration.anchor_columns = [
            anchor for anchor in configuration.anchor_columns if anchor in configuration.selected_columns
        ]
        if configuration.max_variables > len(configuration.selected_columns):
            configuration.max_variables = len(configuration.selected_columns)

    if update.analysis_mode is not None:
        configuration.analysis_mode = update.analysis_mode

    if update.max_variables is not None:
        max_variables = _validate_numeric(update.max_variables, field="max_variables")
        if max_variables and configuration.selected_columns:
            if max_variables > len(configuration.selected_columns):
                raise ValueError("max_variables cannot exceed selected_columns length")
        if max_variables is not None:
            configuration.max_variables = max_variables

    if update.interaction_depth is not None:
        interaction_depth = _validate_numeric(update.interaction_depth, field="interaction_depth")
        if interaction_depth is not None:
            configuration.interaction_depth = interaction_depth

    if update.include_interactions is not None:
        configuration.include_interactions = update.include_interactions

    if update.anchor_columns is not None:
        _validate_columns(update.anchor_columns, available, label="anchor_columns")
        anchors = _normalise(update.anchor_columns)
        missing = set(anchors) - set(configuration.selected_columns)
        if missing:
            raise ValueError("Anchor columns must also be selected")
        configuration.anchor_columns = anchors

    if update.filters is not None:
        validated_filters = _validate_filters(update.filters, available)
        for column in list(configuration.filters.keys()):
            if column not in validated_filters and column in update.filters:
                configuration.filters.pop(column, None)
        for column, values in validated_filters.items():
            configuration.filters[column] = values
        # Allow clearing all filters when an empty mapping is provided
        if not update.filters:
            configuration.filters = {}

    configuration = DatasetConfiguration.model_validate(configuration.model_dump())
    return _STORE.set(configuration)


def normalise_configuration(
    dataset_id: str,
    configuration: DatasetConfiguration,
    profile: schema_detection.DatasetProfile,
) -> DatasetConfiguration:
    """Return a validated configuration aligned with the dataset profile."""

    copy = configuration.model_copy(deep=True)
    copy.dataset_id = dataset_id
    available = _available_columns(profile)
    if not copy.selected_columns:
        raise ValueError("Configuration must select at least one column")
    _validate_columns(copy.selected_columns, available, label="selected_columns")
    _validate_columns(copy.anchor_columns, available, label="anchor_columns")
    missing_anchors = set(copy.anchor_columns) - set(copy.selected_columns)
    if missing_anchors:
        raise ValueError("Anchor columns must also be selected")

    if copy.max_variables > len(copy.selected_columns):
        raise ValueError("max_variables cannot exceed selected_columns length")
    if copy.max_variables < 1:
        raise ValueError("max_variables must be at least 1")
    if copy.interaction_depth < 1:
        raise ValueError("interaction_depth must be at least 1")

    copy.filters = _validate_filters(copy.filters, available)
    return DatasetConfiguration.model_validate(copy.model_dump())


def replace_configuration(
    dataset_id: str,
    configuration: DatasetConfiguration,
    profile: schema_detection.DatasetProfile,
) -> DatasetConfiguration:
    """Replace the stored configuration for a dataset after validation."""

    validated = normalise_configuration(dataset_id, configuration, profile)
    return _STORE.set(validated)


def apply_configuration_to_frame(
    frame: pd.DataFrame, configuration: DatasetConfiguration
) -> pd.DataFrame:
    """Return a filtered view of ``frame`` according to ``configuration``."""

    filtered = frame
    if configuration.filters:
        mask = pd.Series(True, index=frame.index)
        for column, values in configuration.filters.items():
            if column not in frame.columns:
                raise ValueError(f"Filter references unknown column: '{column}'")
            mask &= frame[column].isin(values)
        filtered = frame.loc[mask]

    if configuration.selected_columns:
        missing = set(configuration.selected_columns) - set(filtered.columns)
        if missing:
            raise ValueError(f"Selected columns missing from frame: {sorted(missing)!r}")
        filtered = filtered.loc[:, configuration.selected_columns]

    return filtered.copy()

