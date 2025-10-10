"""Caching helpers for RelatAI services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict
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
    """Simple LRU in-memory cache suitable for development and testing."""

    def __init__(self, *, max_entries: int | None = 1024) -> None:
        self._store: OrderedDict[str, T] = OrderedDict()
        self._max_entries = max_entries

    def get(self, key: str) -> T | None:
        value = self._store.get(key)
        if value is not None:
            self._store.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        self._store[key] = value
        self._store.move_to_end(key)
        if self._max_entries is not None and len(self._store) > self._max_entries:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)


def cached(
    cache: CacheBackend[T],
    key_builder: Callable[..., str],
) -> Callable[[Callable[..., T]], Callable[..., T]]:
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
