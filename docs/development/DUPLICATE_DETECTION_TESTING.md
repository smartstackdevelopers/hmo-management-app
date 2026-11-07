# F3.11 — Duplicate Detection Testing

## Unit (no DB)

```powershell
cd apps/api
python -m pytest tests/test_f311_duplicate_detection_unit.py -q
```

Covers normalisation, match-hit ordering, and human-review notice text. No AI provider.

## PostgreSQL integration

Requires the shared `postgres` pytest marker and migrated test database (head includes `20261107_2500_f311`).

```powershell
cd apps/api
python -m pytest tests/test_f311_duplicate_detection.py -m postgres -q
```

Real DB coverage includes:

- Exact email duplicate detection without AI (`used_ai=false`)
- Name-only hits stay `possible`
- Source tenants/applications/files never mutated on detect or review
- RBAC denial for Support Worker
- Cross-organisation run isolation
- Housing and file checksum duplicates
- Sticky dismiss (false positive not re-created)
- Record-scoped candidate limiting
- Audit events

## Frontend helpers

```powershell
cd apps/web
npx playwright test e2e/duplicate-detection.spec.ts
```

## Safety assertions

Detection and review paths snapshot source-record counts and refuse if counts change. API payloads set `identity_proven`, `auto_merged`, and `auto_deleted` to false.
