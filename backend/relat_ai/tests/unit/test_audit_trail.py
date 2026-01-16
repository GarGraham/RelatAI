"""Unit tests for SQLite-backed audit trail persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from relat_ai.services.audit_trail import (
    AuditTrailStore,
    get_audit_log,
    initialise_audit_log,
    list_audit_logs,
    record_preprocessing_action,
    reset_audit_trail,
    set_audit_db_path,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    """Configure audit trail to use a temp database for tests."""
    db_path = tmp_path / "test_audit.db"
    set_audit_db_path(db_path)
    reset_audit_trail()
    yield db_path
    reset_audit_trail()
    set_audit_db_path(None)


class TestAuditTrailStore:
    """Tests for AuditTrailStore SQLite persistence."""

    def test_store_creates_database_file(self, tmp_path: Path) -> None:
        """Store should create the SQLite database file."""
        db_path = tmp_path / "audit.db"
        store = AuditTrailStore(db_path=db_path)

        assert db_path.exists()

    def test_initialise_log_persists_to_db(self, tmp_path: Path) -> None:
        """Initialised log should be retrievable after store recreation."""
        db_path = tmp_path / "audit.db"

        # Create and populate store
        store1 = AuditTrailStore(db_path=db_path)
        store1.initialise_log(
            dataset_id="ds1",
            dataset_name="test.csv",
            dataset_hash="abc123",
            row_count=100,
            column_count=5,
        )

        # Create new store instance (simulates server restart)
        store2 = AuditTrailStore(db_path=db_path)
        log = store2.get("ds1")

        assert log is not None
        assert log.dataset_id == "ds1"
        assert log.dataset_name == "test.csv"
        assert log.dataset_hash == "abc123"
        assert log.row_count == 100
        assert log.column_count == 5

    def test_record_action_persists(self, tmp_path: Path) -> None:
        """Recorded actions should survive store recreation."""
        db_path = tmp_path / "audit.db"

        store1 = AuditTrailStore(db_path=db_path)
        store1.initialise_log(
            dataset_id="ds2",
            dataset_name="test.csv",
            dataset_hash="def456",
            row_count=50,
            column_count=3,
        )
        store1.record_action(
            "ds2",
            action_type="missing_imputation",
            details={"method": "median", "count": 5},
            column="value",
        )
        store1.record_action(
            "ds2",
            action_type="outlier_clip",
            details={"strategy": "iqr"},
            column="value",
        )

        # Recreate store
        store2 = AuditTrailStore(db_path=db_path)
        log = store2.get("ds2")

        assert log is not None
        assert len(log.actions) == 2
        assert log.actions[0].action_type == "missing_imputation"
        assert log.actions[0].details["method"] == "median"
        assert log.actions[0].column == "value"
        assert log.actions[1].action_type == "outlier_clip"

    def test_record_action_raises_for_missing_log(self, tmp_path: Path) -> None:
        """Recording action for non-existent log should raise KeyError."""
        db_path = tmp_path / "audit.db"
        store = AuditTrailStore(db_path=db_path)

        with pytest.raises(KeyError, match="does not exist"):
            store.record_action(
                "nonexistent",
                action_type="test",
                details={},
                column=None,
            )

    def test_list_logs_returns_all(self, tmp_path: Path) -> None:
        """list_logs should return all stored logs."""
        db_path = tmp_path / "audit.db"
        store = AuditTrailStore(db_path=db_path)

        for i in range(3):
            store.initialise_log(
                dataset_id=f"ds{i}",
                dataset_name=f"test{i}.csv",
                dataset_hash=f"hash{i}",
                row_count=i * 10,
                column_count=i + 1,
            )

        logs = store.list_logs()
        assert len(logs) == 3
        dataset_ids = {log.dataset_id for log in logs}
        assert dataset_ids == {"ds0", "ds1", "ds2"}

    def test_clear_removes_all_data(self, tmp_path: Path) -> None:
        """clear() should remove all logs and actions."""
        db_path = tmp_path / "audit.db"
        store = AuditTrailStore(db_path=db_path)

        store.initialise_log(
            dataset_id="ds1",
            dataset_name="test.csv",
            dataset_hash="abc",
            row_count=10,
            column_count=2,
        )
        store.record_action("ds1", action_type="test", details={}, column=None)

        store.clear()

        assert store.get("ds1") is None
        assert store.list_logs() == []

    def test_reinitialise_log_replaces_existing(self, tmp_path: Path) -> None:
        """Re-initialising a log should replace existing data."""
        db_path = tmp_path / "audit.db"
        store = AuditTrailStore(db_path=db_path)

        store.initialise_log(
            dataset_id="ds1",
            dataset_name="old.csv",
            dataset_hash="old_hash",
            row_count=50,
            column_count=3,
        )
        store.record_action("ds1", action_type="old_action", details={}, column=None)

        # Re-initialise with new data
        store.initialise_log(
            dataset_id="ds1",
            dataset_name="new.csv",
            dataset_hash="new_hash",
            row_count=100,
            column_count=5,
        )

        log = store.get("ds1")
        assert log is not None
        assert log.dataset_name == "new.csv"
        assert log.dataset_hash == "new_hash"
        assert log.row_count == 100
        assert len(log.actions) == 0  # Old actions should be gone


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_full_workflow(self, temp_db: Path) -> None:
        """Test the full audit trail workflow using module functions."""
        # Initialise log
        log = initialise_audit_log(
            dataset_id="workflow_test",
            dataset_name="workflow.csv",
            dataset_hash="workflow_hash",
            row_count=200,
            column_count=10,
        )
        assert log.dataset_id == "workflow_test"

        # Record actions
        action1 = record_preprocessing_action(
            "workflow_test",
            action_type="missing_imputation",
            details={"method": "median"},
            column="metric_a",
        )
        assert action1.action_type == "missing_imputation"

        action2 = record_preprocessing_action(
            "workflow_test",
            action_type="scaling",
            details={"strategy": "robust"},
        )
        assert action2.action_type == "scaling"

        # Retrieve log
        retrieved = get_audit_log("workflow_test")
        assert retrieved is not None
        assert len(retrieved.actions) == 2

        # List all logs
        all_logs = list_audit_logs()
        assert any(log.dataset_id == "workflow_test" for log in all_logs)

    def test_persistence_across_reset(self, temp_db: Path) -> None:
        """Data should persist even after reset (new store instance)."""
        initialise_audit_log(
            dataset_id="persist_test",
            dataset_name="persist.csv",
            dataset_hash="persist_hash",
            row_count=50,
            column_count=5,
        )
        record_preprocessing_action(
            "persist_test",
            action_type="test_action",
            details={"key": "value"},
        )

        # Reset the store without clearing data (simulates restart)
        reset_audit_trail(clear_data=False)

        # Should still be able to retrieve data
        log = get_audit_log("persist_test")
        assert log is not None
        assert log.dataset_id == "persist_test"
        assert len(log.actions) == 1
        assert log.actions[0].details["key"] == "value"
