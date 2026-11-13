"""F8.3 payment gateway adapters — test/Stripe architecture, no card storage."""

from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import Settings


@dataclass(frozen=True)
class CheckoutSessionResult:
    provider_session_id: str
    checkout_url: str | None
    mode: str


def create_checkout_session(
    *,
    amount: Decimal,
    currency: str,
    provider: str,
    settings: Settings,
) -> CheckoutSessionResult:
    if provider == "stripe" and settings.rent_stripe_secret_key:
        # Live Stripe integration deferred — fall back to explicit test session ids.
        sid = f"stripe_test_cs_{uuid.uuid4().hex[:24]}"
        return CheckoutSessionResult(provider_session_id=sid, checkout_url=None, mode="stripe_test")
    sid = f"test_cs_{uuid.uuid4().hex}"
    return CheckoutSessionResult(
        provider_session_id=sid,
        checkout_url=f"https://checkout.test.hmore.local/session/{sid}",
        mode="test",
    )


def verify_webhook_signature(body: bytes, signature: str | None, settings: Settings) -> None:
    secret = settings.rent_payment_webhook_signing_secret
    if not secret:
        return
    if not signature:
        raise ValueError("Missing webhook signature")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid webhook signature")
