"""Dataset ingestion helpers for RelatAI."""

from pathlib import Path
from typing import BinaryIO

import pandas as pd

from relat_ai.core.models import DatasetMetadata
from relat_ai.core.config import get_settings


SUPPORTED_EXTENSIONS = {".csv", ".parquet", ".xlsx"}


def save_upload(file_obj: BinaryIO, filename: str) -> DatasetMetadata:
    """Persist an uploaded dataset to temporary storage and return metadata."""

    settings = get_settings()
    destination_dir = Path(settings.temp_storage_path)
    destination_dir.mkdir(parents=True, exist_ok=True)

    target_path = destination_dir / filename
    with target_path.open("wb") as buffer:
        buffer.write(file_obj.read())

    frame = load_frame(target_path)
    return DatasetMetadata(
        name=filename,
        path=target_path,
        row_count=len(frame.index),
        column_count=len(frame.columns),
    )


def load_frame(path: Path) -> pd.DataFrame:
    """Load a Pandas DataFrame from the supported file types."""

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_excel(path)
