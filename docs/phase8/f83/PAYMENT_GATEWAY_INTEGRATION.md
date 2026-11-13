# Payment Gateway Integration Guide

1. Configure `RENT_PAYMENT_WEBHOOK_SIGNING_SECRET`.
2. Enable org gateway after privacy review.
3. Create checkout via `POST /rent-payments/checkout-sessions` (tenant, test URL in dev).
4. Post signed webhook to `/rent-payments/webhooks/provider` with duplicate `provider_event_id` protection.
5. Never persist card data — use provider tokens only.
