# F8.5 Contractor Marketplace Architecture

## Scope

Optional add-on linking approved contractors to `maintenance_requests`, `properties`, and existing work-order patterns. Does **not** replace F2.8 maintenance management.

## Components

- `organisation_contractor_marketplace_settings` — platform + org gates
- `contractor_directory_profiles` — registration and verification lifecycle
- `contractor_service_categories` — 10 system categories per org
- `marketplace_jobs` — job requests (optional `maintenance_request_id`)
- `marketplace_quotations` — manual approval required
- `marketplace_job_completions` — evidence + landlord/staff review
- `contractor_documents` — private file refs via `file_metadata`
- `marketplace_contractor_feedback` — moderation `pending` until rules approved

## API

`/api/v1/contractor-marketplace`

## Platform gate

`CONTRACTOR_MARKETPLACE_GLOBAL_ENABLED=false` by default.

## Integration

- Maintenance: optional link on job create
- Notifications: `ReminderMessage` via `ops/notifications`
- RBAC: Maintenance & Contractors role uses workspace permissions (no seventh core role)
