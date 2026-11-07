"""Organisation AI budget configuration, reservation and hard-cap enforcement (F3.3).

Reservation algorithm
---------------------
1. Resolve the active budget for the organisation on the current UTC calendar month.
2. Sum billable consumption for the period:
   - Actual cost_amount for completed usage with cost_status='actual'
   - Plus open reservation reserved_amount (conservative in-flight hold)
3. If remaining < requested reservation → reject visibly (hard cap).
4. Insert an open reservation keyed by unique request_id (idempotent on retry).
5. After provider completion, reconcile: record usage with calculated cost,
   set reservation status to reconciled/released, and release unused hold.

Limitations
-----------
- Pre-execution cost is unknown; reservation uses budget.default_reservation_amount
  (or an explicit override), which is a conservative estimate — never treated as
  an actual provider charge.
- Concurrent requests are serialised per organisation via SELECT ... FOR UPDATE
  on the active budget row.
- Cache hits that skip the provider still create a zero-cost usage record after
  a short-circuit path (no reservation held when billable=False / cache_hit).
- Orphaned open reservations older than the retention window should be expired
  by the reconciliation job (release_orphaned_reservations).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.ai_usage.period import period_key_for
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.ai_usage import AiBudgetReservation, AiUsageRecord, OrganisationAiBudget
from app.tenancy.context import OrganisationContext

ZERO = Decimal("0.0000")


class BudgetExceededError(Exception):
    """Hard AI usage cap reached — callers must surface this visibly."""

    def __init__(
        self,
        message: str,
        *,
        organisation_id: UUID,
        period_key: str,
        monthly_limit: Decimal | None,
        consumed: Decimal,
        remaining: Decimal,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.organisation_id = organisation_id
        self.period_key = period_key
        self.monthly_limit = monthly_limit
        self.consumed = consumed
        self.remaining = remaining

    def to_http(self) -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "error": "ai_budget_exceeded",
                "message": self.message,
                "organisation_id": str(self.organisation_id),
                "period_key": self.period_key,
                "monthly_limit": str(self.monthly_limit) if self.monthly_limit is not None else None,
                "consumed": str(self.consumed),
                "remaining": str(self.remaining),
            },
        )


def get_active_budget(
    session: Session,
    organisation_id: UUID,
    *,
    on_date: date | None = None,
    for_update: bool = False,
) -> OrganisationAiBudget | None:
    day = on_date or date.today()
    stmt = (
        select(OrganisationAiBudget)
        .where(
            OrganisationAiBudget.organisation_id == organisation_id,
            OrganisationAiBudget.active.is_(True),
            OrganisationAiBudget.effective_from <= day,
            or_(
                OrganisationAiBudget.effective_to.is_(None),
                OrganisationAiBudget.effective_to >= day,
            ),
        )
        .order_by(OrganisationAiBudget.effective_from.desc())
        .limit(1)
    )
    if for_update:
        stmt = stmt.with_for_update()
    return session.scalars(stmt).first()


def period_actual_spend(session: Session, organisation_id: UUID, period_key: str) -> Decimal:
    """Sum actual costs for completed usage in the period. Estimated/unavailable excluded."""
    total = session.scalar(
        select(func.coalesce(func.sum(AiUsageRecord.cost_amount), 0)).where(
            AiUsageRecord.organisation_id == organisation_id,
            AiUsageRecord.period_key == period_key,
            AiUsageRecord.execution_status == "completed",
            AiUsageRecord.cost_status == "actual",
            AiUsageRecord.cost_amount.is_not(None),
        )
    )
    return Decimal(str(total or 0))


def period_open_reservations(session: Session, organisation_id: UUID, period_key: str) -> Decimal:
    total = session.scalar(
        select(func.coalesce(func.sum(AiBudgetReservation.reserved_amount), 0)).where(
            AiBudgetReservation.organisation_id == organisation_id,
            AiBudgetReservation.period_key == period_key,
            AiBudgetReservation.status == "open",
        )
    )
    return Decimal(str(total or 0))


def budget_status_snapshot(
    session: Session,
    organisation_id: UUID,
    *,
    period_key: str | None = None,
) -> dict[str, Any]:
    pk = period_key or period_key_for()
    budget = get_active_budget(session, organisation_id)
    actual = period_actual_spend(session, organisation_id, pk)
    reserved = period_open_reservations(session, organisation_id, pk)
    consumed = actual + reserved
    limit = budget.monthly_limit if budget else None
    remaining = (limit - consumed) if limit is not None else None
    util_pct: Decimal | None = None
    warning = False
    exhausted = False
    if limit is not None and limit > 0:
        util_pct = (consumed / limit * Decimal("100")).quantize(Decimal("0.01"))
        threshold = budget.warning_threshold_pct if budget else Decimal("80")
        warning = util_pct >= threshold
        exhausted = remaining is not None and remaining <= ZERO
    elif limit == ZERO:
        exhausted = True
        util_pct = Decimal("100.00")
        warning = True

    return {
        "organisation_id": str(organisation_id),
        "period_key": pk,
        "budget_id": str(budget.id) if budget else None,
        "currency": budget.currency if budget else None,
        "monthly_limit": str(limit) if limit is not None else None,
        "actual_spend": str(actual),
        "open_reservations": str(reserved),
        "consumed": str(consumed),
        "remaining": str(remaining) if remaining is not None else None,
        "utilisation_pct": str(util_pct) if util_pct is not None else None,
        "warning_threshold_pct": str(budget.warning_threshold_pct) if budget else None,
        "approaching_limit": warning and not exhausted,
        "budget_exhausted": exhausted,
        "active": bool(budget and budget.active),
        "budget_configured": budget is not None,
    }


def upsert_budget(
    session: Session,
    ctx: OrganisationContext,
    organisation_id: UUID,
    body: dict[str, Any],
) -> OrganisationAiBudget:
    if organisation_id != ctx.organisation_id and ctx.role.value != "super_admin":
        # Organisation context must match unless Super Admin entered that org scope.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organisation mismatch")

    # Deactivate overlapping active budgets for this org (preserve history rows).
    existing_active = list(
        session.scalars(
            select(OrganisationAiBudget).where(
                OrganisationAiBudget.organisation_id == organisation_id,
                OrganisationAiBudget.active.is_(True),
            )
        )
    )
    for row in existing_active:
        row.active = False
        row.updated_by_user_id = ctx.user_id

    budget = OrganisationAiBudget(
        id=uuid.uuid4(),
        organisation_id=organisation_id,
        currency=body["currency"],
        monthly_limit=body["monthly_limit"],
        period_kind=body.get("period_kind", "calendar_month"),
        effective_from=body["effective_from"],
        effective_to=body.get("effective_to"),
        active=body.get("active", True),
        warning_threshold_pct=body.get("warning_threshold_pct", Decimal("80.00")),
        default_reservation_amount=body.get("default_reservation_amount", Decimal("0.0500")),
        created_by_user_id=ctx.user_id,
        updated_by_user_id=ctx.user_id,
        notes=body.get("notes"),
    )
    session.add(budget)
    session.flush()
    record_event(
        session,
        action=audit_events.AI_BUDGET_UPSERT,
        resource_type="organisation_ai_budget",
        resource_id=str(budget.id),
        organisation_id=organisation_id,
        actor_user_id=ctx.user_id,
        actor_role=ctx.role.value,
        outcome=AuditOutcome.SUCCESS,
        summary="Organisation AI budget configured",
        metadata={
            "monthly_limit": str(budget.monthly_limit),
            "currency": budget.currency,
            "warning_threshold_pct": str(budget.warning_threshold_pct),
        },
        raise_on_error=False,
    )
    return budget


def list_budget_history(session: Session, organisation_id: UUID) -> list[OrganisationAiBudget]:
    return list(
        session.scalars(
            select(OrganisationAiBudget)
            .where(OrganisationAiBudget.organisation_id == organisation_id)
            .order_by(OrganisationAiBudget.created_at.desc())
        )
    )


def reserve_budget(
    session: Session,
    *,
    request_id: str,
    organisation_id: UUID,
    user_id: UUID | None,
    feature_id: str,
    workflow_id: str,
    reserved_amount: Decimal | None = None,
    billable: bool = True,
    cache_hit: bool = False,
) -> dict[str, Any]:
    """Atomically reserve budget before a billable AI dispatch.

    Idempotent: repeating the same request_id returns the existing reservation.
    Non-billable / cache-hit short-circuit: no reservation, permitted=True.
    """
    period_key = period_key_for()

    existing = session.scalars(
        select(AiBudgetReservation).where(AiBudgetReservation.request_id == request_id)
    ).first()
    if existing:
        return {
            "permitted": existing.status == "open" or existing.status == "reconciled",
            "request_id": request_id,
            "reservation_id": str(existing.id),
            "status": existing.status,
            "reserved_amount": str(existing.reserved_amount),
            "period_key": existing.period_key,
            "idempotent": True,
        }

    if not billable or cache_hit:
        return {
            "permitted": True,
            "request_id": request_id,
            "reservation_id": None,
            "status": "skipped",
            "reserved_amount": "0",
            "period_key": period_key,
            "idempotent": False,
            "reason": "non_billable_or_cache_hit",
        }

    # Lock the active budget row to serialise concurrent reservations.
    budget = get_active_budget(session, organisation_id, for_update=True)
    if budget is None:
        # No configured budget → hard reject (do not invent a universal limit).
        raise BudgetExceededError(
            "No active AI budget is configured for this organisation",
            organisation_id=organisation_id,
            period_key=period_key,
            monthly_limit=None,
            consumed=ZERO,
            remaining=ZERO,
        )

    amount = reserved_amount if reserved_amount is not None else budget.default_reservation_amount
    if amount < ZERO:
        raise HTTPException(status_code=400, detail="reserved_amount must be non-negative")

    actual = period_actual_spend(session, organisation_id, period_key)
    open_res = period_open_reservations(session, organisation_id, period_key)
    consumed = actual + open_res
    remaining = budget.monthly_limit - consumed

    if remaining < amount:
        record_event(
            session,
            action=audit_events.AI_BUDGET_CAP_REJECTED,
            resource_type="ai_budget_reservation",
            resource_id=request_id,
            organisation_id=organisation_id,
            actor_user_id=user_id,
            actor_role=None,
            outcome=AuditOutcome.DENIED,
            summary="AI usage cap reached — request rejected",
            metadata={
                "period_key": period_key,
                "monthly_limit": str(budget.monthly_limit),
                "consumed": str(consumed),
                "remaining": str(remaining),
                "requested": str(amount),
                "feature_id": feature_id,
                "workflow_id": workflow_id,
            },
            raise_on_error=False,
        )
        # Persist a rejected usage marker (no double-count as completed).
        _record_rejection(
            session,
            request_id=request_id,
            organisation_id=organisation_id,
            user_id=user_id,
            feature_id=feature_id,
            workflow_id=workflow_id,
            period_key=period_key,
        )
        raise BudgetExceededError(
            "Organisation AI usage limit has been reached for this period",
            organisation_id=organisation_id,
            period_key=period_key,
            monthly_limit=budget.monthly_limit,
            consumed=consumed,
            remaining=remaining if remaining > ZERO else ZERO,
        )

    reservation = AiBudgetReservation(
        id=uuid.uuid4(),
        organisation_id=organisation_id,
        request_id=request_id,
        user_id=user_id,
        feature_id=feature_id,
        workflow_id=workflow_id,
        reserved_amount=amount,
        currency=budget.currency,
        status="open",
        period_key=period_key,
    )
    session.add(reservation)
    session.flush()
    record_event(
        session,
        action=audit_events.AI_BUDGET_RESERVED,
        resource_type="ai_budget_reservation",
        resource_id=str(reservation.id),
        organisation_id=organisation_id,
        actor_user_id=user_id,
        actor_role=None,
        outcome=AuditOutcome.SUCCESS,
        summary="AI budget reserved",
        metadata={
            "request_id": request_id,
            "reserved_amount": str(amount),
            "period_key": period_key,
            "feature_id": feature_id,
        },
        raise_on_error=False,
    )
    return {
        "permitted": True,
        "request_id": request_id,
        "reservation_id": str(reservation.id),
        "status": "open",
        "reserved_amount": str(amount),
        "period_key": period_key,
        "currency": budget.currency,
        "idempotent": False,
        "remaining_after_reserve": str(remaining - amount),
    }


def _record_rejection(
    session: Session,
    *,
    request_id: str,
    organisation_id: UUID,
    user_id: UUID | None,
    feature_id: str,
    workflow_id: str,
    period_key: str,
) -> None:
    existing = session.scalars(select(AiUsageRecord).where(AiUsageRecord.request_id == request_id)).first()
    if existing:
        return
    session.add(
        AiUsageRecord(
            id=uuid.uuid4(),
            organisation_id=organisation_id,
            request_id=request_id,
            user_id=user_id,
            workflow_id=workflow_id,
            feature_id=feature_id,
            execution_status="rejected_budget",
            cost_status="unavailable",
            period_key=period_key,
            executed_at=datetime.now(timezone.utc),
            metadata_json={"reason": "budget_exceeded"},
        )
    )
    session.flush()


def release_orphaned_reservations(
    session: Session,
    *,
    older_than_minutes: int = 60,
) -> int:
    """Mark open reservations older than the window as expired (worker-crash recovery)."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=older_than_minutes)
    rows = list(
        session.scalars(
            select(AiBudgetReservation).where(
                AiBudgetReservation.status == "open",
                AiBudgetReservation.created_at < cutoff,
            )
        )
    )
    for row in rows:
        row.status = "expired"
        record_event(
            session,
            action=audit_events.AI_BUDGET_RESERVATION_EXPIRED,
            resource_type="ai_budget_reservation",
            resource_id=str(row.id),
            organisation_id=row.organisation_id,
            actor_user_id=None,
            actor_role=None,
            outcome=AuditOutcome.SUCCESS,
            summary="Orphaned AI budget reservation expired",
            metadata={"request_id": row.request_id, "reserved_amount": str(row.reserved_amount)},
            raise_on_error=False,
        )
    session.flush()
    return len(rows)


def lock_organisation_advisory(session: Session, organisation_id: UUID) -> None:
    """Optional pg_advisory_xact_lock keyed by org UUID for extra serialisation."""
    # Use two int32 keys derived from UUID bits for transaction-scoped lock.
    hex_id = organisation_id.hex
    k1 = int(hex_id[:8], 16) & 0x7FFFFFFF
    k2 = int(hex_id[8:16], 16) & 0x7FFFFFFF
    session.execute(text("SELECT pg_advisory_xact_lock(:k1, :k2)"), {"k1": k1, "k2": k2})
