"""In-memory audit trail store tracking preprocessing actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any

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
    """Thread-safe store for dataset audit logs."""

    def __init__(self) -> None:
        self._logs: dict[str, AuditLog] = {}
        self._lock = RLock()

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

        entry = AuditLog(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            dataset_hash=dataset_hash,
            row_count=row_count,
            column_count=column_count,
        )
        with self._lock:
            self._logs[dataset_id] = entry
        return entry

    def record_action(
        self, dataset_id: str, *, action_type: str, details: dict[str, Any], column: str | None
    ) -> AuditAction:
        """Record a preprocessing action for a dataset."""

        with self._lock:
            log = self._logs.get(dataset_id)
            if log is None:
                raise KeyError(f"Audit log for dataset '{dataset_id}' does not exist")
            action = AuditAction(action_type=action_type, details=details, column=column)
            log.add_action(action)
            return action

    def get(self, dataset_id: str) -> AuditLog | None:
        """Return the audit log for a dataset if available."""

        with self._lock:
            return self._logs.get(dataset_id)

    def list_logs(self) -> list[AuditLog]:
        """Return a snapshot of all audit logs."""

        with self._lock:
            return list(self._logs.values())

    def clear(self) -> None:
        """Remove all stored audit logs."""

        with self._lock:
            self._logs.clear()


_STORE: AuditTrailStore | None = None


def _get_store() -> AuditTrailStore:
    global _STORE
    if _STORE is None:
        _STORE = AuditTrailStore()
    return _STORE


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


def reset_audit_trail() -> None:
    """Reset the global audit trail store (primarily for tests)."""

    global _STORE
    if _STORE is not None:
        _STORE.clear()
    _STORE = None

