"""AI usage metering and reservation reconciliation (F3.3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai_usage.cost import resolve_cost_for_usage
from app.ai_usage.period import period_key_for
from app.audit import events as audit_events
from app.audit.service import AuditOutcome, record_event
from app.db.models.ai_usage import AiBudgetReservation, AiUsageRecord


def record_and_reconcile(
    session: Session,
    *,
    request_id: str,
    organisation_id: UUID,
    execution_status: str,
    feature_id: str,
    workflow_id: str,
    user_id: UUID | None = None,
    provider: str | None = None,
    model_id: str | None = None,
    prompt_id: str | None = None,
    prompt_version: str | None = None,
    provider_request_id: str | None = None,
    batch_job_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
    cache_hit: bool | None = None,
    escalation_occurred: bool | None = None,
    escalation_reason: str | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AiUsageRecord:
    """Persist immutable usage and reconcile any open reservation.

    Duplicate request_id returns the existing record (no double-count).
    Failed/cancelled executions do not contribute actual spend.
    """
    existing = session.scalars(select(AiUsageRecord).where(AiUsageRecord.request_id == request_id)).first()
    if existing:
        return existing

    period_key = period_key_for()
    cost = resolve_cost_for_usage(
        session,
        provider=provider,
        model_id=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hit=cache_hit,
    )

    # Only completed executions with actual cost count toward the budget.
    cost_amount = cost.amount if execution_status == "completed" else None
    cost_status = cost.cost_status if execution_status == "completed" else "unavailable"
    if execution_status != "completed":
        cost_amount = None
        cost_status = "unavailable"

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    record = AiUsageRecord(
        id=uuid.uuid4(),
        organisation_id=organisation_id,
        request_id=request_id,
        user_id=user_id,
        workflow_id=workflow_id,
        feature_id=feature_id,
        provider=provider,
        model_id=model_id,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        provider_request_id=provider_request_id,
        batch_job_id=batch_job_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cache_hit=cache_hit,
        escalation_occurred=escalation_occurred,
        escalation_reason=escalation_reason,
        execution_status=execution_status,
        duration_ms=duration_ms,
        cost_amount=cost_amount,
        cost_status=cost_status,
        currency=cost.currency if cost_amount is not None else None,
        pricing_version=cost.pricing_version if cost_amount is not None else None,
        period_key=period_key,
        executed_at=datetime.now(timezone.utc),
        metadata_json={
            **(metadata or {}),
            "cost_reason": cost.reason,
        },
    )
    session.add(record)
    session.flush()

    reservation = session.scalars(
        select(AiBudgetReservation).where(AiBudgetReservation.request_id == request_id)
    ).first()
    if reservation and reservation.status == "open":
        if execution_status == "completed" and cost_amount is not None:
            reservation.status = "reconciled"
            reservation.reconciled_amount = cost_amount
        else:
            # Failure / unavailable cost: release the hold entirely.
            reservation.status = "released"
            reservation.reconciled_amount = Decimal("0")
        reservation.usage_record_id = record.id
        session.flush()
        record_event(
            session,
            action=audit_events.AI_BUDGET_RECONCILED,
            resource_type="ai_budget_reservation",
            resource_id=str(reservation.id),
            organisation_id=organisation_id,
            actor_user_id=user_id,
            actor_role=None,
            outcome=AuditOutcome.SUCCESS,
            summary="AI budget reservation reconciled",
            metadata={
                "request_id": request_id,
                "reservation_status": reservation.status,
                "reconciled_amount": str(reservation.reconciled_amount)
                if reservation.reconciled_amount is not None
                else None,
                "execution_status": execution_status,
                "cost_status": cost_status,
            },
            raise_on_error=False,
        )

    return record


def usage_to_dict(record: AiUsageRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "organisation_id": str(record.organisation_id),
        "request_id": record.request_id,
        "user_id": str(record.user_id) if record.user_id else None,
        "workflow_id": record.workflow_id,
        "feature_id": record.feature_id,
        "provider": record.provider,
        "model_id": record.model_id,
        "prompt_id": record.prompt_id,
        "prompt_version": record.prompt_version,
        "provider_request_id": record.provider_request_id,
        "batch_job_id": record.batch_job_id,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "total_tokens": record.total_tokens,
        "cache_hit": record.cache_hit,
        "escalation_occurred": record.escalation_occurred,
        "escalation_reason": record.escalation_reason,
        "execution_status": record.execution_status,
        "duration_ms": record.duration_ms,
        "cost_amount": str(record.cost_amount) if record.cost_amount is not None else None,
        "cost_status": record.cost_status,
        "currency": record.currency,
        "pricing_version": record.pricing_version,
        "period_key": record.period_key,
        "executed_at": record.executed_at.isoformat() if record.executed_at else None,
    }
