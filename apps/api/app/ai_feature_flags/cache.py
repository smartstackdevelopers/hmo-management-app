"""Short-lived in-process availability cache (org+feature keyed).

Fail-closed: cache misses force a DB read; cache never invents enabled=true.
Consistency window: TTL_SECONDS (documented). Updates invalidate immediately.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from uuid import UUID

TTL_SECONDS = 15


@dataclass
class _CacheEntry:
    enabled: bool
    pilot_enabled: bool
    expires_at: float


_lock = threading.Lock()
_store: dict[tuple[str, str], _CacheEntry] = {}


def cache_get(organisation_id: UUID, feature_id: str) -> tuple[bool, bool] | None:
    key = (str(organisation_id), feature_id)
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            _store.pop(key, None)
            return None
        return entry.enabled, entry.pilot_enabled


def cache_set(organisation_id: UUID, feature_id: str, *, enabled: bool, pilot_enabled: bool) -> None:
    key = (str(organisation_id), feature_id)
    with _lock:
        _store[key] = _CacheEntry(
            enabled=enabled,
            pilot_enabled=pilot_enabled,
            expires_at=time.monotonic() + TTL_SECONDS,
        )


def cache_invalidate(organisation_id: UUID, feature_id: str | None = None) -> None:
    org = str(organisation_id)
    with _lock:
        if feature_id is None:
            for key in [k for k in _store if k[0] == org]:
                _store.pop(key, None)
        else:
            _store.pop((org, feature_id), None)


def cache_clear_all() -> None:
    with _lock:
        _store.clear()
