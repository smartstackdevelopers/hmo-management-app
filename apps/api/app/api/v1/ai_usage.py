"""F3.3 AI budgets, usage metering, cost dashboards and internal enforcement APIs."""

from __future__ import annotations

import hmac
import secrets
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_usage import access as ai_access
from app.ai_usage.budget import (
    BudgetExceededError,
    budget_status_snapshot,
    list_budget_history,
    release_orphaned_reservations,
    reserve_budget,
    upsert_budget,
)
from app.ai_usage.cost import upsert_pricing
from app.ai_usage.dashboard import organisation_dashboard, platform_dashboard
from app.ai_usage.metering import record_and_reconcile, usage_to_dict
from app.ai_usage.notify import evaluate_and_notify_thresholds
from app.ai_usage.period import period_key_for
from app.ai_usage.schemas import (
    BudgetUpsert,
    PricingUpsert,
    ReconcileBudgetRequest,
    ReserveBudgetRequest,
)
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.core.config import Settings, get_settings
from app.db.models.ai_usage import AiModelPricing, AiUsageRecord, OrganisationAiBudget
from app.db.models.enums import HMoreRole
from app.db.session import get_session
from app.rbac.context import AuthorizationContext
from app.rbac.deps import require_perm
from app.rbac.permissions import Permission
from app.tenancy.context import OrganisationContext
from app.tenancy.deps import get_organisation_context, get_platform_context
from app.tenancy.session_rls import apply_organisation_rls, apply_platform_rls_bypass

router = APIRouter(prefix="/ai", tags=["ai-usage"])
internal_router = APIRouter(prefix="/internal/ai", tags=["ai-usage-internal"])


def _budget_dict(b: OrganisationAiBudget) -> dict[str, Any]:
    return {
        "id": str(b.id),
        "organisation_id": str(b.organisation_id),
        "currency": b.currency,
        "monthly_limit": str(b.monthly_limit),
        "period_kind": b.period_kind,
        "effective_from": b.effective_from.isoformat(),
        "effective_to": b.effective_to.isoformat() if b.effective_to else None,
        "active": b.active,
        "warning_threshold_pct": str(b.warning_threshold_pct),
        "default_reservation_amount": str(b.default_reservation_amount),
        "notes": b.notes,
        "created_by_user_id": str(b.created_by_user_id) if b.created_by_user_id else None,
        "updated_by_user_id": str(b.updated_by_user_id) if b.updated_by_user_id else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


def _pricing_dict(p: AiModelPricing) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "provider": p.provider,
        "model_id": p.model_id,
        "pricing_version": p.pricing_version,
        "currency": p.currency,
        "input_price_per_1k_tokens": str(p.input_price_per_1k_tokens),
        "output_price_per_1k_tokens": str(p.output_price_per_1k_tokens),
        "effective_from": p.effective_from.isoformat(),
        "effective_to": p.effective_to.isoformat() if p.effective_to else None,
        "active": p.active,
        "notes": p.notes,
    }


# --- Organisation-scoped admin APIs ---


@router.get("/budgets/current")
def get_current_budget(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    _authz: AuthorizationContext = Depends(require_perm(Permission.AI_BUDGET_READ)),
) -> dict[str, Any]:
    ai_access.require_ai_budget_read(org)
    rows = list_budget_history(session, org.organisation_id)
    active = next((r for r in rows if r.active), None)
    return {
        "budget": _budget_dict(active) if active else None,
        "status": budget_status_snapshot(session, org.organisation_id),
    }


@router.get("/budgets/history")
def get_budget_history(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    _authz: AuthorizationContext = Depends(require_perm(Permission.AI_BUDGET_READ)),
) -> dict[str, Any]:
    ai_access.require_ai_budget_read(org)
    rows = list_budget_history(session, org.organisation_id)
    return {"items": [_budget_dict(r) for r in rows]}


@router.put("/budgets")
def put_budget(
    body: BudgetUpsert,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    _authz: AuthorizationContext = Depends(require_perm(Permission.AI_BUDGET_MANAGE)),
) -> dict[str, Any]:
    ai_access.require_ai_budget_manage(org)
    budget = upsert_budget(session, org, org.organisation_id, body.model_dump())
    session.commit()
    return {"budget": _budget_dict(budget), "status": budget_status_snapshot(session, org.organisation_id)}


@router.get("/usage/status")
def get_usage_status(
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    _authz: AuthorizationContext = Depends(require_perm(Permission.AI_USAGE_READ)),
) -> dict[str, Any]:
    ai_access.require_ai_usage_read(org)
    snap = budget_status_snapshot(session, org.organisation_id)
    alerts = evaluate_and_notify_thresholds(session, organisation_id=org.organisation_id, snapshot=snap)
    return {**snap, "alerts": alerts}


@router.get("/usage/records")
def list_usage_records(
    period_key: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    feature_id: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    execution_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    _authz: AuthorizationContext = Depends(require_perm(Permission.AI_USAGE_READ)),
) -> dict[str, Any]:
    ai_access.require_ai_usage_read(org)
    pk = period_key or period_key_for()
    stmt = select(AiUsageRecord).where(
        AiUsageRecord.organisation_id == org.organisation_id,
        AiUsageRecord.period_key == pk,
    )
    if feature_id:
        stmt = stmt.where(AiUsageRecord.feature_id == feature_id)
    if provider:
        stmt = stmt.where(AiUsageRecord.provider == provider)
    if model_id:
        stmt = stmt.where(AiUsageRecord.model_id == model_id)
    if execution_status:
        stmt = stmt.where(AiUsageRecord.execution_status == execution_status)
    stmt = stmt.order_by(AiUsageRecord.executed_at.desc())
    rows = list(session.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return {
        "period_key": pk,
        "page": page,
        "page_size": page_size,
        "items": [usage_to_dict(r) for r in rows],
    }


@router.get("/dashboard")
def get_org_ai_dashboard(
    period_key: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    period_from: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    period_to: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    feature_id: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    execution_status: str | None = None,
    org: OrganisationContext = Depends(get_organisation_context),
    session: Session = Depends(get_session),
    _authz: AuthorizationContext = Depends(require_perm(Permission.AI_COST_DASHBOARD_VIEW)),
) -> dict[str, Any]:
    ai_access.require_ai_cost_dashboard(org)
    data = organisation_dashboard(
        session,
        org.organisation_id,
        period_key=period_key,
        period_from=period_from,
        period_to=period_to,
        feature_id=feature_id,
        provider=provider,
        model_id=model_id,
        execution_status=execution_status,
    )
    record_event(
        session,
        action=audit_events.AI_COST_DASHBOARD_VIEW,
        resource_type="ai_cost_dashboard",
        resource_id=str(org.organisation_id),
        organisation_id=org.organisation_id,
        actor_user_id=org.user_id,
        actor_role=org.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Viewed organisation AI cost dashboard",
        metadata={"period_key": period_key or period_key_for()},
        raise_on_error=False,
    )
    session.commit()
    return data


@router.get("/platform/dashboard")
def get_platform_ai_dashboard(
    period_key: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    period_from: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    period_to: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    feature_id: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    execution_status: str | None = None,
    authz: AuthorizationContext = Depends(get_platform_context),
    session: Session = Depends(get_session),
    _perm: AuthorizationContext = Depends(require_perm(Permission.AI_PLATFORM_COST_VIEW)),
) -> dict[str, Any]:
    ai_access.require_platform_ai_dashboard(authz.active_role or HMoreRole.TENANT)
    data = platform_dashboard(
        session,
        period_key=period_key,
        period_from=period_from,
        period_to=period_to,
        feature_id=feature_id,
        provider=provider,
        model_id=model_id,
        execution_status=execution_status,
    )
    record_event(
        session,
        action=audit_events.AI_COST_DASHBOARD_VIEW,
        resource_type="ai_cost_dashboard",
        resource_id="platform",
        organisation_id=None,
        actor_user_id=authz.user.id,
        actor_role=authz.active_role.value if authz.active_role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="Viewed platform AI cost dashboard",
        metadata={"period_key": period_key or period_key_for()},
        raise_on_error=False,
    )
    session.commit()
    return data


@router.put("/pricing")
def put_pricing(
    body: PricingUpsert,
    authz: AuthorizationContext = Depends(get_platform_context),
    session: Session = Depends(get_session),
    _perm: AuthorizationContext = Depends(require_perm(Permission.AI_PRICING_MANAGE)),
) -> dict[str, Any]:
    row = upsert_pricing(session, body.model_dump(), actor_user_id=authz.user.id)
    record_event(
        session,
        action=audit_events.AI_PRICING_UPSERT,
        resource_type="ai_model_pricing",
        resource_id=str(row.id),
        organisation_id=None,
        actor_user_id=authz.user.id,
        actor_role=authz.active_role.value if authz.active_role else None,
        outcome=AuditOutcome.SUCCESS,
        summary="AI model pricing configured",
        metadata={
            "provider": row.provider,
            "model_id": row.model_id,
            "pricing_version": row.pricing_version,
        },
        raise_on_error=False,
    )
    session.commit()
    return {"pricing": _pricing_dict(row)}


@router.get("/pricing")
def list_pricing(
    authz: AuthorizationContext = Depends(get_platform_context),
    session: Session = Depends(get_session),
    _perm: AuthorizationContext = Depends(require_perm(Permission.AI_PRICING_MANAGE)),
) -> dict[str, Any]:
    rows = list(session.scalars(select(AiModelPricing).order_by(AiModelPricing.provider, AiModelPricing.model_id)))
    return {"items": [_pricing_dict(r) for r in rows]}


# --- Internal S2S endpoints (AI service → core API) ---


def require_ai_service_token(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    expected = (settings.ai_service_token or "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service token is not configured on the core API",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    presented = authorization.split(" ", 1)[1].strip()
    if not hmac.compare_digest(expected.encode("utf-8"), presented.encode("utf-8")):
        secrets.compare_digest(b"x" * 32, b"y" * 32)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")


@internal_router.post("/budget/reserve")
def internal_reserve(
    body: ReserveBudgetRequest,
    session: Session = Depends(get_session),
    _: None = Depends(require_ai_service_token),
) -> dict[str, Any]:
    apply_platform_rls_bypass(session)
    try:
        result = reserve_budget(
            session,
            request_id=body.request_id,
            organisation_id=body.organisation_id,
            user_id=body.user_id,
            feature_id=body.feature_id,
            workflow_id=body.workflow_id,
            reserved_amount=body.reserved_amount,
            billable=body.billable,
            cache_hit=body.cache_hit,
        )
        session.commit()
        return result
    except BudgetExceededError as exc:
        session.commit()
        raise exc.to_http() from exc


@internal_router.post("/budget/reconcile")
def internal_reconcile(
    body: ReconcileBudgetRequest,
    session: Session = Depends(get_session),
    _: None = Depends(require_ai_service_token),
) -> dict[str, Any]:
    apply_platform_rls_bypass(session)
    # Ensure org RLS context is consistent for any downstream RLS-aware code.
    apply_organisation_rls(session, body.organisation_id)
    apply_platform_rls_bypass(session)
    record = record_and_reconcile(
        session,
        request_id=body.request_id,
        organisation_id=body.organisation_id,
        execution_status=body.execution_status,
        feature_id=body.feature_id,
        workflow_id=body.workflow_id,
        user_id=body.user_id,
        provider=body.provider,
        model_id=body.model_id,
        prompt_id=body.prompt_id,
        prompt_version=body.prompt_version,
        provider_request_id=body.provider_request_id,
        batch_job_id=body.batch_job_id,
        input_tokens=body.input_tokens,
        output_tokens=body.output_tokens,
        total_tokens=body.total_tokens,
        cache_hit=body.cache_hit,
        escalation_occurred=body.escalation_occurred,
        escalation_reason=body.escalation_reason,
        duration_ms=body.duration_ms,
        metadata=body.metadata,
    )
    snap = budget_status_snapshot(session, body.organisation_id)
    evaluate_and_notify_thresholds(session, organisation_id=body.organisation_id, snapshot=snap)
    session.commit()
    return {"usage": usage_to_dict(record), "budget_status": snap}


@internal_router.post("/budget/expire-orphans")
def internal_expire_orphans(
    older_than_minutes: int = Query(60, ge=5, le=24 * 60),
    session: Session = Depends(get_session),
    _: None = Depends(require_ai_service_token),
) -> dict[str, Any]:
    apply_platform_rls_bypass(session)
    count = release_orphaned_reservations(session, older_than_minutes=older_than_minutes)
    session.commit()
    return {"expired": count}
