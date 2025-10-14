"""Dataset ingestion helpers for RelatAI."""

from __future__ import annotations

import hashlib
import logging
import time
from collections import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import BinaryIO

import pandas as pd

from relat_ai.core.config import get_settings
from relat_ai.core.exceptions import DatasetRegistryPersistenceError
from relat_ai.core.models import DatasetMetadata, DatasetUploadResponse
from relat_ai.services import schema_detection
from relat_ai.services.configuration import initialise_configuration
from relat_ai.services.audit_trail import (
    initialise_audit_log,
    record_preprocessing_action,
)
from relat_ai.services.preprocessing import PreprocessingConfig, preprocess_frame
from relat_ai.services.registry_state import (
    RegistryStateEntry,
    load_registry_state,
    save_registry_state,
)

SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx"}
WRITE_CHUNK_SIZE = 1024 * 1024
PERSISTENCE_RETRY_DELAYS = (0.0, 0.1, 0.3)


@dataclass(slots=True)
class DatasetRecord:
    """Represents persisted dataset metadata and associated profile."""

    metadata: DatasetMetadata
    profile: schema_detection.DatasetProfile


class DatasetRegistry:
    """Thread-safe registry of uploaded datasets with persistence support."""

    def __init__(self, *, max_items: int | None = None, state_path: Path | None = None) -> None:
        self._items: OrderedDict[str, DatasetRecord] = OrderedDict()
        self._lock = RLock()
        self._max_items = max_items
        self._state_path = state_path
        self._logger = logging.getLogger(__name__)
        self._dirty = False
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
            if self._evict_if_needed_locked():
                self._dirty = True
            self._dirty = True
            self._persist_state_locked()

    def get(self, dataset_id: str) -> DatasetRecord | None:
        """Return a dataset record if it exists."""

        with self._lock:
            record = self._items.get(dataset_id)
            if record is None:
                return None
            # Maintain LRU semantics by moving the record to the end.
            self._items.move_to_end(dataset_id)
            return record

    def remove(self, dataset_id: str) -> None:
        """Remove a dataset from the registry if it exists."""

        with self._lock:
            record = self._items.pop(dataset_id, None)
            if record is None:
                return
            self._cleanup_record(record)
            self._dirty = True
            self._persist_state_locked()

    def clear(self) -> None:
        """Remove all dataset records (primarily for testing)."""

        with self._lock:
            if not self._items:
                return
            for record in self._items.values():
                self._cleanup_record(record)
            self._items.clear()
            self._dirty = True
            self._persist_state_locked()

    def _evict_if_needed_locked(self) -> bool:
        if self._max_items is None:
            return False

        evicted = False
        while len(self._items) > self._max_items:
            dataset_id, record = self._items.popitem(last=False)
            self._logger.info(
                "Evicting dataset '%s' to enforce registry capacity", dataset_id
            )
            self._cleanup_record(record)
            evicted = True
        return evicted

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
        if self._state_path is None or not self._dirty:
            return

        entries = [
            RegistryStateEntry(metadata=record.metadata, profile=record.profile)
            for record in self._items.values()
        ]
        for delay in PERSISTENCE_RETRY_DELAYS:
            if save_registry_state(self._state_path, entries, logger=self._logger):
                self._dirty = False
                return
            if delay:
                time.sleep(delay)

        message = (
            "Failed to persist dataset registry state after %s attempts"
            % len(PERSISTENCE_RETRY_DELAYS)
        )
        self._logger.error(message)
        raise DatasetRegistryPersistenceError(message)

    def _restore_state(self) -> None:
        if self._state_path is None:
            return

        entries = load_registry_state(self._state_path, logger=self._logger)
        for entry in entries:
            self._items[entry.metadata.dataset_id] = DatasetRecord(
                metadata=entry.metadata,
                profile=entry.profile,
            )

        if self._evict_if_needed_locked():
            self._dirty = True
            self._persist_state_locked()


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


def save_upload(
    file_obj: BinaryIO,
    filename: str,
    *,
    content_type: str | None = None,
) -> DatasetUploadResponse:
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

    dataset_hash = _hash_file(target_path)

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

    initialise_audit_log(
        dataset_id=dataset_metadata.dataset_id,
        dataset_name=dataset_metadata.original_filename or dataset_metadata.name,
        dataset_hash=dataset_hash,
        row_count=dataset_metadata.row_count,
        column_count=dataset_metadata.column_count,
    )
    record_preprocessing_action(
        dataset_metadata.dataset_id,
        action_type="dataset_ingested",
        details={
            "row_count": dataset_metadata.row_count,
            "column_count": dataset_metadata.column_count,
            "file_size_bytes": bytes_written,
            "content_type": dataset_metadata.content_type,
        },
    )

    preprocessing_config = PreprocessingConfig.from_settings(settings)
    processed_frame = preprocess_frame(
        frame,
        dataset_id=dataset_metadata.dataset_id,
        config=preprocessing_config,
    )

    dataset_metadata.row_count = len(processed_frame.index)
    dataset_metadata.column_count = len(processed_frame.columns)

    profile = schema_detection.profile_frame(
        processed_frame,
        dataset_id=dataset_metadata.dataset_id,
        sample_size=settings.profile_sample_size,
        dataset_name=dataset_metadata.original_filename or dataset_metadata.name,
    )

    initialise_configuration(dataset_metadata.dataset_id, profile)

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


def _hash_file(path: Path, *, chunk_size: int = 8192) -> str:
    """Return the SHA-256 hash for a file on disk."""

    digest = hashlib.sha256()
    with path.open("rb") as buffer:
        for chunk in iter(lambda: buffer.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
