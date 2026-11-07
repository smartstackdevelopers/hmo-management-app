from __future__ import annotations

import threading
import time
from typing import Protocol


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...

    def acquire_lock(self, key: str, ttl_seconds: int) -> bool: ...

    def release_lock(self, key: str) -> None: ...

    def available(self) -> bool: ...


class MemoryCacheBackend:
    """In-process cache for unit tests / Redis-less local runs."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float | None]] = {}
        self._locks: dict[str, float] = {}
        self._lock = threading.RLock()

    def available(self) -> bool:
        return True

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            value, expires = item
            if expires is not None and expires < time.time():
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires = time.time() + ttl_seconds if ttl_seconds > 0 else None
        with self._lock:
            self._data[key] = (value, expires)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def acquire_lock(self, key: str, ttl_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            expires = self._locks.get(key)
            if expires and expires > now:
                return False
            self._locks[key] = now + ttl_seconds
            return True

    def release_lock(self, key: str) -> None:
        with self._lock:
            self._locks.pop(key, None)


class RedisCacheBackend:
    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._client.ping()

    def available(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001
            return False

    def get(self, key: str) -> str | None:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds > 0:
            self._client.setex(key, ttl_seconds, value)
        else:
            self._client.set(key, value)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def acquire_lock(self, key: str, ttl_seconds: int) -> bool:
        return bool(self._client.set(key, "1", nx=True, ex=max(1, ttl_seconds)))

    def release_lock(self, key: str) -> None:
        self._client.delete(key)


class NullCacheBackend:
    """When caching is disabled — always miss, never store."""

    def available(self) -> bool:
        return False

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None

    def delete(self, key: str) -> None:
        return None

    def acquire_lock(self, key: str, ttl_seconds: int) -> bool:
        return True

    def release_lock(self, key: str) -> None:
        return None
