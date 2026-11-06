# Document management (F2.11)

Centralised organisation-scoped **metadata** for files stored through **F1.8 private storage** (`file_metadata` + backend `upload_file` / `download_file`). The API never returns storage keys or public object URLs.

## Data model (PostgreSQL + RLS)

- `managed_document_categories` — org-configurable codes, titles, and `access_classification` (`standard` | `confidential` | `restricted`).
- `organisation_document_settings` — reminder windows (`expiry_reminder_days_*`) and optional retention review defaults; **not** statutory periods.
- `managed_documents` — reference, title, category, status (`draft` | `active` | `archived`), expiry fields, retention metadata, legal hold.
- `managed_document_versions` — each version points at one `file_metadata` row; **current** version is `managed_documents.current_version_id` (FK with defer).
- `managed_document_links` — polymorphic links (`tenant`, `property`, `housing_application`, `support_plan`, `complaint`, `maintenance`, `other`). Visibility is **not** “all tenant documents”; it requires a matching link **and** role/resource checks in `app/managed_documents/access.py`.
- Access workflow: `managed_document_access_requests`, `managed_document_access_grants` (time-bounded; revocable).
- E-sign (internal record): `managed_document_signature_requests` bound to **exact** `version_id`; completion stores JSON `signature_evidence` with disclaimer text — **not** a qualified trust-service signature.
- Reminder audit trail: `managed_document_reminder_logs` (paired with `ReminderRecord` idempotency).

## Private storage

- Uploads use `app.storage.service.upload_file` with `resource_type="managed_document_version"`.
- Downloads use `download_version` → `download_file` after permission checks.

## Expiry reminders

1. **Scan** (Celery `hmore.managed_documents.scan_expiry_reminders`, hourly): inserts `ReminderRecord` rows for `managed_document` when expiry falls in configured windows (`document_expiring_soon`, `document_expiring_urgent`, `document_expired`), **idempotent** per `(org, resource, kind, scheduled_for hour bucket)`.
2. **Dispatch** (existing `dispatch_due_reminders`): revalidates document state, sends via `LogNotificationProvider` (F2.12 defers real channels). On success for managed documents: updates `expiry_tracking`, `last_expiry_reminder_at`, writes `ManagedDocumentReminderLog`, audit `managed_document.expiry.reminder`.

## External e-sign boundary

No third-party API is wired by default. A future provider would sit behind the same service layer, still binding requests to `version_id` and preserving audit. UI and API copy state clearly that in-app completion is an **acknowledgement record** only.

## Related code

- Service: `apps/api/app/managed_documents/service.py`
- Access rules: `apps/api/app/managed_documents/access.py`
- Jobs: `apps/api/app/managed_documents/jobs.py`, `apps/api/app/workers/tasks.py`
- API: `apps/api/app/api/v1/managed_documents.py`
- Web: `apps/web/src/app/dashboard/documents/**`, `apps/web/src/lib/managedDocumentsApi.ts`
