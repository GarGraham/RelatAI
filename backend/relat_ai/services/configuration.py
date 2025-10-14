"""Configuration management and filtering utilities for analysis workflows."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Iterable

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
class ConfigurationVersion:
    """Historical snapshot of a dataset configuration and its field changes."""

    version: int
    configuration: DatasetConfiguration
    changed_at: datetime
    changes: dict[str, tuple[Any | None, Any | None]]


@dataclass(slots=True)
class _ConfigurationStore:
    """Thread-safe storage for dataset configurations and their history."""

    _items: dict[str, DatasetConfiguration]
    _history: dict[str, list[ConfigurationVersion]]
    _lock: RLock

    def __init__(self) -> None:
        self._items = {}
        self._history = {}
        self._lock = RLock()

    def get(self, dataset_id: str) -> DatasetConfiguration | None:
        with self._lock:
            configuration = self._items.get(dataset_id)
            if configuration is None:
                return None
            return configuration.model_copy(deep=True)

    def _record_change(
        self,
        dataset_id: str,
        previous: DatasetConfiguration | None,
        current: DatasetConfiguration,
    ) -> None:
        history = self._history.setdefault(dataset_id, [])
        previous_dump = previous.model_dump() if previous is not None else {}
        current_dump = current.model_dump()
        fields = set(previous_dump) | set(current_dump)
        changes: dict[str, tuple[Any | None, Any | None]] = {}
        for field in fields:
            before = previous_dump.get(field)
            after = current_dump.get(field)
            if before != after:
                changes[field] = (before, after)

        history.append(
            ConfigurationVersion(
                version=len(history) + 1,
                configuration=current.model_copy(deep=True),
                changed_at=datetime.now(UTC),
                changes=changes,
            )
        )

    def set(self, configuration: DatasetConfiguration) -> DatasetConfiguration:
        with self._lock:
            dataset_id = configuration.dataset_id
            previous = self._items.get(dataset_id)
            stored = configuration.model_copy(deep=True)
            self._items[dataset_id] = stored
            self._record_change(dataset_id, previous, stored)
            return configuration

    def ensure(self, configuration: DatasetConfiguration) -> DatasetConfiguration:
        with self._lock:
            dataset_id = configuration.dataset_id
            existing = self._items.get(dataset_id)
            if existing is None:
                stored = configuration.model_copy(deep=True)
                self._items[dataset_id] = stored
                self._record_change(dataset_id, None, stored)
                return stored.model_copy(deep=True)
            return existing.model_copy(deep=True)

    def list_versions(self, dataset_id: str) -> list[ConfigurationVersion]:
        with self._lock:
            history = self._history.get(dataset_id, [])
            return [
                ConfigurationVersion(
                    version=entry.version,
                    configuration=entry.configuration.model_copy(deep=True),
                    changed_at=entry.changed_at,
                    changes=deepcopy(entry.changes),
                )
                for entry in history
            ]

    def restore(self, dataset_id: str, version: int) -> DatasetConfiguration:
        with self._lock:
            history = self._history.get(dataset_id)
            if not history:
                raise KeyError(f"No configuration history for dataset '{dataset_id}'")
            target = next((entry for entry in history if entry.version == version), None)
            if target is None:
                raise KeyError(f"Version {version} not found for dataset '{dataset_id}'")

            previous = self._items.get(dataset_id)
            restored = target.configuration.model_copy(deep=True)
            self._items[dataset_id] = restored
            self._record_change(dataset_id, previous, restored)
            return restored.model_copy(deep=True)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._history.clear()


_STORE = _ConfigurationStore()


def reset_store() -> None:
    """Reset the in-memory configuration store (primarily for tests)."""

    _STORE.clear()


class ConfigurationValidator:
    """Centralised validation for dataset configurations."""

    def __init__(self, profile: schema_detection.DatasetProfile) -> None:
        self._available_columns = {column.name for column in profile.columns}

    def validate_columns(self, columns: Iterable[str], *, label: str) -> None:
        missing = set(columns) - self._available_columns
        if missing:
            raise ValueError(f"{label} reference unknown columns: {sorted(missing)!r}")

    def ensure_selected_columns(self, columns: Iterable[str]) -> list[str]:
        selected = list(columns)
        if not selected:
            raise ValueError("selected_columns must contain at least one column")
        self.validate_columns(selected, label="selected_columns")
        return _normalise(selected)

    def prune_missing_anchors(self, anchors: Iterable[str], selected: Iterable[str]) -> list[str]:
        selected_set = set(selected)
        return [anchor for anchor in _normalise(anchors) if anchor in selected_set]

    def validate_anchor_columns(self, anchors: Iterable[str], selected: Iterable[str]) -> list[str]:
        anchors_list = list(anchors)
        self.validate_columns(anchors_list, label="anchor_columns")
        normalised = _normalise(anchors_list)
        missing = set(normalised) - set(selected)
        if missing:
            raise ValueError("Anchor columns must also be selected")
        return normalised

    def validate_filters(self, filters: dict[str, list[object]]) -> dict[str, list[object]]:
        validated: dict[str, list[object]] = {}
        for column, values in filters.items():
            if column not in self._available_columns:
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

    @staticmethod
    def validate_numeric(value: int | None, *, field: str) -> int | None:
        if value is None:
            return None
        if value < 1:
            raise ValueError(f"{field} must be at least 1")
        return value

    def validate_max_variables(self, value: int | None, selected_count: int) -> int | None:
        validated = self.validate_numeric(value, field="max_variables")
        if validated is not None and selected_count and validated > selected_count:
            raise ValueError("max_variables cannot exceed selected_columns length")
        return validated

    def validate_interaction_depth(self, value: int | None) -> int | None:
        return self.validate_numeric(value, field="interaction_depth")


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

    validator = ConfigurationValidator(profile)

    if update.selected_columns is not None:
        configuration.selected_columns = validator.ensure_selected_columns(update.selected_columns)
        configuration.anchor_columns = validator.prune_missing_anchors(
            configuration.anchor_columns, configuration.selected_columns
        )
        if configuration.max_variables > len(configuration.selected_columns):
            configuration.max_variables = len(configuration.selected_columns)

    if update.analysis_mode is not None:
        configuration.analysis_mode = update.analysis_mode

    if update.max_variables is not None:
        max_variables = validator.validate_max_variables(
            update.max_variables, len(configuration.selected_columns)
        )
        if max_variables is not None:
            configuration.max_variables = max_variables

    if update.interaction_depth is not None:
        interaction_depth = validator.validate_interaction_depth(update.interaction_depth)
        if interaction_depth is not None:
            configuration.interaction_depth = interaction_depth

    if update.include_interactions is not None:
        configuration.include_interactions = update.include_interactions

    if update.anchor_columns is not None:
        configuration.anchor_columns = validator.validate_anchor_columns(
            update.anchor_columns, configuration.selected_columns
        )

    if update.filters is not None:
        if not update.filters:
            configuration.filters = {}
        else:
            validated_filters = validator.validate_filters(update.filters)
            for column in list(configuration.filters.keys()):
                if column in update.filters and column not in validated_filters:
                    configuration.filters.pop(column, None)
            configuration.filters.update(validated_filters)

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
    validator = ConfigurationValidator(profile)
    copy.selected_columns = validator.ensure_selected_columns(copy.selected_columns)
    copy.anchor_columns = validator.validate_anchor_columns(copy.anchor_columns, copy.selected_columns)
    validated_max = validator.validate_max_variables(copy.max_variables, len(copy.selected_columns))
    if validated_max is not None:
        copy.max_variables = validated_max
    validated_interaction = validator.validate_interaction_depth(copy.interaction_depth)
    if validated_interaction is not None:
        copy.interaction_depth = validated_interaction

    copy.filters = validator.validate_filters(copy.filters)
    return DatasetConfiguration.model_validate(copy.model_dump())


def replace_configuration(
    dataset_id: str,
    configuration: DatasetConfiguration,
    profile: schema_detection.DatasetProfile,
) -> DatasetConfiguration:
    """Replace the stored configuration for a dataset after validation."""

    validated = normalise_configuration(dataset_id, configuration, profile)
    return _STORE.set(validated)


def list_configuration_versions(dataset_id: str) -> list[ConfigurationVersion]:
    """Return the configuration history for ``dataset_id``."""

    return _STORE.list_versions(dataset_id)


def restore_configuration_version(dataset_id: str, version: int) -> DatasetConfiguration:
    """Restore the configuration for ``dataset_id`` to a previous ``version``."""

    return _STORE.restore(dataset_id, version)


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

