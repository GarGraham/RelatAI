"""Tests covering dataset ingestion workflows."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from relat_ai.core.exceptions import DatasetRegistryPersistenceError
from relat_ai.services import ingestion


def test_save_upload_persists_metadata(settings):
    """Saving an upload should persist metadata and return a profile response."""

    csv_content = "a,b\n1,2\n3,4\n"
    response = ingestion.save_upload(BytesIO(csv_content.encode("utf-8")), "sample.csv")

    assert response.metadata.original_filename == "sample.csv"
    assert response.metadata.file_size_bytes == len(csv_content.encode("utf-8"))
    assert response.metadata.row_count == 2
    assert response.profile.row_count == 2
    column_names = [column.name for column in response.profile.columns]
    assert column_names == ["a", "b"]


def test_save_upload_respects_size_limit(settings):
    """Uploads exceeding the configured size limit should raise an error."""

    settings.max_upload_size_mb = 0
    with pytest.raises(ValueError, match="size limit"):
        ingestion.save_upload(BytesIO(b"0" * 2048), "too_large.csv")


def test_save_upload_cleans_up_on_load_failure(settings, monkeypatch):
    """Temporary files should be removed if frame loading fails."""

    captured_path: Path | None = None

    def _fail_load(path: Path) -> pd.DataFrame:  # pragma: no cover - type stub
        nonlocal captured_path
        captured_path = path
        raise ValueError("boom")

    monkeypatch.setattr(ingestion, "load_frame", _fail_load)

    with pytest.raises(ValueError, match="boom"):
        ingestion.save_upload(BytesIO(b"value\n1"), "broken.csv")

    assert captured_path is not None
    assert not captured_path.exists()


def test_load_frame_supports_multiple_formats(tmp_path):
    """Loading frames should support CSV and Parquet formats."""

    csv_path = tmp_path / "example.csv"
    csv_path.write_text("c\n1\n2\n", encoding="utf-8")
    csv_frame = ingestion.load_frame(csv_path)
    assert list(csv_frame.columns) == ["c"]

    frame = pd.DataFrame({"value": [1, 2, 3]})
    parquet_path = tmp_path / "example.parquet"
    try:
        frame.to_parquet(parquet_path)
    except ImportError:  # pragma: no cover - optional dependency guard
        pytest.skip("pyarrow is required for parquet support")
    parquet_frame = ingestion.load_frame(parquet_path)
    assert parquet_frame["value"].tolist() == [1, 2, 3]


def test_load_frame_rejects_unsupported_extension(tmp_path):
    """Unsupported formats should raise a ValueError."""

    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("content")

    with pytest.raises(ValueError, match="Unsupported"):
        ingestion.load_frame(txt_path)


def test_save_upload_raises_when_registry_write_fails(
    settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dataset uploads should surface persistence failures to the caller."""

    monkeypatch.setattr(ingestion, "save_registry_state", lambda *args, **kwargs: False)

    with pytest.raises(DatasetRegistryPersistenceError):
        ingestion.save_upload(BytesIO(b"a,b\n1,2"), "failing.csv")
