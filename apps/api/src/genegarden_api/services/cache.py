import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class CacheEntry[T]:
    value: T
    expires_at: float


class TTLMemoryCache[T]:
    """Small process-local cache for bounded ingestion runs.

    PostgreSQL remains the durable record store. This cache only prevents repeated
    upstream calls within and across short-lived requests in one API process.
    """

    def __init__(self, ttl_seconds: float, max_entries: int = 256) -> None:
        if ttl_seconds <= 0 or max_entries <= 0:
            raise ValueError("Cache TTL and capacity must be positive")
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> T | None:
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= monotonic():
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            return entry.value

    async def set(self, key: str, value: T) -> None:
        async with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=monotonic() + self._ttl_seconds)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)
