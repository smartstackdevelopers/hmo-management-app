# Role Permission Matrix (F1.4)

Legend: **A** = allow, **D** = deny. Deny is the default for any permission not listed as allow for that role.

Source of truth: `apps/api/app/rbac/matrix.py` and `apps/api/app/rbac/permissions.py`.

## Roles

1. Super Admin (`super_admin`)
2. Organisation Admin (`organisation_admin`)
3. Landlord (`landlord`)
4. Tenant (`tenant`)
5. Support Worker (`support_worker`)
6. Maintenance & Contractors (`maintenance_contractor`)

## Platform and organisation administration

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| organisations.create | Create organisations | A | D | D | D | D | D |
| organisations.read | Read organisation directory | A | A | D | D | D | D |
| organisations.manage | Update/deactivate organisations | A | D | D | D | D | D |
| platform.settings.manage | Platform-wide settings | A | D | D | D | D | D |
| platform.monitoring.read | Platform monitoring | A | D | D | D | D | D |
| organisation.users.read | List org users | D | A | D | D | D | D |
| organisation.users.manage | Invite/update org users | D | A | D | D | D | D |
| organisation.settings.manage | Org settings | D | A | D | D | D | D |
| organisation.workflows.manage | Org workflows | D | A | D | D | D | D |
| applications.review | Review applications | D | A | D | D | D | D |
| compliance.check | Compliance checks | D | A | D | D | D | D |
| reports.read | Reports | A | A | D | D | D | D |
| audit_logs.read | Audit logs (sensitive) | A | A | D | D | D | D |
| files.read | Private org file read/download | A | A | D | D | D | D |
| files.manage | Private org file upload/delete | A | A | D | D | D | D |
| occupancy.read | Occupancy counts / survey read (sensitive) | A | A | D | D | A | D |
| occupancy.alerts.manage | Occupancy alerts / survey write | A | A | D | D | D | D |
| role_assignments.manage | Assign roles | A | A | D | D | D | D |

## Housing / landlord

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| properties.read | Read properties | D | A | A | D | A | A |
| properties.manage | Manage properties (ownership) | D | D | A | D | D | D |
| rooms.read | Read rooms | D | A | A | D | A | A |
| rooms.manage | Manage rooms | D | D | A | D | D | D |
| vacancies.manage | Manage vacancies | D | D | A | D | D | D |
| tenancies.manage | Manage tenancies | D | D | A | D | A* | D |
| inspections.manage | Inspections | D | D | A | D | D | D |
| rent_records.manage | Rent records (sensitive) | D | D | A | D | D | D |
| repairs.status.read | Repair status on own properties | D | D | A | D | D | D |

\* Support Worker tenancy manage is **assigned caseload only** — resource check required; F1.5+ data isolation still required for queries.

## Tenant self-service

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| profile.read.own | Own profile | D | D | A | A | A | A |
| profile.update.own | Update own profile | D | D | A | A | D | D |
| plans.read.own | Own plan | D | D | D | A | D | D |
| documents.read.own | Own documents | D | D | D | A | D | D |
| repairs.create.own | Report own repairs | D | D | D | A | D | D |
| complaints.create.own | Own complaints | D | D | D | A | D | D |
| services.discover | Local services | D | D | D | A | D | D |
| jobs.discover | Jobs discovery | D | D | D | A | D | D |
| training.discover | Training discovery | D | D | D | A | D | D |

## Support Worker (assigned)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| support_notes.read.assigned | Assigned notes / F2.1 oversight | D | A | D | D | A | D |
| support_notes.create.assigned | Create assigned notes | D | D | D | D | A | D |
| support_plans.manage.assigned | Assigned plans | D | D | D | D | A | D |
| visits.manage.assigned | Visits | D | D | D | D | A | D |
| tasks.manage.assigned | Tasks | D | D | D | D | A | D |
| employment_support.manage.assigned | Employment support | D | D | D | D | A | D |
| incidents.create.assigned | Incidents | D | D | D | D | A | D |

## Maintenance & Contractors (assigned)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| work_orders.read.assigned | Assigned work orders | D | D | D | D | D | A |
| work_orders.update.assigned | Update assigned jobs | D | D | D | D | D | A |
| work_orders.evidence.upload.assigned | Evidence upload | D | D | D | D | D | A |
| work_orders.schedule.assigned | Scheduling | D | D | D | D | D | A |
| work_orders.approve.assigned | Job approvals | D | A | D | D | D | A |

## Scope notes (not F1.5 completion)

| Actor | Required scope check |
| --- | --- |
| Tenant | Own user / tenant record only (`assert_same_user`) |
| Landlord | Own properties within active organisation |
| Support Worker | Assigned caseload within organisation |
| Maintenance & Contractors | Assigned work orders within organisation |
| Organisation Admin | Active organisation membership |
| Super Admin | Platform duties; org header is optional context |

## Privileged / sensitive actions

Require explicit allow in the matrix: organisation create/manage, platform settings, audit logs, compliance, occupancy, rent records, role assignment.
