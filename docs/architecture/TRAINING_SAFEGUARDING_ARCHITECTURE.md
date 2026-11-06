# Training & Safeguarding Reminders (F2.3)

## Scope

Staff training records with expiry tracking, and safeguarding follow-up reminders. Reuses F2.2 Celery + Redis `reminder_records` delivery. Not an LMS and not a safeguarding case-management system.

## Data model

| Table | Purpose |
| --- | --- |
| `staff_training_records` | Org-scoped training history (stored status + derived expiry status) |
| `safeguarding_reminders` | Follow-up reminders with controlled status workflow |

Delivery continues to use `reminder_records` with `resource_type` values `staff_training` and `safeguarding_reminder`.

## Configuration (not statutory)

Organisations set their own training intervals. Lead times are env-configurable:

- `REMINDER_TRAINING_EXPIRY_LEAD_DAYS` (default 30)
- `REMINDER_SAFEGUARDING_LEAD_MINUTES` (default 1440)

Do not treat defaults as regulatory requirements.

## Notification boundary

`LogNotificationProvider` only until **F2.12**. Safeguarding notification payloads use the reminder title only — never confidential case notes.

## Authorisation

- Org Admin: `training.records.manage`, `safeguarding.reminders.manage`
- Support Worker: own training read; assigned safeguarding reminders
- Landlords / Tenants / Maintenance: no access to these APIs

## APIs

`/api/v1/training`, `/api/v1/safeguarding-reminders`
