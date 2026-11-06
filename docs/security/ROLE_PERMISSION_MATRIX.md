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

## Complaints workflow (F2.7)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| complaints.manage | Manage org complaints | D | A | D | D | D | D |
| complaints.assign | Assign complaints | D | A | D | D | D | D |
| complaints.priority.manage | Change priority | D | A | D | D | D | D |
| complaints.notes.internal | View internal notes | D | A | D | D | D | D |
| complaints.notes.add | Add notes | D | A | D | D | A | D |
| complaints.deadlines.manage | Update deadlines | D | A | D | D | D | D |
| complaints.escalate | Escalate / resolve escalations | D | A | D | D | D | D |
| complaints.close | Close / reopen | D | A | D | D | D | D |
| complaints.create.own | Submit own complaint | D | D | D | A | D | D |
| complaints.read.own | Read own complaints | D | D | D | A | D | D |
| complaints.create.assigned | Create for assigned tenants | D | D | D | D | A | D |
| complaints.read.assigned | Read assigned/caseload | D | D | D | D | A | D |
| complaints.read.property | Read property-linked complaints | D | D | A | D | D | D |

Deadlines and categories are **operational**, not statutory.

## Maintenance & repairs (F2.8)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| maintenance.manage | Full org workflow | D | A | D | D | D | D |
| maintenance.create.own | Submit own requests | D | D | D | A | D | D |
| maintenance.read.own | Read own requests | D | D | D | A | D | D |
| maintenance.create.assigned | Create for assigned tenants | D | D | D | D | A | D |
| maintenance.read.assigned | Read assigned / caseload | D | D | D | D | A | A |
| maintenance.read.property | Read property-linked requests | D | D | A | D | D | D |
| maintenance.priority.manage | Change priority (audited) | D | A | D | D | D | D |
| maintenance.assign | Assign staff/contractor | D | A | D | D | D | D |
| maintenance.schedule | Schedule / reschedule visits | D | A | D | D | A | A |
| maintenance.approve | Approve / reject when required | D | A | D | D | D | D |
| maintenance.notes.add | Internal / tenant-visible notes | D | A | D | D | A | A |
| maintenance.photo.upload | Upload evidence | D | A | D | A | A | A |
| maintenance.photo.read | View maintenance evidence | D | A | A | A | A | A |
| maintenance.complete | Record completion | D | A | D | D | A | A |
| maintenance.close | Close / reopen | D | A | D | D | D | D |
| maintenance.emergency.manage | Edit gas/fire guidance | D | A | D | D | D | D |

Photo downloads for maintenance use `maintenance.photo.read` plus request-level visibility checks (not `files.read` alone).

## Tenant timeline (F2.9)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| timeline.read | Aggregated timeline (staff) | A | A | D | D | A | D |
| timeline.read.own | Own tenant timeline slice | D | D | D | A | D | D |
| timeline.read.landlord | Property-linked activity only | D | D | A | D | D | D |
| timeline.meeting.create | Schedule meetings | D | A | D | D | A | D |
| timeline.meeting.read | View meetings | D | A | D | A | A | D |
| timeline.meeting.notes.internal | Confidential meeting notes | D | A | D | D | A | D |
| timeline.appointment.manage | Create/update appointments | D | A | D | D | A | D |
| timeline.followup.manage | Create/update follow-ups | D | A | D | D | A | D |
| timeline.followup.read.assigned | List staff follow-ups (assignee-scoped for SW) | D | A | D | D | A | D |
| timeline.needs.manage | Record needs/goals (staff) | D | A | D | D | A | D |

Tenants only see **tenant follow-up** rows where `show_to_tenant=true`. Internal notes on follow-ups remain staff-only.

## Structured support plans (F2.10)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| support_plans.read | Read plans/goals/reviews (scope-enforced) | A | A | A | D | A | D |
| support_plans.read.own | Read own plans (non-internal fields) | D | D | D | A | D | D |
| support_plans.manage | Create/update plans, goals, milestones, draft reviews | A | A | D | D | A | D |
| support_plans.notes.internal | View internal plan/goal/review notes | A | A | D | D | A | D |
| support_plans.export | Generate/download progress PDF | A | A | D | D | A | D |
| support_plans.review.finalise | Finalise weekly/monthly reviews | A | A | D | D | A | D |

Landlord access is **property-scoped** (aligned with `timeline.read.landlord`). Maintenance & contractors have **no** support-plan permissions. Tenant progress notes use `show_to_tenant` for visibility.

## Housing evidence packs (F2.6)

| Permission | Purpose | SA | OA | LL | TN | SW | MC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| evidence.manage | Manage org evidence checklists | D | A | D | D | D | D |
| evidence.manage.assigned | Manage assigned application evidence | D | D | D | D | A | D |
| evidence.read.assigned | Read assigned application evidence | D | D | D | D | A | D |
| evidence.read.own | Read own application evidence | D | D | D | A | D | D |
| evidence.review | Accept/reject evidence | D | A | D | D | D | D |
| evidence.pack.generate | Generate/download evidence packs | D | A | D | D | D | D |

Support workers also receive `files.read` so linked private evidence files can be downloaded within org scope. Pack generation remains organisation-admin.

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
