# F8.3 Rent & Tenancy Payments Architecture

## Relationship to core

- **Source of truth for rent amounts:** existing `rent_records` (F6.1) — not duplicated.
- **Payment overlay:** `rent_obligation_extensions` + `rent_payments` tables link 1:n to each rent record.
- **Finance link:** optional future `finance_records.rent_record_id` unchanged.

## Gateway

- Provider modes: `test`, `stripe`, `pending_approval`.
- Checkout sessions + signed webhooks; no PAN/CVV storage.
- Live Stripe only when `RENT_STRIPE_SECRET_KEY` and organisational approval are in place.

## Verification model

| Source | `verified` | Receipt |
|--------|------------|---------|
| Manual admin entry | false until verify endpoint | After verify |
| Gateway webhook | true on success event | After webhook |

## Platform gate

`RENT_PAYMENTS_GLOBAL_ENABLED=false` default; org `organisation_rent_payment_settings.enabled`.

## API

Prefix `/api/v1/rent-payments` — settings, dashboard, obligations, payments, checkout, disputes, arrears plans, receipts PDF, webhooks.
