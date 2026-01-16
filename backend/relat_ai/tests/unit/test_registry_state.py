"""Unit tests for registry_state persistence helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest import mock

import pytest

from relat_ai.core.models import DatasetMetadata
from relat_ai.services.schema_detection import ColumnProfile, DatasetProfile
from relat_ai.services.registry_state import (
    RegistryStateEntry,
    load_registry_state,
    save_registry_state,
)


def _make_entry(dataset_id: str, tmp_path: Path) -> RegistryStateEntry:
    """Create a minimal RegistryStateEntry for testing."""
    csv_path = tmp_path / f"{dataset_id}.csv"
    csv_path.write_text("a,b\n1,2\n", encoding="utf-8")
    metadata = DatasetMetadata(
        dataset_id=dataset_id,
        name=f"{dataset_id}.csv",
        path=csv_path,
        size_bytes=100,
        row_count=1,
        column_count=2,
    )
    profile = DatasetProfile(
        dataset_id=dataset_id,
        name=f"{dataset_id}.csv",
        row_count=1,
        column_count=2,
        missing_cell_count=0,
        memory_usage_bytes=100,
        columns=[
            ColumnProfile(
                name="a",
                logical_type="numeric",
                pandas_dtype="int64",
                non_null_count=1,
                null_count=0,
                unique_count=1,
            ),
            ColumnProfile(
                name="b",
                logical_type="numeric",
                pandas_dtype="int64",
                non_null_count=1,
                null_count=0,
                unique_count=1,
            ),
        ],
    )
    return RegistryStateEntry(metadata=metadata, profile=profile)


class TestSaveRegistryState:
    """Tests for save_registry_state atomic write behavior."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        """save_registry_state should create the registry file."""
        registry_path = tmp_path / "registry.json"
        entry = _make_entry("ds1", tmp_path)

        result = save_registry_state(registry_path, [entry])

        assert result is True
        assert registry_path.exists()
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        assert len(payload) == 1
        assert payload[0]["metadata"]["dataset_id"] == "ds1"

    def test_save_overwrites_existing_file(self, tmp_path: Path) -> None:
        """save_registry_state should atomically replace existing content."""
        registry_path = tmp_path / "registry.json"
        registry_path.write_text('{"old": "data"}', encoding="utf-8")
        entry = _make_entry("ds2", tmp_path)

        result = save_registry_state(registry_path, [entry])

        assert result is True
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        assert "old" not in payload[0] if isinstance(payload, list) else True
        assert payload[0]["metadata"]["dataset_id"] == "ds2"

    def test_save_cleans_up_temp_on_failure(self, tmp_path: Path) -> None:
        """When os.replace fails, temp file should be removed."""
        registry_path = tmp_path / "registry.json"
        entry = _make_entry("ds3", tmp_path)

        with mock.patch("os.replace", side_effect=OSError("disk full")):
            result = save_registry_state(registry_path, [entry])

        assert result is False
        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []

    def test_save_no_partial_writes(self, tmp_path: Path) -> None:
        """Original file should remain intact if write fails."""
        registry_path = tmp_path / "registry.json"
        original_content = '[{"metadata": {"dataset_id": "original"}}]'
        registry_path.write_text(original_content, encoding="utf-8")
        entry = _make_entry("new", tmp_path)

        with mock.patch("os.replace", side_effect=OSError("disk full")):
            result = save_registry_state(registry_path, [entry])

        assert result is False
        # Original content should be untouched
        assert registry_path.read_text(encoding="utf-8") == original_content


class TestLoadRegistryState:
    """Tests for load_registry_state defensive loading."""

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        """Missing registry file should return empty list."""
        registry_path = tmp_path / "nonexistent.json"

        result = load_registry_state(registry_path)

        assert result == []

    def test_load_valid_roundtrip(self, tmp_path: Path) -> None:
        """Saved entries should be loadable."""
        registry_path = tmp_path / "registry.json"
        entry = _make_entry("roundtrip", tmp_path)
        save_registry_state(registry_path, [entry])

        loaded = load_registry_state(registry_path)

        assert len(loaded) == 1
        assert loaded[0].metadata.dataset_id == "roundtrip"
        assert loaded[0].profile.dataset_id == "roundtrip"

    def test_load_invalid_json_returns_empty(self, tmp_path: Path) -> None:
        """Invalid JSON should return empty list with warning logged."""
        registry_path = tmp_path / "registry.json"
        registry_path.write_text("not valid json {{{", encoding="utf-8")
        logger = mock.Mock()

        result = load_registry_state(registry_path, logger=logger)

        assert result == []
        assert logger.warning.called
