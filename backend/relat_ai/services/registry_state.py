"""Persistence helpers for :mod:`relat_ai.services.ingestion`."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from relat_ai.core.models import DatasetMetadata
from relat_ai.services import schema_detection


@dataclass(slots=True)
class RegistryStateEntry:
    """Represents a single persisted dataset registry entry."""

    metadata: DatasetMetadata
    profile: schema_detection.DatasetProfile


def load_registry_state(
    path: Path, *, logger: logging.Logger | None = None
) -> list[RegistryStateEntry]:
    """Load registry entries from *path* with defensive error handling."""

    if not path.exists():
        return []

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        if logger:
            logger.warning("Unable to read dataset registry state: %s", exc)
        return []

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        if logger:
            logger.warning("Invalid dataset registry state JSON: %s", exc)
        return []

    entries: list[RegistryStateEntry] = []
    for entry in payload:
        metadata_dict = entry.get("metadata") if isinstance(entry, dict) else None
        profile_dict = entry.get("profile") if isinstance(entry, dict) else None
        if not isinstance(metadata_dict, dict) or not isinstance(profile_dict, dict):
            if logger:
                logger.warning("Skipping malformed dataset registry entry: %s", entry)
            continue

        path_value = metadata_dict.get("path")
        if not path_value:
            if logger:
                logger.warning(
                    "Skipping dataset restoration with missing path information: %s",
                    metadata_dict,
                )
            continue

        metadata_dict = dict(metadata_dict)
        metadata_dict["path"] = Path(path_value)

        try:
            metadata = DatasetMetadata(**metadata_dict)
        except (ValidationError, TypeError, ValueError) as exc:
            if logger:
                logger.warning("Skipping dataset with invalid metadata: %s", exc)
            continue

        if not metadata.path.exists():
            if logger:
                logger.warning(
                    "Skipping dataset '%s' because path '%s' is missing",
                    metadata.dataset_id,
                    metadata.path,
                )
            continue

        try:
            profile = _deserialize_profile(profile_dict)
        except (TypeError, ValueError, KeyError) as exc:
            if logger:
                logger.warning("Skipping dataset with invalid profile: %s", exc)
            continue

        entries.append(RegistryStateEntry(metadata=metadata, profile=profile))

    return entries


def save_registry_state(
    path: Path,
    entries: Sequence[RegistryStateEntry],
    *,
    logger: logging.Logger | None = None,
) -> bool:
    """Persist *entries* to *path* with basic error handling.

    Returns ``True`` when the payload was successfully written and ``False`` when
    an :class:`OSError` prevented persistence.  Callers can use the boolean
    return value to decide whether to retry or surface an error to clients.
    """

    serialised = [
        {
            "metadata": _serialize_metadata(entry.metadata),
            "profile": _serialize_profile(entry.profile),
        }
        for entry in entries
    ]

    try:
        path.write_text(json.dumps(serialised), encoding="utf-8")
    except OSError as exc:
        if logger:
            logger.warning("Unable to persist dataset registry: %s", exc)
        return False

    return True

def _serialize_metadata(metadata: DatasetMetadata) -> dict[str, object]:
    payload = metadata.model_dump(mode="json", exclude_none=True)
    payload["path"] = str(metadata.path)
    return payload


def _serialize_profile(
    profile: schema_detection.DatasetProfile,
) -> dict[str, object]:
    return profile.model_dump()


def _deserialize_profile(
    payload: dict[str, object],
) -> schema_detection.DatasetProfile:
    columns = [
        schema_detection.ColumnProfile(**column)
        for column in payload.get("columns", [])
        if isinstance(column, dict)
    ]
    return schema_detection.DatasetProfile(
        dataset_id=str(payload.get("dataset_id", "")),
        name=str(payload.get("name", "")),
        row_count=int(payload.get("row_count", 0) or 0),
        column_count=int(payload.get("column_count", 0) or 0),
        missing_cell_count=int(payload.get("missing_cell_count", 0) or 0),
        memory_usage_bytes=int(payload.get("memory_usage_bytes", 0) or 0),
        columns=columns,
    )
