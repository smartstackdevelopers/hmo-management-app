"""AI cost dashboard aggregations (F3.3).

All aggregations apply organisation isolation before grouping. Super Admin
platform views must use RLS bypass via get_platform_context.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.ai_usage.budget import budget_status_snapshot
from app.ai_usage.period import period_key_for, previous_period_key
from app.db.models.ai_usage import AiUsageRecord
from app.db.models.organisation import Organisation


def _base_filters(
    *,
    organisation_id: UUID | None,
    period_key: str | None,
    period_from: str | None,
    period_to: str | None,
    feature_id: str | None,
    provider: str | None,
    model_id: str | None,
    execution_status: str | None,
) -> list:
    clauses: list = []
    if organisation_id is not None:
        clauses.append(AiUsageRecord.organisation_id == organisation_id)
    if period_key:
        clauses.append(AiUsageRecord.period_key == period_key)
    elif period_from and period_to:
        clauses.append(AiUsageRecord.period_key >= period_from)
        clauses.append(AiUsageRecord.period_key <= period_to)
    elif period_from:
        clauses.append(AiUsageRecord.period_key >= period_from)
    elif period_to:
        clauses.append(AiUsageRecord.period_key <= period_to)
    if feature_id:
        clauses.append(AiUsageRecord.feature_id == feature_id)
    if provider:
        clauses.append(AiUsageRecord.provider == provider)
    if model_id:
        clauses.append(AiUsageRecord.model_id == model_id)
    if execution_status:
        clauses.append(AiUsageRecord.execution_status == execution_status)
    return clauses


def _sum_actual_cost():
    return func.coalesce(
        func.sum(
            case(
                (
                    (AiUsageRecord.cost_status == "actual")
                    & (AiUsageRecord.execution_status == "completed")
                    & AiUsageRecord.cost_amount.is_not(None),
                    AiUsageRecord.cost_amount,
                ),
                else_=0,
            )
        ),
        0,
    )


def _apply_where(stmt, clauses: list):
    if clauses:
        return stmt.where(*clauses)
    return stmt


def organisation_dashboard(
    session: Session,
    organisation_id: UUID,
    *,
    period_key: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    feature_id: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    execution_status: str | None = None,
) -> dict[str, Any]:
    pk = period_key or (None if (period_from or period_to) else period_key_for())
    clauses = _base_filters(
        organisation_id=organisation_id,
        period_key=pk,
        period_from=period_from,
        period_to=period_to,
        feature_id=feature_id,
        provider=provider,
        model_id=model_id,
        execution_status=execution_status,
    )

    totals = session.execute(
        _apply_where(
            select(
                func.count(AiUsageRecord.id),
                func.coalesce(func.sum(AiUsageRecord.input_tokens), 0),
                func.coalesce(func.sum(AiUsageRecord.output_tokens), 0),
                _sum_actual_cost(),
                func.sum(case((AiUsageRecord.execution_status == "completed", 1), else_=0)),
                func.sum(case((AiUsageRecord.execution_status == "failed", 1), else_=0)),
                func.sum(case((AiUsageRecord.execution_status == "rejected_budget", 1), else_=0)),
                func.sum(case((AiUsageRecord.cache_hit.is_(True), 1), else_=0)),
                func.sum(case((AiUsageRecord.cache_hit.is_(False), 1), else_=0)),
                func.sum(case((AiUsageRecord.escalation_occurred.is_(True), 1), else_=0)),
                func.sum(case((AiUsageRecord.cost_status == "unavailable", 1), else_=0)),
            ),
            clauses,
        )
    ).one()

    by_feature = _group_breakdown(session, clauses, AiUsageRecord.feature_id, "feature_id")
    by_provider = _group_breakdown(session, clauses, AiUsageRecord.provider, "provider")
    by_model = _group_breakdown(session, clauses, AiUsageRecord.model_id, "model_id")
    by_status = _group_breakdown(session, clauses, AiUsageRecord.execution_status, "execution_status")

    budget = budget_status_snapshot(session, organisation_id, period_key=pk or period_key_for())

    return {
        "scope": "organisation",
        "organisation_id": str(organisation_id),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "period_key": pk,
            "period_from": period_from,
            "period_to": period_to,
            "feature_id": feature_id,
            "provider": provider,
            "model_id": model_id,
            "execution_status": execution_status,
        },
        "budget": budget,
        "totals": {
            "execution_count": int(totals[0] or 0),
            "input_tokens": int(totals[1] or 0),
            "output_tokens": int(totals[2] or 0),
            "actual_cost": str(Decimal(str(totals[3] or 0))),
            "completed_count": int(totals[4] or 0),
            "failed_count": int(totals[5] or 0),
            "rejected_budget_count": int(totals[6] or 0),
            "cache_hit_count": int(totals[7] or 0),
            "cache_miss_count": int(totals[8] or 0),
            "premium_escalation_count": int(totals[9] or 0),
            "unavailable_cost_count": int(totals[10] or 0),
        },
        "by_feature": by_feature,
        "by_provider": by_provider,
        "by_model": by_model,
        "by_status": by_status,
        "empty": int(totals[0] or 0) == 0,
    }


def _group_breakdown(session: Session, clauses: list, column, key_name: str) -> list[dict[str, Any]]:
    stmt = (
        select(
            column,
            func.count(AiUsageRecord.id),
            _sum_actual_cost(),
            func.coalesce(func.sum(AiUsageRecord.input_tokens), 0),
            func.coalesce(func.sum(AiUsageRecord.output_tokens), 0),
            func.sum(case((AiUsageRecord.execution_status == "completed", 1), else_=0)),
            func.sum(case((AiUsageRecord.execution_status == "failed", 1), else_=0)),
            func.sum(case((AiUsageRecord.cache_hit.is_(True), 1), else_=0)),
            func.sum(case((AiUsageRecord.escalation_occurred.is_(True), 1), else_=0)),
        )
        .group_by(column)
        .order_by(func.count(AiUsageRecord.id).desc())
    )
    rows = session.execute(_apply_where(stmt, clauses)).all()
    return [
        {
            key_name: (r[0] if r[0] is not None else "unknown"),
            "execution_count": int(r[1] or 0),
            "actual_cost": str(Decimal(str(r[2] or 0))),
            "input_tokens": int(r[3] or 0),
            "output_tokens": int(r[4] or 0),
            "completed_count": int(r[5] or 0),
            "failed_count": int(r[6] or 0),
            "cache_hit_count": int(r[7] or 0),
            "premium_escalation_count": int(r[8] or 0),
        }
        for r in rows
    ]


def platform_dashboard(
    session: Session,
    *,
    period_key: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    feature_id: str | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    execution_status: str | None = None,
) -> dict[str, Any]:
    """Platform-wide Super Admin view. Caller must enable RLS bypass."""
    pk = period_key or (None if (period_from or period_to) else period_key_for())
    clauses = _base_filters(
        organisation_id=None,
        period_key=pk,
        period_from=period_from,
        period_to=period_to,
        feature_id=feature_id,
        provider=provider,
        model_id=model_id,
        execution_status=execution_status,
    )

    totals = session.execute(
        _apply_where(
            select(
                func.count(AiUsageRecord.id),
                _sum_actual_cost(),
                func.coalesce(func.sum(AiUsageRecord.input_tokens), 0),
                func.coalesce(func.sum(AiUsageRecord.output_tokens), 0),
                func.sum(case((AiUsageRecord.execution_status == "failed", 1), else_=0)),
                func.sum(case((AiUsageRecord.execution_status == "rejected_budget", 1), else_=0)),
                func.sum(case((AiUsageRecord.cache_hit.is_(True), 1), else_=0)),
                func.sum(case((AiUsageRecord.escalation_occurred.is_(True), 1), else_=0)),
            ),
            clauses,
        )
    ).one()

    org_stmt = (
        select(
            AiUsageRecord.organisation_id,
            func.count(AiUsageRecord.id),
            _sum_actual_cost(),
        )
        .group_by(AiUsageRecord.organisation_id)
        .order_by(_sum_actual_cost().desc())
    )
    org_rows = session.execute(_apply_where(org_stmt, clauses)).all()

    org_names = {str(o.id): o.name for o in session.scalars(select(Organisation)).all()}

    organisations: list[dict[str, Any]] = []
    approaching: list[dict[str, Any]] = []
    exhausted: list[dict[str, Any]] = []
    for org_id, count, cost in org_rows:
        snap = budget_status_snapshot(session, org_id, period_key=pk or period_key_for())
        entry = {
            "organisation_id": str(org_id),
            "organisation_name": org_names.get(str(org_id)),
            "execution_count": int(count or 0),
            "actual_cost": str(Decimal(str(cost or 0))),
            "budget": snap,
        }
        organisations.append(entry)
        if snap.get("budget_exhausted"):
            exhausted.append(entry)
        elif snap.get("approaching_limit"):
            approaching.append(entry)

    return {
        "scope": "platform",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": {
            "period_key": pk,
            "period_from": period_from,
            "period_to": period_to,
            "feature_id": feature_id,
            "provider": provider,
            "model_id": model_id,
            "execution_status": execution_status,
        },
        "totals": {
            "execution_count": int(totals[0] or 0),
            "actual_cost": str(Decimal(str(totals[1] or 0))),
            "input_tokens": int(totals[2] or 0),
            "output_tokens": int(totals[3] or 0),
            "failed_count": int(totals[4] or 0),
            "rejected_budget_count": int(totals[5] or 0),
            "cache_hit_count": int(totals[6] or 0),
            "premium_escalation_count": int(totals[7] or 0),
        },
        "organisations": organisations,
        "approaching_limit": approaching,
        "budget_exhausted": exhausted,
        "by_feature": _group_breakdown(session, clauses, AiUsageRecord.feature_id, "feature_id"),
        "by_provider": _group_breakdown(session, clauses, AiUsageRecord.provider, "provider"),
        "by_model": _group_breakdown(session, clauses, AiUsageRecord.model_id, "model_id"),
        "empty": int(totals[0] or 0) == 0,
        "suggested_periods": {
            "current": period_key_for(),
            "previous": previous_period_key(period_key_for()),
        },
    }
