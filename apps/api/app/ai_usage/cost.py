"""Cost calculation from verified provider/model pricing (F3.3).

Rules:
- Never invent model prices.
- Never present estimated costs as actual costs.
- If pricing is missing, cost_status is 'unavailable' and cost_amount is None.
- Cache hits that did not invoke a provider remain unavailable/zero-reservation;
  they are not billed using model pricing unless a verified cache-billing rule exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.ai_usage import AiModelPricing

MONEY_QUANT = Decimal("0.000001")
THOUSAND = Decimal("1000")


@dataclass(frozen=True, slots=True)
class CostResult:
    amount: Decimal | None
    currency: str | None
    pricing_version: str | None
    cost_status: str  # actual | estimated | unavailable
    reason: str | None = None


def _q(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def find_active_pricing(
    session: Session,
    *,
    provider: str,
    model_id: str,
    on_date: date | None = None,
) -> AiModelPricing | None:
    """Select the active pricing row effective on on_date (defaults to today UTC date)."""
    day = on_date or date.today()
    stmt = (
        select(AiModelPricing)
        .where(
            AiModelPricing.provider == provider,
            AiModelPricing.model_id == model_id,
            AiModelPricing.active.is_(True),
            AiModelPricing.effective_from <= day,
            or_(AiModelPricing.effective_to.is_(None), AiModelPricing.effective_to >= day),
        )
        .order_by(AiModelPricing.effective_from.desc())
        .limit(1)
    )
    return session.scalars(stmt).first()


def calculate_token_cost(
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    pricing: AiModelPricing | None,
    cache_hit: bool | None = None,
) -> CostResult:
    """Calculate cost from verified pricing and provider-reported token counts.

    Cache hits without a provider call: cost unavailable (not invented as zero actual).
    Missing tokens or missing pricing: unavailable.
    """
    if cache_hit:
        return CostResult(
            amount=None,
            currency=None,
            pricing_version=None,
            cost_status="unavailable",
            reason="cache_hit_no_provider_billing_rule",
        )
    if pricing is None:
        return CostResult(
            amount=None,
            currency=None,
            pricing_version=None,
            cost_status="unavailable",
            reason="pricing_missing",
        )
    if input_tokens is None or output_tokens is None:
        return CostResult(
            amount=None,
            currency=pricing.currency,
            pricing_version=pricing.pricing_version,
            cost_status="unavailable",
            reason="token_counts_unavailable",
        )

    input_cost = (Decimal(input_tokens) / THOUSAND) * pricing.input_price_per_1k_tokens
    output_cost = (Decimal(output_tokens) / THOUSAND) * pricing.output_price_per_1k_tokens
    total = _q(input_cost + output_cost)
    return CostResult(
        amount=total,
        currency=pricing.currency,
        pricing_version=pricing.pricing_version,
        cost_status="actual",
        reason=None,
    )


def resolve_cost_for_usage(
    session: Session,
    *,
    provider: str | None,
    model_id: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cache_hit: bool | None,
    on_date: date | None = None,
) -> CostResult:
    if not provider or not model_id:
        return CostResult(
            amount=None,
            currency=None,
            pricing_version=None,
            cost_status="unavailable",
            reason="provider_or_model_missing",
        )
    pricing = find_active_pricing(session, provider=provider, model_id=model_id, on_date=on_date)
    return calculate_token_cost(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        pricing=pricing,
        cache_hit=cache_hit,
    )


def upsert_pricing(session: Session, body: dict, *, actor_user_id: UUID | None = None) -> AiModelPricing:
    """Create or update a pricing version row. Historical versions are preserved by unique key."""
    from uuid import uuid4

    existing = session.scalars(
        select(AiModelPricing).where(
            AiModelPricing.provider == body["provider"],
            AiModelPricing.model_id == body["model_id"],
            AiModelPricing.pricing_version == body["pricing_version"],
        )
    ).first()
    if existing:
        existing.currency = body["currency"]
        existing.input_price_per_1k_tokens = body["input_price_per_1k_tokens"]
        existing.output_price_per_1k_tokens = body["output_price_per_1k_tokens"]
        existing.effective_from = body["effective_from"]
        existing.effective_to = body.get("effective_to")
        existing.active = body.get("active", True)
        existing.notes = body.get("notes")
        session.flush()
        return existing

    row = AiModelPricing(
        id=uuid4(),
        provider=body["provider"],
        model_id=body["model_id"],
        pricing_version=body["pricing_version"],
        currency=body["currency"],
        input_price_per_1k_tokens=body["input_price_per_1k_tokens"],
        output_price_per_1k_tokens=body["output_price_per_1k_tokens"],
        effective_from=body["effective_from"],
        effective_to=body.get("effective_to"),
        active=body.get("active", True),
        notes=body.get("notes"),
    )
    session.add(row)
    session.flush()
    _ = actor_user_id  # reserved for future audit linkage on pricing rows
    return row
