# F1.7 Audit Event Architecture

Centralised, append-oriented audit logging for HMore Phase 1.

## Purpose

Record security-relevant and significant business events with trusted actor and organisation attribution. Clients cannot submit arbitrary audit rows or impersonate actors.

## Components

| Piece | Location |
| --- | --- |
| Event recorder | `apps/api/app/audit/service.py` (`record_event`, `record_event_independent`) |
| Redaction / bounds | `apps/api/app/audit/redaction.py` |
| Action names | `apps/api/app/audit/events.py` |
| Emergency logging | `apps/api/app/audit/emergency.py` |
| Read queries | `apps/api/app/audit/query.py` |
| HTTP API | `apps/api/app/api/v1/audit.py`, `emergency_access.py` |
| Migration | `20261105_1900_f17_audit_framework` |

## Schema (`audit_events`)

| Field | Notes |
| --- | --- |
| `id` | UUID primary key |
| `organisation_id` | Nullable; null = platform/system-scoped event |
| `actor_user_id` | Nullable for system events |
| `actor_role` | Role string at time of event when known |
| `action` | Canonical event name (see naming) |
| `resource_type` / `resource_id` | Target resource |
| `outcome` | `success`, `failure`, or `denied` |
| `correlation_id` | Optional request correlation |
| `source` | Origin hint (default `api`) |
| `summary` | Bounded text |
| `metadata_json` | JSONB, redacted and size-capped (4 KiB) |
| `created_at` | `timestamptz`, UTC via PostgreSQL `now()` |

## Naming conventions

Dot-separated resource verbs, for example:

- `auth.access.denied`, `auth.token.invalid`, `auth.mfa.required`
- `organisation.create`, `membership.assign`, `membership.status_change`
- `tenant.create` / `tenant.update` / `tenant.archive` (same pattern for property/room)
- `emergency_access.requested` … `revoked`
- `audit.read`

## Actor and organisation attribution

- Actor and organisation come from trusted backend context (`OrganisationContext` / `AuthorizationContext`), never from client-supplied identity fields on the audit payload.
- Organisation-scoped CRUD and membership events set `organisation_id` from the active org.
- Platform Super Admin organisation creation audits with the new organisation id.
- Null-organisation events are for platform/system cases and are only readable under explicit RLS bypass (`get_platform_context`).

## Transaction policy

1. **Default (`record_event`)**: same DB transaction as the business write. Rollback of the business operation rolls back the success audit row.
2. **Independent (`record_event_independent`)**: separate connection/commit for paths that raise (token invalid, MFA denied, permission denied) so the security event survives request rollback.
3. Recursion guard (`_RECORDING`) prevents audit failures from writing further audit rows.

## Emergency access logging

Endpoints under `/api/v1/emergency-access` create and transition `emergency_access_grants` rows and matching audit events.

**Important:** recording a request, approval, activation, expiry, or revocation does **not** grant RBAC permissions or bypass organisation isolation. Elevated break-glass access remains a future explicit control. API responses include `grants_permissions: false`.

Pending future work: binding active grants to temporary permission elevation, notification workflows, and formal approval queues.

## Access control

- Read: `audit_logs.read` (Super Admin, Organisation Admin only in the Phase 1 matrix).
- Org list/get: `GET /api/v1/audit-events` — scoped by `get_organisation_context` + RLS.
- Platform list: `GET /api/v1/audit-events/platform` — Super Admin + platform RLS bypass.
- No create/update/delete audit HTTP APIs for clients.
- Tenant / Landlord / Support Worker / Contractor cannot read audit logs.

## Sensitive data

Metadata keys matching password/token/secret/MFA/session/etc. are replaced with `[REDACTED]`. Reasons and summaries are length-bounded. Do not put credentials or unnecessary PII in metadata.

## Retention

Retention and deletion policy is a **product/legal decision not specified in Phase 1**. Operationally, application role `hmore_app` cannot `UPDATE`/`DELETE` audit rows (migration revoke). Table owners / superusers can still modify data — this is **not** claimed as tamper-proof immutable storage.

## Organisation isolation / RLS

Migration enables `FORCE ROW LEVEL SECURITY` on `audit_events` with org match or `app.rls_bypass`. Platform-null rows require bypass. Existing tenant/property/room RLS is unchanged.

## Known limitations

- Auth0 interactive login success/failure is not fully mirrored in-app (IdP-owned); backend records invalid tokens, MFA policy denials, and permission denials.
- Emergency access is logging-only; no permission elevation.
- Append-only is privilege-based for `hmore_app`, not cryptographic immutability.
- Independent audit writes require a working `DATABASE_URL` / session factory.
