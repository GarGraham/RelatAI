"""Custom exception hierarchy for RelatAI services."""

from __future__ import annotations


class RelatAIError(Exception):
    """Base class for all domain-specific exceptions."""


class PersistenceError(RelatAIError):
    """Raised when durable storage operations fail."""


class DatasetRegistryPersistenceError(PersistenceError):
    """Raised when the dataset registry cannot be persisted to disk."""
