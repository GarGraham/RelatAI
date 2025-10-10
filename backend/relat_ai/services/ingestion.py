"""Dataset ingestion helpers for RelatAI."""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from typing import Any, BinaryIO, Iterator

import pandas as pd

from relat_ai.core.config import get_settings
from relat_ai.core.models import DatasetMetadata, DatasetUploadResponse
from relat_ai.services import schema_detection


SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx"}
WRITE_CHUNK_SIZE = 1024 * 1024


@dataclass(slots=True)
class DatasetRecord:
    """Represents persisted dataset metadata and associated profile."""

    metadata: DatasetMetadata
    profile: schema_detection.DatasetProfile


class DatasetRegistry:
    """Thread-safe registry of uploaded datasets with persistence support."""

    def __init__(self, *, max_items: int | None = None, state_path: Path | None = None) -> None:
        self._items: "OrderedDict[str, DatasetRecord]" = OrderedDict()
        self._lock = RLock()
        self._max_items = max_items
        self._state_path = state_path
        self._logger = logging.getLogger(__name__)
        if self._state_path is not None:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._restore_state()

    def add(self, record: DatasetRecord) -> None:
        """Register a dataset record."""

        with self._lock:
            dataset_id = record.metadata.dataset_id
            if dataset_id in self._items:
                self._items.pop(dataset_id)
            self._items[dataset_id] = record
            self._evict_if_needed_locked()
            self._persist_state_locked()

    def get(self, dataset_id: str) -> DatasetRecord | None:
        """Return a dataset record if it exists."""

        with self._lock:
            record = self._items.get(dataset_id)
            if record is None:
                return None
            # Maintain LRU semantics by moving the record to the end.
            self._items.move_to_end(dataset_id)
            self._persist_state_locked()
            return record

    def remove(self, dataset_id: str) -> None:
        """Remove a dataset from the registry if it exists."""

        with self._lock:
            record = self._items.pop(dataset_id, None)
            if record is None:
                return
            self._cleanup_record(record)
            self._persist_state_locked()

    def clear(self) -> None:
        """Remove all dataset records (primarily for testing)."""

        with self._lock:
            for record in self._items.values():
                self._cleanup_record(record)
            self._items.clear()
            self._persist_state_locked()

    def _evict_if_needed_locked(self) -> None:
        if self._max_items is None:
            return

        while len(self._items) > self._max_items:
            dataset_id, record = self._items.popitem(last=False)
            self._logger.info(
                "Evicting dataset '%s' to enforce registry capacity", dataset_id
            )
            self._cleanup_record(record)

    def _cleanup_record(self, record: DatasetRecord) -> None:
        try:
            record.metadata.path.unlink(missing_ok=True)
        except OSError as exc:
            self._logger.warning(
                "Failed to remove dataset file '%s': %s",
                record.metadata.path,
                exc,
            )

    def _persist_state_locked(self) -> None:
        if self._state_path is None:
            return

        state = [
            {
                "metadata": self._serialize_metadata(record.metadata),
                "profile": self._serialize_profile(record.profile),
            }
            for record in self._items.values()
        ]

        try:
            self._state_path.write_text(json.dumps(state), encoding="utf-8")
        except OSError as exc:
            self._logger.warning("Unable to persist dataset registry: %s", exc)

    def _restore_state(self) -> None:
        if not self._state_path.exists():
            return

        try:
            raw = self._state_path.read_text(encoding="utf-8")
            entries = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            self._logger.warning("Failed to restore dataset registry: %s", exc)
            return

        for entry in entries:
            try:
                metadata_dict = entry.get("metadata", {})
                profile_dict = entry.get("profile", {})
                path_value = metadata_dict.get("path")
                if path_value is None:
                    self._logger.warning(
                        "Skipping dataset restoration with missing path information: %s",
                        metadata_dict,
                    )
                    continue
                metadata_dict["path"] = Path(path_value)
                metadata = DatasetMetadata(**metadata_dict)
                if not metadata.path.exists():
                    self._logger.warning(
                        "Skipping dataset '%s' during registry restoration because path '%s' is missing",
                        metadata.dataset_id,
                        metadata.path,
                    )
                    continue
                profile = self._deserialize_profile(profile_dict)
            except Exception as exc:  # pragma: no cover - defensive path
                self._logger.warning("Skipping invalid dataset registry entry: %s", exc)
                continue

            self._items[metadata.dataset_id] = DatasetRecord(metadata=metadata, profile=profile)

        self._evict_if_needed_locked()
        self._persist_state_locked()

    def _serialize_metadata(self, metadata: DatasetMetadata) -> dict[str, Any]:
        data = metadata.model_dump(mode="json", exclude_none=True)
        data["path"] = str(metadata.path)
        return data

    def _serialize_profile(
        self, profile: schema_detection.DatasetProfile
    ) -> dict[str, Any]:
        payload = asdict(profile)
        payload["columns"] = [asdict(column) for column in profile.columns]
        return payload

    def _deserialize_profile(self, payload: dict[str, Any]) -> schema_detection.DatasetProfile:
        columns = [schema_detection.ColumnProfile(**column) for column in payload.get("columns", [])]
        return schema_detection.DatasetProfile(
            dataset_id=payload.get("dataset_id", ""),
            name=payload.get("name", ""),
            row_count=int(payload.get("row_count", 0)),
            column_count=int(payload.get("column_count", 0)),
            missing_cell_count=int(payload.get("missing_cell_count", 0)),
            memory_usage_bytes=int(payload.get("memory_usage_bytes", 0)),
            columns=columns,
        )


_REGISTRY: DatasetRegistry | None = None


def _create_registry() -> DatasetRegistry:
    settings = get_settings()
    max_items = settings.dataset_registry_max_items
    if max_items is not None and max_items <= 0:
        max_items = None

    return DatasetRegistry(
        max_items=max_items,
        state_path=settings.dataset_registry_state_path,
    )


def get_registry() -> DatasetRegistry:
    """Return the global dataset registry instance."""

    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _create_registry()
    return _REGISTRY


def register_dataset(record: DatasetRecord) -> None:
    """Register a dataset with the global registry."""

    get_registry().add(record)


def reset_registry() -> None:
    """Clear and reinitialise the global dataset registry."""

    global _REGISTRY
    if _REGISTRY is not None:
        _REGISTRY.clear()
    _REGISTRY = None


def get_dataset(dataset_id: str) -> DatasetUploadResponse | None:
    """Retrieve a dataset response from the registry if it exists."""

    record = get_registry().get(dataset_id)
    if record is None:
        return None
    return _build_response(record)


def save_upload(file_obj: BinaryIO, filename: str, *, content_type: str | None = None) -> DatasetUploadResponse:
    """Persist an uploaded dataset, profile it, and return metadata and profile."""

    sanitized_name = Path(filename).name
    suffix = Path(sanitized_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    settings = get_settings()
    destination_dir = Path(settings.temp_storage_path)
    destination_dir.mkdir(parents=True, exist_ok=True)

    dataset_metadata = DatasetMetadata(name=sanitized_name, path=destination_dir)
    stored_name = f"{dataset_metadata.dataset_id}{suffix}"
    target_path = destination_dir / stored_name

    file_obj.seek(0)
    bytes_written = _write_stream(file_obj, target_path, settings.max_upload_size_bytes)

    try:
        frame = load_frame(target_path)
    except Exception:
        target_path.unlink(missing_ok=True)
        raise
    dataset_metadata.path = target_path
    dataset_metadata.original_filename = sanitized_name
    dataset_metadata.content_type = content_type
    dataset_metadata.file_size_bytes = bytes_written
    dataset_metadata.name = stored_name
    dataset_metadata.row_count = len(frame.index)
    dataset_metadata.column_count = len(frame.columns)

    profile = schema_detection.profile_frame(
        frame,
        dataset_id=dataset_metadata.dataset_id,
        sample_size=settings.profile_sample_size,
        dataset_name=dataset_metadata.original_filename or dataset_metadata.name,
    )

    record = DatasetRecord(metadata=dataset_metadata, profile=profile)
    register_dataset(record)

    return _build_response(record)


def load_frame(path: Path) -> pd.DataFrame:
    """Load a Pandas DataFrame from the supported file types."""

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".csv":
        return _read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    return _read_excel(path)


def _build_response(record: DatasetRecord) -> DatasetUploadResponse:
    """Convert a dataset record into an API response payload."""

    return DatasetUploadResponse(
        metadata=record.metadata,
        profile=schema_detection.to_model(record.profile),
    )


def _read_csv(path: Path) -> pd.DataFrame:
    """Attempt to read a CSV file with sensible fallbacks for encoding."""

    try:
        return pd.read_csv(path)
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="latin-1")


def _read_excel(path: Path) -> pd.DataFrame:
    """Read an Excel workbook using openpyxl when available."""

    try:
        return pd.read_excel(path, engine="openpyxl")
    except ImportError as exc:
        raise ValueError("Excel support requires the 'openpyxl' dependency") from exc


def _write_stream(source: BinaryIO, destination: Path, max_bytes: int) -> int:
    """Write a binary stream to disk enforcing the configured size limit."""

    total = 0
    with destination.open("wb") as buffer:
        for chunk in _iter_chunks(source):
            total += len(chunk)
            if total > max_bytes:
                destination.unlink(missing_ok=True)
                raise ValueError("Upload exceeds configured size limit")
            buffer.write(chunk)
    return total


def _iter_chunks(source: BinaryIO) -> Iterator[bytes]:
    """Yield chunks from a binary stream for incremental writes."""

    while True:
        chunk = source.read(WRITE_CHUNK_SIZE)
        if not chunk:
            break
        yield chunk
