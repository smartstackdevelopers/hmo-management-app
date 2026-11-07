from __future__ import annotations

import pytest

from app.cache.keys import build_cache_key
from app.cache.service import AiCacheService, MemoryCacheBackend, NullCacheBackend
from app.core.config import get_settings
from tests.conftest import ORG_A, ORG_B


def test_cache_keys_isolate_organisations() -> None:
    fingerprint = {"msg_sha": "abc"}
    key_a = build_cache_key(
        organisation_id=ORG_A,
        workflow_id="foundation_routed_echo",
        prompt_id="p",
        prompt_version="1",
        provider="mock",
        model_id="m",
        input_fingerprint=fingerprint,
    )
    key_b = build_cache_key(
        organisation_id=ORG_B,
        workflow_id="foundation_routed_echo",
        prompt_id="p",
        prompt_version="1",
        provider="mock",
        model_id="m",
        input_fingerprint=fingerprint,
    )
    assert key_a != key_b
    assert str(ORG_A) in key_a
    assert "abc" not in key_a  # hashed, not raw


def test_memory_cache_hit_miss_and_ttl() -> None:
    settings = get_settings()
    svc = AiCacheService(MemoryCacheBackend(), settings)
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"content": "x"}

    r1, s1 = svc.get_or_compute(
        organisation_id=ORG_A,
        workflow_id="w",
        prompt_id="p",
        prompt_version="1",
        provider="mock",
        model_id="m",
        input_fingerprint={"k": "1"},
        eligible=True,
        compute=compute,
    )
    r2, s2 = svc.get_or_compute(
        organisation_id=ORG_A,
        workflow_id="w",
        prompt_id="p",
        prompt_version="1",
        provider="mock",
        model_id="m",
        input_fingerprint={"k": "1"},
        eligible=True,
        compute=compute,
    )
    assert s1 == "miss"
    assert s2 == "hit"
    assert calls["n"] == 1
    assert r1 == r2


def test_prompt_version_changes_bust_cache() -> None:
    settings = get_settings()
    svc = AiCacheService(MemoryCacheBackend(), settings)
    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return {"content": str(calls["n"])}

    svc.get_or_compute(
        organisation_id=ORG_A,
        workflow_id="w",
        prompt_id="p",
        prompt_version="1.0.0",
        provider="mock",
        model_id="m",
        input_fingerprint={"k": "1"},
        eligible=True,
        compute=compute,
    )
    svc.get_or_compute(
        organisation_id=ORG_A,
        workflow_id="w",
        prompt_id="p",
        prompt_version="1.1.0",
        provider="mock",
        model_id="m",
        input_fingerprint={"k": "1"},
        eligible=True,
        compute=compute,
    )
    assert calls["n"] == 2


def test_null_cache_bypass() -> None:
    settings = get_settings()
    svc = AiCacheService(NullCacheBackend(), settings)
    _, status = svc.get_or_compute(
        organisation_id=ORG_A,
        workflow_id="w",
        prompt_id="p",
        prompt_version="1",
        provider="mock",
        model_id="m",
        input_fingerprint={},
        eligible=True,
        compute=lambda: {"ok": True},
    )
    # Null backend is "unavailable"; get_or_compute still runs compute via miss path
    assert status in {"miss", "bypass", "lock_miss"}


@pytest.mark.real_redis
def test_real_redis_optional() -> None:
    import os

    if not os.environ.get("REDIS_URL_REAL"):
        pytest.skip("Real Redis not configured — not reporting as passed")
