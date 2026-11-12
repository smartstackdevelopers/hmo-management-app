"""F6.6 finance records, budgets, dashboard, and exports."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.finance import FinanceBudget, FinanceBudgetLine, FinanceRecord
from app.db.models.landlord_enterprise import RentRecord
from app.db.models.property import Property
from app.finance import access
from app.finance.constants import (
    BUDGET_STATUSES,
    DEFAULT_CATEGORIES,
    FINANCE_DISCLAIMER,
    RECORD_STATUSES,
    RECORD_TYPES,
)
from app.rbac.permissions import Permission
from app.reporting.exports import rows_to_csv, rows_to_xlsx, summary_to_pdf
from app.tenancy.context import OrganisationContext


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dec(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _append_history(row: FinanceRecord, entry: dict[str, Any]) -> None:
    history = list(row.history_json or [])
    history.append(entry)
    row.history_json = history[-100:]


def record_to_dict(row: FinanceRecord) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "record_type": row.record_type,
        "category_code": row.category_code,
        "category_label": row.category_label,
        "amount": str(row.amount),
        "currency": row.currency,
        "effective_date": row.effective_date.isoformat(),
        "reference": row.reference,
        "description": row.description,
        "status": row.status,
        "property_id": str(row.property_id) if row.property_id else None,
        "rent_record_id": str(row.rent_record_id) if row.rent_record_id else None,
        "supporting_file_id": str(row.supporting_file_id) if row.supporting_file_id else None,
        "history": row.history_json or [],
        "void_reason": row.void_reason,
        "voided_at": row.voided_at.isoformat() if row.voided_at else None,
        "is_archived": row.is_archived,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def budget_to_dict(row: FinanceBudget, lines: list[FinanceBudgetLine] | None = None) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "currency": row.currency,
        "status": row.status,
        "notes": row.notes,
        "property_id": str(row.property_id) if row.property_id else None,
        "lines": [
            {
                "id": str(line.id),
                "category_code": line.category_code,
                "category_label": line.category_label,
                "planned_amount": str(line.planned_amount),
                "sort_order": line.sort_order,
                "notes": line.notes,
            }
            for line in (lines or [])
        ],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def categories() -> list[dict[str, str]]:
    return [{"code": k, "label": v} for k, v in DEFAULT_CATEGORIES.items()]


def create_record(
    session: Session,
    ctx: OrganisationContext,
    *,
    record_type: str,
    category_code: str,
    amount: Decimal | float | int | str,
    effective_date: date,
    category_label: str | None = None,
    currency: str = "GBP",
    reference: str | None = None,
    description: str | None = None,
    status: str = "draft",
    property_id: uuid.UUID | None = None,
    rent_record_id: uuid.UUID | None = None,
    supporting_file_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    access.require_finance_manage(ctx)
    if record_type not in RECORD_TYPES:
        raise HTTPException(status_code=400, detail="Invalid record_type")
    if status not in RECORD_STATUSES or status == "voided":
        raise HTTPException(status_code=400, detail="Invalid status for create")
    amt = _dec(amount)
    if amt < 0:
        raise HTTPException(status_code=400, detail="Amount must be >= 0")
    label = category_label or DEFAULT_CATEGORIES.get(category_code) or category_code
    if property_id is not None:
        prop = session.get(Property, property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Property not found")
    if rent_record_id is not None:
        rent = session.get(RentRecord, rent_record_id)
        if rent is None or rent.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Rent record not found")
        if property_id is None:
            property_id = rent.property_id

    row = FinanceRecord(
        organisation_id=ctx.organisation_id,
        record_type=record_type,
        category_code=category_code.strip()[:64],
        category_label=label.strip()[:120],
        amount=amt,
        currency=(currency or "GBP")[:3].upper(),
        effective_date=effective_date,
        reference=(reference or None),
        description=description,
        status=status,
        property_id=property_id,
        rent_record_id=rent_record_id,
        supporting_file_id=supporting_file_id,
        history_json=[
            {
                "at": _now().isoformat(),
                "action": "create",
                "by": str(ctx.user_id),
                "status": status,
                "amount": str(amt),
            }
        ],
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
    )
    session.add(row)
    session.flush()
    record_event(
        session,
        action=audit_events.FINANCE_RECORD_CREATE,
        resource_type="finance_record",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Created finance {record_type} record {label}",
        metadata={"amount": str(amt), "status": status},
        raise_on_error=False,
    )
    return record_to_dict(row)


def update_record(
    session: Session,
    ctx: OrganisationContext,
    record_id: uuid.UUID,
    *,
    category_code: str | None = None,
    category_label: str | None = None,
    amount: Decimal | float | int | str | None = None,
    effective_date: date | None = None,
    reference: str | None = None,
    description: str | None = None,
    status: str | None = None,
    property_id: uuid.UUID | None = None,
    supporting_file_id: uuid.UUID | None = None,
    clear_supporting_file: bool = False,
) -> dict[str, Any]:
    access.require_finance_manage(ctx)
    row = _get_record(session, ctx, record_id)
    if row.status == "voided" or row.is_archived:
        raise HTTPException(status_code=400, detail="Cannot update voided/archived record")
    changes: dict[str, Any] = {}
    if category_code is not None:
        row.category_code = category_code.strip()[:64]
        changes["category_code"] = row.category_code
    if category_label is not None:
        row.category_label = category_label.strip()[:120]
        changes["category_label"] = row.category_label
    if amount is not None:
        row.amount = _dec(amount)
        if row.amount < 0:
            raise HTTPException(status_code=400, detail="Amount must be >= 0")
        changes["amount"] = str(row.amount)
    if effective_date is not None:
        row.effective_date = effective_date
        changes["effective_date"] = effective_date.isoformat()
    if reference is not None:
        row.reference = reference
        changes["reference"] = reference
    if description is not None:
        row.description = description
        changes["description"] = description
    if status is not None:
        if status not in RECORD_STATUSES or status == "voided":
            raise HTTPException(status_code=400, detail="Use void endpoint to void a record")
        row.status = status
        changes["status"] = status
    if property_id is not None:
        prop = session.get(Property, property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Property not found")
        row.property_id = property_id
        changes["property_id"] = str(property_id)
    if clear_supporting_file:
        row.supporting_file_id = None
        changes["supporting_file_id"] = None
    elif supporting_file_id is not None:
        row.supporting_file_id = supporting_file_id
        changes["supporting_file_id"] = str(supporting_file_id)
    row.updated_by_user_id = ctx.user_id
    _append_history(
        row,
        {"at": _now().isoformat(), "action": "update", "by": str(ctx.user_id), "changes": changes},
    )
    session.flush()
    record_event(
        session,
        action=audit_events.FINANCE_RECORD_UPDATE,
        resource_type="finance_record",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Updated finance record {row.category_label}",
        raise_on_error=False,
    )
    return record_to_dict(row)


def void_record(session: Session, ctx: OrganisationContext, record_id: uuid.UUID, reason: str) -> dict[str, Any]:
    access.require_finance_manage(ctx)
    if not reason.strip():
        raise HTTPException(status_code=400, detail="Void reason required")
    row = _get_record(session, ctx, record_id)
    if row.status == "voided":
        return record_to_dict(row)
    row.status = "voided"
    row.voided_at = _now()
    row.voided_by_user_id = ctx.user_id
    row.void_reason = reason.strip()[:2000]
    row.updated_by_user_id = ctx.user_id
    _append_history(
        row,
        {"at": _now().isoformat(), "action": "void", "by": str(ctx.user_id), "reason": row.void_reason},
    )
    session.flush()
    record_event(
        session,
        action=audit_events.FINANCE_RECORD_VOID,
        resource_type="finance_record",
        resource_id=row.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Voided finance record {row.category_label}",
        raise_on_error=False,
    )
    return record_to_dict(row)


def _get_record(session: Session, ctx: OrganisationContext, record_id: uuid.UUID) -> FinanceRecord:
    row = session.get(FinanceRecord, record_id)
    if row is None or row.organisation_id != ctx.organisation_id or row.is_archived:
        raise HTTPException(status_code=404, detail="Finance record not found")
    return row


def list_records(
    session: Session,
    ctx: OrganisationContext,
    *,
    record_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    access.require_finance_read(ctx)
    stmt = select(FinanceRecord).where(
        FinanceRecord.organisation_id == ctx.organisation_id,
        FinanceRecord.is_archived.is_(False),
    )
    if record_type:
        stmt = stmt.where(FinanceRecord.record_type == record_type)
    if status:
        stmt = stmt.where(FinanceRecord.status == status)
    rows = session.scalars(stmt.order_by(FinanceRecord.effective_date.desc()).limit(limit)).all()
    return [record_to_dict(r) for r in rows]


def create_budget(
    session: Session,
    ctx: OrganisationContext,
    *,
    name: str,
    period_start: date,
    period_end: date,
    lines: list[dict[str, Any]],
    currency: str = "GBP",
    notes: str | None = None,
    property_id: uuid.UUID | None = None,
    status: str = "draft",
) -> dict[str, Any]:
    access.require_budget_manage(ctx)
    if period_end < period_start:
        raise HTTPException(status_code=400, detail="period_end must be on/after period_start")
    if status not in BUDGET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid budget status")
    if property_id is not None:
        prop = session.get(Property, property_id)
        if prop is None or prop.organisation_id != ctx.organisation_id:
            raise HTTPException(status_code=404, detail="Property not found")
    budget = FinanceBudget(
        organisation_id=ctx.organisation_id,
        name=name.strip()[:200],
        period_start=period_start,
        period_end=period_end,
        currency=(currency or "GBP")[:3].upper(),
        status=status,
        notes=notes,
        property_id=property_id,
        created_by_user_id=ctx.user_id,
    )
    session.add(budget)
    session.flush()
    created_lines: list[FinanceBudgetLine] = []
    for idx, raw in enumerate(lines or []):
        code = str(raw.get("category_code") or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail=f"lines[{idx}] missing category_code")
        label = str(raw.get("category_label") or DEFAULT_CATEGORIES.get(code) or code)
        planned = _dec(raw.get("planned_amount") or 0)
        line = FinanceBudgetLine(
            organisation_id=ctx.organisation_id,
            budget_id=budget.id,
            category_code=code[:64],
            category_label=label[:120],
            planned_amount=planned,
            sort_order=int(raw.get("sort_order") or idx),
            notes=raw.get("notes"),
        )
        session.add(line)
        created_lines.append(line)
    session.flush()
    record_event(
        session,
        action=audit_events.FINANCE_BUDGET_CREATE,
        resource_type="finance_budget",
        resource_id=budget.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Created budget {budget.name}",
        raise_on_error=False,
    )
    return budget_to_dict(budget, created_lines)


def list_budgets(session: Session, ctx: OrganisationContext) -> list[dict[str, Any]]:
    access.require_budget_read(ctx)
    budgets = session.scalars(
        select(FinanceBudget)
        .where(FinanceBudget.organisation_id == ctx.organisation_id)
        .order_by(FinanceBudget.period_start.desc())
    ).all()
    out = []
    for b in budgets:
        lines = session.scalars(
            select(FinanceBudgetLine)
            .where(FinanceBudgetLine.budget_id == b.id)
            .order_by(FinanceBudgetLine.sort_order)
        ).all()
        out.append(budget_to_dict(b, list(lines)))
    return out


def update_budget_status(
    session: Session, ctx: OrganisationContext, budget_id: uuid.UUID, status: str
) -> dict[str, Any]:
    access.require_budget_manage(ctx)
    if status not in BUDGET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid budget status")
    budget = session.get(FinanceBudget, budget_id)
    if budget is None or budget.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Budget not found")
    budget.status = status
    session.flush()
    action = (
        audit_events.FINANCE_BUDGET_ACTIVATE
        if status == "active"
        else audit_events.FINANCE_BUDGET_CLOSE
        if status == "closed"
        else audit_events.FINANCE_BUDGET_CREATE
    )
    record_event(
        session,
        action=action,
        resource_type="finance_budget",
        resource_id=budget.id,
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Budget {budget.name} -> {status}",
        raise_on_error=False,
    )
    lines = session.scalars(select(FinanceBudgetLine).where(FinanceBudgetLine.budget_id == budget.id)).all()
    return budget_to_dict(budget, list(lines))


def budget_variance(session: Session, ctx: OrganisationContext, budget_id: uuid.UUID) -> dict[str, Any]:
    access.require_budget_read(ctx)
    budget = session.get(FinanceBudget, budget_id)
    if budget is None or budget.organisation_id != ctx.organisation_id:
        raise HTTPException(status_code=404, detail="Budget not found")
    lines = session.scalars(
        select(FinanceBudgetLine)
        .where(FinanceBudgetLine.budget_id == budget.id)
        .order_by(FinanceBudgetLine.sort_order)
    ).all()
    comparisons = []
    for line in lines:
        actual = session.scalar(
            select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
                FinanceRecord.organisation_id == ctx.organisation_id,
                FinanceRecord.is_archived.is_(False),
                FinanceRecord.status == "posted",
                FinanceRecord.category_code == line.category_code,
                FinanceRecord.effective_date >= budget.period_start,
                FinanceRecord.effective_date <= budget.period_end,
            )
        )
        actual_d = _dec(actual or 0)
        planned = _dec(line.planned_amount)
        variance = actual_d - planned
        comparisons.append(
            {
                "category_code": line.category_code,
                "category_label": line.category_label,
                "planned_amount": str(planned),
                "actual_amount": str(actual_d),
                "variance": str(variance),
            }
        )
    return {
        "budget": budget_to_dict(budget, list(lines)),
        "comparisons": comparisons,
        "disclaimer": FINANCE_DISCLAIMER,
    }


def dashboard(session: Session, ctx: OrganisationContext) -> dict[str, Any]:
    access.require_finance_read(ctx)
    org = ctx.organisation_id
    income = session.scalar(
        select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.organisation_id == org,
            FinanceRecord.is_archived.is_(False),
            FinanceRecord.status == "posted",
            FinanceRecord.record_type == "income",
        )
    )
    expense = session.scalar(
        select(func.coalesce(func.sum(FinanceRecord.amount), 0)).where(
            FinanceRecord.organisation_id == org,
            FinanceRecord.is_archived.is_(False),
            FinanceRecord.status == "posted",
            FinanceRecord.record_type == "expense",
        )
    )
    rent_outstanding = session.scalar(
        select(func.coalesce(func.sum(RentRecord.amount), 0)).where(
            RentRecord.organisation_id == org,
            RentRecord.is_archived.is_(False),
            RentRecord.status.in_(("due", "outstanding")),
        )
    )
    rent_recorded = session.scalar(
        select(func.count()).select_from(RentRecord).where(
            RentRecord.organisation_id == org,
            RentRecord.is_archived.is_(False),
        )
    )
    return {
        "generated_at": _now().isoformat(),
        "disclaimer": FINANCE_DISCLAIMER,
        "income_posted": str(_dec(income or 0)),
        "expense_posted": str(_dec(expense or 0)),
        "net_posted": str(_dec(income or 0) - _dec(expense or 0)),
        "rent_outstanding_total": str(_dec(rent_outstanding or 0)),
        "rent_record_count": int(rent_recorded or 0),
        "recent_records": list_records(session, ctx, limit=10),
        "budgets": (
            list_budgets(session, ctx)[:5]
            if ctx.authorization.has_permission(Permission.FINANCE_BUDGETS_READ)
            or ctx.authorization.has_permission(Permission.FINANCE_BUDGETS_MANAGE)
            else []
        ),
        "categories": categories(),
    }


def export_records(
    session: Session,
    ctx: OrganisationContext,
    *,
    export_format: Literal["csv", "pdf", "xlsx"] = "csv",
) -> tuple[bytes, str, str]:
    access.require_finance_export(ctx)
    rows = list_records(session, ctx, limit=500)
    headers = [
        "id",
        "record_type",
        "category_code",
        "category_label",
        "amount",
        "currency",
        "effective_date",
        "status",
        "reference",
    ]
    flat = [{h: r.get(h) for h in headers} for r in rows]
    record_event(
        session,
        action=audit_events.FINANCE_EXPORT,
        resource_type="finance_export",
        organisation_id=ctx.organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary=f"Exported finance records as {export_format}",
        raise_on_error=False,
    )
    if export_format == "csv":
        return rows_to_csv(headers, flat), "text/csv", "finance-records.csv"
    if export_format == "xlsx":
        return rows_to_xlsx("Finance", headers, flat), (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ), "finance-records.xlsx"
    pdf = summary_to_pdf(
        "Finance records export",
        {"count": len(rows), "disclaimer": FINANCE_DISCLAIMER},
        [f"{r['effective_date']} {r['record_type']} {r['category_label']} {r['amount']} {r['status']}" for r in rows],
    )
    return pdf, "application/pdf", "finance-records.pdf"
