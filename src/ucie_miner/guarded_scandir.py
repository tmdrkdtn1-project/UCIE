"""UCIE candidate guard for sharing one os.scandir iterator between threads.

Consequence of observed hosted runner native crashes: the caller must
serialize *all* next() and close() operations on the same iterator.
This is a first-party mitigation, not evidence that CPython is fixed.
"""
from __future__ import annotations

import os
import threading
from typing import Any


class GuardedScandir:
    """Bounded, explicitly owned iterator with a single synchronization lock.

    Do not bypass this guard and call methods on a raw iterator concurrently.
    Caller must close / use with-statement; no hidden process modification.
    """

    def __init__(self, path: os.PathLike[str] | str):
        self._lock = threading.Lock()
        self._iterator = os.scandir(path)
        self._closed = False

    def __iter__(self) -> "GuardedScandir":
        return self

    def __next__(self) -> Any:
        with self._lock:
            if self._closed:
                raise StopIteration
            try:
                return next(self._iterator)
            except StopIteration:
                self._close_locked()
                raise

    def _close_locked(self) -> None:
        if not self._closed:
            self._closed = True
            self._iterator.close()

    def close(self) -> None:
        with self._lock:
            self._close_locked()

    def __enter__(self) -> "GuardedScandir":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
