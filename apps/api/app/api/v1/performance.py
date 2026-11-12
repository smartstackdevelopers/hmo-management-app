"""F7.4 performance monitoring API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.performance import service as performance_service
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/dashboard")
def dashboard(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return performance_service.dashboard(session, org)


@router.post("/benchmarks/run")
def run_benchmark(
    samples: int = Query(default=10, ge=1, le=30),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return performance_service.trigger_benchmark(session, org, samples=samples)
