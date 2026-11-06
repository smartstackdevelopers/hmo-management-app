# Tenant timeline, meetings, appointments, and follow-ups (F2.9)

## Overview

F2.9 adds organisation-scoped records for **meetings**, **appointments**, **tenant follow-ups**, and structured **needs/goals**, plus an **aggregated tenant timeline** that points at existing modules (daily logs, handovers, visits, tasks, housing, complaints, maintenance, incidents).

The timeline **does not clone** source bodies. Each item includes `resource_type`, `resource_id`, and `detail_api_path`; the client must call the underlying API, which re-applies permission checks. Items may set `can_view=false` when the row exists in aggregate but the current principal would be denied on the detail endpoint.

## Data sources

| Activity type | Source |
| --- | --- |
| `daily_log`, `handover` | F2.1 (`daily_logs`, `handovers`) |
| `tenant_visit`, `operational_task` | F2.2 (`tenant_visits`, `operational_tasks`) |
| `housing_application`, `housing_status` | F2.5 |
| `complaint`, `complaint_event` | F2.7 |
| `maintenance`, `maintenance_event` | F2.8 |
| `incident` | F2.4 |
| `meeting`, `appointment`, `tenant_follow_up`, `need`, `goal` | New tables in `tenant_timeline` models |

## API

Base path: `/api/v1/tenants/{tenant_id}/timeline`

- `GET /` — paginated timeline (query: `sort`, `activity_type`, `date_from`, `date_to`, `assigned_user_id`, `q`)
- Meetings: `POST /meetings`, `GET /meetings`, `GET /meetings/{id}`, `PATCH /meetings/{id}`, `POST .../complete`, `POST .../cancel`
- Appointments: `POST /appointments`, `GET`, `GET /{id}`, `PATCH`, `POST .../cancel`
- Follow-ups: `POST /follow-ups`, `GET`, `GET /{id}`, `PATCH`, `POST .../complete`
- Needs/goals: `POST /needs-goals`, `GET`, `GET /{id}`, `PATCH`

## RBAC

Permissions are defined in `apps/api/app/rbac/permissions.py` and wired in `apps/api/app/rbac/matrix.py`.

- **Timeline read**: `timeline.read` (staff), `timeline.read.own` (tenant), `timeline.read.landlord` (landlord — property-linked activity only).
- **Meetings**: `timeline.meeting.create`, `timeline.meeting.read`, `timeline.meeting.notes.internal`.
- **Appointments**: `timeline.appointment.manage`.
- **Follow-ups**: `timeline.followup.manage`, `timeline.followup.read.assigned` (plus tenant self-read where exposed).
- **Needs/goals**: `timeline.needs.manage`; read uses `timeline.read.own` for tenants and `timeline.needs.manage` for staff on list/detail.

Maintenance contractors do not receive timeline permissions by default.

## Organisation isolation

All F2.9 tables include `organisation_id` and use the same RLS policy pattern as F2.8 (`hmore_org_isolation`).

## Audit

Actions are recorded in `apps/api/app/audit/events.py` (`tenant_timeline.read`, `tenant_meeting.*`, `tenant_appointment.*`, `tenant_follow_up.*`, `tenant_need_goal.*`).

## Migrations

`apps/api/migrations/versions/20261106_2000_f29_tenant_timeline.py` — creates tables and enables RLS.

## Testing

- Backend: `apps/api/tests/test_f29_tenant_timeline.py` (marked `@pytest.mark.postgres` — requires `TEST_DATABASE_URL` or `DATABASE_URL`).
- Frontend: `apps/web/e2e/timeline.spec.ts` — badge class mapping for activity types.

Run API tests from `apps/api` after migrations:

```bash
pytest tests/test_f29_tenant_timeline.py -m postgres -v
```
