# Communication platform (F2.12)

## Overview

The communication platform provides:

- In-app messaging (`communication_messages` + recipients).
- Channel delivery with an explicit status machine (`communication_deliveries`) — outbox rows created before provider calls.
- Organisation-scoped reminders (`communication_scheduled_reminders`) processed by Celery (`hmore.communication.dispatch_scheduled_reminders`).
- Emergency-style announcements (`communication_announcements`) with audience resolution and synchronous in-app fan-out (system messages) plus optional email/SMS via the same delivery path.
- Recipient preferences (`communication_user_preferences`) and audited changes.
- Templates (`communication_templates`) with allow-listed placeholders (see `app/communication/template_render.py`).
- Translation records (`communication_translations`) — originals are never overwritten; provider defaults to a **test echo** until a real API is wired.

Workflow modules (appointments, complaints, documents, …) continue to use `reminder_records` (F2.2). Dispatch now writes `communication_deliveries` with idempotency `reminder_record:{id}` and channels default to `in_app`.

## Delivery status semantics

| Status | Meaning |
| --- | --- |
| `created` | Outbox row inserted |
| `queued` | Marked for worker / synchronous dispatch |
| `attempted` | Provider call started |
| `provider_accepted` | SMTP accepted / Twilio SID returned — **not** proof of inbox/handset delivery |
| `sending` | Push worker started an attempt. Not handset receipt. |
| `sent` | Expo push ticket status was `ok`. Not handset receipt. See `PUSH_NOTIFICATIONS_ARCHITECTURE.md`. |
| `delivered` | In-app content stored for retrieval |
| `failed` | Terminal failure |
| `retrying` | Reserved |
| `cancelled` | Reserved |

## Provider configuration

See `docs/development/ENVIRONMENT_VARIABLES.md` for F2.12 variables.

- **Email**: default `EMAIL_ADAPTER_MODE=test` (no network). Set `EMAIL_ADAPTER_MODE=smtp` and SMTP env vars for real SMTP.
- **SMS**: default `SMS_ADAPTER_MODE=test`. Set Twilio env vars + `SMS_ADAPTER_MODE=twilio` for real SMS.
- **Translation**: test echo only until an approved API is integrated.

## RBAC

New permissions in `communication.*` — see `docs/security/ROLE_PERMISSION_MATRIX.md` (regenerate from `apps/api/app/rbac/matrix.py`).

Emergency announcement **publish** is limited to Organisation Admin and Super Admin at the service layer, even when the permission is present.
