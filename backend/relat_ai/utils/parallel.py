"""Parallel execution utilities."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from typing import Callable, Iterable, Iterator, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def chunked_iterable(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield lists of at most ``size`` items from an iterable."""

    iterator = iter(iterable)
    while chunk := list(islice(iterator, size)):
        yield chunk


def run_in_executor(function: Callable[[T], R], items: Iterable[T], max_workers: int = 4) -> list[R]:
    """Execute a function for each item using a thread pool."""

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(function, item) for item in items]
    return [future.result() for future in futures]
