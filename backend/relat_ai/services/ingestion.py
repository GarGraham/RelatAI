"""Dataset ingestion helpers for RelatAI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import BinaryIO, Iterator

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
    """Thread-safe in-memory registry of uploaded datasets."""

    def __init__(self) -> None:
        self._items: dict[str, DatasetRecord] = {}
        self._lock = RLock()

    def add(self, record: DatasetRecord) -> None:
        """Register a dataset record."""

        with self._lock:
            self._items[record.metadata.dataset_id] = record

    def get(self, dataset_id: str) -> DatasetRecord | None:
        """Return a dataset record if it exists."""

        with self._lock:
            return self._items.get(dataset_id)

    def clear(self) -> None:
        """Remove all dataset records (primarily for testing)."""

        with self._lock:
            self._items.clear()


_REGISTRY = DatasetRegistry()


def get_registry() -> DatasetRegistry:
    """Return the global dataset registry instance."""

    return _REGISTRY


def register_dataset(record: DatasetRecord) -> None:
    """Register a dataset with the global registry."""

    _REGISTRY.add(record)


def reset_registry() -> None:
    """Clear the global dataset registry."""

    _REGISTRY.clear()


def get_dataset(dataset_id: str) -> DatasetUploadResponse | None:
    """Retrieve a dataset response from the registry if it exists."""

    record = _REGISTRY.get(dataset_id)
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

    frame = load_frame(target_path)
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
