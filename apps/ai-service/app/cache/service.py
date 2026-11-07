from __future__ import annotations

import json
import time
from typing import Any, Callable
from uuid import UUID

from app.cache.backend import CacheBackend, MemoryCacheBackend, NullCacheBackend, RedisCacheBackend
from app.cache.keys import build_cache_key, lock_key_for
from app.core.config import Settings
from app.core.errors import WorkflowError
from app.core.logging import get_logger

logger = get_logger("hmore.ai.cache")


def create_cache_backend(settings: Settings) -> CacheBackend:
    mode = settings.ai_cache_backend
    if mode == "none" or not settings.ai_cache_enabled:
        return NullCacheBackend()
    if mode == "memory":
        return MemoryCacheBackend()
    if mode == "redis":
        try:
            return RedisCacheBackend(settings.redis_url)
        except Exception as exc:  # noqa: BLE001
            if settings.ai_cache_fail_open:
                logger.warning("redis_unavailable_using_null reason=%s", type(exc).__name__)
                return NullCacheBackend()
            raise WorkflowError("AI cache Redis unavailable", status_code=503) from exc
    raise WorkflowError(f"Unsupported AI_CACHE_BACKEND '{mode}'", status_code=500)


class AiCacheService:
    def __init__(self, backend: CacheBackend, settings: Settings) -> None:
        self._backend = backend
        self._settings = settings

    @property
    def available(self) -> bool:
        return self._backend.available()

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self._backend.get(key)
        if raw is None:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._backend.delete(key)
            return None
        if not isinstance(data, dict):
            self._backend.delete(key)
            return None
        return data

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._settings.ai_cache_ttl_seconds
        # Never persist secrets / tokens
        safe = {k: v for k, v in value.items() if k.lower() not in {"token", "authorization", "api_key"}}
        self._backend.set(key, json.dumps(safe, separators=(",", ":")), ttl)

    def invalidate(self, key: str) -> None:
        self._backend.delete(key)

    def get_or_compute(
        self,
        *,
        organisation_id: UUID,
        workflow_id: str,
        prompt_id: str,
        prompt_version: str,
        provider: str,
        model_id: str,
        input_fingerprint: dict[str, Any],
        eligible: bool,
        compute: Callable[[], dict[str, Any]],
    ) -> tuple[dict[str, Any], str]:
        """Return (payload, cache_status) where cache_status is hit|miss|bypass|lock_miss."""
        if not eligible or not self._settings.ai_cache_enabled:
            return compute(), "bypass"

        key = build_cache_key(
            organisation_id=organisation_id,
            workflow_id=workflow_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            provider=provider,
            model_id=model_id,
            input_fingerprint=input_fingerprint,
        )
        cached = self.get_json(key)
        if cached is not None:
            return cached, "hit"

        lock = lock_key_for(key)
        got_lock = self._backend.acquire_lock(lock, self._settings.ai_cache_lock_ttl_seconds)
        try:
            if not got_lock:
                # Brief wait for producer — then re-check; else compute locally (no unrelated org data).
                time.sleep(min(0.05, self._settings.ai_cache_lock_wait_seconds))
                cached = self.get_json(key)
                if cached is not None:
                    return cached, "hit"
                result = compute()
                return result, "lock_miss"

            cached = self.get_json(key)
            if cached is not None:
                return cached, "hit"
            result = compute()
            self.set_json(key, result)
            return result, "miss"
        finally:
            if got_lock:
                self._backend.release_lock(lock)


_CACHE: AiCacheService | None = None


def get_cache_service(settings: Settings | None = None) -> AiCacheService:
    global _CACHE
    from app.core.config import get_settings

    settings = settings or get_settings()
    if _CACHE is None:
        _CACHE = AiCacheService(create_cache_backend(settings), settings)
    return _CACHE


def reset_cache_service_for_tests(settings: Settings | None = None) -> AiCacheService:
    global _CACHE
    from app.core.config import get_settings

    settings = settings or get_settings()
    _CACHE = AiCacheService(create_cache_backend(settings), settings)
    return _CACHE
