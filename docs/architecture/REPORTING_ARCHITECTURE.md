# F2.14 Reporting and dashboards

## API

Base: `/api/v1/reports`

- `GET /dashboard` — permission-filtered sections (housing, complaints, caseload)
- `GET /housing/summary`, `/housing/rows`
- `GET /complaints/summary`, `/complaints/rows`
- `GET /caseload/summary`, `/caseload/rows`
- `GET /export/{housing|complaints|caseload}/{csv|pdf|xlsx}`

## Metric definitions

- **Housing**: counts by `housing_applications.status`; date filter on `created_at`, `submitted_at`, or `updated_at`.
- **Complaints**: `overdue_operational` uses `response_due_at` vs now for open statuses — organisation operational target, not statutory.
- **Caseload**: active `case_assignments`, open `tenant_follow_ups`, pending `handovers`, upcoming `tenant_visits`.

## Exports

- CSV: UTF-8 BOM, formula injection neutralisation on cell values.
- PDF: `build_simple_pdf` text layout (not council-certified).
- Excel: minimal Office Open XML `.xlsx` (zip+xml) without confidential note columns.

## RBAC

Granular permissions `reports.*` plus legacy `reports.read` for Organisation Admins.
