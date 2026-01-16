"""SQLite-backed audit trail store tracking preprocessing actions.

This module provides persistent storage for audit logs, replacing the previous
in-memory implementation. Logs survive server restarts, which is critical for
regulatory traceability in quality event investigations.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from relat_ai.core.config import get_settings
from relat_ai.core.models import AuditActionModel, AuditLogModel


@dataclass(slots=True)
class AuditAction:
    """Represents a single preprocessing action applied to a dataset."""

    action_type: str
    details: dict[str, Any]
    column: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_model(self) -> AuditActionModel:
        """Convert the action into an API response model."""

        return AuditActionModel(
            action_type=self.action_type,
            column=self.column,
            timestamp=self.timestamp,
            details=self.details,
        )


@dataclass(slots=True)
class AuditLog:
    """Audit log captured for a dataset ingestion workflow."""

    dataset_id: str
    dataset_name: str
    dataset_hash: str
    row_count: int
    column_count: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    actions: list[AuditAction] = field(default_factory=list)

    def add_action(self, action: AuditAction) -> None:
        """Append an action to the audit trail."""

        self.actions.append(action)

    def to_model(self) -> AuditLogModel:
        """Convert the audit log into a serializable model."""

        return AuditLogModel(
            dataset_id=self.dataset_id,
            dataset_name=self.dataset_name,
            dataset_hash=self.dataset_hash,
            row_count=self.row_count,
            column_count=self.column_count,
            created_at=self.created_at,
            actions=[action.to_model() for action in self.actions],
        )


class AuditTrailStore:
    """Thread-safe SQLite-backed store for dataset audit logs."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = db_path or get_settings().audit_db_path
        self._lock = RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Return a new connection to the SQLite database."""
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    dataset_id TEXT PRIMARY KEY,
                    dataset_name TEXT NOT NULL,
                    dataset_hash TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    column_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dataset_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    column_name TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(dataset_id) REFERENCES audit_logs(dataset_id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_dataset ON audit_actions(dataset_id)")
            conn.commit()

    def initialise_log(
        self,
        *,
        dataset_id: str,
        dataset_name: str,
        dataset_hash: str,
        row_count: int,
        column_count: int,
    ) -> AuditLog:
        """Create or replace the audit log for a dataset."""
        created_at = datetime.now(timezone.utc)
        with self._lock:
            with self._get_connection() as conn:
                # Delete existing log and actions (if any)
                conn.execute("DELETE FROM audit_actions WHERE dataset_id = ?", (dataset_id,))
                conn.execute("DELETE FROM audit_logs WHERE dataset_id = ?", (dataset_id,))
                # Insert new log
                conn.execute(
                    """
                    INSERT INTO audit_logs (dataset_id, dataset_name, dataset_hash, row_count, column_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (dataset_id, dataset_name, dataset_hash, row_count, column_count, created_at.isoformat()),
                )
                conn.commit()

        return AuditLog(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_hash=dataset_hash,
            row_count=row_count,
            column_count=column_count,
            created_at=created_at,
        )

    def record_action(
        self, dataset_id: str, *, action_type: str, details: dict[str, Any], column: str | None
    ) -> AuditAction:
        """Record a preprocessing action for a dataset."""
        timestamp = datetime.now(timezone.utc)
        with self._lock:
            with self._get_connection() as conn:
                # Verify log exists
                row = conn.execute(
                    "SELECT 1 FROM audit_logs WHERE dataset_id = ?", (dataset_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(f"Audit log for dataset '{dataset_id}' does not exist")
                conn.execute(
                    """
                    INSERT INTO audit_actions (dataset_id, action_type, details, column_name, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (dataset_id, action_type, json.dumps(details), column, timestamp.isoformat()),
                )
                conn.commit()

        return AuditAction(action_type=action_type, details=details, column=column, timestamp=timestamp)

    def get(self, dataset_id: str) -> AuditLog | None:
        """Return the audit log for a dataset if available."""
        with self._lock:
            with self._get_connection() as conn:
                log_row = conn.execute(
                    "SELECT * FROM audit_logs WHERE dataset_id = ?", (dataset_id,)
                ).fetchone()
                if log_row is None:
                    return None

                action_rows = conn.execute(
                    "SELECT * FROM audit_actions WHERE dataset_id = ? ORDER BY id",
                    (dataset_id,),
                ).fetchall()

                actions = [
                    AuditAction(
                        action_type=row["action_type"],
                        details=json.loads(row["details"]),
                        column=row["column_name"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                    )
                    for row in action_rows
                ]

                return AuditLog(
                    dataset_id=log_row["dataset_id"],
                    dataset_name=log_row["dataset_name"],
                    dataset_hash=log_row["dataset_hash"],
                    row_count=log_row["row_count"],
                    column_count=log_row["column_count"],
                    created_at=datetime.fromisoformat(log_row["created_at"]),
                    actions=actions,
                )

    def list_logs(self) -> list[AuditLog]:
        """Return a snapshot of all audit logs."""
        with self._lock:
            with self._get_connection() as conn:
                log_rows = conn.execute("SELECT dataset_id FROM audit_logs ORDER BY created_at DESC").fetchall()
                return [self.get(row["dataset_id"]) for row in log_rows if self.get(row["dataset_id"]) is not None]

    def clear(self) -> None:
        """Remove all stored audit logs."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM audit_actions")
                conn.execute("DELETE FROM audit_logs")
                conn.commit()


_STORE: AuditTrailStore | None = None
_TEST_DB_PATH: Path | None = None


def _get_store() -> AuditTrailStore:
    global _STORE
    if _STORE is None:
        _STORE = AuditTrailStore(db_path=_TEST_DB_PATH)
    return _STORE


def set_audit_db_path(db_path: Path | None) -> None:
    """Set a custom database path (primarily for testing).

    Call reset_audit_trail() after this to reinitialize the store with the new path.
    """
    global _TEST_DB_PATH
    _TEST_DB_PATH = db_path


def initialise_audit_log(
    *,
    dataset_id: str,
    dataset_name: str,
    dataset_hash: str,
    row_count: int,
    column_count: int,
) -> AuditLog:
    """Initialise the audit log for a dataset."""

    return _get_store().initialise_log(
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        dataset_hash=dataset_hash,
        row_count=row_count,
        column_count=column_count,
    )


def record_preprocessing_action(
    dataset_id: str,
    *,
    action_type: str,
    details: dict[str, Any],
    column: str | None = None,
) -> AuditAction:
    """Record a preprocessing action for a dataset."""

    return _get_store().record_action(
        dataset_id,
        action_type=action_type,
        details=details,
        column=column,
    )


def get_audit_log(dataset_id: str) -> AuditLog | None:
    """Return the audit log associated with a dataset."""

    return _get_store().get(dataset_id)


def list_audit_logs() -> list[AuditLog]:
    """Return all audit logs currently stored."""

    return _get_store().list_logs()


def reset_audit_trail(*, clear_data: bool = True) -> None:
    """Reset the global audit trail store.

    Args:
        clear_data: If True (default), delete all audit data. If False, just
            reset the store instance without clearing persisted data (useful
            for simulating application restarts in tests).
    """
    global _STORE
    if _STORE is not None and clear_data:
        _STORE.clear()
    _STORE = None

