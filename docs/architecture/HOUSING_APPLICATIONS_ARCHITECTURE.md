# Housing Applications, Waiting Lists & Approvals (F2.5)

## Scope

Organisation-scoped housing applications, controlled status workflow, approval decisions with separation of duties, and a FIFO waiting list. Not an allocation engine and not F2.13 custom workflows.

## Status transitions

`draft → submitted → under_review → information_required | approved | rejected → closed`

Also: `draft|submitted|under_review|information_required → withdrawn`; `rejected → under_review` (reopen for review).

Invalid transitions are rejected by the backend.

## Waiting list

- Positions are allocated per organisation with row locks (`SELECT … FOR UPDATE`).
- Ordering is FIFO by position; priority is an informational label unless org policy defines otherwise.
- **Waiting-list position does not guarantee accommodation allocation.**

## Separation of duties

The user who created an application cannot record its approve/reject decision.

## Permissions

| Role | Access |
| --- | --- |
| Organisation Admin | Manage / review applications; manage waiting list |
| Support Worker | Create/read for assigned caseload tenants; read waiting list |
| Tenant | Create/read own linked tenant applications |
| Landlord / Maintenance | No housing application access by default |

## APIs

`/api/v1/housing-applications`, `/api/v1/waiting-list`
