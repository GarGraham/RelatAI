"""Caching helpers for RelatAI services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import wraps
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class CacheBackend(ABC, Generic[T]):
    """Abstract interface for caching backends."""

    @abstractmethod
    def get(self, key: str) -> T | None:
        """Return the cached value, if present."""

    @abstractmethod
    def set(self, key: str, value: T) -> None:
        """Store a value in the cache."""

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Remove a cache entry."""


class InMemoryCache(CacheBackend[T]):
    """Simple in-memory cache suitable for development and testing."""

    def __init__(self) -> None:
        self._store: dict[str, T] = {}

    def get(self, key: str) -> T | None:
        return self._store.get(key)

    def set(self, key: str, value: T) -> None:
        self._store[key] = value

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


def cached(cache: CacheBackend[T], key_builder: Callable[..., str]) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator applying caching semantics to a function."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            key = key_builder(*args, **kwargs)
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper

    return decorator
