# F6.1 Landlord Enterprise Tools

## Scope

- Enterprise landlord dashboard (live aggregates)
- Portfolio analytics with filters
- Rent records ledger (no payment gateway)
- Property inspections at scale
- Repair oversight over owned properties

## Ownership

Uses existing `properties.landlord_user_id`. Landlords only see their own (or unassigned) properties.

## Data

- Reuses `properties`, `rooms`, `tenants`, `maintenance_requests`
- Adds `rent_records`, `property_inspections` (Alembic `20261111_3900_f61`)

## API

`/api/v1/landlord-enterprise/*` — dashboard, portfolio, rent-records, inspections, repairs

## Permissions

Existing: `properties.*`, `rent_records.manage`, `inspections.manage`, `repairs.status.read`, `maintenance.read.property`
