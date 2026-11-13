# Contractor Verification Guide

Administrators with `contractor_marketplace.manage`:

1. Review submitted profile and linked documents.
2. Record decision via `POST /contractor-marketplace/profiles/{id}/verify` with `approve`, `reject`, `request_evidence`, or `suspend`.
3. Each decision appends `contractor_verification_reviews` and audit `contractor_marketplace.verification.recorded`.

Insurance and certification expiry should be tracked on `contractor_documents.expiry_date` — automated reminders use org `reminder_config` when enabled.
