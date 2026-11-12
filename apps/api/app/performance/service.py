"""F7.4 benchmark orchestration."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.db.models.performance import PerformanceBenchmarkRun, PerformanceJourneyResult
from app.performance import access as perf_access
from app.performance.journeys import CRITICAL_JOURNEY_PROBES, run_probe
from app.performance.stats import summarize
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def run_benchmark_suite(
    session: Session,
    *,
    samples: int = 10,
    concurrent_users: int = 20,
    environment_label: str = "local",
    persist: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    samples = max(1, min(samples, 50))
    run = PerformanceBenchmarkRun(
        environment_label=environment_label,
        status="running",
        started_at=_now(),
        sample_count_per_journey=samples,
        concurrent_health_users=concurrent_users,
    )
    if persist:
        session.add(run)
        session.flush()

    from app.main import app

    client = TestClient(app)
    journey_results: list[dict[str, Any]] = []

    for probe in CRITICAL_JOURNEY_PROBES:
        timings: list[float] = []
        status_hist: dict[str, int] = {}
        errors = 0
        for _ in range(samples):
            code, ms = run_probe(client, probe)
            timings.append(ms)
            key = str(code)
            status_hist[key] = status_hist.get(key, 0) + 1
            if code >= 500:
                errors += 1
        stats = summarize(timings)
        row = PerformanceJourneyResult(
            benchmark_run_id=run.id,
            journey_key=probe.key,
            category=probe.category,
            description=probe.description,
            samples=samples,
            error_count=errors,
            avg_ms=stats["avg_ms"],
            p50_ms=stats["p50_ms"],
            p95_ms=stats["p95_ms"],
            p99_ms=stats["p99_ms"],
            status_codes=status_hist,
        )
        if persist:
            session.add(row)
        journey_results.append(
            {
                "journey_key": probe.key,
                "category": probe.category,
                **stats,
                "error_count": errors,
                "status_codes": status_hist,
            }
        )

    health_latencies: list[float] = []

    def _hit_health() -> float:
        _, ms = run_probe(client, CRITICAL_JOURNEY_PROBES[-2])  # health.liveness
        return ms

    with ThreadPoolExecutor(max_workers=min(concurrent_users, 32)) as pool:
        futures = [pool.submit(_hit_health) for _ in range(concurrent_users)]
        for fut in as_completed(futures):
            try:
                health_latencies.append(fut.result())
            except Exception:
                health_latencies.append(0.0)

    load_stats = summarize(health_latencies)
    run.summary = {
        "journeys_tested": len(CRITICAL_JOURNEY_PROBES),
        "load_test": {
            "concurrent_users": concurrent_users,
            "endpoint": "/health",
            **load_stats,
        },
        "gzip_enabled": True,
        "notes": "Synthetic auth-gate probes measure middleware + routing, not full authenticated journeys.",
    }
    run.status = "completed"
    run.completed_at = _now()
    session.flush()
    return {
        "run_id": str(run.id),
        "status": run.status,
        "journeys": journey_results,
        "summary": run.summary,
    }


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    perf_access.require_performance_read(ctx)
    latest = session.scalar(select(PerformanceBenchmarkRun).order_by(desc(PerformanceBenchmarkRun.started_at)).limit(1))
    rows = []
    if latest:
        rows = session.scalars(
            select(PerformanceJourneyResult)
            .where(PerformanceJourneyResult.benchmark_run_id == latest.id)
            .order_by(PerformanceJourneyResult.p95_ms.desc())
        ).all()
    slowest = [
        {
            "journey_key": r.journey_key,
            "p95_ms": r.p95_ms,
            "avg_ms": r.avg_ms,
            "category": r.category,
        }
        for r in rows[:8]
    ]
    return {
        "latest_run": {
            "id": str(latest.id) if latest else None,
            "status": latest.status if latest else None,
            "started_at": latest.started_at.isoformat() if latest and latest.started_at else None,
            "summary": latest.summary if latest else {},
        },
        "slowest_journeys_p95": slowest,
        "sentry_configured": False,
        "capacity_targets": "pending_approval",
    }


def trigger_benchmark(session: Session, ctx: OrganisationContext, samples: int = 10) -> dict[str, Any]:
    perf_access.require_performance_run(ctx)
    return run_benchmark_suite(session, samples=samples, environment_label=get_settings().environment, persist=True)
