"""Phase 9 — performance helpers: TTL cache + fast learned indexing."""
from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Tiny thread-safe LRU+TTL cache for expensive research calls."""

    def __init__(self, maxsize: int = 128, ttl_sec: float = 300.0) -> None:
        self.maxsize = maxsize
        self.ttl = ttl_sec
        self._lock = threading.Lock()
        self._data: OrderedDict[str, tuple[float, T]] = OrderedDict()

    def get(self, key: str) -> Optional[T]:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            ts, val = item
            if now - ts > self.ttl:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return val

    def set(self, key: str, value: T) -> None:
        with self._lock:
            self._data[key] = (time.time(), value)
            self._data.move_to_end(key)
            while len(self._data) > self.maxsize:
                self._data.popitem(last=False)

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        hit = self.get(key)
        if hit is not None:
            return hit
        value = factory()
        self.set(key, value)
        return value


# Shared research cache (module-level, process-local — fine on Render free)
research_cache: TTLCache[Any] = TTLCache(maxsize=160, ttl_sec=420.0)
