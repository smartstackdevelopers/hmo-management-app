"""Resolve the configured storage backend."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.storage.local import LocalDiskStorage
from app.storage.memory import InMemoryStorage
from app.storage.protocol import StorageBackend
from app.storage.s3 import S3CompatibleStorage

_SHARED_MEMORY = InMemoryStorage()


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    return build_storage_backend(settings)


def build_storage_backend(settings: Settings) -> StorageBackend:
    provider = (settings.storage_provider or "memory").strip().lower()
    if provider == "memory":
        return _SHARED_MEMORY
    if provider == "local":
        return LocalDiskStorage(settings.storage_local_root)
    if provider == "s3":
        return S3CompatibleStorage(settings)
    raise RuntimeError(f"Unsupported STORAGE_PROVIDER: {provider}")


def reset_storage_backend_cache() -> None:
    get_storage_backend.cache_clear()
