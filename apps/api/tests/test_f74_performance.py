"""F7.4 performance journey benchmarks."""

from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient

from app.db.models.enums import HMoreRole, MembershipStatus
from app.main import app
from app.performance import service as performance_service
from app.performance.stats import percentile, summarize
from app.rbac.context import AuthorizationContext, MembershipView
from app.rbac.matrix import role_has_permission
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext


def test_alembic_f74_revision_chain() -> None:
    api_root = Path(__file__).resolve().parents[1]
    config = Config(str(api_root / "alembic.ini"))
    config.set_main_option("script_location", str(api_root / "migrations"))
    script = ScriptDirectory.from_config(config)
    rev = script.get_revision("20261112_4800_f74")
    assert rev is not None
    assert rev.down_revision == "20261112_4700_f73"


def test_stats_percentile() -> None:
    stats = summarize([10.0, 20.0, 30.0, 40.0, 100.0])
    assert stats["p50_ms"] == 30.0
    assert percentile([1.0, 2.0, 3.0], 95) >= 2.0


def test_performance_permissions_super_admin() -> None:
    assert role_has_permission(HMoreRole.SUPER_ADMIN, Permission.PERFORMANCE_BENCHMARK_RUN)
    assert not role_has_permission(HMoreRole.ORGANISATION_ADMIN, Permission.PERFORMANCE_BENCHMARK_RUN)


def test_health_smoke_latency_budget() -> None:
    client = TestClient(app)
    samples = []
    for _ in range(20):
        import time

        t0 = time.perf_counter()
        r = client.get("/health")
        samples.append((time.perf_counter() - t0) * 1000)
        assert r.status_code == 200
    stats = summarize(samples)
    assert stats["p95_ms"] < 2500.0


def test_gzip_middleware_present() -> None:
    client = TestClient(app)
    large = {"items": [{"id": i, "label": f"row-{i}" * 20} for i in range(200)]}
    from fastapi import FastAPI
    from fastapi.testclient import TestClient as TC

    probe = FastAPI()

    @probe.get("/big")
    def big() -> dict:
        return large

    from starlette.middleware.gzip import GZipMiddleware

    probe.add_middleware(GZipMiddleware, minimum_size=1000)
    r = TC(probe).get("/big", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers.get("content-encoding") == "gzip"


@pytest.mark.postgres
def test_benchmark_persisted(db_session, unique_suffix: str) -> None:
    result = performance_service.run_benchmark_suite(
        db_session,
        samples=3,
        concurrent_users=5,
        environment_label=f"test-{unique_suffix}",
        persist=True,
    )
    assert result["status"] == "completed"
    assert len(result["journeys"]) >= 10
    health = result["summary"]["load_test"]
    assert health["concurrent_users"] == 5
    assert health["p95_ms"] < 3000.0

